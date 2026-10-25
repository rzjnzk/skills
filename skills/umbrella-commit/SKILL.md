---
name: umbrella-commit
description: >
  Repo-history commit writer. Subject is a 50-char umbrella covering every
  change in the diff; body uses 74-char imperative-mood paragraphs (no
  bullets, no indentation) where each paragraph covers exactly one change
  or area of change so the whole commit reads as a concise high-level view
  with no blindspots. Always staged via `git add -A` from the repo root,
  written to a temp file, and committed with `git commit -F` to avoid
  shell-expansion issues. Always appends the `Is-ai-assisted-commit-message:
  true` trailer. Use when the user says "write a commit", "commit this",
  "make a commit", "/commit", "/umbrella-commit", or asks to commit staged
  changes.
---

Write commit messages that read like repo history, not chat. The whole
message — subject and body — is in **imperative mood**. The subject is a
single umbrella description that encapsulates ABSOLUTELY all changes in
the diff. The body is composed of blank-line-separated paragraphs where
each paragraph covers exactly one individual change or one area of change,
so the message gives a concise high-level view of every change in the
commit with absolutely no blindspots. Then stage, write, and commit
without using `git commit -m`.

## Workflow (perform in this order)

1. Resolve the repo root with `git rev-parse --show-toplevel` and `cd` to
   it. All subsequent git commands run from the repo root.
2. Run `git status -sb` and `git diff --stat HEAD` to enumerate every
   changed file. Read the actual diffs of any non-trivial files before
   writing the message — the message must reflect the diff, not the
   conversation.
3. Run `git add -A` from the repo root unless the user explicitly
   requested partial staging.
4. Compose the message according to the rules below. Verify mentally
   (or by listing) that every changed file or area appears in either the
   subject's umbrella or one of the body paragraphs.
5. Write the message to `/tmp/commitmsg.txt` using a heredoc or a
   `printf`-style write. Never `echo` a multi-line message with unquoted
   `!` — bash history expansion will break it.
6. Run `git commit -F /tmp/commitmsg.txt`.
7. Confirm with `git log -1 --stat` and report the resulting subject back
   to the user.

Never use `git commit -m` for multi-line messages. Never bypass hooks
(`--no-verify`) unless the user explicitly asks.

## Subject line

- Hard cap **50 characters**.
- An **umbrella** description that encapsulates ABSOLUTELY all changes in
  the diff — reading only the subject must leave no relevant change
  unmentioned.
- **Imperative mood**: "Add", "Improve", "Wire", "Restructure", "Fix".
  Never "Added", "Adding", "Adds".
- Capitalised first word, no trailing period, no Conventional Commits
  prefix unless the repo already uses one.
- If a tight specific subject won't fit 50 chars, use generic umbrella
  language. Example: "Improve admin edit, client cart, and server logic".

## Blank line

A single blank line separates the subject from the body. Always present
when there is a body.

## Body

- Hard cap **74 characters per line**. Wrap at the full 74-char limit —
  do **not** wrap prematurely.
- **Imperative mood throughout**. Write each paragraph as a directive
  describing what the commit does to the codebase: "Add", "Move",
  "Replace", "Tighten", "Wire", "Drop", "Rename".
- **One paragraph per change or area of change**, separated by a single
  blank line. Each paragraph is a self-contained high-level summary of
  one logical change. Together the paragraphs cover every changed file
  or area in the diff with no blindspots.
- **No bullets, no dashes, no asterisks, no numbered lists, no
  indentation as a list marker.** Plain flowing prose only.
- Wrap file paths in backticks, e.g. ``` `src/apps/server/src/index.mjs` ```.
- Mention paths inside natural sentences. Never write bracketed list
  forms like `[src/x.mjs, src/y.mjs]`.
- Pure repo-history voice. Never mention the chat process or iteration —
  no "as discussed", "fix typo from previous attempt", "iterated",
  "refined", "user requested", "I", "we", "now", "currently".

## Trailers

After the body, append a blank line and the trailer:

```
Is-ai-assisted-commit-message: true
```

Combine with other trailers (`Co-authored-by:`, `Closes #N`, etc.) in the
same trailer block, separated from the body by a single blank line.

If the diff is a one-file trivial change with no body, still emit the
trailer block on its own after a blank line.

## What NEVER goes in

- Bullets, dashes, asterisks, indentation as list markers.
- Bracketed path lists like `[file1, file2]`.
- "This commit", "Now", "Currently", first-person pronouns.
- Conversational refinement language ("as requested", "after discussion").
- AI tool attribution beyond the required trailer.
- Past-tense or progressive verbs in subject or body.

## Examples

Diff touches admin Edit modal SCSS, MenuItem decrement logic, a new server
route, and the route registry.

Subject:

```
Improve admin edit, cart UX, and orders routes
```

Body (each paragraph = one area; wrapped at 74 chars):

```
Tighten Remove Choice and Remove Group corner morphing on the admin
Edit modal in
`src/apps/client/src/components/pages/Menu/Content/MenuItem/Edit/Edit.module.scss`
so the buttons sit flush in the option group card corners. Split out
a dedicated `.buttonAddChoice` class so Add Choice keeps its 25% width
while Add Group fills its row.

Open the Selection view in manage mode when the cart minus button is
pressed on an item with option groups in
`src/apps/client/src/components/pages/Menu/Content/MenuItem/MenuItem.jsx`.
Skip the confirm-remove modal for pending instances inside the
Selection view via the new `onInstanceRemoveSkipConfirm` prop.

Add a `DELETE /v1/orders/clear-history` endpoint in
`src/apps/server/src/routes/v1/orders/clear-history/index.mjs` and
register it in the manual route table at
`src/apps/server/src/routes/index.mjs` for the Cloudflare Workers
build path.

Is-ai-assisted-commit-message: true
```

Diff is a single typo fix in one file:

```
Fix typo in admin edit validation message

Is-ai-assisted-commit-message: true
```

Subject alone covers the whole change; no body paragraphs needed. The
trailer block still appears after a blank line.

## Boundaries

This skill writes the message AND runs the commit. It does not push, force
push, amend published commits, or rewrite history. If the user asks for any
of those, confirm explicitly before proceeding.

If `git status` shows merge conflicts or a detached HEAD, stop and surface
that to the user before staging or committing.
