"""Shared pytest helpers."""

from __future__ import annotations

from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def wrap_edit_config(inner_xml: str) -> str:
    body = inner_xml.strip()
    if body.startswith("<?xml"):
        body = body.split("?>", 1)[1].strip()
    if body.startswith("<config"):
        config_body = body
    else:
        config_body = f"<config>\n{body}\n</config>"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
  <edit-config>
    <target>
      <running />
    </target>
    {config_body}
  </edit-config>
</rpc>
"""
