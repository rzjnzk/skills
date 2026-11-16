#!/usr/bin/env python3
"""xai_usage_check.py: probe every known xAI and Grok usage source and report it.

READ THIS FIRST IF YOU ARE AN LLM OR AGENT
==========================================

What it does
------------
The script makes real HTTP calls to every usage-related xAI endpoint it
knows of, catches every failure, and prints one block that lists each
probed source. A source that answers shows its real values; a source that
fails or does not exist shows an honest static line, such as 'Grok app
quota: not exposed via API'. The script never invents a number and never
asks which kind of usage to show; it always prints everything.

The probes are:

  api_key_info      GET  https://api.x.ai/v1/api-key                verified
  models            GET  https://api.x.ai/v1/models                 verified
  language_models   GET  https://api.x.ai/v1/language-models        verified
  rate_limit_hdrs   x-ratelimit-* headers on GET /v1/models        speculative
  mgmt_usage_30d    POST https://management-api.x.ai/v1/billing/teams/{team_id}/usage
                    daily USD spend for 30 days, grouped by model   verified
  mgmt_tokens_7d    the same endpoint, daily tokens for 7 days,
                    grouped by token type and model                 verified
  mgmt_prepaid      GET  .../billing/teams/{team_id}/prepaid/balance          verified
  mgmt_invoice      GET  .../billing/teams/{team_id}/postpaid/invoice/preview verified
  mgmt_limits       GET  .../billing/teams/{team_id}/postpaid/spending-limits verified
  grok_app_quota    POST https://grok.com/rest/rate-limits          speculative
  grokbot_usage     no public endpoint is known; static line        speculative
  api_usage_guess   GET  https://api.x.ai/v1/usage, /v1/billing     speculative

'verified' means the endpoint is documented at https://docs.x.ai or in the
Swagger UI at https://api.x.ai/docs/. 'speculative' means it is a guess,
probed only so that a change in xAI's offering is noticed.

Where to run it
---------------
It needs outbound internet access to `api.x.ai`, `management-api.x.ai`,
and `grok.com`. Run it on a normal machine, a terminal in VS Code, or a
bot or agent with network access. Do NOT run it in a sandboxed code
executor, such as the Python tool in Grok chat or a similar notebook
sandbox, since those usually have no network and every probe would fail.
It uses only the Python 3.8+ standard library: `python3 xai_usage_check.py`.

How to load credentials
-----------------------
Credentials come from environment variables or from a `.env` file of
`KEY=value` lines in the current directory or beside this script.
Environment variables win over the `.env` file. Nothing sensitive belongs
in the repository; `.env` is gitignored, and the script never prints a key.

  XAI_API_KEY          inference API key; needed for the api.x.ai probes
  XAI_MANAGEMENT_KEY   management key from the xAI Console settings page;
                       needed for every management-api.x.ai probe, since
                       an ordinary API key is rejected there with HTTP 401
  XAI_TEAM_ID          optional; otherwise read from GET /v1/api-key
  XAI_USAGE_TIMEZONE   optional IANA zone for day boundaries; default
                       Etc/GMT

Limits
------
Real values exist only for the xAI API: key status, models, team spend,
tokens, prepaid balance, invoice preview, and spending limits. SuperGrok,
the Grok app's consumer quota, and Grok Bot usage have no public API, so
the script prints static text for them unless a speculative probe
unexpectedly answers. Spend figures are those of the xAI team that owns
the keys, not of any consumer subscription.

Self-update behaviour
---------------------
The `EXPECTED` dictionary below records whether each probe is expected to
be 'ok' or 'unavailable'. After printing, the script compares what it saw
against `EXPECTED`. A probe that only lacked a credential or hit a network
error is not a finding and is ignored. If any probe differs, the script
lists the mismatches and asks one question:

  Capabilities changed — edit this skill file, commit, and push? (y/n)

On 'y' it rewrites `EXPECTED` in this file to the observed values, checks
the file with `py_compile`, and runs `git add`, `git commit`, and `git push`
in the repository that contains it. On 'n' it does nothing.

If standard input is not a terminal, the script does not block. It prints
the question and instructions instead. An LLM running it should put that
single question to the user verbatim and, on 'y', rerun the script with
`--apply-update`, which performs the edit, commit, and push without
prompting. `--no-update` skips the comparison step entirely. The LLM may
also improve the matching probe's code by hand before committing, but it
must follow the commit rules in `skills/umbrella-commit` of this
repository.
"""

