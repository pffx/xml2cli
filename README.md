# xml2cli

Bidirectional NETCONF XML ↔ CLI converter driven by official YANG tree models.

## Board families

| Family | Boards | CLI style |
|--------|--------|-----------|
| **IHUB** | LANT-A, LMNT-A/B/C/D | `configure ...` |
| **NT** | LANT-A, LBNT-A, LDNT-A, LMNT-A/B/C/D | `system ...`, `nokia-debug ...` |
| **LT** | LLLT-A, LWLT-C, LGLT-D | LT roots + `onus onu <name> fromroot ...` |

YANG models live in `yang_model/`. Compiled schemas in `yang_schema/` (build step below).

## Install

```bash
pip install -e ".[dev]"
```

## Build schemas (required before conversion)

```bash
PYTHONPATH=. python -m xml2cli build-schemas
# single board: --board LWLT-C
# full tree:     --yang-tree all   # writes yang_schema/{family}/{board}.all.json
```

## CLI Usage

```bash
# XML → CLI (auto-detect board)
xml2cli xml2cli input.xml

# CLI → XML RPC
xml2cli cli2xml "classifiers classifier-entry eg0 ..." --profile LWLT-C

# Start web UI
xml2cli serve --host 0.0.0.0 --port 8888
# HTTPS (needed for one-click paste from clipboard when using LAN IP, not localhost):
# openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes -subj /CN=localhost
# xml2cli serve --host 0.0.0.0 --port 8888 --ssl-certfile cert.pem --ssl-keyfile key.pem
```

Web UI: **Paste** reads the system clipboard when the browser allows it (HTTPS or `http://127.0.0.1`). Plain `http://<LAN-IP>` cannot auto-paste in modern browsers; use Ctrl+V in the input box or HTTPS as above.

NETCONF ports follow chassis layout: **831** IHUB, **832** NT, **833–848** LT slots 1–16. CLI SSH uses port **22**.

Legacy profile names still map: `831-ihub` → `IHUB-LMNT-A`, `832-nt` → `NT-LMNT-A`, `833-LT-1` → `LWLT-C` (port 833).

## Tests

```bash
PYTHONPATH=. pytest -v
```

## Design docs

- Spec: `docs/superpowers/specs/2026-07-31-yang-driven-xml2cli-design.md`
- Plan: `docs/superpowers/plans/2026-07-31-yang-driven-xml2cli.md`
