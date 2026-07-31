"""Abstract family interface for schema-driven conversion."""

from __future__ import annotations

from abc import ABC, abstractmethod
import xml.etree.ElementTree as ET
from typing import Sequence

from xml2cli.yang.schema import BoardSchema, SchemaNode


class Family(ABC):
    @abstractmethod
    def cli_prefix(self) -> list[str]:
        ...

    @abstractmethod
    def parse_cli_line(self, tokens: Sequence[str], schema: BoardSchema) -> ET.Element:
        ...

    @abstractmethod
    def xml_to_cli_lines(
        self,
        elem: ET.Element,
        schema: BoardSchema,
        path: list[str],
    ) -> list[str]:
        ...

    @abstractmethod
    def wrap_edit_config(self, config_elems: Sequence[ET.Element]) -> str:
        ...

    @abstractmethod
    def wrap_special_rpc(self, rpc_kind: str) -> str:
        ...
