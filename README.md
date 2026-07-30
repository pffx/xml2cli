# xml2cli

Bidirectional NETCONF XML ↔ CLI converter for Nokia device profiles.

## Profiles

| Folder | Device type |
|--------|-------------|
| `831-ihub` | Nokia SR OS |
| `832-nt` | IETF System (Fixed Networks) |
| `833-LT-1` | BBF ONU |

## Install

```bash
pip install -e ".[dev]"
```

## CLI Usage

```bash
# XML → CLI
xml2cli xml2cli xml/831-ihub/Config_port.xml

# CLI → XML RPC
xml2cli cli2xml "configure service vpls 4093 sap 1/1/c1/1:0 admin-state enable" --profile 831-ihub

# Start web UI
xml2cli serve --host 0.0.0.0 --port 8888
```

## Web UI

Open `http://localhost:8080/` after starting the server. Supports:

- Paste XML or CLI text
- Upload `.xml` or `.txt` files
- Profile selection
- Copy / download results

## Tests

```bash
pytest -v
```
