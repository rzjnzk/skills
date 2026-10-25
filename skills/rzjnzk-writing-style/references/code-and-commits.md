# Code and commit messages

## Code in prose

- Put exact programmatic text in backticks: commands, tool names, function and variable names, snippets, and paths. This applies in literary prose as well, e.g. `sed`.
- Omit backticks only where characters are scarce, such as in file names and git commit subject lines.

## Git commit messages

Follow the `umbrella-commit` skill in this repo. In short:

- Subject line: an imperative umbrella of at most 50 characters covering every change, beginning with a capital letter, with no backticks and no final full stop. Commas, and full stops between sentences, are acceptable.
  - Example: `Ignore /build in gitignore. Simplify build script`
- A blank line follows the subject line.
- Body: one imperative paragraph per change or area, wrapped at 74 characters, written in the normal style including backticks, with no bullets.
- End with the trailer `Is-ai-assisted-commit-message: true`.
