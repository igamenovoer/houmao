"""Revision-checked existing-account online attachment without body lifecycle effects."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from houmao.agents.mailbox_runtime_models import StalwartMailboxResolvedConfig
from houmao.agents.mailbox_runtime_support import (
    mailboxes_resolved_config_from_payload,
    safe_registry_mailboxes_projection,
    stalwart_discovery_url,
)
from houmao.agents.realm_controller.gateway_storage import gateway_paths_from_session_root
from houmao.agents.realm_controller.manifest import (
    MailboxBindingConflict,
    load_session_manifest,
    mutate_session_mailbox_binding,
)
from houmao.agents.realm_controller.registry_models import ManagedAgentRegistryRecordV3
from houmao.agents.realm_controller.registry_storage import (
    load_managed_agent_record_by_agent_id,
    publish_managed_agent_record,
)
from houmao.mailbox.notifier_admission import cancel_pending_mail_reminders
from houmao.mailbox.online_authority import OnlineConnectionAuthority
from houmao.mailbox.online_models import (
    OnlineAttachRequest,
    OnlineAuthorityContext,
    OnlineBindingError,
    OnlineBindingStatus,
    OnlineControlRequest,
)
from houmao.mailbox.online_secrets import prepare_online_credential, retire_online_credential
from houmao.mailbox.stalwart import (
    StalwartConnectionPolicyError,
    StalwartError,
    StalwartJmapClient,
    StalwartReadinessError,
    is_plaintext_jmap_origin,
    jmap_origin,
    normalize_jmap_origins,
)
from houmao.mailbox.stalwart_models import ValidatedJmapBinding


def _pin_binding(
    config: StalwartMailboxResolvedConfig, validated: ValidatedJmapBinding
) -> StalwartMailboxResolvedConfig:
    """Record the verified provider scope with the candidate revision."""
    return replace(
        config,
        account_id=validated.account_id,
        identity_id=validated.identity_id,
        api_origin=jmap_origin(validated.api_url),
    )


class OnlineBindingService:
    """Own candidate validation and coordinated online configuration changes."""

    def __init__(self) -> None:
        self.m_authority: OnlineConnectionAuthority

    @classmethod
    def from_context(cls, context: OnlineAuthorityContext) -> OnlineBindingService:
        """Create a pure local service bound to explicit runtime authority."""

        instance = cls()
        instance.m_authority = OnlineConnectionAuthority.from_context(context)
        return instance

    def status(
        self, *, committed: bool = False, warnings: list[str] | None = None
    ) -> OnlineBindingStatus:
        """Return safe configured identity without passwords or protected references."""

        slot, binding = self.m_authority.snapshot()
        state = self.m_authority.state()
        approvals = list(binding.trusted_jmap_origins) if binding else []
        details = list(warnings or [])
        if any(is_plaintext_jmap_origin(origin) for origin in approvals):
            details.append("Approved plaintext HTTP exposes mailbox credentials in transit.")
        discovery_origin = api_origin = None
        if binding is not None:
            try:
                discovery_origin = jmap_origin(binding.jmap_url)
                api_origin = binding.pinned_api_origin
            except StalwartError:
                details.append("Configured JMAP discovery endpoint is invalid.")
        available = (
            binding is not None
            and binding.account_id is not None
            and binding.credential_file is not None
            and binding.credential_file.is_file()
        )
        return OnlineBindingStatus(
            agent_id=self.m_authority.context.agent_id,
            revision=slot.revision,
            binding_id=binding.binding_id if binding else None,
            address=binding.address if binding else None,
            provider="stalwart" if binding else None,
            account_id=binding.account_id if binding else None,
            identity_id=binding.identity_id if binding else None,
            discovery_origin=discovery_origin,
            api_origin=api_origin,
            trusted_jmap_origins=approvals,
            epoch_id=state.get("epoch_id"),
            state="retiring"
            if state.get("closing")
            else "absent"
            if binding is None
            else "configured"
            if available
            else "degraded",
            available=available,
            committed=committed,
            warnings=details,
        )

    def _validate(
        self, config: StalwartMailboxResolvedConfig, timeout: float
    ) -> ValidatedJmapBinding:
        """Validate exact account/address through mailbox access without management calls."""

        if config.credential_file is None:
            raise OnlineBindingError(
                "credential_source_invalid", "A private credential snapshot is required"
            )
        try:
            client = StalwartJmapClient(
                jmap_url=config.jmap_url,
                login_identity=config.login_identity,
                credential_file=config.credential_file,
                timeout_seconds=timeout,
                sender_address=config.address,
                account_id=config.account_id,
                identity_id=config.identity_id,
                allowed_api_origins=config.trusted_jmap_origins,
                api_origin=config.pinned_api_origin,
            )
            return client.validate_binding(sender_address=config.address)
        except (StalwartConnectionPolicyError, StalwartReadinessError) as exc:
            raise OnlineBindingError(exc.code, str(exc)) from None
        except (StalwartError, OSError, ValueError):
            raise OnlineBindingError(
                "candidate_validation_failed",
                "Online account authentication, address, or capability validation failed",
            ) from None

    def _commit(
        self,
        config: StalwartMailboxResolvedConfig | None,
        *,
        expected: str,
        timeout: float,
        reconnect: bool = False,
    ) -> OnlineBindingStatus:
        """Drain old managed I/O before committing, retaining confirmed outcomes on projection errors."""

        authority = self.m_authority
        context = authority.context
        _, old = authority.snapshot()
        committed = False
        try:
            with authority.control(expected_revision=expected, timeout_seconds=timeout):
                if not reconnect:
                    mutate_session_mailbox_binding(
                        context.manifest_path,
                        channel="online",
                        expected_revision=expected,
                        binding=config,
                        agent_id=context.agent_id,
                        session_id=context.session_id,
                    )
                    committed = True
                authority.advance_epoch()
                committed = True
                if old is not None and not reconnect:
                    cancel_pending_mail_reminders(
                        gateway_paths_from_session_root(
                            session_root=context.manifest_path.resolve().parent
                        ).queue_path,
                        agent_id=context.agent_id,
                        channel="online",
                        binding_id=old.binding_id,
                        revision=expected,
                    )
                self._publish_projection()
        except MailboxBindingConflict:
            raise OnlineBindingError(
                "mail_binding_conflict", "Online slot revision changed"
            ) from None
        except Exception:
            if committed:
                return self.status(
                    committed=True,
                    warnings=["Binding committed; connection activation requires reconciliation"],
                )
            raise
        if old is not None and (config is None or old.credential_ref != config.credential_ref):
            try:
                retire_online_credential(
                    old.credential_ref,
                    session_root=context.manifest_path.resolve().parent,
                    protected_source=config.credential_source_ref
                    if config
                    else old.credential_source_ref,
                )
            except OSError:
                return self.status(
                    committed=True,
                    warnings=["Binding committed; retired private copy requires cleanup"],
                )
        return self.status(committed=True)

    def _publish_projection(self) -> None:
        """Refresh an existing discovery hint without creating a new agent record."""

        context = self.m_authority.context
        record = load_managed_agent_record_by_agent_id(context.agent_id)
        if record is None or record.runtime.manifest_path != str(context.manifest_path.resolve()):
            return
        handle = load_session_manifest(context.manifest_path)
        mailboxes = mailboxes_resolved_config_from_payload(
            handle.payload["launch_plan"]["mailboxes"], manifest_path=handle.path
        )
        payload = record.model_dump(mode="json")
        payload["mailboxes"] = safe_registry_mailboxes_projection(mailboxes)
        payload["canonical_mail_identity"] = mailboxes.canonical_mail_identity
        publish_managed_agent_record(ManagedAgentRegistryRecordV3.model_validate(payload))

    def attach(self, request: OnlineAttachRequest) -> OnlineBindingStatus:
        """Validate a private existing account and explicitly replace only when requested."""

        slot, old = self.m_authority.snapshot()
        if slot.revision != request.expected_revision:
            raise OnlineBindingError("mail_binding_conflict", "Online slot revision changed")
        try:
            url = (
                request.jmap_url
                if request.jmap_url is not None
                else stalwart_discovery_url(request.base_url or "")
            )
            origins = normalize_jmap_origins(request.trusted_jmap_origins)
        except StalwartConnectionPolicyError as exc:
            raise OnlineBindingError(exc.code, str(exc)) from None
        except ValueError:
            raise OnlineBindingError("endpoint_invalid", "JMAP base URL is invalid.") from None
        source = Path(request.credential_source_ref).expanduser().resolve()
        reference, credential = prepare_online_credential(
            source, session_root=self.m_authority.context.manifest_path.parent
        )
        candidate = StalwartMailboxResolvedConfig(
            transport="stalwart",
            principal_id=self.m_authority.context.agent_id,
            agent_id=self.m_authority.context.agent_id,
            binding_id=old.binding_id if old else uuid4().hex,
            address=request.address,
            jmap_url=url,
            management_url=None,
            login_identity=request.login_identity,
            credential_ref=reference,
            credential_file=credential,
            credential_source_ref=str(source),
            bindings_version=slot.revision,
            account_id=request.account_id,
            trusted_jmap_origins=origins,
        )
        try:
            validated = self._validate(candidate, request.timeout_seconds)
            candidate = _pin_binding(candidate, validated)
            if old is not None:
                if old.account_id is None and not request.replace:
                    old = _pin_binding(old, self._validate(old, request.timeout_seconds))
                same = (old.jmap_url.rstrip("/"), old.account_id, old.pinned_api_origin) == (
                    candidate.jmap_url.rstrip("/"),
                    candidate.account_id,
                    candidate.api_origin,
                )
                if not same:
                    if not request.replace:
                        raise OnlineBindingError(
                            "replacement_required",
                            "A different online account or JMAP endpoint requires --replace.",
                        )
                    candidate = replace(candidate, binding_id=uuid4().hex)
            return self._commit(candidate, expected=slot.revision, timeout=request.timeout_seconds)
        except Exception:
            retire_online_credential(
                reference,
                session_root=self.m_authority.context.manifest_path.parent,
                protected_source=str(source),
            )
            raise

    def refresh(self, request: OnlineControlRequest) -> OnlineBindingStatus:
        """Validate the same account using a new immutable credential revision."""

        slot, old = self.m_authority.snapshot()
        if old is None:
            raise OnlineBindingError("online_not_configured", "No online binding is configured")
        if slot.revision != request.expected_revision:
            raise OnlineBindingError("mail_binding_conflict", "Online slot revision changed")
        source = request.credential_source_ref or old.credential_source_ref
        if source is None:
            raise OnlineBindingError(
                "credential_source_required",
                "Refresh requires an explicitly selected private credential source",
            )
        reference, credential = prepare_online_credential(
            Path(source), session_root=self.m_authority.context.manifest_path.parent
        )
        candidate = replace(
            old,
            credential_ref=reference,
            credential_file=credential,
            credential_source_ref=str(Path(source).expanduser().resolve()),
        )
        try:
            validated = self._validate(candidate, request.timeout_seconds)
            if old.account_id is not None and validated.account_id != old.account_id:
                raise OnlineBindingError(
                    "account_mismatch", "Credential refresh cannot select another account"
                )
            candidate = _pin_binding(candidate, validated)
            return self._commit(candidate, expected=slot.revision, timeout=request.timeout_seconds)
        except Exception:
            retire_online_credential(
                reference,
                session_root=self.m_authority.context.manifest_path.parent,
                protected_source=source,
            )
            raise

    def reconnect(self, request: OnlineControlRequest) -> OnlineBindingStatus:
        """Revalidate immutable current credentials and replace only the connection epoch."""

        self._reject_unused_source(request)
        slot, old = self.m_authority.snapshot()
        if old is None:
            raise OnlineBindingError("online_not_configured", "No online binding is configured")
        if slot.revision != request.expected_revision:
            raise OnlineBindingError("mail_binding_conflict", "Online slot revision changed")
        if old.account_id is None or old.identity_id is None:
            self.adopt(expected_binding_id=old.binding_id, timeout_seconds=request.timeout_seconds)
            return self.status(committed=True)
        self._validate(old, request.timeout_seconds)
        return self._commit(
            old, expected=slot.revision, timeout=request.timeout_seconds, reconnect=True
        )

    def detach(self, request: OnlineControlRequest) -> OnlineBindingStatus:
        """Remove online configuration while retaining provider mail and source credentials."""

        self._reject_unused_source(request)
        return self._commit(
            None, expected=request.expected_revision, timeout=request.timeout_seconds
        )

    def adopt(self, *, expected_binding_id: str, timeout_seconds: float) -> None:
        """Pin an existing foundation binding on its first validated connection."""

        slot, binding = self.m_authority.snapshot()
        if binding is None or binding.binding_id != expected_binding_id:
            raise OnlineBindingError("mail_binding_conflict", "Online binding changed")
        if binding.account_id is not None and binding.identity_id is not None:
            return
        if binding.credential_file is None:
            raise OnlineBindingError(
                "online_credentials_unavailable", "Online credential snapshot is unavailable"
            )
        reference, credential = prepare_online_credential(
            binding.credential_file, session_root=self.m_authority.context.manifest_path.parent
        )
        candidate = replace(binding, credential_ref=reference, credential_file=credential)
        try:
            validated = self._validate(candidate, timeout_seconds)
            candidate = _pin_binding(candidate, validated)
            self._commit(candidate, expected=slot.revision, timeout=timeout_seconds)
        except Exception:
            retire_online_credential(
                reference, session_root=self.m_authority.context.manifest_path.parent
            )
            raise

    @staticmethod
    def _reject_unused_source(request: OnlineControlRequest) -> None:
        """Reject source changes on controls that keep existing credential material."""

        if request.credential_source_ref is not None:
            raise OnlineBindingError(
                "unexpected_credential_source", "Only refresh accepts a credential source"
            )
