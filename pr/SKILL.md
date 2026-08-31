---
name: pr
description: Use when the user asks to open, write, or draft a pull request, or when a PR title and body must be written. Writes the PR like a changelog entry in ASD-STE100 Simplified Technical English, then opens it with gh.
allowed-tools: Bash, Read, Write, Grep, Glob
---

# pr

Write the pull request as a changelog entry in ASD-STE100 Simplified Technical English (STE), then open it with gh.

1. Inspect `git log <base>..HEAD` and `git diff <base>...HEAD`; the base is the default branch unless the user names one. Find the issue in the branch name, the commit footers, or the user's message; none found: ask once, then write `No issue` and why.
2. Run `python <skill-dir>/scripts/prdiagram.py changes . <base> HEAD -o <tmp>/pr-changes.drawio --png` (`<skill-dir>` = this skill's folder; `<tmp>` = the OS temp dir; quote paths with spaces; `python3` where `python` is absent). It prints the change graph and writes the diagram; the `.png` appears only when draw.io desktop is installed. A non-zero exit prints one line that says why; fix the input and run again.
3. Title: one STE sentence that names the outcome, ≤72 chars, no type prefix, no period.
4. Body, in this order:
   - `## Context`: the important changes, one bullet each, most important first. Start each bullet with Add, Change, Fix, or Remove.
   - `> **NOTE:**` under any bullet with something of note: a breaking change, a migration, a workaround, a side effect that the title does not show, a security or performance effect.
   - `## Changes`: first the summary diagram. Write `<tmp>/pr-summary.json`: `{"title": <the PR title>, "commits": [{"sha", "subject", "changes": ["Add …", …]}]}`, one to three changes per commit, ≤5 words each, first word Add, Change, Fix, or Remove. Run `prdiagram.py summary <tmp>/pr-summary.json -o <tmp>/pr-summary.drawio --png` and write `<!-- attach pr-summary.drawio.png -->`. Then the change graph in a code block; after each file add ` — <what changed>`, ≤6 words, when the file name does not say it. Then `<!-- attach pr-changes.drawio.png -->` (the `.drawio` when there is no `.png`).
   - `## Design`, only when the diff adds, removes, or rewires a component (a module, a service, or a dependency between them). Write `<tmp>/pr-design.json`: `before` and `after`, each `{"nodes": [{"id", "label"}], "edges": [[from, to]]}`; the same `id` on both sides is the same component. Run `prdiagram.py design <tmp>/pr-design.json -o <tmp>/pr-design.drawio --png`. One bullet per component added, removed, or rewired, then the attach comment.
   - `## Rationale`: one or two lines on why. No rationale: the issue link is mandatory.
   - `## Watch for`: what a reviewer must check, one bullet each.
   - `## Visuals`, only when the diff changes UI files: a screenshot or a recording. Ask the user for one if you cannot capture it and leave `<!-- add screenshot -->`.
   - Last line: `Closes #<id>` or `Refs #<id>`.
5. STE: active voice, present tense, one idea per sentence, ≤20 words, articles before nouns, no contractions, no -ing verbs, noun clusters ≤3 words. Write change (not update, modify), make sure (not ensure, verify), must (not should), let (not allow, enable), use (not utilize), before (not prior to), for example (not e.g.).
6. Push the branch if it has no upstream, then `gh pr create --title "<title>" --body-file <file>` and show the URL. No gh or no remote: print the title and the body. End with the paths of the diagram files so the user can drag them into the PR. The author is the user; write no AI attribution.
