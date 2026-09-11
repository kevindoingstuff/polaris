---
name: docstring
description: Use when the user asks to fix, clean up, rewrite, or audit docstrings, wants Google style docstrings, or types /docstring. Strips implementation narration, redundant type text, changelog cruft, and claims the code does not support.
argument-hint: "<file, directory, or nothing for the current diff>"
---

# docstring

Rewrite every docstring — module, class, function — to PEP 257 + Google style,
keeping only the **interface contract**: what a caller must know without reading
the body.

Target = the argument, else the files in `git diff` (else `git diff HEAD~1`).

## Cut

- **Narration** — loops, locals, algorithm steps, complexity. Delete it; do not
  move it to a comment and do not restate it as contract.
- **Prose types** on an annotated signature — `timeout (int): seconds` becomes
  `timeout: seconds`. Parenthesised types survive only where annotations do not.
- **Signature echo** — a summary respelling the name, or an `Args:`/`Returns:`/
  `Yields:` entry that only renames what the signature says. Delete the entry;
  never pad it.
- **Cruft** — changelogs, dates, authors, tickets, `TODO`, design rationale,
  assistant boilerplate ("Certainly! Here is"), marketing ("robust",
  "gracefully handles"), hedging ("should generally", "if applicable").

## Keep — only what the body proves

Purpose, non-obvious argument meaning, return meaning, raises, side effects,
units, constraints a caller can violate.

Trace before you assert. A parameter the body never reads is documented
`unused`, never given an invented purpose. A doctest survives only if you traced
it and its output is what the code returns — a stale example is a false claim,
so delete it. Where the body does not settle a question, say nothing.

## Shape

Obvious from the name and signature, no raises, no side effects → one imperative
line, quotes closed on it:

```python
def slugify(text: str) -> str:
    """Return `text` lowercased with non-alphanumerics collapsed to hyphens."""
```

Otherwise: summary, blank line, then only the sections that carry information,
and nothing over ~60 words. `_private` helpers may describe implementation —
that is their contract.

## Output

Docstrings only; leave every line of code untouched. One line per file:
`path: N rewritten, M untouched`.
