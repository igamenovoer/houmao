Houmao 3.0.0rc4 adds browser sign-in for managed Web agents, a bundled operator manual, and headless pane display settings. It also honors explicit native permission settings during unattended launch.

## Upgrade From 3.0.0rc3

- Unattended launch fills omitted native permission settings with the broadest supported unattended defaults. To keep DSH's previous workspace boundary, set `tool_params.permissions.sandbox` to `workspace-write` in the specialist or launch profile. [Launch Policy](https://igamenovoer.github.io/houmao/reference/build-phase/launch-policy/)
- Restart a gateway running RC3 to pick up the browser entry routes. Web entry uses the owner-local gateway and native Web addresses. [Gateway Access](https://igamenovoer.github.io/houmao/reference/gateway/operations/access/#open-a-live-web-agent)

## What Changed

- For a live DSH or Kimi Web agent, an enrolled admin can open `/v1/web/enter` on the owner-local gateway. The page supplies a terminal command that signs the challenge locally and submits the proof. The same browser tab then opens the native app. Automation can request a one-time link with `gateway web-entry`. [Browser Sign-In and Signed Links](https://igamenovoer.github.io/houmao/reference/gateway/operations/access/#open-a-live-web-agent)
- Run `houmao-mgr manual` for concise, offline guides on preparing, launching, and operating agents. Start with `houmao-mgr manual start first-agent` for a guided first launch.
- Set `--headless-display-style` (`plain`, `json`, `fancy`) or `--headless-display-detail` (`concise`, `detail`) on project launch or a specialist-backed profile. A one-shot flag overrides the corresponding saved field. Resume and relaunch reuse the values recorded by the instance. [Headless Display Options](https://igamenovoer.github.io/houmao/reference/cli/houmao-mgr/#headless-display-options)

## Install the Candidate

```bash
uv tool install 'houmao==3.0.0rc4'
npx skills add https://github.com/igamenovoer/houmao-skills#v3.0.0rc4
```

## Qualification

The candidate passed 5,090 unit tests with 14 skips and six isolated integration tests covering gateway HTTPS access and headless pane rendering. Lint, type checking, skill-version validation, the strict docs build, and Twine checks passed. Both distributions contain the bundled manual and browser sign-in assets.

[Compare v3.0.0rc3 and v3.0.0rc4](https://github.com/igamenovoer/houmao/compare/v3.0.0rc3...v3.0.0rc4)
