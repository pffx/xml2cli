# YANG-Driven xml2cli Redesign

**Date:** 2026-07-31  
**Status:** Approved  
**Replaces:** `2026-07-24-xml2cli-design.md` (profile rules derived from sample XML)

## Overview

Redevelop `xml2cli` to drive XML ↔ CLI conversion from official **pyang tree** files under `yang_model/`, replacing hand-maintained profile rules and deleted `xml/` sample fixtures.

## Confirmed Decisions

| Decision | Choice |
|----------|--------|
| Model source | `yang_model/` official board YANG trees |
| Default tree file | `*_yang_tree.txt` |
| Extended tree | `*_yang_tree_all.txt` via explicit option (`--yang-tree all` / API flag) |
| Scope | All **15** board `_yang_tree.txt` files across IHUB, NT, LT |
| Approach | **Hybrid:** shared runtime parser + build-time precompiled schema cache |

## Board Inventory

### IHUB (5) — SR OS `configure` style

| Board ID | Path |
|----------|------|
| LANT-A | `yang_model/IHUB/LANT-A/LS-MF-IHUB-LANT-A_yang_tree.txt` |
| LMNT-A | `yang_model/IHUB/LMNT-A/LS-MF-IHUB-LMNT-A_yang_tree.txt` |
| LMNT-B | `yang_model/IHUB/LMNT-B/LS-MF-IHUB-LMNT-B_yang_tree.txt` |
| LMNT-C | `yang_model/IHUB/LMNT-C/LS-MF-IHUB-LMNT-C_yang_tree.txt` |
| LMNT-D | `yang_model/IHUB/LMNT-D/LS-MF-IHUB-LMNT-D_yang_tree.txt` |

Single module per file: `action-rpc`, containing NETCONF RPC definitions and `+--rw configure`.

### NT (7) — IETF/Nokia mounted config

| Board ID | Path |
|----------|------|
| LANT-A | `yang_model/NT/LANT-A/LS-MF-LANT-A_yang_tree.txt` |
| LBNT-A | `yang_model/NT/LBNT-A/LS-MF-LBNT-A_yang_tree.txt` |
| LDNT-A | `yang_model/NT/LDNT-A/LS-MF-LDNT-A_yang_tree.txt` |
| LMNT-A | `yang_model/NT/LMNT-A/LS-MF-LMNT-A_yang_tree.txt` |
| LMNT-B | `yang_model/NT/LMNT-B/LS-MF-LMNT-B_yang_tree.txt` |
| LMNT-C | `yang_model/NT/LMNT-C/LS-MF-LMNT-C_yang_tree.txt` |
| LMNT-D | `yang_model/NT/LMNT-D/LS-MF-LMNT-D_yang_tree.txt` |

Multi-module; config roots are module-level `+--rw` nodes (e.g. `system`, `interfaces`, `nokia-debug`).

### LT (3) — BBF xPON / ONU / QoS

| Board ID | Path |
|----------|------|
| LLLT-A | `yang_model/LT/LLLT-A/LS-MF-LLLT-A_yang_tree.txt` |
| LWLT-C | `yang_model/LT/LWLT-C/LS-MF-LWLT-C_yang_tree.txt` |
| LGLT-D | `yang_model/LT/LGLT-D/LS-MF-LGLT-D_yang_tree.txt` |

Multi-module; **multiple LT-level config roots** under `<config>` (e.g. `classifiers`, `xpongemtcont`, `policies`, `qos-policy-profiles`, `onus`). ONU subtree uses **`fromroot`** (not `root`).

## Architecture

```
yang_model/                 # Source trees (read-only, user-provided)
yang_schema/                # Compiled JSON schemas (build artifact)
xml2cli/
  yang/
    tree_parser.py          # Parse pyang tree text → AST lines
    schema.py               # SchemaNode dataclasses
    schema_builder.py       # AST → board schema graph
    schema_store.py         # Load/cache compiled schemas
  board_registry.py         # 15 boards, family, paths, CLI conventions
  engine.py                 # Schema-driven XML↔CLI (replaces rule lists)
  families/
    base.py                 # Family interface
    ihub.py                 # configure prefix, RPC specials
    nt.py                   # system-style roots
    lt.py                   # multi-root + onus onu prefix
  xml_parser.py             # RPC parsing (retained)
  api.py / cli.py / web/    # Updated for board selection
```

### Data Flow

1. **Build:** `python -m xml2cli.build_schemas` parses each board tree → `yang_schema/{family}/{board_id}.json`
2. **XML → CLI:** Parse RPC → detect board/family → load schema → traverse config XML using schema → emit CLI lines
3. **CLI → XML:** Tokenize CLI → detect board/family → load schema → walk tokens against schema → build config element(s) → wrap in RPC

