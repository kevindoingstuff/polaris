---
name: docs
description: Use when the user asks to document the codebase, write or update the docs, generate module documentation, a user guide, an architecture doc, a Sphinx docs site, or a system map, or types /docs. Reads the code and the design docs that exist, then writes a user-guide-first docs/<module>.md per module with draw.io diagrams, and a Sphinx (MyST) site for Python repos or docs/README.md as the index otherwise.
argument-hint: "[update | create <module>... | <module>...]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion
---

# docs

Writes `docs/<module>.md` per module (operator guide first, cited reference last), its diagrams (`.drawio` plus `.drawio.png`), and the index. Python repos run in Sphinx mode: MyST markdown, `docs/index.md`, a scaffolded `conf.py` when none exists, diagrams under `docs/_static/diagrams/`. Other repos run plain mode: `docs/README.md`, diagrams under `docs/diagrams/`. Areas run in order. Details: [`references/modules.md`](references/modules.md) (what a module is), [`references/template.md`](references/template.md) (the doc and what a component is), [`references/sphinx.md`](references/sphinx.md) (the mode, scaffold, index, guide page), [`references/diagrams.md`](references/diagrams.md) (the diagram specs). `<skill-dir>` is this skill's folder (quote paths with spaces; `python3` where `python` is absent). `<tmp>` is the OS temp dir. `<img>` is the diagram root for the mode.

Rules for the whole run:

- Output: one short line per area, like `targets: api (update), auth (create)`, plus the warning lines an area names. Nothing else.
- Make no commits. The user reviews with `git diff -- docs/`.
- Cited or absent: every snippet, command, path, key, and schema field in a doc is quoted from a real file and carries its source where `references/template.md` puts it. A fact with no source stays out.

## 0. Survey

Read, do not ask: `git rev-parse HEAD`; `git status --porcelain` (a dirty file under a module: one warning line, the stamp is still HEAD); ecosystem files (`package.json` and its `workspaces`, `pyproject.toml`, `go.mod`, `Cargo.toml` and its `[workspace]`); the mode: Python present: sphinx, and `docs/conf.py` present: existing setup, else scaffold; no Python: plain; stamped docs (`grep -l '^generated_from:' docs/*.md`); design docs (`README.md`, `ARCHITECTURE.md`, `CONTEXT.md`, `docs/adr/`, `adr/`, `design/`, `notebooks/*.md`, and `docs/**/*.md` without a stamp, at most 20 by size: a stamped doc is output, never a source); a plain-mode `docs/README.md` or a Sphinx-mode `docs/index.md` without a stamp: one warning line, the file is left alone; modules per `references/modules.md` (a detected package with no source beyond `__init__.py` is dropped with one warning line).

Done when you have the module list with paths, the mode, and the design doc list. Line: `survey: python, 5 modules, 2 stamped, mode: sphinx (scaffold), design docs: README.md notebooks/data_pipeline.md`.

## 1. Targets

- No argument: the picker. One `AskUserQuestion` call, `multiSelect: true`, four options per question, as many questions as the modules need (four per call at most; more than 16 modules: a second call). Option label = module id; description = its path, then the first line of its own README, docstring, or `package.json` description when it has one. The tool's own "Other" field takes modules the detection missed as `name=path`, comma separated; each becomes a module at that path; a path with no tracked source file is skipped with one warning line.
- `update`: every stamped doc, mode update.
- `create <m>...`: those modules, mode create, even when a stamped doc exists.
- `<m>...`: those modules; a stamped doc exists: update; else create.
- A name that matches no module id or path: print the detected list, ask once which path it is.

Done when every target has a mode. Line: `targets: api (update), auth (create), shared (update)`.

## 2. Guide

`docs/get_started.md` exists: skip, no line. Else one `AskUserQuestion` call, two questions, both with a **Skip** option first and the real answers typed into "Other": (1) header `Setup`: "How does a new user set up their environment? Tools to install, credentials, proxies, cloud profiles." (2) header `First task`: "What does a new user run first, and what should they see?" Both skipped, or the first skipped: no guide page, line `guide: skipped`. Else the page is written in area 6 per `references/sphinx.md`; line `guide: get_started.md`.

Done when the two answers are held or the page is skipped.

## 3. Update check

Update-mode targets only. Read `generated_from` from the doc's frontmatter. `git cat-file -e <sha>` fails: the module counts as changed. Else `git diff --stat <sha>..HEAD -- <module paths>`; empty output: skip the module, line `shared: unchanged since <sha7>`. Changed: no line; hold every `<!-- keep -->` ... `<!-- /keep -->` block together with the heading it sits under, at any level.

Done when every update target is changed or skipped, and the keep blocks of the changed ones are held.

## 4. Read

Design docs first. Per target note the vocabulary (the names the docs use), the boundary (what the doc says the module owns and does not own), and the stated flows. Then the code: entry points (`main`, the Python `__main__` guard, exported symbols, route tables, job and event handlers); start commands (`package.json` scripts, `Makefile`, `justfile`, `Dockerfile`, `Procfile`, notebooks that call the module); config reads (`process.env.X`, `os.environ`, `os.Getenv`, `env::var`, config file loaders, CLI flags); every file, table, bucket path, queue, or request the module reads and writes, with its schema where the code states one (dataframe columns, dataclass and pydantic fields, TypedDict, JSON schema files, config keys, CLI arguments, route bodies); log and output paths; imports of the other modules.

