# What a module is

A module is one folder the docs describe as a unit. Detection runs per language, in this order; the first rule that yields modules wins for that language. Several languages in one repo: run each, then merge.

| Language | Signal | Modules |
|---|---|---|
| JS / TS | `package.json` with `workspaces` | every folder the globs match |
| JS / TS | `src/` | every `src/<dir>` that has an `index.*` or two or more source files |
| JS / TS | `packages/`, `apps/` | every direct child |
| Python | packages | every folder with `__init__.py` whose parent has none (the top-level packages), searched from the repo root and `src/` |
| Go | `cmd/`, `internal/`, `pkg/` | every direct child of each |
| Rust | `Cargo.toml` with `[workspace]` | every `members` entry |
| Rust | single crate | `src/bin/*` each as one module, plus `src/` as one |
| Any | fallback | the top-level folders of `src/`, else of the repo, that hold source files |

Exclude always: `node_modules`, `dist`, `build`, `target`, `vendor`, `.venv`, `venv`, `__pycache__`, `.git`, `coverage`, `*.egg-info`, `docs`, and every folder `.gitignore` lists.

## Ids and paths

- Module id: the folder name, lowercased. Two languages give the same id: suffix the language (`api`, `api-py`).
- Module paths: the folder, plus a sibling test folder when one exists (`tests/<id>`, `test/<id>`, `<folder>/tests`). These paths feed `git diff --stat` in the update check.

## The picker

One `AskUserQuestion` call holds four questions of four options each, so 16 modules fit in one call; more modules: a second call. Headers: `Modules 1-4`, `Modules 5-8`, and so on. `multiSelect: true` on every question.

The tool adds an "Other" field on its own. A user types missed modules there as `name=path`, comma separated: `billing=src/legacy/billing, cli=tools/cli`. Each pair becomes a module with that id and path.
