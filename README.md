# skills

Agent skills for AI coding assistants and chat agents, in the [Agent Skills](https://agentskills.io/specification) format. Each skill is a folder under `skills/` containing a `SKILL.md`.

## Skills

| Skill | Source | Description |
|---|---|---|
| `rzjnzk-writing-style` | Original | rzjnzk's English writing style for files and artefacts |
| `umbrella-commit` | Original | Repo-history commit messages with a 50-character umbrella subject |
| `rzjnzk-posix-sh` | Original | rzjnzk's portable POSIX `sh` style, from his scripts in `~/.u` |
| `caveman` | [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) | Terse chat replies that keep every technical fact |
| `ultracave` | [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) | A more aggressive variant of `caveman` |
| `megacave` | [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) | A Classical Chinese variant of `caveman` |

## Installation

With `npx skills`:

```sh
# List the skills in this repository
npx skills add rzjnzk/skills --list

# Install one skill globally
npx skills add rzjnzk/skills --skill rzjnzk-writing-style -g

# Install every skill, for every agent, without prompts
npx skills add rzjnzk/skills --all -g
```

With the GitHub CLI, version 2.90 or later:

```sh
gh skill install rzjnzk/skills rzjnzk-writing-style
```

## Third-party skills

Third-party skills are unmodified copies of their upstream folders. Each retains its upstream licence in `LICENSE` and records its source commit in `NOTICE`. This repository is not affiliated with or endorsed by their authors.