import datetime
import json
import os
import py_compile
import re
import subprocess
import sys
import tempfile
import textwrap
import urllib.error
import urllib.request

API_BASE = "https://api.x.ai"
MGMT_BASE = "https://management-api.x.ai"
GROK_APP_BASE = "https://grok.com"
TIMEOUT = 20
USER_AGENT = "xai-usage-check/1.0 (+https://github.com/rzjnzk/skills)"

PROMPT = "Capabilities changed — edit this skill file, commit, and push? (y/n)"
GROK_APP_STATIC = "Grok app quota: not exposed via API"
GROKBOT_STATIC = "Grokbot usage: not exposed via API"

# Probe states. Only 'ok' and 'unavailable' are compared against EXPECTED;
# 'no_credentials' and 'network_error' say nothing about xAI's offering.
OK = "ok"
UNAVAILABLE = "unavailable"
NO_CREDENTIALS = "no_credentials"
NETWORK_ERROR = "network_error"

# BEGIN EXPECTED (rewritten in place by the self-update step)
EXPECTED = {
    "api_key_info": "ok",
    "models": "ok",
    "language_models": "ok",
    "rate_limit_hdrs": "unavailable",
    "mgmt_usage_30d": "ok",
    "mgmt_tokens_7d": "ok",
    "mgmt_prepaid": "ok",
    "mgmt_invoice": "ok",
    "mgmt_limits": "ok",
    "grok_app_quota": "unavailable",
    "grokbot_usage": "unavailable",
    "api_usage_guess": "unavailable",
}
# END EXPECTED


# --------------------------------------------------------------------------
# Credentials


def load_dotenv():
    """Read KEY=value lines from .env in the cwd and the script's folder."""
    here = os.path.dirname(os.path.abspath(__file__))
    seen = set()
    for folder in (os.getcwd(), here):
        path = os.path.join(folder, ".env")
        if path in seen or not os.path.isfile(path):
            continue
        seen.add(path)
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    if line.startswith("export "):
                        line = line[len("export "):]
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip("'").strip('"')
                    if key and key not in os.environ:
                        os.environ[key] = value
        except OSError:
            pass


# --------------------------------------------------------------------------
# HTTP


class Resp:
    def __init__(self, status, body, headers, error=None):
        self.status = status
        self.body = body
        self.headers = headers or {}
        self.error = error

    def json(self):
        try:
            return json.loads(self.body)
        except (ValueError, TypeError):
            return None

    def short_error(self):
        if self.error:
            return self.error
        data = self.json()
        msg = ""
        if isinstance(data, dict):
            msg = data.get("message") or data.get("error") or data.get("code") or ""
        if msg and not isinstance(msg, str):
            msg = json.dumps(msg)
        if not msg:
            msg = (self.body or "")[:120].replace("\n", " ")
        return "HTTP %s %s" % (self.status, msg)


def http(method, url, key=None, payload=None):
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    data = None
    if key:
        headers["Authorization"] = "Bearer " + key
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read().decode("utf-8", "replace")
            return Resp(r.status, body, {k.lower(): v for k, v in r.headers.items()})
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            body = ""
        return Resp(e.code, body, {k.lower(): v for k, v in (e.headers or {}).items()})
    except Exception as e:  # DNS, TLS, timeout, no network
        return Resp(None, "", {}, error="%s: %s" % (type(e).__name__, e))


def classify(resp):
    """Map a response to a probe state."""
    if resp.status is None:
        return NETWORK_ERROR
    if 200 <= resp.status < 300 and resp.json() is not None:
        return OK
    if resp.status in (401, 403):
        return NO_CREDENTIALS
    return UNAVAILABLE


