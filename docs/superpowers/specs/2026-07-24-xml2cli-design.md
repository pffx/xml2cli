# xml2cli Design Specification

**Date:** 2026-07-24  
**Status:** Implemented

## Overview

`xml2cli` bidirectionally converts between NETCONF RPC XML and CLI commands. It is delivered as a **Python CLI** and a **Web UI**, sharing the same conversion engine. Three device profiles under `xml/` map to distinct YANG models, RPC wrappers, and CLI vocabulary.

## Requirements

| Item | Decision |
|------|----------|
| Direction | Bidirectional: XML ↔ CLI |
| Profile detection | Auto by parent folder name (CLI); manual select on web for pasted CLI |
| v1 scope | All three profiles: `831-ihub`, `832-nt`, `833-LT-1` |
| Implementation | Python (CLI + FastAPI web server) |
| CLI → XML output | Full NETCONF RPC (with `<rpc>`, `<edit-config>`, `<target>`, etc.) |
| Frontend | Web UI in v1 — paste text or upload files, download/copy results |
| Status | Implemented |

## Architecture

```
xml2cli/
├── pyproject.toml
├── xml2cli/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py              # argparse entry point
│   ├── engine.py           # generic tree traversal (shared core)
│   ├── xml_parser.py       # RPC parsing
│   ├── cli_parser.py       # CLI token parsing
│   ├── api.py              # FastAPI routes
│   └── profiles/
│       ├── base.py         # Profile abstract interface
│       ├── sr_os.py        # 831-ihub
│       ├── ietf_nt.py      # 832-nt
│       └── onu_lt.py       # 833-LT-1
├── web/
│   ├── index.html          # single-page UI
│   ├── app.js
│   └── style.css
├── profiles.yaml           # folder name → profile mapping
├── tests/
│   ├── test_sr_os.py
│   ├── test_ietf_nt.py
│   ├── test_onu_lt.py
│   └── test_api.py
└── xml/                    # existing sample files
```

### Data Flow

1. **XML → CLI:** Parse RPC type → select profile by folder name (or user selection on web) → traverse config tree → emit CLI lines.
2. **CLI → XML:** Parse CLI tokens → rebuild config tree → wrap in profile-specific RPC template → emit full XML.

Both CLI and Web UI call the same `engine.py` functions; no duplicated conversion logic.

### Approach

**Rule-driven with profile plugins** (recommended over YANG-based or hardcoded approaches):

- Each profile is a Python plugin plus YAML metadata (root node, namespace, list keys, RPC templates).
- Balances maintainability, development speed, and extensibility without requiring YANG model files.

## CLI Interface

```bash
# XML → CLI (single file or directory, recursive)
xml2cli xml2cli xml/831-ihub/Config_port.xml
xml2cli xml2cli xml/831-ihub/

# CLI → full RPC XML (profile required — no folder context)
xml2cli cli2xml "configure service vpls 4093 sap 1/1/c1/1:0 admin-state enable" \
  --profile 831-ihub

# Write output to directory
xml2cli xml2cli xml/831-ihub/ -o output/

# Start web server
xml2cli serve --host 0.0.0.0 --port 8080
```

## Web Frontend

### Purpose

Provide a browser-based interface to import XML or CLI input and convert to the corresponding CLI commands or full NETCONF RPC XML, without requiring command-line usage.

### Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Backend API | FastAPI | Same Python codebase as CLI; auto OpenAPI docs |
| Frontend | Vanilla HTML/CSS/JS | No build step; easy to deploy on server |
| Shared core | `engine.py` | Single source of truth for conversion |

### Input Modes

Both XML and CLI support **two input methods** (not upload-only):

| Input method | XML | CLI |
|--------------|-----|-----|
| **Paste text** | Textarea: paste raw XML content | Textarea: paste one or more CLI lines |
| **Upload file** | `.xml` file upload | `.txt` file upload (one command per line) |

Pasting CLI text is a first-class feature — users are not required to save commands to a file first.

### UI Layout

```
┌─────────────────────────────────────────────────────┐
│  xml2cli                                    [Profile ▼] │
├──────────────────────┬──────────────────────────────┤
│  Input               │  Output                      │
│  ○ XML → CLI         │  (converted result)          │
│  ○ CLI → XML         │                              │
│                      │                              │
│  [Paste] [Upload]    │  [Copy] [Download]           │
│  ┌────────────────┐  │  ┌────────────────────────┐  │
│  │ textarea /     │  │  │ result textarea        │  │
│  │ file drop zone │  │  │                        │  │
│  └────────────────┘  │  └────────────────────────┘  │
│         [Convert]    │                              │
└──────────────────────┴──────────────────────────────┘
```

### Profile Selection (Web)

| Direction | Profile handling |
|-----------|------------------|
| XML → CLI | Dropdown: `831-ihub` / `832-nt` / `833-LT-1` (required for pasted XML; auto-suggested if filename hints profile) |
| CLI → XML | Dropdown required (no folder context when pasting) |

### API Endpoints

```
POST /api/xml2cli
  Body: { "content": "<rpc>...</rpc>", "profile": "831-ihub" }
  Response: { "cli": ["configure service vpls ..."], "errors": [] }

POST /api/cli2xml
  Body: { "content": "configure service vpls ...", "profile": "831-ihub" }
  Response: { "xml": "<rpc>...</rpc>", "errors": [] }

GET /api/profiles
  Response: { "profiles": ["831-ihub", "832-nt", "833-LT-1"] }
```

