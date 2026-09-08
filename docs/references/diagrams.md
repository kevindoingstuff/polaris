# Diagram specs

`<skill-dir>/scripts/docsdiagram.py` turns a JSON spec into a `.drawio` file, and a `.drawio.png` beside it with `--png` when draw.io desktop is installed. Files live under `docs/<img>/<module>/` (`<img>` = `_static/diagrams` in Sphinx mode, `diagrams` in plain mode): `system.drawio`, `components.drawio`, `sequence.drawio`, plus one `<component-slug>.drawio` per gated component. The whole-system map without a highlight is `docs/<img>/system.drawio`.

## system

Every detected module plus the external systems it touches, at most 15 nodes. Written once per run, reused with `--highlight <id>` per module.

```json
{"title": "shopling",
 "nodes": [{"id": "api", "label": "API"},
           {"id": "auth", "label": "Auth"},
           {"id": "worker", "label": "Worker"},
           {"id": "db", "label": "Postgres", "external": true},
           {"id": "queue", "label": "Queue", "external": true}],
 "edges": [{"from": "api", "to": "auth", "label": "verify token", "kind": "call"},
           {"from": "api", "to": "db", "label": "orders", "kind": "data"},
           {"from": "api", "to": "queue", "label": "order.created", "kind": "event"},
           {"from": "worker", "to": "queue", "label": "polls", "kind": "event"}]}
```

- `external: true`: a dashed outline, for what the repo does not own (database, queue, third-party API). A store the modules read or write (a bucket, a database, a model registry) is `kind: data` with a `role`, so the map shows the same cylinders as the module charts; the node vocabulary below applies here too.
- An edge is `[from, to]` or `{"from", "to", "label", "kind"}`. `kind`: `call` (solid, default), `data` (dashed), `event` (dotted, open arrow).
- `--highlight api`: the `api` box turns yellow with a thick border, and every edge that touches it thickens.

## Node vocabulary

Every graph spec (`system`, `components`, `flow`) draws what a node *is*, the way a hand-drawn pipeline chart does:

| Field | Values | Draws |
|---|---|---|
| `kind` | `process` (default), `data`, `config`, `model` | a white rounded box, a cylinder, an orange note, a hexagon |
| `role` | `input`, `intermediate`, `output` | the cylinder colour: teal, lavender, red; a legend lists the roles used |
| `group` | a function or step name | one dashed container around every node with that group, labelled with it; its process boxes turn orange |
| `note` | short text | italic text under the node: a format, a path, a shape, a caveat |
| `external` | `true` | a dashed outline, for what the repo does not own |

Rules: a file, table, bucket path, queue, or in-memory dataframe the flow hands from one step to the next is a `data` node with a `role`, not an edge label. What enters the module from outside is `input`, what leaves it is `output`, what only lives between two steps is `intermediate`. A config file is one `config` node with an edge to every step that reads a key; the key name goes on the edge label. A trained model is `model`. A store that one module writes and another reads (a bucket, a registry) is `intermediate` on the system map. One `group` per flow: a helper the function calls is a step in the same group, its name in the step's `note`. A `note` names the format or path the reader would look for (`.tif/.tiff, 547 x 768`, `/tmp/processed_images`).

## components

The parts inside one module, left to right in flow order: the process steps with the data between them, 3 to 15 nodes. Process names match the doc's `###` component headings.

```json
{"title": "preprocessing: pipeline.py",
 "nodes": [{"id": "cfg", "label": "config.json", "kind": "config"},
           {"id": "raw", "label": "Raw images", "kind": "data", "role": "input", "note": ".tif/.tiff"},
           {"id": "process_images", "label": "Process images"},
           {"id": "proc", "label": "Processed images", "kind": "data", "role": "intermediate", "note": "/tmp/processed_images"},
           {"id": "split_data", "label": "Split data"},
           {"id": "splits", "label": "train / val / test", "kind": "data", "role": "output", "note": "df_annotations.parquet"}],
 "edges": [["raw", "process_images"], ["cfg", "process_images"], ["process_images", "proc"], ["proc", "split_data"],
           {"from": "cfg", "to": "split_data", "label": "split ratios, seed"}, ["split_data", "splits"]]}
```

A component outside the module that this module calls (another module, a library) is a node with `external: true`. A source node sits in the column before its first consumer; an edge to another row leaves its source to the right, runs down the column gutter and along the row gap, and enters the target from above or below.

## flow

One component: what happens to one item, left to right, 3 to 10 nodes. The component's own function is the `group`; the item in and out are `data` nodes with `input` and `output` roles; a side output (an error file, a log) is an `output` data node on a branch edge. Same spec shape and layout as `components`.

```json
{"title": "process_images: one image",
 "nodes": [{"id": "img", "label": "Image", "kind": "data", "role": "input", "note": "np.ndarray"},
           {"id": "read", "label": "Process single image", "group": "process_images()"},
           {"id": "validate", "label": "Validate single image", "group": "process_images()", "note": "547 x 768"},
           {"id": "augment", "label": "Augment single image", "group": "process_images()"},
           {"id": "out", "label": "Image", "kind": "data", "role": "output"},
           {"id": "errors", "label": "error.txt", "kind": "data", "role": "output"}],
 "edges": [["img", "read"], ["read", "validate"], ["validate", "augment"], ["augment", "out"],
           {"from": "validate", "to": "errors", "label": "AssertionError", "kind": "data"}]}
```

## sequence

One flow, the main one: 3 to 6 participants, at most 12 messages.

```json
{"title": "POST /orders",
 "participants": [{"id": "client", "label": "Client"},
                  {"id": "api", "label": "API"},
                  {"id": "auth", "label": "Auth"},
                  {"id": "db", "label": "Postgres"}],
 "messages": [{"from": "client", "to": "api", "label": "POST /orders", "activate": true},
              {"from": "api", "to": "auth", "label": "verify(token)", "activate": true},
              {"from": "auth", "to": "api", "label": "claims", "kind": "return"},
              {"from": "api", "to": "db", "label": "INSERT order"},
              {"from": "api", "to": "api", "label": "log request"},
              {"from": "api", "to": "client", "label": "201 Created", "kind": "return"}]}
```

- `kind`: `call` (solid, default), `return` (dashed, open arrow), `async` (open arrow). Any other value on a message fails.
- `activate: true` draws a bar on the receiver's lifeline from that message until its next `return` (or the last message).
- `from` equal to `to` draws a self message.

## Sub-diagrams

A component inside a module earns its own diagram only when it has three or more internal units or a flow of its own; a one-file helper gets none. Pick the kind by what dominates: `flow` for what happens to one item (a function with steps, the usual case), `components` for structure with several data hand-offs, `sequence` for actors exchanging messages. File: `docs/<img>/<module>/<component-slug>.drawio`, slug from the component name (lowercase, digits, hyphens); a slug that collides with `system`, `components`, or `sequence` gets `-detail`. The three module-level files stay the contract; sub-diagrams add to them.

## Exit status

0: wrote the `.drawio` (and the `.png` when draw.io was found; otherwise one notice on stderr, still 0). 2 with one line on stderr: unknown command, missing `-o`, spec missing or invalid JSON, empty nodes, participants, or messages, duplicate id, an edge, message, or `--highlight` that names an unknown id, unknown `kind`. A traceback is a bug.

## Size

The script needs Python and draw.io desktop only, and keeps up to about 15 nodes readable: ports spread along each box, one lane per jog, labels placed clear of boxes, lines, and each other. Past that, split the spec.
