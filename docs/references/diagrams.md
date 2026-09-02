# Diagram specs

`<skill-dir>/scripts/docsdiagram.py` turns a JSON spec into a `.drawio` file, and a `.drawio.png` beside it with `--png` when draw.io desktop is installed. Files live under `docs/diagrams/<module>/`: `system.drawio`, `components.drawio`, `sequence.drawio`, plus one `<component-slug>.drawio` per gated component. The whole-system map without a highlight is `docs/diagrams/system.drawio`.

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

- `external: true`: a dashed box, for what the repo does not own (database, queue, third-party API).
- An edge is `[from, to]` or `{"from", "to", "label", "kind"}`. `kind`: `call` (solid, default), `data` (dashed), `event` (dotted, open arrow).
- `--highlight api`: the `api` box turns yellow with a thick border, and every edge that touches it thickens.

## components

The parts inside one module: 3 to 10 units with the same names the doc's `###` component headings use. Same shape as `system`.

```json
{"title": "api",
 "nodes": [{"id": "server", "label": "server.js"},
           {"id": "routes", "label": "routes/orders.js"},
           {"id": "store", "label": "store.js"},
           {"id": "auth", "label": "auth.verify", "external": true}],
 "edges": [{"from": "server", "to": "routes", "label": "mounts", "kind": "call"},
           {"from": "routes", "to": "auth", "label": "verify", "kind": "call"},
           {"from": "routes", "to": "store", "label": "Order row", "kind": "data"}]}
```

A component outside the module that this module calls (another module, a library) is a node with `external: true`.

## flow

One order-dominated component or pipeline: stages left to right, 3 to 10 boxes, branches and merges as extra edges. Same spec shape as `system` (nodes, edges, `external`, kinds).

```json
{"title": "the training pipeline",
 "nodes": [{"id": "validate"}, {"id": "augment", "label": "JIT augment"},
           {"id": "train"}, {"id": "evaluate"},
           {"id": "hub", "label": "Model hub", "external": true}],
 "edges": [["validate", "augment"], ["augment", "train"], ["train", "evaluate"],
           {"from": "train", "to": "hub", "label": "weights", "kind": "data"}]}
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

A component inside a module earns its own diagram only when it has three or more internal units or a flow of its own; a one-file helper gets none. Pick the kind by what dominates: `components` for structure, `flow` for order (a pipeline), `sequence` for actors exchanging messages. File: `docs/diagrams/<module>/<component-slug>.drawio`, slug from the component name (lowercase, digits, hyphens); a slug that collides with `system`, `components`, or `sequence` gets `-detail`. The three module-level files stay the contract; sub-diagrams add to them.

## Exit status

0: wrote the `.drawio` (and the `.png` when draw.io was found; otherwise one notice on stderr, still 0). 2 with one line on stderr: unknown command, missing `-o`, spec missing or invalid JSON, empty nodes, participants, or messages, duplicate id, an edge, message, or `--highlight` that names an unknown id, unknown `kind`. A traceback is a bug.

## Two engines

The survey picks the engine. Graphviz (`dot -V`) and the `drawio-skill` plugin (365-skills) both present: the skill calls `drawio-skill`, whose extractors read the imports directly and whose `autolayout.py` handles any size. Otherwise: the script here, which needs Python and draw.io desktop only. The script keeps up to about 15 nodes readable: ports spread along each box, one lane per jog, labels placed clear of boxes, lines, and each other. Past that, split the spec, or install Graphviz and the plugin.

Either engine may add an ERD or a C4 set into the same folder. The charts above are the contract.
