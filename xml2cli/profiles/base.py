"""Profile base class and registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import yaml

from xml2cli.profiles.ietf_nt import IetfNtProfile
from xml2cli.profiles.onu_lt import OnuLtProfile
from xml2cli.profiles.sr_os import SrOsProfile


class Profile(ABC):
    name: str
    folder_names: list[str]
    list_keys: set[str]
    config_root_tags: set[str]
    cli_prefix: list[str]

    @abstractmethod
    def get_key_for_container(self, container: str, keys: dict[str, str]) -> Optional[str]:
        ...

    @abstractmethod
    def wrap_config_in_rpc(self, config_elem) -> str:
        ...

    @abstractmethod
    def parse_cli_line(self, line: str):
        ...

    def special_rpc_to_cli(self, rpc_type: str, payload) -> Optional[list[str]]:
        return None


_PROFILES: dict[str, Profile] = {
    "sr_os": SrOsProfile(),
    "ietf_nt": IetfNtProfile(),
    "onu_lt": OnuLtProfile(),
}

_FOLDER_MAP: dict[str, str] = {}


def _load_folder_map() -> dict[str, str]:
    global _FOLDER_MAP
    if _FOLDER_MAP:
        return _FOLDER_MAP

    config_path = Path(__file__).resolve().parent.parent.parent / "profiles.yaml"
    if config_path.exists():
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        _FOLDER_MAP = {str(k): str(v) for k, v in data.items()}
    else:
        _FOLDER_MAP = {
            "831-ihub": "sr_os",
            "832-nt": "ietf_nt",
            "833-LT-1": "onu_lt",
        }
    return _FOLDER_MAP


def get_profile_by_id(profile_id: str) -> Profile:
    profile = _PROFILES.get(profile_id)
    if profile is None:
        raise ValueError(
            f"Unknown profile '{profile_id}'. Supported: {', '.join(sorted(_PROFILES))}"
        )
    return profile


def get_profile_by_folder(folder_name: str) -> Profile:
    folder_map = _load_folder_map()
    profile_id = folder_map.get(folder_name)
    if profile_id is None:
        raise ValueError(
            f"Unknown folder profile for '{folder_name}'. "
            f"Supported folders: {', '.join(sorted(folder_map))}"
        )
    return get_profile_by_id(profile_id)


def list_profile_folders() -> list[str]:
    return sorted(_load_folder_map())


def resolve_profile_name(name: str) -> Profile:
    folder_map = _load_folder_map()
    if name in folder_map:
        return get_profile_by_id(folder_map[name])
    return get_profile_by_id(name)