# --------------------------------------------------------------------------
# Formatting


def usd(x):
    return "$%.4f" % x


def cents_val(obj):
    """Return USD from xAI's {'val': '<cents>'} or a plain cents string."""
    if isinstance(obj, dict):
        obj = obj.get("val")
    try:
        return int(str(obj)) / 100.0
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------
# Probes. Each returns (state, [lines]).


def probe_api_key_info(ctx):
    key = ctx["api_key"]
    if not key:
        return NO_CREDENTIALS, ["XAI_API_KEY not set"]
    r = http("GET", API_BASE + "/v1/api-key", key)
    state = classify(r)
    if state != OK:
        return state, [r.short_error()]
    d = r.json()
    ctx["team_id"] = ctx["team_id"] or d.get("team_id")
    return OK, [
        "key name: %s" % d.get("name"),
        "team id: %s" % d.get("team_id"),
        "acls: %s" % ", ".join(d.get("acls") or []),
        "blocked: team=%s key=%s disabled=%s"
        % (d.get("team_blocked"), d.get("api_key_blocked"), d.get("api_key_disabled")),
    ]


def probe_models(ctx):
    key = ctx["api_key"]
    if not key:
        return NO_CREDENTIALS, ["XAI_API_KEY not set"]
    r = http("GET", API_BASE + "/v1/models", key)
    ctx["models_headers"] = r.headers
    state = classify(r)
    if state != OK:
        return state, [r.short_error()]
    ids = [m.get("id") for m in (r.json().get("data") or [])]
    return OK, ["%d models: %s" % (len(ids), ", ".join(ids))]


def probe_language_models(ctx):
    key = ctx["api_key"]
    if not key:
        return NO_CREDENTIALS, ["XAI_API_KEY not set"]
    r = http("GET", API_BASE + "/v1/language-models", key)
    state = classify(r)
    if state != OK:
        return state, [r.short_error()]
    lines = []
    for m in r.json().get("models") or []:
        # Prices are in 1e-10 USD per token; x 1e4 gives USD per 1M tokens.
        p_in = m.get("prompt_text_token_price")
        p_out = m.get("completion_text_token_price")
        if p_in is not None and p_out is not None:
            lines.append("%s: $%.2f in / $%.2f out per 1M tokens"
                         % (m.get("id"), p_in / 1e4, p_out / 1e4))
        else:
            lines.append(str(m.get("id")))
    return OK, lines or ["no language models listed"]


def probe_rate_limit_hdrs(ctx):
    if "models_headers" not in ctx:
        return NO_CREDENTIALS, ["needs the models probe"]
    hdrs = {k: v for k, v in ctx["models_headers"].items() if "ratelimit" in k}
    if not hdrs:
        return UNAVAILABLE, ["no x-ratelimit-* headers on GET /v1/models"]
    return OK, ["%s: %s" % kv for kv in sorted(hdrs.items())]


def _mgmt_ready(ctx):
    if not ctx["mgmt_key"]:
        return ["XAI_MANAGEMENT_KEY not set; an ordinary API key gets HTTP 401 here"]
    if not ctx["team_id"]:
        return ["team id unknown; set XAI_TEAM_ID or XAI_API_KEY"]
    return None


def _usage_request(ctx, days, value, group_by):
    tz = ctx["tz"]
    end = datetime.date.today() + datetime.timedelta(days=1)
    start = end - datetime.timedelta(days=days)
    payload = {
        "analyticsRequest": {
            "timeRange": {
                "startTime": start.strftime("%Y-%m-%d 00:00:00"),
                "endTime": end.strftime("%Y-%m-%d 00:00:00"),
                "timezone": tz,
            },
            "timeUnit": "TIME_UNIT_DAY",
            "values": [{"name": value, "aggregation": "AGGREGATION_SUM"}],
            "groupBy": group_by,
            "filters": [],
        }
    }
    url = "%s/v1/billing/teams/%s/usage" % (MGMT_BASE, ctx["team_id"])
    return http("POST", url, ctx["mgmt_key"], payload)


