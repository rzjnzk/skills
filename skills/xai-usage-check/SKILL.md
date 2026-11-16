---
name: xai-usage-check
description: Use when rzjnzk asks about his xAI API spend, token usage, prepaid balance, invoice, or spending limits, or about SuperGrok, Grok app, or Grok Bot quota. Runs `scripts/xai_usage_check.py`, which probes every known usage source over HTTP and prints one report.
---

# xAI usage check

Run `python3 scripts/xai_usage_check.py` on a machine or bot with internet access, never in a sandboxed code executor without network. Show the user its whole report; do not ask which kind of usage they mean.

## Credentials

Set `XAI_API_KEY` for the inference API probes and `XAI_MANAGEMENT_KEY` for team spend, tokens, prepaid balance, invoice preview, and spending limits. An ordinary API key is rejected by `management-api.x.ai` with HTTP 401. `XAI_TEAM_ID` is optional, since the script reads it from `GET /v1/api-key`. Either export them or put `KEY=value` lines in a `.env` file beside the script; `.env` is gitignored. Never print, paste, or commit a key.

## Limits

Real figures exist only for the xAI API team that owns the keys. SuperGrok, the Grok app's consumer quota, and Grok Bot usage have no public API, so the report prints 'Grok app quota: not exposed via API' and 'Grokbot usage: not exposed via API' unless a speculative probe unexpectedly answers.

## Self-update

The script compares each probe with its baked-in `EXPECTED` states. If any differ, it asks once: 'Capabilities changed — edit this skill file, commit, and push? (y/n)'. In a non-interactive run it prints that question instead of blocking. Put the question to the user verbatim and once. On 'y', rerun with `--apply-update`, which rewrites `EXPECTED`, compile-checks the file, and commits and pushes it. On 'n', do nothing. A probe that only lacked a credential or hit a network error does not count as a change.

The header docstring of the script carries the full probe list, which endpoints are documented by xAI, and which are speculative.
