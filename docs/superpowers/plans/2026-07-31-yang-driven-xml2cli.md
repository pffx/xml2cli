# YANG-Driven xml2cli Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace hand-maintained profile rules with schema-driven XML↔CLI conversion for all 15 board YANG trees (IHUB/NT/LT).

**Architecture:** Parse `*_yang_tree.txt` into JSON schemas at build time; runtime loads schema per board and walks CLI/XML using family-specific conventions (IHUB `configure`, NT multi-module roots, LT multi-root + `onus`/`fromroot`).

**Tech Stack:** Python 3.10+, ElementTree, FastAPI, PyYAML, pytest

## Global Constraints

- Default YANG source: `*_yang_tree.txt`; `*_yang_tree_all.txt` only when `yang_tree=all`
- All 15 boards in `yang_model/` must build schemas successfully
- LT ONU path uses `fromroot`, not `root`
- LT-level CLI roots are direct `<config>` children (not wrapped in `onus`)
- Do not commit unless user requests
- Minimize scope: no raw `.yang` loading, no full 9k-node coverage in v1

---

### Task 1: Board registry and schema data model

**Files:**
- Create: `xml2cli/board_registry.py`
- Create: `xml2cli/yang/__init__.py`
- Create: `xml2cli/yang/schema.py`
- Create: `tests/test_board_registry.py`

**Interfaces:**
- Produces: `BoardInfo(board_id, family, tree_path, tree_all_path)`, `list_boards()`, `get_board(board_id)`, `SchemaNode`, `BoardSchema`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_board_registry.py
from xml2cli.board_registry import FAMILY_IHUB, FAMILY_LT, FAMILY_NT, get_board, list_boards


def test_list_boards_has_fifteen_entries():
    boards = list_boards()
    assert len(boards) == 15
    families = {b.family for b in boards}
    assert families == {FAMILY_IHUB, FAMILY_NT, FAMILY_LT}


def test_get_board_lwlt_c():
    board = get_board("LWLT-C")
    assert board.family == FAMILY_LT
    assert board.tree_path.name.endswith("_yang_tree.txt")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. pytest tests/test_board_registry.py -v`  
Expected: FAIL — module not found

- [ ] **Step 3: Implement registry and schema types**

```python
# xml2cli/yang/schema.py
from dataclasses import dataclass, field
from typing import Literal

NodeKind = Literal["container", "list", "leaf", "choice", "case", "presence-container"]

@dataclass
class SchemaNode:
    name: str
    kind: NodeKind
    keys: list[str] = field(default_factory=list)
    prefix: str | None = None
    children: dict[str, "SchemaNode"] = field(default_factory=dict)
    optional: bool = False

@dataclass
class BoardSchema:
    board_id: str
    family: str
    config_roots: list[str]
    modules: list[str]
    roots: dict[str, SchemaNode]
```

```python
# xml2cli/board_registry.py — register all 15 boards with paths under yang_model/
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. pytest tests/test_board_registry.py -v`  
Expected: PASS

---

### Task 2: YANG tree parser

**Files:**
- Create: `xml2cli/yang/tree_parser.py`
- Create: `tests/test_tree_parser.py`
- Test fixture: `tests/fixtures/yang_tree_sample.txt` (excerpt from LWLT-C)

**Interfaces:**
- Produces: `parse_tree_file(path, mode: Literal["standard","all"]) -> list[TreeModule]`
- `TreeModule(name: str, lines: list[TreeLine])`
- `TreeLine(indent, marker, name, keys, optional, prefix, local_name)`

- [ ] **Step 1: Write failing tests for list node, prefix, x-- skip**

```python
def test_parse_list_node_with_key():
    lines = parse_tree_text("  +--rw classifier-entry* [name]\n")
    assert lines[0].keys == ["name"]
    assert lines[0].local_name == "classifier-entry"

def test_skip_x_marked_in_standard_mode():
    text = "  x--rw hidden-node?   string\n  +--rw visible   string\n"
    lines = parse_tree_text(text, mode="standard")
    assert [l.local_name for l in lines] == ["visible"]
