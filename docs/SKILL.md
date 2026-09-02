---
name: docs
description: Use when the user asks to document the codebase, write or update the docs, generate module documentation, an architecture doc, or a system map, or types /docs. Reads the code and the design docs that exist, then writes docs/<module>.md per module with draw.io diagrams and docs/README.md as the index.
argument-hint: "[update | create <module>... | <module>...]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion
---

# docs

Writes `docs/<module>.md` per module, its diagrams under `docs/diagrams/<module>/` (`.drawio` plus `.drawio.png`), and `docs/README.md` as the index. Areas run in order. Details: [`references/modules.md`](references/modules.md) (what a module is), [`references/template.md`](references/template.md) (the doc and what a component is), [`references/diagrams.md`](references/diagrams.md) (the diagram specs). `<skill-dir>` is this skill's folder (quote paths with spaces; `python3` where `python` is absent). `<tmp>` is the OS temp dir.

Rules for the whole run:

- Output: one short line per area, like `targets: api (update), auth (create)`, plus the warning lines an area names. Nothing else.
- Make no commits. The user reviews with `git diff -- docs/`.
- Cited or absent: every snippet, command, path, and config name in a doc is quoted from a real file and carries `(from path:line)`. A fact with no source stays out.

## 0. Survey

Read, do not ask: `git rev-parse HEAD`; `git status --porcelain` (a dirty file under a module: one warning line, the stamp is still HEAD); ecosystem files (`package.json` and its `workspaces`, `pyproject.toml`, `go.mod`, `Cargo.toml` and its `[workspace]`); the diagram engine: `dot -V` succeeds and the `drawio-skill` skill is listed: engine = drawio-skill, else engine = script; stamped docs (`grep -l '^generated_from:' docs/*.md`); design docs (`README.md`, `ARCHITECTURE.md`, `CONTEXT.md`, `docs/adr/`, `adr/`, `design/`, and `docs/**/*.md` without a stamp: a stamped doc is output, never a source); modules per `references/modules.md`.

Done when you have the module list with paths and the design doc list. Line: `survey: node+python, 4 modules, 2 stamped, engine: script, design docs: README.md ARCHITECTURE.md`.

## 1. Targets

- No argument: the picker. One `AskUserQuestion` call, `multiSelect: true`, four options per question, as many questions as the modules need (four per call at most; more than 16 modules: a second call). Option label = module id; description = its path, then the first line of its own README, docstring, or `package.json` description when it has one. The tool's own "Other" field takes modules the detection missed as `name=path`, comma separated; each becomes a module at that path.
- `update`: every stamped doc, mode update.
- `create <m>...`: those modules, mode create, even when a stamped doc exists.
- `<m>...`: those modules; a stamped doc exists: update; else create.
- A name that matches no module id or path: print the detected list, ask once which path it is.

Done when every target has a mode. Line: `targets: api (update), auth (create), shared (update)`.

## 2. Update check

Update-mode targets only. Read `generated_from` from the doc's frontmatter. `git cat-file -e <sha>` fails: the module counts as changed. Else `git diff --stat <sha>..HEAD -- <module paths>`; empty output: skip the module, line `shared: unchanged since <sha7>`. Changed: no line; hold every `<!-- keep -->` ... `<!-- /keep -->` block together with the heading it sits under, at any level.

Done when every update target is changed or skipped, and the keep blocks of the changed ones are held.

## 3. Read

Design docs first. Per target note the vocabulary (the names the docs use), the boundary (what the doc says the module owns and does not own), and the stated flows. Then the code: entry points (`main`, the Python `__main__` guard, exported symbols, route tables, job and event handlers); start commands (`package.json` scripts, `Makefile`, `Dockerfile`, `Procfile`); config reads (`process.env.X`, `os.environ`, `os.Getenv`, `env::var`, config file loaders, CLI flags); log and output paths; imports of the other modules.

Then the components, per `references/template.md`: the direct child folders and top-level files of the module source, unless the traced flow shows a clearer logical split (a `main` that validates, augments, trains, evaluates is four components in one file). Per component: inputs, outputs, config reads, and the facts that would trip a user (an ordering constraint, a side effect, a hardcoded value, a surprising default), each with `path:line`.

