---
name: docstring
description: Use when the user asks to fix, clean up, rewrite, add, or audit docstrings, wants Google style docstrings, or types /docstring. Cuts implementation narration, redundant type text and changelog cruft, writes the docstrings that are missing, and corrects or completes the ones that do not match the code.
argument-hint: "<file, directory, or nothing for the current diff>"
---

# docstring

Reconcile every docstring — module, class, function — with its body, in PEP 257
+ Google style. The docstring carries the **interface contract**: what a caller
must know without reading the body, and nothing else.

Target = the argument, else the files in `git diff` (else `git diff HEAD~1`).

## Cut

- **Narration** — loops, locals, algorithm steps, complexity. Delete it; do not
  move it to a comment and do not restate it as contract.
- **Prose types** on an annotated signature — `timeout (int): seconds` becomes
  `timeout: seconds`. Parenthesised types survive only where annotations do not.
- **Signature echo** — a summary respelling the name, or an `Args:`/`Returns:`/
  `Yields:` entry that renames the parameter or repeats the summary. Delete it;
  never pad it. Keep an entry only where deleting it loses a fact stated nowhere
  else in the docstring or the signature: a unit, a range, a meaning, `unused`.
- **`Args:` is all or nothing.** A section listing some parameters and not
  others reads as an oversight, renders as a hole in the Sphinx parameter
  table, and trips `D417`. If one parameter carries a fact, list every
  parameter and keep the echoes to a few bare words. If none does, delete the
  whole section and put any single fact in the summary or one line under it.
  Never a partial table. The same applies to `Attributes:`.
- **Cruft** — changelogs, dates, authors, tickets, `TODO`, design rationale,
  assistant boilerplate ("Certainly! Here is"), marketing ("robust",
  "gracefully handles"), hedging ("should generally", "if applicable").

## Reconcile

- **Absent** — write one. A public object always gets a docstring; `__init__`,
  other dunders, and a `_private` helper whose name and signature already say
  everything may stay bare.
- **Wrong** — correct it to what the body does.
- **Silent** — add the fact the body proves. Change only what the addition
  needs, keep the wording that is already right, and apply the Cut rules to what
  you keep. A docstring that reads well is the usual hiding place for a missing
  fact, so check it against the body instead of reading it.

Take each object through the list below before you move on, a class and a
generator as well as a function. A sentinel in the signature or in `Attributes:`
(`x: int | None = None`) always needs its meaning.

The facts worth adding are the ones a caller cannot see in the signature: a
raise the caller can hit, a mutated argument or other side effect, a unit the
name does not carry, what a sentinel means on a parameter, an attribute or a
return (`None` means no limit, `None` on a miss), a precondition the caller can
violate, and how a generator ends. A class or dataclass carries the same duty in
`Attributes:`. Add nothing else.

The same list governs a docstring you write from scratch. State the unit, not
the formula: `base * 2**attempt` is the implementation; "seconds" is the
contract.

## Prove it

Trace before you assert. A `Raises:` entry needs a `raise` in the body or in
something the body calls; never infer one from a type, a range, or a name. A
parameter the body never reads is documented `unused`, never given an invented
purpose. A doctest survives only if you traced
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
`path: N rewritten, M added, K untouched`.
