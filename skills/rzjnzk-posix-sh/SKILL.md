---
name: rzjnzk-posix-sh
description: Use whenever you write or edit a shell script for rzjnzk, or port a tool to `sh` for him. Covers his portable POSIX `sh` style, taken from his scripts in `~/.u`, including tool choice, quoting, layout, line continuation, comments, naming, error output, and `tput` colours.
---

# rzjnzk's POSIX `sh` style

rzjnzk writes portable POSIX `sh` that should run on restricted systems, such as embedded devices and BusyBox, as well as on full Linux and macOS. Match his style exactly when writing a new script or editing one of his. The rules below come from his own scripts: `~/.u/libexec/bin/u`, `~/.u/u`, `~/.u/lib/*.sh`, and `~/.u/etc/profile`.

Write comments and documentation in English according to the `rzjnzk-writing-style` skill.

## Portability

- Use `#!/bin/sh` and POSIX `sh` only: no `local`, arrays, `[[ ]]`, `function`, `source`, `$RANDOM`, `echo -e`, process substitution, or `<<<`.
- Use `sed` for all text work. Never use `awk` or `grep`. Avoid `tr`, `cut`, `readlink`, `realpath`, `mktemp`, and `jq` too, since they are missing or differ on small systems. His scripts also use `head -n 1`, but `sed -n "1p"` does the same with one tool fewer.
- Keep `sed` to POSIX: no `-i`, `-E`, or `-r`; no `\n` or `\t` in a replacement; no `\|`, `\+`, or `\?`. Put a newline into a replacement as a backslash and a real newline, and get a tab or carriage return from `printf`:

  ```sh
  _tab="$(printf "\t")"
  _cr="$(printf "\r")"
  ```

- Check that a command exists with `command -v NAME > /dev/null 2>&1`, never `which`.
- Prefer a fallback chain to a hard dependency, as with `curl` then `wget` in `~/.u/u`.
- Run every script through `sh -n`, `dash -n`, and `shellcheck -s sh` when they exist, and through `busybox sh` when it exists.

## Quoting and expansion

- Always brace variables, and always quote them: `"${var}"`, `"${1}"`, `"${@}"`, `"${?}"`.
- Prefer double quotes everywhere, including around `sed` scripts, and escape what the shell would otherwise expand:

  ```sh
  sed -n "s/.*\"sha\"[ ]*:[ ]*\"\([0-9a-f]*\)\".*/\1/p"
  ```

- Use single quotes only when a string must not be expanded at all.
- Write code names in messages with escaped backticks: `` "Failed to source \`${1}\`." ``.

## Layout

- Indent with 4 spaces. Leave a blank line between logical steps, and before `exit`, `return`, `break`, and `continue` when they follow other commands.
- Put `if`, `elif`, `while`, and `then` or `do` on their own lines, with the condition indented below:

  ```sh
  if
      ! test -d "${HOME}"
  then
      printf "%s\n" "${_t_f_red}Error:${_t_reset} The \`HOME\` environment variable is not a valid path." 1>&2

      exit 1
  fi
  ```

- Write an endless loop as `while`, then `:` on its own line, then `do`.
- Break `for` after the keyword with a backslash:

  ```sh
  for \
      _path in "${HOME}/bin/"*
  do
      ...
  done
  ```

- Use `test`, never `[ ]`. Use `if` and `elif` chains of `test "${1}" = "value"`, not `case`.
- Define functions as `_name()` with the opening brace on the next line. When a function needs no globals of its own, wrap its body in `( )` so its variables stay local; otherwise give each variable a prefix unique to the function or module.
- Redirect into a loop after a continued `done`:

  ```sh
  done \
  < "${U_DIR}/config/profile/.conf"
  ```

## Line continuation