def probe_mgmt_usage_30d(ctx):
    missing = _mgmt_ready(ctx)
    if missing:
        return NO_CREDENTIALS, missing
    r = _usage_request(ctx, 30, "usd", ["description"])
    state = classify(r)
    if state != OK:
        return state, [r.short_error()]
    d = r.json()
    per_model, per_day = {}, {}
    for ts in d.get("timeSeries") or []:
        label = " / ".join(ts.get("groupLabels") or ts.get("group") or ["?"])
        for dp in ts.get("dataPoints") or []:
            v = float((dp.get("values") or [0])[0] or 0)
            day = (dp.get("timestamp") or "")[:10]
            per_model[label] = per_model.get(label, 0.0) + v
            per_day.setdefault(day, {})
            per_day[day][label] = per_day[day].get(label, 0.0) + v
    total = sum(per_model.values())
    lines = ["30-day total: %s (timezone %s)" % (usd(total), ctx["tz"])]
    for label, v in sorted(per_model.items(), key=lambda kv: -kv[1]):
        if v:
            lines.append("  %-48s %s" % (label, usd(v)))
    lines.append("last 7 days, by day:")
    for day in sorted(per_day)[-7:]:
        models = {k: v for k, v in per_day[day].items() if v}
        lines.append("  %s  %s" % (day, usd(sum(models.values()))))
        for label, v in sorted(models.items(), key=lambda kv: -kv[1]):
            lines.append("      %-44s %s" % (label, usd(v)))
    if d.get("limitReached"):
        lines.append("warning: limitReached is true; figures may be incomplete")
    return OK, lines


def probe_mgmt_tokens_7d(ctx):
    missing = _mgmt_ready(ctx)
    if missing:
        return NO_CREDENTIALS, missing
    r = _usage_request(ctx, 7, "units", ["unit_type", "description"])
    state = classify(r)
    if state != OK:
        return state, [r.short_error()]
    rows = []
    for ts in r.json().get("timeSeries") or []:
        label = " / ".join(ts.get("groupLabels") or ts.get("group") or ["?"])
        n = sum(float((dp.get("values") or [0])[0] or 0) for dp in ts.get("dataPoints") or [])
        if n:
            rows.append((label, n))
    lines = ["7-day units by token type and model:"]
    for label, n in sorted(rows, key=lambda kv: -kv[1]):
        lines.append("  %-56s %d" % (label, n))
    if not rows:
        lines.append("  none")
    return OK, lines


def _mgmt_get(ctx, suffix):
    url = "%s/v1/billing/teams/%s/%s" % (MGMT_BASE, ctx["team_id"], suffix)
    return http("GET", url, ctx["mgmt_key"])


def probe_mgmt_prepaid(ctx):
    missing = _mgmt_ready(ctx)
    if missing:
        return NO_CREDENTIALS, missing
    r = _mgmt_get(ctx, "prepaid/balance")
    state = classify(r)
    if state != OK:
        return state, [r.short_error()]
    d = r.json()
    total = cents_val(d.get("total"))
    # xAI records purchases as negative amounts, so a negative total is credit.
    lines = ["prepaid total: %s" % ("n/a" if total is None else usd(-total) + " credit")]
    lines.append("balance changes on record: %d" % len(d.get("changes") or []))
    return OK, lines


def probe_mgmt_invoice(ctx):
    missing = _mgmt_ready(ctx)
    if missing:
        return NO_CREDENTIALS, missing
    r = _mgmt_get(ctx, "postpaid/invoice/preview")
    state = classify(r)
    if state != OK:
        return state, [r.short_error()]
    d = r.json()
    inv = d.get("coreInvoice") or {}
    cyc = d.get("billingCycle") or {}
    lines = ["billing cycle: %s-%s" % (cyc.get("year"), cyc.get("month"))]
    for label, raw in (
        ("amount after VAT", inv.get("amountAfterVat")),
        ("prepaid credits used", inv.get("prepaidCreditsUsed")),
        ("effective spending limit", d.get("effectiveSpendingLimit")),
        ("default credits", d.get("defaultCredits")),
    ):
        v = cents_val(raw)
        lines.append("%s: %s" % (label, "n/a" if v is None else usd(v)))
    return OK, lines


