---
name: commit
description: Use when the user asks to commit, or when a git commit message must be written. Writes the message in ASD-STE100 Simplified Technical English with the Conventional Commits format, then commits.
allowed-tools: Bash, Read, Grep, Glob
---

# commit

Write the commit message in ASD-STE100 Simplified Technical English (STE) and the Conventional Commits format, then commit.

1. Inspect: `git status --short`, `git diff --cached`. Nothing staged: review `git diff`, stage the files that belong to the work, leave secrets and scratch files, tell the user what you staged.
2. Split: one commit per change. A breaking change, a fix, a feature, and a dependency change are four commits, even when they touch the same file.
3. Header `<type>(<scope>)!: <description>`: one imperative STE sentence with its articles, no period, ≤72 chars. Types: feat, fix, refactor, perf, docs, test, build, ci, style, chore, revert.
4. Body: what changed and why. Footers only: `BREAKING CHANGE:` (required with `!`), `Refs:`, `Closes:`, `Reverts:`. The author is the user; write no other trailer.
5. STE: active voice, present tense, one idea per sentence, ≤20 words, articles before nouns, no contractions, no -ing verbs, noun clusters ≤3 words. Write change (not update, modify), make sure (not ensure, verify), must (not should), let (not allow, enable), use (not utilize), before (not prior to), for example (not e.g.).
6. Commit with a quoted heredoc; show `git log -1 --format=%B`.