## YANG Tree Parsing Rules

| Tree marker | Handling |
|-------------|----------|
| `+--rw` | Config node (container, list, or leaf) |
| `+--ro` | Skip for config conversion (state/read-only) |
| `x--rw` / `x--ro` | Skip in `standard` mode; include in `all` mode |
| `* [key]` | List with key(s) |
| `prefix:local-name` | Store local name; record prefix for XML xmlns when known |
| `+--:(case)` | YANG choice case — follow path present in CLI/XML |
| `?` suffix | Optional leaf/container |
| `!` suffix | Presence container |
| `module:` blocks | Separate schema subtrees; identify config roots per family |

## Family CLI Conventions

### IHUB

- CLI prefix: `configure`
- Config XML under `action-rpc` → `configure`
- Special lines: `commit`, `discard`, `oam-save` → separate RPC wrappers
- RPC target: `<candidate/>` (retain existing behavior)

### NT

- No global prefix; path starts at config root name (e.g. `system management debug ...`)
- Single-root or multi-root per module top-level `+--rw`
- RPC target: `<running/>`

### LT

- **LT-level roots** (no prefix): `xpongemtcont`, `classifiers`, `policies`, `qos-policy-profiles`, etc.
- **ONU-level:** `onus onu <name> ...` → XML under `onus/onu/fromroot/...`
- Multiple config roots merge as siblings under `<config>` in one `<edit-config>`
- RPC target: `<running/>`

## API / CLI Changes

### CLI

```bash
xml2cli xml2cli input.xml --board LWLT-C
xml2cli cli2xml "classifiers ..." --board LWLT-C
xml2cli cli2xml "..." --board LMNT-A --family IHUB
xml2cli build-schemas                    # compile all yang trees
xml2cli build-schemas --board LWLT-C     # single board
```

### API

```json
POST /api/xml2cli  { "content": "...", "board": "LWLT-C", "yang_tree": "standard" }
POST /api/cli2xml  { "content": "...", "board": "LWLT-C", "yang_tree": "all" }
GET  /api/boards   { "boards": [{ "id": "LWLT-C", "family": "LT", ... }] }
```

`yang_tree`: `"standard"` (default) | `"all"`

### Web UI

- Replace legacy profile folder dropdown with **board selector** grouped by IHUB / NT / LT
- Optional toggle:「完整模型 (yang_tree_all)」
- Auto-detect board from XML namespace / CLI first token when possible

## Board Detection

| Input | Detection strategy |
|-------|-------------------|
| XML | Match xmlns / root elements against schema roots per family |
| CLI | First token(s): `configure` → IHUB; `onus` → LT; `system`/`nokia-debug`/… → NT; LT roots → LT |
| Ambiguous | Require explicit `--board` |

## Schema Cache Format (JSON)

Per board file:

```json
{
  "board_id": "LWLT-C",
  "family": "LT",
  "source": "yang_model/LT/LWLT-C/LS-MF-LWLT-C_yang_tree.txt",
  "yang_tree_mode": "standard",
  "modules": [...],
  "config_roots": ["classifiers", "xpongemtcont", "onus", ...],
  "nodes": { "path/key": { "kind": "list", "keys": ["name"], ... } }
}
```

## Migration

| Retain | Replace / Remove |
|--------|------------------|
| `xml_parser.py` RPC parsing | Hand-tuned `CONTAINERS` in `onu_lt.py`, `ietf_nt.py`, `sr_os.py` |
| FastAPI + web shell | `profiles.yaml` folder → profile mapping |
| `engine.py` traversal pattern | Tests tied to deleted `xml/` samples |
| CLI `serve` entry point | Old profile IDs `831-ihub`, `832-nt`, `833-LT-1` |

## Testing Strategy

1. **Parser unit tests:** list keys, prefixes, choice markers, `x--` filtering
2. **Schema build smoke:** all 15 boards compile without error
3. **Family golden tests:** hand-crafted XML/CLI pairs per family (not from deleted xml/)
4. **Regression:** user QoS/xPON CLI sample on LWLT-C
5. **Round-trip:** XML → CLI → XML structural equivalence for core paths

## Out of Scope (v1)

- Loading raw `.yang` source files (tree text only)
- Template variable substitution (`%%ONU_NAME%%`)
- `rpc-reply` / state-only conversion
- Full coverage of all 9k+ nodes per LT board
- User authentication

## Error Handling

| Condition | Response |
|-----------|----------|
| Unknown board | Error listing valid board IDs |
| Schema not built | Prompt to run `build-schemas` |
| CLI token not in schema | Line number + expected child/key |
| Ambiguous board detection | Error requesting `--board` |
| Mixed families in one CLI paste | Error per line |
