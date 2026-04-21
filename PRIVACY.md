# Privacy Policy

**Effective date:** 2026-04-21
**Project:** [`xiao`](https://github.com/dacrypt/xiao) — open-source Python CLI for controlling a Xiaomi Robot Vacuum via Xiaomi Cloud.
**License:** MIT (this is a free, open-source project, not a commercial service).

## TL;DR

**`xiao` does not collect, transmit, store, or share any personal data.**
There is no server, no telemetry, no analytics, and no backend operated by
the maintainers. Everything runs on your machine; the only network traffic
goes to Xiaomi's cloud API on your behalf.

## What `xiao` is (and isn't)

`xiao` is a command-line tool that you install and run locally on your own
computer. It is **not** a hosted service. The maintainers of this project
never see any of your data. The repository is open source under the MIT
license — every request it makes is auditable in the source code.

## Data that stays on your machine

When you run `xiao setup cloud`, the tool stores the following locally in
a config file (platform-specific location — typically
`~/Library/Application Support/xiao/config.toml` on macOS or
`~/.config/xiao/config.toml` on Linux):

- Your Xiaomi account username (email)
- Your Xiaomi account password (hashed client-side)
- The device ID of your vacuum (discovered from Xiaomi's API)
- Short-lived Xiaomi Cloud session tokens (`serviceToken`, `ssecurity`) that
  expire every ~6–8 hours and are refreshed automatically

**This data never leaves your machine** except when `xiao` calls Xiaomi's
own cloud API on your behalf to send commands to your vacuum. It is not
sent to the maintainers, not sent to any third party, and not uploaded
anywhere else.

## Network traffic

The only outbound network traffic `xiao` generates is:

1. **Xiaomi Cloud API** (e.g. `api.io.mi.com`, `account.xiaomi.com`) —
   required for the tool to function. All commands to your vacuum are
   RC4-signed and go through Xiaomi's official endpoints.
2. **The persistent Chromium session on `127.0.0.1:18800`** — a local
   browser that you run yourself for automatic token refresh. This is
   localhost only; no external party is involved.
3. **(Fallback)** If the local Chromium session is not available, `xiao`
   uses Playwright to open a browser window for full login. Traffic again
   goes only to Xiaomi.

No request goes to any server controlled by the maintainers of this
project. There is no such server.

## What governs Xiaomi's use of your data

When you use `xiao`, you are interacting with Xiaomi's cloud service using
your existing Xiaomi account. Xiaomi's own privacy policy governs what
Xiaomi does with your account, your vacuum's telemetry, and your usage
data. See: <https://www.mi.com/global/about/privacy>.

The maintainers of `xiao` are not affiliated with Xiaomi and have no
control over Xiaomi's data practices.

## Analytics and telemetry

**None.** `xiao` has zero built-in analytics, crash reporting, or
telemetry. The CLI does not phone home. The only thing the maintainers
see is what you voluntarily share in a GitHub issue, pull request, or
public discussion.

## Logs

`xiao` may write local log files (e.g. `~/.npm/_logs/` from npm, or
Playwright browser caches) during debugging. These stay on your machine
and are not shipped anywhere.

## Source code

All behavior described above is verifiable in the public source code at
<https://github.com/dacrypt/xiao>. If you find a request that does not
match this policy, please open an issue — it's a bug we'll fix.

## Changes to this policy

Because `xiao` does not collect data, there is nothing to change about
our handling practices. If the project ever adds any telemetry,
analytics, or network call to a maintainer-operated server, this file
will be updated in the same commit that introduces the change, and
listed in `CHANGELOG.md`. Until then, the answer is always "no, we don't
collect that."

## Contact

Issues, questions, or concerns about this policy: open a GitHub issue at
<https://github.com/dacrypt/xiao/issues> or reach the maintainer listed
in [`pyproject.toml`](pyproject.toml).