### Output Actions

- Display result in output panel
- **Copy to clipboard** button
- **Download** as `.txt` (CLI) or `.xml` (RPC)

### Deployment

```bash
xml2cli serve --host 0.0.0.0 --port 8080
# Serves API + static web UI at http://<server>:8080/
```

## Conversion Rules (Engine)

1. **List nodes:** Container name is kept; key element outputs value only (`service-name 4093` → `4093`).
2. **Leaf nodes:** Output as `leaf-name value`.
3. **operation attribute:** `delete` appends `delete` to the path; `merge`/`replace` are omitted from CLI.
4. **Multiple siblings:** Each instance (e.g. multiple `<sap>`) produces a separate CLI line.
5. **Namespaces:** Stripped from element names during traversal; re-applied when generating XML.

## Profile: `831-ihub` (Nokia SR OS)

| Property | Value |
|----------|-------|
| YANG namespace | `urn:nokia.com:sros:ns:yang:sr:conf` |
| Config root | `<configure>` |
| RPC target | `<candidate/>` |
| CLI prefix | `configure` |

### RPC Type Mapping

| RPC Type | CLI Output |
|----------|------------|
| `edit-config` | `configure ...` |
| `get-config` | `admin display-config ...` |
| `get` (state) | `show ...` |
| `commit` | `commit` |
| `discard-changes` | `discard` |
| `action` (oamsave) | `oam-save` |

### List Key Elements

`service-name`, `service-id`, `sap-id`, `port-id`, `interface-name`, `router-name`, `lag-index`, `slot-number`, `mda-slot`, `ip-prefix`, `sub-group-id`

### Examples

```
# Config_port.xml
configure service vpls 4093 sap 1/1/c1/1:0 admin-state enable

# Del_vpls.xml
configure service vpls 4093 delete
```

### CLI → XML RPC Template

```xml
<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
  <edit-config>
    <target><candidate/></target>
    <config>
      <configure xmlns="urn:nokia.com:sros:ns:yang:sr:conf">
        <!-- generated from CLI -->
      </configure>
    </config>
  </edit-config>
</rpc>
```

## Profile: `832-nt` (IETF System)

| Property | Value |
|----------|-------|
| YANG namespace | `urn:ietf:params:xml:ns:yang:ietf-system` |
| Config root | `<system>` |
| RPC target | `<running/>` |
| CLI prefix | none (starts with `system`) |

### Examples

```
# debug_lemi.xml
system management debug lemi enable true
```

### List Key Elements

`name` (used as identifier in nested lists)

### CLI → XML RPC Template

```xml
<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
  <edit-config>
    <target><running/></target>
    <config>
      <system xmlns="urn:ietf:params:xml:ns:yang:ietf-system">
        <!-- generated from CLI -->
      </system>
    </config>
  </edit-config>
</rpc>
```

Note: Nokia augment namespaces (e.g. `nokia-ietf-system-aug`) are preserved on child elements during XML generation.

## Profile: `833-LT-1` (BBF ONU)

| Property | Value |
|----------|-------|
| YANG namespace | `urn:bbf:params:xml:ns:yang:bbf-fiber-onu-emulated-mount` |
| Config root | `<onus><onu>` |
| RPC target | `<running/>` |
| CLI prefix | `onus` |

### Examples

```
# Change_DHCP to Static.xml (abbreviated)
onus onu PON5/ONT5 root interfaces interface VOIP_IPHOST ipv4 enabled true ...
```

### List Key Elements

`name` (onu, interface, server, classifier-entry, etc.)

### CLI → XML RPC Template

```xml
<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
  <edit-config>
    <target><running/></target>
    <config>
      <onus xmlns="urn:bbf:params:xml:ns:yang:bbf-fiber-onu-emulated-mount">
        <onu>
          <!-- generated from CLI -->
        </onu>
      </onus>
    </config>
  </edit-config>
</rpc>
```

Note: Mounted YANG child namespaces (e.g. `ietf-interfaces-mounted`, `ietf-ip-mounted`) are applied per-element based on profile rules. CLI for this profile is path-based, not SR OS `configure` style.

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Unrecognized folder profile | Error with list of supported profiles |
| XML parse failure | Report filename and line number |
| Unknown RPC type | Warning; attempt `edit-config` handling |
| Ambiguous CLI parse | Error with expected format hint |
| Reverse conversion without profile | Require `--profile` flag |

## Testing Strategy

1. **XML → CLI golden tests:** All 29 XML files under `xml/` as regression fixtures.
2. **Round-trip tests:** Core `831-ihub` samples — XML → CLI → XML, compare structure.
3. **Per-profile coverage:** At minimum one test each for `edit-config`, `delete`, `get`/`get-config`, and special RPCs (`commit`, `discard`, `action`).

## Out of Scope (v1)

- Batch folder / zip upload (single paste or single file per conversion)
- YANG model loading
- Template variable substitution (e.g. `%%ONU_NAME%%` in `080_template.xml`)
- `rpc-reply` / read-only data files (e.g. `Default_configuration.xml`)
- User authentication / multi-tenant access control

## Folder → Profile Mapping

```yaml
# profiles.yaml
831-ihub: sr_os
832-nt: ietf_nt
833-LT-1: onu_lt
```
