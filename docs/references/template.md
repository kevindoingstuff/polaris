# The module doc

Every `docs/<module>.md` has this shape. The operator sections come first (what it does, what goes in and out, how to run it), the cited reference last. The title is `# <Module name> User Guide`. Module-level headings are `##` in Title Case, in this order. Components nest as `###` inside `## Components`, their parts as `####`. Two module sections are conditional: Data flow (only with a flow) and Drift (only with conflicts). `<img>` is `_static/diagrams` in Sphinx mode, `diagrams` in plain mode (see [`sphinx.md`](sphinx.md)).

````markdown
---
module: trainer
generated_from: 3c13dab69f44c61cbe762c353b3841ae250004f9
generated_at: 2026-08-31
---

# Trainer User Guide

## Overview

![trainer in the system](<img>/trainer/system.drawio.png)

The trainer turns your validated order rows into a fitted model and a metrics file, so you can compare runs before you ship one. One paragraph in the domain's words: what it does for the reader, who calls it, what it owns.

The module runs in four stages:

1. **Validate**: rejects rows that miss a field.
2. **Augment**: expands each row into its variants.
3. **Train**: fits the model on the augmented rows.
4. **Evaluate**: scores the model on the held-out split.

You provide the rows under `DATA_PATH`; the trainer produces a model under `out/model/` and a metrics file beside it.

## Inputs and Outputs

### Inputs

1. `data/orders.jsonl` (JSON lines, one order per line)

| Field | Type | Description | Source |
|---|---|---|---|
| `id` | `str` | The order id. | `trainer/pipeline.py:13` |
| `total` | `float` | The order total in cents. | `trainer/pipeline.py:14` |

2. `config.json` (the training keys, see Quickstart)

### Outputs

1. `out/model/model.bin` (the fitted model)
2. `out/model/metrics.json`

| Field | Type | Description | Source |
|---|---|---|---|
| `mae` | `float` | Mean absolute error on the test split. | `trainer/pipeline.py:53` |

## Folder Structure

```
trainer/
├── pipeline.py     # the four stages, main() is the entry point
└── config.json     # training parameters
```

## Quickstart

:::{note}
Put the rows under `DATA_PATH` before you start. The pipeline reads them once at start.
:::

### 1. Point the pipeline at your data

- Set `DATA_PATH` to the rows file (default `data/orders.jsonl`).

### 2. Adjust the training parameters

- Edit `config.json`: `epochs`, `batch_size`, `learning_rate`.

### 3. Run it

```
npm run train        # package.json:7
```

Outputs land in `out/model/`; the log is `logs/train.log`.

### Configuration

| Key | Type | Default | Description | Source |
|---|---|---|---|---|
| `epochs` | `int` | `3` | Passes over the data. | `trainer/config.json:2` |
| `DATA_PATH` | env | `data/orders.jsonl` | The input rows. | `trainer/pipeline.py:7` |

## Components

![trainer components](<img>/trainer/components.drawio.png)

| Component | Lives in | Description |
|---|---|---|
| validate | `trainer/pipeline.py:12` | Rejects rows that miss a field. |
| augment | `trainer/pipeline.py:20` | Expands each row into its variants. |

### validate

One or two sentences: what the component is and does.

![validate](<img>/trainer/validate.drawio.png)

#### Inputs and Outputs

- In: raw rows from `DATA_PATH` (`trainer/pipeline.py:12`)
- Out: the same rows, or `ValueError` on a bad row (`trainer/pipeline.py:14`)

#### Configuration

| Name | Type | Default | Where read |
|---|---|---|---|
| `EPOCHS` | number | `3` | `trainer/pipeline.py:28` |

#### Things to Note

- The seed is hardcoded to `1337`: runs repeat, they do not vary (`trainer/pipeline.py:9`).

## Data Flow

![the pipeline](<img>/trainer/sequence.drawio.png)

Numbered steps for the flow in the diagram, one sentence each, each with its source.

1. `main` loads the rows from `DATA_PATH` (`trainer/pipeline.py:47`).
2. `validate` rejects the run on a bad row (`trainer/pipeline.py:14`).

## Drift

One bullet per conflict, both citations, which side the doc follows.

- `ARCHITECTURE.md:14` says auth validates sessions against Redis. The code verifies a JWT with `JWT_SECRET` (`src/auth/verify.js:6`). This doc follows the code.
````

The fenced example is content only: the rules below never appear in a generated doc.

## Sections