Then the components, per `references/template.md`: the direct child folders and top-level files of the module source, unless the traced flow shows a clearer logical split (a `main` that validates, augments, trains, evaluates is four components in one file). Per component: inputs, outputs, config reads, and the notes per `references/template.md` (a cited fact that contradicts the docs, the config, or a sibling module; at most three per module), each with `path:line`.

A conflict is one fact a design doc states and the code contradicts: a name, a boundary, a dependency, a flow, a config name or default. One sentence with two wrong facts is two conflicts; the same wrong fact stated twice is one. A conflict belongs to the module whose code contradicts it.

Done when each target has its stages, its input and output list with schemas, its component list, a fact list per component where every fact carries `path:line`, and a conflict list (empty is fine).

## 5. Drift

Conflicts exist: one `AskUserQuestion` call per four conflicts. Per question: header = module id; question = `<doc path> says "<claim>". The code does <fact> (<path:line>). Which does the doc follow?`; options **The code** (the design doc is stale) and **The design doc** (the code is behind). The answer is the fact the doc states; the doc records no conflict of its own. No conflicts: no question.

Done when every conflict has an answer. Line: `drift: 2 conflicts, 2 follow the code`.

## 6. Diagrams

Write the specs in `<tmp>` per `references/diagrams.md`. `system.json` once per run: every detected module plus the external systems the code reaches (a connection, a request, a file outside the repo; a variable that is read and never used is not a system), reused for every highlight. Then run:

```
python <skill-dir>/scripts/docsdiagram.py system <tmp>/system.json -o docs/<img>/system.drawio --png
python <skill-dir>/scripts/docsdiagram.py system <tmp>/system.json -o docs/<img>/<m>/system.drawio --highlight <m> --png
python <skill-dir>/scripts/docsdiagram.py components <tmp>/<m>-components.json -o docs/<img>/<m>/components.drawio --png
python <skill-dir>/scripts/docsdiagram.py sequence <tmp>/<m>-sequence.json -o docs/<img>/<m>/sequence.drawio --png
python <skill-dir>/scripts/docsdiagram.py flow <tmp>/<m>-<c>.json -o docs/<img>/<m>/<c>.drawio --png
```

Every graph spec uses the node vocabulary in `references/diagrams.md`: the data a step reads or writes is a `data` node with a `role`, config is a `config` node, a function's steps share a `group`, and a `note` carries the format or path. `sequence` only when the module handles a request, a job, or an event itself; a module that only answers calls from another module has none. One flow, the main one. A component with three or more internal units or a flow of its own gets a sub-diagram (`components`, `flow`, or `sequence` per `references/diagrams.md`); fewer: none. A non-zero exit prints one line that says why: fix the spec, run again. No `.png` (draw.io desktop absent): link the `.drawio` and name it in area 8.

Done when every target has `system.drawio` and `components.drawio` (plus `.png` when draw.io is present), `sequence.drawio` when it has a flow, every gated component its sub-diagram, and `docs/<img>/system.drawio` exists.

## 7. Write

`docs/<m>.md` from `references/template.md`, the stamp first:

```
---
module: <id>
generated_from: <full sha from git rev-parse HEAD>
generated_at: <YYYY-MM-DD>
---
```

Title `# <Module name> User Guide`. Module sections as `##`, in this order: Overview; Inputs and Outputs; Folder Structure; Quickstart (with its `### Configuration` table); Components (summary table, then one `###` per component with `#### Inputs and Outputs` always, `#### Configuration` and `#### Things to Note` when earned); Data Flow (only with a flow). Held keep blocks return verbatim at the end of their section; heading gone: append them at the end of the doc under the original heading. Image links are relative to `docs/`.

Prose per the Prose section of `references/template.md`: second person for the reader, purpose before names, the reason beside a surprising choice, an example beside every Quickstart variable, no dashes.

Then the guide page when area 2 held answers, per `references/sphinx.md`. Then the index. Sphinx mode, scaffold: `conf.py`, `reference/api.rst`, the doc dependencies, and `index.md` per `references/sphinx.md`. Sphinx mode, existing setup: `index.md` only when it carries the stamp or is absent, else the toctree warning lines. Plain mode: `docs/README.md` rebuilt every run: the system map, a table (module, purpose, doc link, sha7) from the frontmatter and Overview paragraph of every stamped doc, then the line `Refresh with /docs update.`

Done when each target doc has the headings in order, the stamp, a citation on every table row, command, and note, every component its subsection, and the index lists every stamped doc.

## 8. Report

One line per `.drawio` that has no `.png`, when any. Sphinx mode: the line `build: sphinx-build -b html docs docs/_build` (scaffold: preceded by `install: uv sync --group docs` or `pip install -r docs/requirements.txt`), then the line `view: python -m http.server -d docs/_build 8000, then open http://localhost:8000`. Then the last line: `docs: api updated, auth created, shared unchanged; review with git diff -- docs/`.