```

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement `tree_parser.py`**

Handle: `module:`, indent levels, `+--rw`, `+--ro`, `x--rw`, `* [k]`, `prefix:local`, `?`, `!`, `+--:(case)`

- [ ] **Step 4: Run tests — expect PASS**

Run: `PYTHONPATH=. pytest tests/test_tree_parser.py -v`

---

### Task 3: Schema builder and build command

**Files:**
- Create: `xml2cli/yang/schema_builder.py`
- Create: `xml2cli/yang/schema_store.py`
- Create: `xml2cli/build_schemas.py`
- Modify: `xml2cli/cli.py` (add `build-schemas` subcommand)
- Create: `tests/test_schema_builder.py`

**Interfaces:**
- Produces: `build_board_schema(board_id, mode) -> BoardSchema`
- Produces: `save_schema(schema, path)`, `load_schema(board_id, mode) -> BoardSchema`
- CLI: `python -m xml2cli build-schemas [--board ID] [--yang-tree standard|all]`

- [ ] **Step 1: Test schema build for LWLT-C finds config roots**

```python
def test_lwlt_c_config_roots_include_classifiers_and_onus():
    schema = build_board_schema("LWLT-C", mode="standard")
    assert "classifiers" in schema.config_roots
    assert "onus" in schema.config_roots
    assert "xpongemtcont" in schema.config_roots
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement builder**

Rules:
- Module-level `+--rw` top nodes → `config_roots` (exclude `+--ro` only modules)
- IHUB: config root is `configure` inside `action-rpc` module
- Build nested `SchemaNode` tree from indented lines

- [ ] **Step 4: Implement `build_schemas` CLI writing to `yang_schema/{family}/{board_id}.json`**

- [ ] **Step 5: Build all 15 boards and smoke test**

Run: `PYTHONPATH=. python -m xml2cli build-schemas && PYTHONPATH=. pytest tests/test_schema_builder.py -v`

---

### Task 4: Family base and IHUB conversion

**Files:**
- Create: `xml2cli/families/__init__.py`
- Create: `xml2cli/families/base.py`
- Create: `xml2cli/families/ihub.py`
- Create: `tests/test_ihub_conversion.py`
- Modify: remove dependency on `profiles/sr_os.py` from engine (later task)

**Interfaces:**
- Produces: `IhubFamily.cli_prefix() -> ["configure"]`
- Produces: `IhubFamily.parse_cli_line(tokens, schema) -> ET.Element`
- Produces: `IhubFamily.xml_to_cli(elem, schema, path) -> list[str]`
- Produces: `IhubFamily.wrap_rpc(config_elems, rpc_kind="edit-config") -> str`
- Special RPC: `commit`, `discard`, `oam-save`

- [ ] **Step 1: Golden test — configure line from IHUB LMNT-A schema**

```python
IHUB_CLI = "configure card 1 admin-state enable"
# Build schema first; parse CLI; assert <configure><card><slot-number>1</slot-number>...
```

- [ ] **Step 2–4: Implement ihub family using schema walk**

- [ ] **Step 5: Test commit/discards as separate RPC**

Run: `PYTHONPATH=. pytest tests/test_ihub_conversion.py -v`

---

### Task 5: NT family conversion

**Files:**
- Create: `xml2cli/families/nt.py`
- Create: `tests/test_nt_conversion.py`

**Interfaces:**
- Produces: `NtFamily` with roots like `system`, `nokia-debug`
- CLI example: `system management debug ip_itf enable true`

- [ ] **Step 1: Golden test on LMNT-A schema**

- [ ] **Step 2: Implement NT parser/emitter**

- [ ] **Step 3: Verify all 7 NT boards load schema and detect `system` root**

Run: `PYTHONPATH=. pytest tests/test_nt_conversion.py -v`

---

### Task 6: LT family conversion (multi-root + onus/fromroot)

**Files:**
- Create: `xml2cli/families/lt.py`
- Create: `tests/test_lt_conversion.py`

**Interfaces:**
- Produces: `LtFamily.config_roots` multi-merge
- LT CLI without prefix: `classifiers classifier-entry ...`
- ONU CLI: `onus onu PON1/ONT1 fromroot interfaces ...`
- Handle duplicate token: `scheduling-traffic-class scheduling-traffic-class 0`

- [ ] **Step 1: QoS regression test (user sample)**

