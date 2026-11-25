Houmao 3.0.0rc7 adds retained gateway roles, versioned agent file updates, and a repeatable local email setup.

## What Changed

- Assign observer, requester, maintainer, or operator access on a target. PyCasbin evaluates exact grants, and the gateway distinguishes attributed work requests, direct prompts, and native commands. The CLI and public dashboard explain open and keyed access. [Authorization Policy](https://igamenovoer.github.io/houmao/reference/gateway/operations/authorization-policy/) and [Issue #97](https://github.com/igamenovoer/houmao/issues/97)
- Edit and commit a draft on an enabled file mount, then explicitly publish it against the expected base. A qualified managed agent can schedule a saved revision for its next idle boundary with `--when-idle`. [Versioned File Edits](https://igamenovoer.github.io/houmao/reference/gateway/operations/versioned-file-edits/)
- Mail send, reply, and post return compact CLI receipts with references for follow-up reads. Managed launches use prompt header version 2, and the packaged skills cover access administration and versioned file edits. [Agent Mail CLI](https://igamenovoer.github.io/houmao/reference/cli/agents-mail/)
- Run `./dockers/email-system/up.sh --pull-missing-images` from a fresh checkout to start Stalwart and Cypht. The setup provisions admin and operator mailboxes on `houmao.localhost`. [Local Email System](https://github.com/igamenovoer/houmao/blob/v3.0.0rc7/dockers/email-system/README.md)

## Upgrade From 3.0.0rc6

- Follow the authorization cutover for existing gateways and relaunch agents to register their managed-self SSH keys. Review retained `agent.prompt` grants and assign `agent.request.submit`, `agent.prompt.direct`, or `agent.command.invoke` as appropriate. [Authorization Policy](https://igamenovoer.github.io/houmao/reference/gateway/operations/authorization-policy/)
- Update CLI consumers to read mail receipts and use `mail peek` for message contents. Install the matching skills for the new nested `metadata.houmao_version` format.

## Install the Candidate

```bash
uv tool install 'houmao==3.0.0rc7'
npx skills add https://github.com/igamenovoer/houmao-skills#v3.0.0rc7
```

[Compare v3.0.0rc6 and v3.0.0rc7](https://github.com/igamenovoer/houmao/compare/v3.0.0rc6...v3.0.0rc7)
