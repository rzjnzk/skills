# Agent skills index

Any AI agent working for rzjnzk, whether GitHub Copilot in VS Code, the Grok API, a Grok Bot, plain Grok chat, or another assistant, should read this file first and apply every matching skill automatically, without waiting for the user to name one. The source of truth is the repository https://github.com/rzjnzk/skills on branch `master`; each skill is a folder under `skills/` containing a `SKILL.md`.

| Skill | Path | When to use | Notes |
|---|---|---|---|
| `rzjnzk-writing-style` | `skills/rzjnzk-writing-style/SKILL.md` | Writing any English prose for rzjnzk into a file or artefact, such as a README, documentation, code comments, commit messages, or Anki card fields | Not for chat replies. Applies alongside every other skill that writes to files |
| `umbrella-commit` | `skills/umbrella-commit/SKILL.md` | Writing or making a commit: 'write a commit', 'commit this', `/commit`, `/umbrella-commit`, or committing staged changes | 50-character umbrella subject, 74-character imperative paragraphs, `git commit -F`, and the trailer `Is-ai-assisted-commit-message: true` |
| `rzjnzk-posix-sh` | `skills/rzjnzk-posix-sh/SKILL.md` | Writing or editing a shell script for rzjnzk, or porting a tool to `sh` | Portable POSIX `sh` taken from his scripts in `~/.u` |
| `caveman` | `skills/caveman/SKILL.md` | `/caveman`, 'caveman mode', 'talk like caveman', 'be brief', or 'less tokens' | Terse chat replies that keep every technical fact. Stays on until 'stop caveman' or 'normal mode'. Third-party |
| `ultracave` | `skills/ultracave/SKILL.md` | Only on `/ultracave` or `/caveman ultra` | `disable-model-invocation: true`. Maximum compression. Third-party |
| `megacave` | `skills/megacave/SKILL.md` | Only on `/megacave` or `/caveman wenyan` | `disable-model-invocation: true`. Classical Chinese register with technical terms verbatim. Third-party |
| `xai-usage-check` | `skills/xai-usage-check/SKILL.md` | Questions about xAI API spend, token usage, prepaid balance, invoice, or spending limits, or about SuperGrok, Grok app, or Grok Bot quota | Runs `skills/xai-usage-check/scripts/xai_usage_check.py`. Needs network; `XAI_API_KEY` and `XAI_MANAGEMENT_KEY` from the environment or a `.env` file. Consumer quotas are static text. Self-updating. Works from Grok chat, a Grok Bot, the xAI API, or Copilot, given network access |

## How to use

Match the user's request against the 'When to use' column, and apply every skill that matches. Read the matching `SKILL.md` in full before acting, together with any files it references. A skill that runs a script needs a surface with network access, not a sandboxed code executor. A skill marked `disable-model-invocation: true` activates only on its explicit command. If no skill matches, say so and proceed normally.

## Maintenance

Update this file in the same commit whenever a skill is added, renamed, removed, or has its description changed. `xai-usage-check` may propose edits to its own script when the probed capabilities change; accept them only after the user answers 'y'.
