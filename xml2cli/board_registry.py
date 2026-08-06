"""Static registry for board YANG tree files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

FAMILY_IHUB = "IHUB"
FAMILY_NT = "NT"
FAMILY_LT = "LT"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
YANG_MODEL_ROOT = PROJECT_ROOT / "yang_model"


@dataclass(frozen=True, slots=True)
class BoardInfo:
    board_id: str
    family: str
    tree_path: Path
    tree_all_path: Path | None = None
    lt_slot: int | None = None  # LT chassis slot 1–16 → NETCONF ports 833–848


def _tree_paths(family: str, board_dir: str, tree_file: str) -> tuple[Path, Path | None]:
    family_root = YANG_MODEL_ROOT / family / board_dir
    tree_path = family_root / tree_file
    if family == FAMILY_IHUB:
        return tree_path, None
    return tree_path, family_root / tree_file.replace("_yang_tree.txt", "_yang_tree_all.txt")


def _board(
    board_id: str,
    family: str,
    board_dir: str,
    tree_file: str,
    lt_slot: int | None = None,
) -> BoardInfo:
    tree_path, tree_all_path = _tree_paths(family, board_dir, tree_file)
    return BoardInfo(
        board_id=board_id,
        family=family,
        tree_path=tree_path,
        tree_all_path=tree_all_path,
        lt_slot=lt_slot,
    )


_BOARDS: tuple[BoardInfo, ...] = (
    _board("IHUB-LANT-A", FAMILY_IHUB, "LANT-A", "LS-MF-IHUB-LANT-A_yang_tree.txt"),
    _board("IHUB-LMNT-A", FAMILY_IHUB, "LMNT-A", "LS-MF-IHUB-LMNT-A_yang_tree.txt"),
    _board("IHUB-LMNT-B", FAMILY_IHUB, "LMNT-B", "LS-MF-IHUB-LMNT-B_yang_tree.txt"),
    _board("IHUB-LMNT-C", FAMILY_IHUB, "LMNT-C", "LS-MF-IHUB-LMNT-C_yang_tree.txt"),
    _board("IHUB-LMNT-D", FAMILY_IHUB, "LMNT-D", "LS-MF-IHUB-LMNT-D_yang_tree.txt"),
    _board("NT-LANT-A", FAMILY_NT, "LANT-A", "LS-MF-LANT-A_yang_tree.txt"),
    _board("NT-LBNT-A", FAMILY_NT, "LBNT-A", "LS-MF-LBNT-A_yang_tree.txt"),
    _board("NT-LDNT-A", FAMILY_NT, "LDNT-A", "LS-MF-LDNT-A_yang_tree.txt"),
    _board("NT-LMNT-A", FAMILY_NT, "LMNT-A", "LS-MF-LMNT-A_yang_tree.txt"),
    _board("NT-LMNT-B", FAMILY_NT, "LMNT-B", "LS-MF-LMNT-B_yang_tree.txt"),
    _board("NT-LMNT-C", FAMILY_NT, "LMNT-C", "LS-MF-LMNT-C_yang_tree.txt"),
    _board("NT-LMNT-D", FAMILY_NT, "LMNT-D", "LS-MF-LMNT-D_yang_tree.txt"),
    _board("LLLT-A", FAMILY_LT, "LLLT-A", "LS-MF-LLLT-A_yang_tree.txt", lt_slot=2),
    _board("LWLT-C", FAMILY_LT, "LWLT-C", "LS-MF-LWLT-C_yang_tree.txt", lt_slot=1),
    _board("LGLT-D", FAMILY_LT, "LGLT-D", "LS-MF-LGLT-D_yang_tree.txt", lt_slot=3),
)

_BOARD_INDEX = {board.board_id: board for board in _BOARDS}


def list_boards() -> list[BoardInfo]:
    return list(_BOARDS)


def get_board(board_id: str) -> BoardInfo:
    try:
        return _BOARD_INDEX[board_id]
    except KeyError as exc:
        known = ", ".join(board.board_id for board in _BOARDS)
        raise KeyError(f"Unknown board_id {board_id!r}; known boards: {known}") from exc


__all__ = [
    "BoardInfo",
    "FAMILY_IHUB",
    "FAMILY_LT",
    "FAMILY_NT",
    "YANG_MODEL_ROOT",
    "get_board",
    "list_boards",
]
