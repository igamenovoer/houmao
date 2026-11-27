"""Bounded OpenSSH SSHSIG framing for gateway request proof."""

from __future__ import annotations

import base64
import binascii
import hashlib
import struct
from typing import TypeAlias

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa, utils

SSHSIG_NAMESPACE = "houmao-gateway-access-v1"
WEB_LOGIN_NAMESPACE = "houmao-web-entry-login-v1"
TERMINAL_LOGIN_NAMESPACE = "houmao-terminal-admin-login-v1"
MAX_SIGNATURE_HEADER = 8192
_MAGIC = b"SSHSIG"
_PREFIX = _MAGIC + struct.pack(">I", 1)
_BEGIN = b"-----BEGIN SSH SIGNATURE-----"
_END = b"-----END SSH SIGNATURE-----"
_DIGESTS = {b"sha256": hashlib.sha256, b"sha512": hashlib.sha512}
_EC_HASHES: dict[str, type[hashes.HashAlgorithm]] = {
    "secp256r1": hashes.SHA256,
    "secp384r1": hashes.SHA384,
    "secp521r1": hashes.SHA512,
}
_RSA_HASHES: dict[bytes, type[hashes.HashAlgorithm]] = {
    b"rsa-sha2-256": hashes.SHA256,
    b"rsa-sha2-512": hashes.SHA512,
}
_PUBLIC_KINDS = {
    "ssh-ed25519",
    "ssh-rsa",
    "ecdsa-sha2-nistp256",
    "ecdsa-sha2-nistp384",
    "ecdsa-sha2-nistp521",
}
PublicKey: TypeAlias = ed25519.Ed25519PublicKey | rsa.RSAPublicKey | ec.EllipticCurvePublicKey
PrivateKey: TypeAlias = ed25519.Ed25519PrivateKey | rsa.RSAPrivateKey | ec.EllipticCurvePrivateKey


def load_public_key(value: str) -> PublicKey:
    """Load one supported OpenSSH public key and reject ambiguous line syntax."""

    try:
        if any(ord(char) < 32 and char != "\t" for char in value) or len(value) > 4096:
            raise ValueError
        kind, encoded, *_comment = value.split(maxsplit=2)
        if kind not in _PUBLIC_KINDS:
            raise ValueError
        raw_key = f"{kind} {encoded}".encode("ascii")
        key = serialization.load_ssh_public_key(raw_key)
        if (
            key.public_bytes(serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH)
            != raw_key
        ):
            raise ValueError
        if isinstance(key, ed25519.Ed25519PublicKey):
            return key
        if isinstance(key, rsa.RSAPublicKey) and 2048 <= key.key_size <= 8192:
            return key
        if isinstance(key, ec.EllipticCurvePublicKey) and key.curve.name in _EC_HASHES:
            return key
    except (ValueError, TypeError, UnicodeError, UnsupportedAlgorithm):
        pass
    raise ValueError("invalid or unsupported OpenSSH public key")


def load_private_key(payload: bytes) -> PrivateKey:
    """Deserialize an unencrypted file-based signer of a supported key type."""

    try:
        key = serialization.load_ssh_private_key(payload, password=None)
        if isinstance(key, ed25519.Ed25519PrivateKey):
            return key
        if isinstance(key, rsa.RSAPrivateKey) and 2048 <= key.key_size <= 8192:
            return key
        if isinstance(key, ec.EllipticCurvePrivateKey) and key.curve.name in _EC_HASHES:
            return key
    except (ValueError, TypeError, UnsupportedAlgorithm):
        pass
    raise ValueError("invalid or unsupported OpenSSH private key")


def public_key_text(key: PublicKey) -> str:
    """Return the canonical OpenSSH public key without a comment."""

    return key.public_bytes(
        serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH
    ).decode("ascii")


def key_fingerprint(value: str) -> str:
    """Return the OpenSSH SHA256 fingerprint of a canonical public key."""

    _, encoded = value.split()
    return _fingerprint_blob(base64.b64decode(encoded))


def _fingerprint_blob(blob: bytes) -> str:
    """Hash the SSH wire-format key shared by the roster and proof."""

    encoded_digest = base64.b64encode(hashlib.sha256(blob).digest()).decode("ascii").rstrip("=")
    # Use the URL-safe alphabet so the identifier fits a single path segment.
    return "SHA256:" + encoded_digest.replace("+", "-").replace("/", "_")


def sign_sshsig(key: PrivateKey, message: bytes, *, namespace: str = SSHSIG_NAMESPACE) -> bytes:
    """Sign a message in standard OpenSSH armor using SHA-512 for its digest."""

    kind, public = public_key_text(key.public_key()).encode("ascii").split()
    scope = _scope(namespace.encode("ascii"), b"", b"sha512")
    signed = _signed_bytes(scope, b"sha512", message)
    if isinstance(key, ed25519.Ed25519PrivateKey):
        signature = key.sign(signed)
    elif isinstance(key, rsa.RSAPrivateKey):
        kind = b"rsa-sha2-512"
        signature = key.sign(signed, padding.PKCS1v15(), hashes.SHA512())
    else:
        der = key.sign(signed, ec.ECDSA(_EC_HASHES[key.curve.name]()))
        r, s = utils.decode_dss_signature(der)
        signature = _fields(_mpint(r), _mpint(s))
    framed = _PREFIX + _fields(base64.b64decode(public)) + scope + _fields(_fields(kind, signature))
    encoded = base64.b64encode(framed)
    lines = [encoded[offset : offset + 76] for offset in range(0, len(encoded), 76)]
    return b"\n".join([_BEGIN, *lines, _END, b""])