- End the line with ` \` and start the next line with the operator, at the same indent as the command it continues: `&&`, `||`, or `|`.

  ```sh
  if
      test "${#}" -eq 0 \
      || test "${1}" = "help"
  then
  ```

  ```sh
  curl -sS "https://raw.githubusercontent.com/rzjnzk/u/master/libexec/bin/u" \
  | _repository_fork__url="${_repository_fork__url}" sh -s -- "${@}"
  ```

- Put the arguments of a multi-line `printf` one per line, indented 4 more spaces, with any redirection after the last one:

  ```sh
  printf "%s\n" \
      "${_t_f_red}Error:${_t_reset} Failed to delete the temporary directory: \`${_tmpdir}\`." \
      "${_indent}Please delete the directory manually: \`rm -rf \"${_tmpdir}\"\`" 1>&2
  ```

- Write a long `sed` script as a double-quoted block on its own lines, one command per line ending in `;`, with a continued address before a `{` block:

  ```sh
  sed -n \
      "
          /^# NAME *$/ \
          {
              n;
              s/^.* - //p;
          }
      " \
      "${1}"
  ```

## Names

- Prefix every variable and function with `_`, and use `snake_case`: `_tmpdir`, `_file_name`, `_print_help`.
- Separate a namespace from a name with `__`: `_repository_base__url`, `_lib__print_err`, `_lib_terminal_text_attributes__colors`. A library function is `_lib__NAME`.
- Name booleans `_is_NAME`, with the string values `"true"` and `"false"`, compared with `test "${_is_x}" = "true"`.
- Quote every assigned value, even numbers: `_i="0"`.

## Output and errors

- Print with `printf "%s\n" "text"`, never `echo`.
- Send errors to `stderr` with `1>&2`, starting with a red `Error:`, and indent any follow-up lines with `${_indent}`, which is 4 spaces. Use a blue `Hint:` for advice.
- Silence a probe with `> /dev/null 2>&1`, with spaces around `>`.
- Start scripts with `set -e`, and clean up in an `_on_exit` function that saves `"$?"` first:

  ```sh
  _on_exit()
  {
      _exit_code="$?"

      rm -rf "${_tmpdir}"

      exit "${_exit_code}"
  }

  trap _on_exit EXIT INT TERM HUP
  ```

- Make a temporary directory with a `mkdir` loop on `/tmp/NAME.$$.N`, not `mktemp`.
- Read lines with `IFS="" read -r _line`.
- Source files with `\. "${path}"`, the backslash stopping an alias called `.` from being used.
- Use `--` before path arguments: `mkdir -p -- "${dir}"`, `basename -- "${0}"`, `dirname -- "${0}"`.
- Find the script's own folder with `"$(cd -- "$(dirname -- "${0}")" && pwd)"`.

## Colours

Store `tput` output in variables once, at the top, with errors silenced, then embed the variables in strings. Never write raw ANSI escapes.

```sh
_t_reset="$(tput sgr0 2> /dev/null)"
_t_f_red="$(tput setaf 1 2> /dev/null)"
_t_f_green="$(tput setaf 2 2> /dev/null)"
_t_f_yellow="$(tput setaf 3 2> /dev/null)"
_t_f_blue="$(tput setaf 4 2> /dev/null)"
_t_f_cyan="$(tput setaf 6 2> /dev/null)"
_t_dim="$(tput dim 2> /dev/null)"

printf "%s\n" "${_t_f_red}Error:${_t_reset} Neither \`curl\` nor \`wget\` is available." 1>&2
```

`_t_f_` is a foreground colour, and `_t_` alone is an attribute. The longer `_lib_terminal_text_attributes__fg_red` names in `~/.u/lib/terminal-text-attributes.sh` are the library form of the same idea.

## Comments

- Begin a script with a man-page-style header from line 2, with indented sections: `NAME`, as `name - description`; `SYNOPSIS`; `DESCRIPTION`; `OPTIONS`; `DEPENDENCIES`, a list starting with `- POSIX-compliant shell.`; `AUTHORS`; and `NOTES`. `--help` prints this header with `sed`, from line 3 to the first blank line.
- Write comments as full sentences ending in a full stop, above the code they describe, with code names in backticks.
- Use the tags `# TODO: `, `# INFO: `, and `# shellcheck disable=SCxxxx`, the last directly above the line it covers.
- Mark sections with matching `# BEGIN Description.` and `# END Description.` lines.

## Robustness additions

These go beyond what his existing scripts do, and were agreed for scripts that must not fail on small systems:

- Under `set -e`, a failing command substitution in an assignment ends the script, so add `|| :` where failure is fine: `_t_reset="$(tput sgr0 2> /dev/null || :)"` keeps the script running with no `tput` or no `TERM`.
- His scripts use `expr` for counters, such as `_i="$(expr "${_i}" + 1)"`. For other arithmetic, use `$(( ))`: `expr` exits 1 when the result is 0, which ends a `set -e` script, and it starts a process every time. Keep to whole numbers, such as milliseconds instead of fractions of a second, and add a `1` prefix to stop a leading zero being read as octal: `$((1${_minutes} - 100))`.
- When a script must find its real folder through symlinks, follow each one with `ls -ld` and `sed "s/^.* -> //"`, since `readlink -f` is not POSIX. When `$0` is not a file, because the script was sourced or piped into `sh`, stop with a clear error, using `return 1 2> /dev/null || exit 1`, before `set -e`.
- Build up optional command arguments in `"${@}"` with `set --`, since there are no arrays.