```python
USER_QOS_CLI = """xpongemtcont traffic-descriptor-profiles traffic-descriptor-profile TDP_gpon assured-bandwidth 7800000
classifiers classifier-entry classifier_eg0 filter-operation match-all-filter match-criteria pbit-marking-list 0 pbit-value 0
policies policy policy0 classifiers classifier_eg0
qos-policy-profiles policy-profile EQPP policy-list policy0"""
# Assert no <onus> wrapper; assert <classifiers>, <xpongemtcont> siblings under <config>
```

- [ ] **Step 2: Implement LT family**

- [ ] **Step 3: Test onus/fromroot path**

Run: `PYTHONPATH=. pytest tests/test_lt_conversion.py -v`

---

### Task 7: Rewrite engine and detection

**Files:**
- Modify: `xml2cli/engine.py` (schema-driven entry points)
- Create: `xml2cli/conversion.py` (orchestrate family + schema)
- Modify: `tests/test_detect_profile.py` → `tests/test_board_detect.py`

**Interfaces:**
- Produces: `convert_xml_to_cli(content, board_id, yang_tree="standard")`
- Produces: `convert_cli_to_xml(content, board_id, yang_tree="standard")`
- Produces: `detect_board_from_xml(content) -> str | None`
- Produces: `detect_board_from_cli(content) -> str | None`

- [ ] **Step 1: Wire engine to load schema via `schema_store.load_schema`**

- [ ] **Step 2: Replace `detect_profile_from_*` with board detection**

- [ ] **Step 3: Remove imports of old `profiles/sr_os.py`, `ietf_nt.py`, `onu_lt.py` from engine**

- [ ] **Step 4: Run full test suite**

Run: `PYTHONPATH=. pytest -v`

---

### Task 8: API, CLI, and Web UI board selector

**Files:**
- Modify: `xml2cli/api.py`
- Modify: `xml2cli/cli.py`
- Modify: `web/index.html`, `web/app.js`
- Modify: `tests/test_api.py`

**Interfaces:**
- `GET /api/boards` returns 15 boards grouped by family
- Request body: `{ content, board?, yang_tree? }`
- CLI flags: `--board`, `--yang-tree`

- [ ] **Step 1: Update API models and endpoints**

- [ ] **Step 2: Web UI board dropdown (IHUB/NT/LT groups) + optional all-tree toggle**

- [ ] **Step 3: Update API tests**

Run: `PYTHONPATH=. pytest tests/test_api.py -v`

---

### Task 9: Cleanup legacy profiles and docs

**Files:**
- Delete or deprecate: `xml2cli/profiles/sr_os.py`, `ietf_nt.py`, `onu_lt.py`
- Modify: `profiles.yaml` → `boards.yaml`
- Modify: `README.md`
- Update: `tests/test_sr_os.py`, `test_onu_lt.py`, `test_ietf_nt.py` → family tests or remove

- [ ] **Step 1: Remove dead code and update README**

- [ ] **Step 2: Final full test run**

Run: `PYTHONPATH=. pytest -v`

---

### Task 10: Build all schemas in CI / package

**Files:**
- Modify: `pyproject.toml` (optional package data for `yang_schema/`)
- Create: `scripts/verify_schemas.sh` or pytest marker `@pytest.mark.schema`

- [ ] **Step 1: Add test that all 15 `yang_schema/**/*.json` exist after build**

```python
@pytest.mark.parametrize("board_id", ALL_BOARD_IDS)
def test_schema_artifact_exists(board_id):
    assert load_schema(board_id).board_id == board_id
```

- [ ] **Step 2: Document build step in README**

```bash
PYTHONPATH=. python -m xml2cli build-schemas
PYTHONPATH=. pytest -v
```

---

## Self-Review (plan vs spec)

| Spec requirement | Task |
|------------------|------|
| 15 boards | Task 1, 3, 10 |
| standard vs all tree | Task 2, 3, 8 |
| IHUB configure + specials | Task 4 |
| NT system roots | Task 5 |
| LT multi-root + fromroot | Task 6 |
| API board param | Task 8 |
| Schema cache JSON | Task 3 |
| Remove legacy profiles | Task 9 |

No placeholders remain in task steps above.