def sshsig_header(armor: bytes) -> str:
    """Convert one standard SSHSIG armor document to its one-line HTTP value."""

    if len(armor) > MAX_SIGNATURE_HEADER + 512:
        raise ValueError("invalid SSHSIG armor")
    lines = armor.splitlines()
    if len(lines) < 3 or lines[0] != _BEGIN or lines[-1] != _END:
        raise ValueError("invalid SSHSIG armor")
    encoded = b"".join(lines[1:-1])
    _decode_header(encoded)
    return encoded.decode("ascii")


def sshsig_key_id(proof: str) -> str:
    """Identify an untrusted candidate key from a bounded proof envelope."""

    public, _, _, _, _ = _parse_proof(proof)
    return _fingerprint_blob(public)


def verify_sshsig(
    public_key: str, message: bytes, proof: str, *, namespace: str = SSHSIG_NAMESPACE
) -> bool:
    """Verify an SSHSIG envelope against one selected key and protocol namespace."""

    try:
        public, signed_namespace, reserved, digest, signature = _parse_proof(proof)
        key = load_public_key(public_key)
        expected_kind, encoded = public_key_text(key).encode("ascii").split()
        if public != base64.b64decode(encoded) or signed_namespace != namespace.encode("ascii"):
            return False
        if digest not in _DIGESTS:
            return False
        kind, raw = _read_fields(signature, 2)
        signed = _signed_bytes(_scope(signed_namespace, reserved, digest), digest, message)
        if isinstance(key, rsa.RSAPublicKey):
            if kind not in _RSA_HASHES:
                return False
            key.verify(raw, signed, padding.PKCS1v15(), _RSA_HASHES[kind]())
        elif kind != expected_kind:
            return False
        elif isinstance(key, ed25519.Ed25519PublicKey):
            key.verify(raw, signed)
        else:
            r, s = _read_fields(raw, 2)
            der = utils.encode_dss_signature(_positive_mpint(r), _positive_mpint(s))
            key.verify(der, signed, ec.ECDSA(_EC_HASHES[key.curve.name]()))
    except (InvalidSignature, UnsupportedAlgorithm, ValueError, TypeError, UnicodeError):
        return False
    return True


def _parse_proof(proof: str) -> list[bytes]:
    """Read the public key and signature fields of a version-one envelope."""

    blob = _decode_header(proof.encode("ascii"))
    if not blob.startswith(_PREFIX):
        raise ValueError("invalid SSHSIG envelope")
    return _read_fields(blob[len(_PREFIX) :], 5)


def _decode_header(encoded: bytes) -> bytes:
    """Decode a bounded ASCII proof value."""

    if not encoded or len(encoded) > MAX_SIGNATURE_HEADER:
        raise ValueError("invalid SSHSIG envelope")
    try:
        return base64.b64decode(encoded, validate=True)
    except binascii.Error:
        raise ValueError("invalid SSHSIG envelope") from None


def _read_fields(blob: bytes, count: int) -> list[bytes]:
    """Parse a fixed number of bounded SSH strings and detect trailing data."""

    offset = 0
    fields = []
    for _ in range(count):
        if len(blob) - offset < 4:
            raise ValueError("truncated SSH string")
        size = struct.unpack_from(">I", blob, offset)[0]
        offset += 4
        if size > len(blob) - offset:
            raise ValueError("truncated SSH string")
        fields.append(blob[offset : offset + size])
        offset += size
    if offset != len(blob):
        raise ValueError("unexpected SSH signature data")
    return fields


def _fields(*values: bytes) -> bytes:
    """Frame byte strings as specified by the SSH binary format."""

    return b"".join(struct.pack(">I", len(value)) + value for value in values)


def _scope(namespace: bytes, reserved: bytes, digest: bytes) -> bytes:
    """Encode the SSHSIG scope and hash algorithm."""

    return _fields(namespace, reserved, digest)


def _signed_bytes(scope: bytes, digest: bytes, message: bytes) -> bytes:
    """Build the bytes covered by the SSH signature."""

    return _MAGIC + scope + _fields(_DIGESTS[digest](message).digest())


def _mpint(value: int) -> bytes:
    """Represent a positive ECDSA coordinate as an SSH mpint."""

    return value.to_bytes((value.bit_length() + 8) // 8, "big")


def _positive_mpint(value: bytes) -> int:
    """Decode a canonical positive ECDSA coordinate."""

    if not value or len(value) > 67:
        raise ValueError("invalid SSH signature coordinate")
    parsed = int.from_bytes(value, "big", signed=True)
    if parsed <= 0 or _mpint(parsed) != value:
        raise ValueError("invalid SSH signature coordinate")
    return parsed
