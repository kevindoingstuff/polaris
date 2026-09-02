# The module doc

Every `docs/<module>.md` has this shape. Module-level headings are `##`, in this order. Components nest as `###` inside `## Components`, their parts as `####`. Two module sections are conditional: Data flow (only with a flow) and Drift (only with conflicts).

````markdown
---
module: trainer
generated_from: 3c13dab69f44c61cbe762c353b3841ae250004f9
generated_at: 2026-08-31
---

# trainer

One paragraph: what the module is for, in the vocabulary of the design docs. Two to four sentences.

## Purpose and public interface

What the module does and what it exposes to the rest of the system: exported functions, routes, CLI commands, events it publishes. One row per entry point.

| Entry point | Kind | What it does | Source |
|---|---|---|---|
| `python -m trainer.pipeline` | command | Runs the training pipeline end to end | `trainer/pipeline.py:55` |

## Where it fits

![trainer in the system](diagrams/trainer/system.drawio.png)

Two to four sentences: who calls this module, what it calls, what it owns (its tables, queues, files).

## Quick start

A runbook, three parts, each a short list:

**Start it**: the command and where to run it, quoted from `package.json`, `Makefile`, `Dockerfile`, or `Procfile`. A module with no command of its own (a library, a helper package): name the process it runs inside and cite that process's command.

```
npm run train            (from package.json:7)
```

**Configure it first**: only the variables the module needs before it runs at all, with the default the code gives each.

- `DATA_PATH`: the input rows, default `data/orders.jsonl` (from trainer/pipeline.py:7)

**Where things go**: log files, output folders, tables written.

- Metrics: `out/model/metrics.json` (from trainer/pipeline.py:53)

## Components

![trainer components](diagrams/trainer/components.drawio.png)

The overview diagram shows every component, then one `### <component>` per component, ordered by the flow. Heading names match the diagram.

### validate

One or two sentences: what the component is and does (from trainer/pipeline.py:12).

![validate](diagrams/trainer/validate.drawio.png)

#### Inputs and outputs

- In: raw rows from `DATA_PATH` (from trainer/pipeline.py:12)
- Out: the same rows, or `ValueError` on a bad row (from trainer/pipeline.py:14)

#### Configuration

| Name | Type | Default | Where read |
|---|---|---|---|
| `EPOCHS` | number | `3` | `trainer/pipeline.py:28` |

#### Things to note

- The seed is hardcoded to `1337`: runs repeat, they do not vary (from trainer/pipeline.py:9).

## Data flow

![the pipeline](diagrams/trainer/sequence.drawio.png)

Numbered steps for the flow in the diagram, one sentence each, each with its source.

1. `main` loads the rows from `DATA_PATH` (from trainer/pipeline.py:47).
2. `validate` rejects the run on a bad row (from trainer/pipeline.py:14).

## Drift

One bullet per conflict, both citations, which side the doc follows.

- `ARCHITECTURE.md:14` says auth validates sessions against Redis. The code verifies a JWT with `JWT_SECRET` (`src/auth/verify.js:6`). This doc follows the code.
````

## Components

What a component is: a direct child folder or top-level file of the module source. The traced flow overrides when it shows a clearer logical split: a `main` that validates, augments, trains, and evaluates is four components, even in one file. Each unit then cites where it lives.

Per component, in order:

- The heading, then one or two cited sentences.
- The sub-diagram, only when the component has three or more internal units or a flow of its own; kind and file name per [`diagrams.md`](diagrams.md). A one-file helper gets none.
- `#### Inputs and outputs`: always present. Plain lines under three entries, a table from three.
- `#### Configuration`: only when the component reads any. At most 15 variable rows; the overflow becomes one pointer row naming the defining file. A variable read by one component belongs to that component, not to Quick start (which keeps only the boot-critical ones).
- `#### Things to note`: only with notes. A note is a cited fact that would trip a user: an ordering constraint, a side effect, a hardcoded value, a surprising default.

## Keep blocks

A reader who edits a doc by hand wraps the part to protect:

```markdown
<!-- keep -->
Anything here survives an update, verbatim.
<!-- /keep -->
```

On update, each block goes back at the end of the section whose heading it was found under, at any level (`##`, `###`, `####`). Heading gone from the new doc: the block is appended at the end of the doc under that original heading. The rest of a hand edit outside a keep block does not survive.

## Citations

Every snippet, command, path, and config name carries its source: `(from path:line)` after prose, a `Source` column in tables, the path in a comment after a command. A line number for a symbol or a read; a path alone for a whole file.

## The index

`docs/README.md`, rebuilt every run:

````markdown
# Docs

![system](diagrams/system.drawio.png)

| Module | Purpose | Doc | Generated from |
|---|---|---|---|
| api | Serves the HTTP API | [api.md](api.md) | `3c13dab` |

Refresh with `/docs update`.
````

The Purpose column is the first sentence of each doc's opening paragraph.

## Prose

Active voice, present tense, short sentences, articles kept, no contractions. Longer titles and more words are fine when they help the reader. Clauses are separated with a colon, a comma, or a new sentence.

| Write | Not |
|---|---|
| The server reads `PORT` at start. | `PORT` is read by the server at start. |
| The worker polls the queue: it does not read the table. | The worker polls the queue — it doesn't read the table. |
| Set `DATABASE_URL` before you start the server. | Ensure `DATABASE_URL` is configured prior to startup. |