def probe_mgmt_limits(ctx):
    missing = _mgmt_ready(ctx)
    if missing:
        return NO_CREDENTIALS, missing
    r = _mgmt_get(ctx, "postpaid/spending-limits")
    state = classify(r)
    if state != OK:
        return state, [r.short_error()]
    limits = r.json().get("spendingLimits") or {}
    lines = []
    for k, raw in sorted(limits.items()):
        v = cents_val(raw)
        lines.append("%s: %s" % (k, json.dumps(raw) if v is None else usd(v)))
    return OK, lines or ["no spending limits returned"]


def probe_grok_app_quota(ctx):
    # Speculative: the grok.com web app's own endpoint, which normally needs
    # a browser session. Without one it is expected to fail.
    r = http("POST", GROK_APP_BASE + "/rest/rate-limits", None,
             {"requestKind": "DEFAULT", "modelName": "grok-4"})
    d = r.json() if classify(r) == OK else None
    if isinstance(d, dict) and ("remainingQueries" in d or "totalQueries" in d):
        return OK, ["%s: %s" % kv for kv in sorted(d.items())]
    return UNAVAILABLE, [GROK_APP_STATIC + " (probe: %s)" % r.short_error()]


def probe_grokbot_usage(ctx):
    # No public Grok Bot usage endpoint is known; nothing to call.
    return UNAVAILABLE, [GROKBOT_STATIC]


def probe_api_usage_guess(ctx):
    found = []
    for path in ("/v1/usage", "/v1/billing"):
        r = http("GET", API_BASE + path, ctx["api_key"])
        if classify(r) == OK:
            found.append("%s: %s" % (path, r.body[:200].replace("\n", " ")))
        else:
            found.append("%s: %s" % (path, r.short_error()))
    ok = any(": HTTP" not in f and "Error" not in f for f in found)
    return (OK if ok else UNAVAILABLE), found


PROBES = [
    ("api_key_info", "xAI API key info", probe_api_key_info),
    ("models", "xAI models", probe_models),
    ("language_models", "xAI language models and prices", probe_language_models),
    ("rate_limit_hdrs", "xAI rate-limit headers", probe_rate_limit_hdrs),
    ("mgmt_usage_30d", "xAI team spend, 30 days", probe_mgmt_usage_30d),
    ("mgmt_tokens_7d", "xAI team tokens, 7 days", probe_mgmt_tokens_7d),
    ("mgmt_prepaid", "xAI prepaid balance", probe_mgmt_prepaid),
    ("mgmt_invoice", "xAI invoice preview", probe_mgmt_invoice),
    ("mgmt_limits", "xAI spending limits", probe_mgmt_limits),
    ("grok_app_quota", "SuperGrok / Grok app quota", probe_grok_app_quota),
    ("grokbot_usage", "Grok Bot usage", probe_grokbot_usage),
    ("api_usage_guess", "Other xAI usage endpoints", probe_api_usage_guess),
]


# --------------------------------------------------------------------------
# Self-update


