<h1 align="center">Polaris</h1>

<p align="center">Every sailor who ever crossed a dark sea knew one thing: find the star that does not move, and you will not be lost.</p>

<p align="center"><img src=".github/polaris.png" alt="Star trails circle the night sky. Every star moves except Polaris at the centre." width="100%"></p>

Polaris is that star for the agent: small folders of instructions that tell
it how to do a job well. When the agent is moving fast, the ground shifts, the
map runs out, and it is easy to drift. These skills hold still. The agent does
not need to know the whole route. It only needs the star.

Each folder is one skill: a `SKILL.md` with YAML frontmatter and instructions, plus any supporting files.

| Skill | What it does | Invoke |
|---|---|---|
| [`commit`](commit/SKILL.md) | Writes the commit message in ASD-STE100 Simplified Technical English with the Conventional Commits format, splits unrelated changes into separate commits, then commits. | `/commit`, or say "commit this" |
| [`pr`](pr/SKILL.md) | Writes the pull request like a changelog entry in ASD-STE100 STE (context, NOTE callouts, rationale, watch for, issue link), draws the changes (summary of every change per commit or theme, before/after design), then opens it with `gh`. | `/pr`, or say "open a PR" |
| [`docs`](docs/SKILL.md) | Reads the code and the design docs that exist, then writes a user guide per module (`docs/<module>.md`): stages, inputs and outputs, quickstart, per-component sections, draw.io diagrams (system map, components, flows, sequences), and drift questions when a design doc and the code disagree. Python repos get a Sphinx (MyST) site; other repos get `docs/README.md` as the index. | `/docs`, or say "document this codebase" |
| [`docstring`](docstring/SKILL.md) | Rewrites Python docstrings to PEP 257 and Google style, and keeps only the interface contract. It removes implementation narration, prose types that repeat the annotations, changelog and author cruft, and every claim that the code does not support. | `/docstring`, or say "clean up these docstrings" |

## How to install the skills

Claude Code loads a skill from `~/.claude/skills/<name>/SKILL.md` (available in every project) or `<project>/.claude/skills/<name>/SKILL.md` (that project only).

**Option 1: copy one skill**

```bash
git clone https://github.com/kevindoingstuff/polaris.git
cp -r polaris/commit ~/.claude/skills/commit
```

**Option 2: clone once, link, and `git pull` to update**

macOS / Linux:

```bash
git clone https://github.com/kevindoingstuff/polaris.git ~/polaris-skills
ln -s ~/polaris-skills/commit ~/.claude/skills/commit
```

Windows (PowerShell, no admin needed):

```powershell
git clone https://github.com/kevindoingstuff/polaris.git $HOME\polaris-skills
New-Item -ItemType Junction -Path $HOME\.claude\skills\commit -Target $HOME\polaris-skills\commit
```

**Option 3: for one project only**

```bash
mkdir -p .claude/skills
cp -r polaris/commit .claude/skills/commit
```

Restart Claude Code after you install. Type `/` to see the skill in the list.

## How to use the skills

### commit

Make your changes, then:

```
> commit this
```

or

```
> /commit
```

The skill inspects the diff, stages the files that belong to the work (it leaves `.env` files and scratch output alone), splits a breaking change, a fix, a feature, and a dependency change into separate commits, and writes each message like this:

```
feat(config)!: replace the timeoutMs option with a timeout in seconds

The timeout option now takes seconds. The default value is 5.

The loader throws an error when a caller passes timeoutMs. This makes
sure that an old configuration does not run with the wrong unit.

BREAKING CHANGE: The timeoutMs option is removed. Use the timeout
option in seconds. For example, change timeoutMs: 5000 to timeout: 5.
```

The author is you. The skill adds no co-author or AI trailer.

### pr

Commit your branch, then:

```
> open a PR
```

or

```
> /pr
```

The skill reads `git log` and `git diff` against the default branch, finds the issue in the branch name or the commit footers, and writes the PR like a changelog entry: a one-sentence title, `## Context` bullets (Add / Change / Fix / Remove) with `NOTE` callouts for breaking changes and side effects, `## Rationale`, `## Watch for`, and `Closes #<id>` or `Refs #<id>` on the last line. Then it runs `gh pr create`. With no `gh` or no remote it prints the title and body instead.

It also draws the change with `scripts/prdiagram.py` (Python 3.8+, no packages):

- **Summary**: the PR title, the commits (or, for a large PR, the themes) left to right, and every change as a coloured chip (Add / Change / Fix / Remove).
- **Change graph**: text in the body, one block per commit with every file:

  ```
  7c47d2c feat(api): enforce limiter in handlers, remove legacy shim
  ├─ Changed  requirements.txt - add redis
  ├─ Changed  src/api/handlers.py - check the limiter before the query
  └─ Removed  src/api/legacy.py
  ```

- **Design**: a before/after component diagram, only when the PR adds, removes, or rewires a component.

The diagrams are `.drawio` files. When [draw.io desktop](https://github.com/jgraph/drawio-desktop/releases) is installed, the skill also exports `.drawio.png` files (editable in draw.io), commits them to an orphan `pr-assets` branch on your remote (`pr-<number>/…`, created on first use, never merged), and puts them in the PR body as images. Without draw.io you get the `.drawio` files only and the body keeps `<!-- attach ... -->` markers.


### docs

From the repo you want documented:

```
> /docs
```

Pick the modules from the picker, or target them with `/docs api worker`. The skill surveys the repo, offers to write a `get_started.md` from two questions, reads the design docs and the code, asks one question per documented claim the code contradicts, then writes `docs/<module>.md` per module. Each doc reads as a user guide first (an overview with the stages, the inputs and outputs with schema tables, the folder structure, a quickstart with its configuration table) and a cited reference last (one section per component with inputs and outputs, configuration, and the notes it earns, plus a data flow).

A Python repo runs in Sphinx mode: MyST markdown, `docs/index.md` as the index, a scaffolded `conf.py` and `reference/api.rst` when the repo has none, diagrams under `docs/_static/diagrams/`. Any other repo runs in plain mode: `docs/README.md` as the index, diagrams under `docs/diagrams/`. Diagrams are `.drawio` files, with `.drawio.png` exports when [draw.io desktop](https://github.com/jgraph/drawio-desktop/releases) is installed.

To read the Sphinx site, install the doc dependencies, build it, and serve it:

```bash
uv sync --group docs          # or: pip install -r docs/requirements.txt
sphinx-build -b html docs docs/_build
python -m http.server -d docs/_build 8000
```

Open http://localhost:8000. The skill prints these commands at the end of a Sphinx run. A plain-mode repo needs none of this: read `docs/README.md` on GitHub.

`/docs update` regenerates only the modules whose code changed since the stamp in each doc; `<!-- keep -->` blocks in a doc survive regeneration. Every fact in a doc carries a `path:line` citation; a fact with no source stays out.

## How to update the skills

```bash
cd ~/polaris-skills && git pull
```

With Option 1 or 3, copy the folder again.