- **Overview**: the system map with this module highlighted, one paragraph, the stages as a numbered list in flow order (each a bold name and one sentence), then one sentence "You provide X; it produces Y". A module with no stages (a library) has the paragraph and the sentence only.
- **Inputs and outputs**: one numbered entry per file, table, queue, or request the module reads, then per one it writes; the format in parentheses. Each entry with a derivable schema gets a table: field, type, description, source. Schema sources: dataframe column assignments and selections, dataclass and pydantic fields, TypedDict and JSON schema files, config keys, CLI arguments, route bodies. Not derivable: the entry alone, no table. Over 20 fields: one row per family with a brace pattern (`{category}_{feature}_{aggregation}_{level}`) cited to the lines that build it, plus the fields outside any family.
- **Folder structure**: a tree of the module folder, one comment per file. Generated folders and caches out.
- **Quickstart**: a callout with the precondition when one exists, then numbered `### N. <verb phrase>` steps from what a first run needs: point at the data, set the keys, run the command, find the outputs. Each step's bullets name the exact variable, key, or file to change. Commands quoted with the source path in a trailing comment. Then `### Configuration`: every key the module reads at start, from config files and the environment, one table; over 15 rows: the boot-critical ones plus one pointer row naming the file.
- **Components**: the components diagram, a summary table (component, where it lives, one sentence), then one `###` per component in flow order. Names match the diagram and the table.
- **Data flow** and **Drift**: as before.

## Components

What a component is: a direct child folder or top-level file of the module source. The traced flow overrides when it shows a clearer logical split: a `main` that validates, augments, trains, and evaluates is four components, even in one file. Each unit then cites where it lives.

Per component, in order:

- The heading, then one or two sentences.
- The sub-diagram, only when the component has three or more internal units or a flow of its own; kind and file name per [`diagrams.md`](diagrams.md). A one-file helper gets none.
- `#### Inputs and Outputs`: always present. Plain lines under three entries, a table from three.
- `#### Configuration`: only when the component reads any. At most 15 variable rows; the overflow becomes one pointer row naming the defining file.
- `#### Things to Note`: rare. A note is a cited fact that contradicts what the reader would assume from the design docs, the config file, or a sibling module: a default that differs between two places, a filter that always runs, a value hardcoded where the config suggests a knob. A raised error, a fixed output order, or any other plain description of what the code does is not a note. At most three notes per module doc; most components have none.

## Keep blocks

A reader who edits a doc by hand wraps the part to protect:

```markdown
<!-- keep -->
Anything here survives an update, verbatim.
<!-- /keep -->
```

On update, each block goes back at the end of the section whose heading it was found under, at any level (`##`, `###`, `####`). Heading gone from the new doc: the block is appended at the end of the doc under that original heading. The rest of a hand edit outside a keep block does not survive.

## Citations

Every fact comes from a file. The citation lives where it does not break the reading: a `Source` column in tables, a trailing `# path:line` comment on a command, `(path:line)` on a bullet in Inputs and outputs, Things to note, Data flow, and Drift. Prose paragraphs carry no citation. A line number for a symbol or a read; a path alone for a whole file.

## Callouts

`:::{note}` for a fact the reader must know before the step, `:::{tip}` for a shortcut. Plain mode: `> **Note:**` and `> **Tip:**`. Text only, no emoji.

## Prose

Written for the person who will run the module, in the voice of a colleague's user guide.

- **Talk to the reader.** Second person for what they own and do: "your images", "you provide a folder of `.tif` files", "you will see three cells". The module and its parts stay third person.
- **Purpose before names.** Every section, stage, and component opens with one plain sentence that says what it does for the reader's data, in the domain's words. Identifiers, paths, and function names come after that sentence, never inside it. "The inference pipeline takes your raw images and produces predicted bin values" first; `model_fn` and friends in the stages list. The Overview paragraph as a whole carries no path and no URL: paths live in Inputs and Outputs and Quickstart, function names in the stages list. A reader should be able to read the paragraph aloud.
- **Say why when it is not obvious.** A choice the reader might question gets its reason in the same sentence, from the code or the design docs: "The model loads on CPU, so any instance type works." No reason in a source: state the fact alone.
- **Examples over abstraction.** A variable in Quickstart shows a value the reader can copy: "Set `INSTANCE_TYPE` (e.g. `ml.g6.xlarge` for GPU training)". Take the example from the code's default or the notebook. No value anywhere in the repo: say what the value is ("the ARN of your MLflow tracking server") and invent nothing.
- **Callouts are specific.** A `note` names a precondition or a trap of this module; a `tip` names a shortcut of this module. A callout that would fit any page is not a callout, and two callouts that say the same thing are one, in the section where the reader acts on it.
- **Plain sentences.** Active voice, present tense, articles kept. Clauses separated with a colon, a comma, or a new sentence. Longer titles and more words are fine when they help the reader.

| Write | Not |
|---|---|
| The pipeline turns your raw images into training-ready datasets. | The preprocessing module is a SageMaker processing job that runs `pipeline.py`. |
| Set `EXPERIMENT_NAME` (e.g. `detectron2_maskrcnn_aisg`) to group your runs in MLflow. | Set `EXPERIMENT_NAME`. |
| The model loads on CPU, so any instance type works. | The model is loaded with `map_location="cpu"`. |
| You should see one `.out` file per image under the output path. | Output: `<image>.out`. |