def find_mismatches(results):
    out = []
    for name, state in results.items():
        if state in (NO_CREDENTIALS, NETWORK_ERROR):
            continue
        if EXPECTED.get(name) != state:
            out.append((name, EXPECTED.get(name), state))
    return out


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def apply_update(mismatches):
    path = os.path.abspath(__file__)
    folder = os.path.dirname(path)
    new = dict(EXPECTED)
    for name, _, observed in mismatches:
        new[name] = observed
    body = "EXPECTED = {\n" + "".join(
        '    "%s": "%s",\n' % (k, v) for k, v in new.items()) + "}\n"
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    pattern = re.compile(r"(# BEGIN EXPECTED[^\n]*\n).*?(# END EXPECTED)", re.S)
    if not pattern.search(src):
        print("update failed: EXPECTED markers not found")
        return 1
    updated = pattern.sub(lambda m: m.group(1) + body + m.group(2), src, count=1)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(updated)
    cfile = os.path.join(tempfile.gettempdir(), "xai_usage_check.pyc")
    try:
        py_compile.compile(path, cfile=cfile, doraise=True)
    except py_compile.PyCompileError as e:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(src)
        print("update failed: edited file did not compile; reverted\n%s" % e)
        return 1

    top = run(["git", "rev-parse", "--show-toplevel"], folder)
    if top.returncode != 0:
        print("file edited, but it is not in a git repository; nothing committed")
        return 1
    root = top.stdout.strip()
    rel = os.path.relpath(path, root).replace(os.sep, "/")

    subject = "Update xai-usage-check expected probe states"
    changes = ", ".join("%s from %s to %s" % (n, e, o) for n, e, o in mismatches)
    para = ("Record the probe states observed on %s in `EXPECTED` of `%s`: %s."
            % (datetime.date.today().isoformat(), rel, changes))
    msg = subject + "\n\n" + textwrap.fill(para, 74) + \
        "\n\nIs-ai-assisted-commit-message: true\n"
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt",
                                     encoding="utf-8") as fh:
        fh.write(msg)
        msg_path = fh.name
    try:
        for cmd in (["git", "add", "--", rel],
                    ["git", "commit", "-F", msg_path],
                    ["git", "push"]):
            res = run(cmd, root)
            print("$ %s\n%s%s" % (" ".join(cmd), res.stdout, res.stderr), end="")
            if res.returncode != 0:
                print("step failed: %s" % " ".join(cmd))
                return 1
    finally:
        os.unlink(msg_path)
    head = run(["git", "rev-parse", "--short", "HEAD"], root).stdout.strip()
    print("committed and pushed %s" % head)
    return 0


# --------------------------------------------------------------------------
# Main


def main(argv):
    if "-h" in argv or "--help" in argv:
        print(__doc__)
        return 0
    load_dotenv()
    ctx = {
        "api_key": os.environ.get("XAI_API_KEY", "").strip() or None,
        "mgmt_key": os.environ.get("XAI_MANAGEMENT_KEY", "").strip() or None,
        "team_id": os.environ.get("XAI_TEAM_ID", "").strip() or None,
        "tz": os.environ.get("XAI_USAGE_TIMEZONE", "").strip() or "Etc/GMT",
    }

    now = datetime.datetime.now().astimezone()
    print("=" * 72)
    print("xAI and Grok usage check, %s" % now.strftime("%Y-%m-%d %H:%M %Z (UTC%z)"))
    print("=" * 72)
    results = {}
    for name, title, fn in PROBES:
        try:
            state, lines = fn(ctx)
        except Exception as e:  # a probe must never crash the report
            state, lines = NETWORK_ERROR, ["probe crashed: %s: %s" % (type(e).__name__, e)]
        results[name] = state
        print("\n[%s] %s" % (state.upper(), title))
        for line in lines:
            print("  " + line)
    print("\n" + "=" * 72)

    if "--no-update" in argv:
        return 0
    mismatches = find_mismatches(results)
    if not mismatches:
        print("All probes match the baked-in expectations.")
        return 0
    print("Probes that differ from the baked-in expectations:")
    for name, exp, obs in mismatches:
        print("  %s: expected %s, observed %s" % (name, exp, obs))
    if "--apply-update" in argv:
        return apply_update(mismatches)
    if not sys.stdin.isatty():
        print(PROMPT)
        print("Non-interactive run. LLM runner: ask the user the question above, "
              "verbatim and once. On 'y', rerun this script with --apply-update. "
              "On 'n', do nothing.")
        return 0
    try:
        answer = input(PROMPT + " ").strip().lower()
    except EOFError:
        answer = ""
    if answer in ("y", "yes"):
        return apply_update(mismatches)
    print("No changes made.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