A conflict is one fact a design doc states and the code contradicts: a name, a boundary, a dependency, a flow, a config name or default. One sentence with two wrong facts is two conflicts; the same wrong fact stated twice is one. A conflict belongs to the module whose code contradicts it.

Done when each target has its component list, a fact list per component where every fact carries `path:line`, and a conflict list (empty is fine).

## 4. Drift

Conflicts exist: one `AskUserQuestion` call per four conflicts. Per question: header = module id; question = `<doc path> says "<claim>". The code does <fact> (<path:line>). Which does the doc follow?`; options **The code** (the design doc is stale) and **The design doc** (the code is behind). No conflicts: no question.

Done when every conflict has an answer. Line: `drift: 2 conflicts, 2 follow the code`.

## 5. Diagrams

Engine drawio-skill (Graphviz and the plugin present): `Call the Skill tool with "drawio-skill"` and ask it for the same charts into the same paths: the system map from the module list with `<m>` highlighted (`autolayout.py`, or `c4.py` for the highlighted view), the components of `<m>` from its imports (`pyimports`, `jsimports`, `goimports`, `rustimports`, `pyclasses`, as the language needs), the sequence with `seqlayout.py`, and the gated component sub-diagrams below. Same file names, same gates, PNG export on. Then skip to Done.

Engine script: write the specs in `<tmp>` per `references/diagrams.md`. `system.json` once per run: every detected module plus the external systems the code reaches (a connection, a request, a file outside the repo; a variable that is read and never used is not a system), reused for every highlight. Then run:

```
python <skill-dir>/scripts/docsdiagram.py system <tmp>/system.json -o docs/diagrams/system.drawio --png
python <skill-dir>/scripts/docsdiagram.py system <tmp>/system.json -o docs/diagrams/<m>/system.drawio --highlight <m> --png
python <skill-dir>/scripts/docsdiagram.py components <tmp>/<m>-components.json -o docs/diagrams/<m>/components.drawio --png
python <skill-dir>/scripts/docsdiagram.py sequence <tmp>/<m>-sequence.json -o docs/diagrams/<m>/sequence.drawio --png
python <skill-dir>/scripts/docsdiagram.py flow <tmp>/<m>-<c>.json -o docs/diagrams/<m>/<c>.drawio --png
```

`sequence` only when the module handles a request, a job, or an event itself; a module that only answers calls from another module has none. One flow, the main one. A component with three or more internal units or a flow of its own gets a sub-diagram (`components`, `flow`, or `sequence` per `references/diagrams.md`); fewer: none. A non-zero exit prints one line that says why: fix the spec, run again. No `.png` (draw.io desktop absent): link the `.drawio` and name it in area 7. Either engine may add extra charts (ERD, C4) to the same folder; the script engine needs nothing beyond Python and draw.io desktop.

Done when every target has `system.drawio` and `components.drawio` (plus `.png` when draw.io is present), `sequence.drawio` when it has a flow, every gated component its sub-diagram, and `docs/diagrams/system.drawio` exists.

## 6. Write

`docs/<m>.md` from `references/template.md`, the stamp first:

```
---
module: <id>
generated_from: <full sha from git rev-parse HEAD>
generated_at: <YYYY-MM-DD>
---
```

Module sections as `##`, in this order: Purpose and public interface; Where it fits; Quick start (boot-critical variables only); Components (one `###` per component with `#### Inputs and outputs` always, `#### Configuration` and `#### Things to note` when earned, per the template); Data flow (only with a flow); Drift (only with conflicts). Held keep blocks return verbatim at the end of their section; heading gone: append them at the end of the doc under the original heading. Image links are relative to `docs/`: `![api components](diagrams/api/components.drawio.png)`.

Prose: active voice, present tense, short sentences, articles kept, no contractions. Longer titles and more words are fine when they make a section easier to read. Separate clauses with a colon, a comma, or a new sentence (no dashes).

`docs/README.md` is rebuilt every run: the system map, a table (module, purpose, doc link, sha7) from the frontmatter and first paragraph of every stamped doc, then the line `Refresh with /docs update.`

Done when each target doc has the headings in order, the stamp, a citation on every snippet and note, every component its subsection, and `docs/README.md` lists every stamped doc.

## 7. Report

One line per `.drawio` that has no `.png`, when any. Then the last line: `docs: api updated, auth created, shared unchanged; review with git diff -- docs/`.
