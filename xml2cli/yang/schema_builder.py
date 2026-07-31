"""Build BoardSchema trees from pyang tree text."""

from __future__ import annotations

from xml2cli.board_registry import BoardInfo, get_board
from xml2cli.yang.schema import BoardSchema, SchemaNode
from xml2cli.yang.tree_parser import TreeLine, TreeMode, TreeModule, parse_tree_file

MODULE_LEVEL_INDENT = 2
IHUB_CONFIGURE_ROOT = "configure"
IHUB_ACTION_RPC_MODULE = "action-rpc"

# Choice/case handling: pyang choice nodes appear as parenthesized names; case branches
# use the +--: marker. Both are preserved as explicit choice/case SchemaNode kinds so
# downstream conversion can branch on alternatives without flattening.


def build_board_schema(board_id: str, mode: TreeMode = "standard") -> BoardSchema:
    board = get_board(board_id)
    tree_path = _tree_path_for_mode(board, mode)
    modules = parse_tree_file(tree_path, mode=mode)

    config_roots: list[str] = []
    roots: dict[str, SchemaNode] = {}

    for module in modules:
        for line in _module_level_config_lines(module):
            root_name = _node_key(line)
            if root_name not in roots:
                config_roots.append(root_name)
                roots[root_name] = _build_subtree(module.lines, line)

    return BoardSchema(
        board_id=board.board_id,
        family=board.family,
        config_roots=config_roots,
        modules=[module.name for module in modules],
        roots=roots,
    )


def _tree_path_for_mode(board: BoardInfo, mode: TreeMode):
    from pathlib import Path

    if mode == "all" and board.tree_all_path is not None:
        return board.tree_all_path
    return board.tree_path


def _module_level_config_lines(module: TreeModule) -> list[TreeLine]:
    module_level = [line for line in module.lines if line.indent == MODULE_LEVEL_INDENT]
    config_lines = [line for line in module_level if line.is_config]
    if not config_lines:
        return []

    # IHUB boards expose configuration under action-rpc/configure, not action-rpc itself.
    if module.name == IHUB_ACTION_RPC_MODULE:
        configure_lines = [
            line for line in config_lines if _node_key(line) == IHUB_CONFIGURE_ROOT
        ]
        if configure_lines:
            return configure_lines

    return config_lines


def _build_subtree(lines: list[TreeLine], root_line: TreeLine) -> SchemaNode:
    root_index = lines.index(root_line)
    root_node = _line_to_schema_node(
        root_line, has_children=_has_child_lines(lines, root_index)
    )
    stack: list[tuple[TreeLine, SchemaNode]] = [(root_line, root_node)]

    for index, line in enumerate(lines):
        if line.indent <= root_line.indent:
            continue
        if line.is_state:
            continue

        node = _line_to_schema_node(line, has_children=_has_child_lines(lines, index))

        while len(stack) > 1 and line.indent <= stack[-1][0].indent:
            stack.pop()

        parent_line, parent_node = stack[-1]
        if line.indent > parent_line.indent:
            parent_node.children[_node_key(line)] = node
            stack.append((line, node))

    return root_node


def _line_to_schema_node(line: TreeLine, has_children: bool) -> SchemaNode:
    kind = _resolve_kind(line, has_children=has_children)
    return SchemaNode(
        name=_node_key(line),
        kind=kind,
        keys=list(line.keys),
        prefix=line.prefix,
        children={},
        optional=line.optional,
    )


def _resolve_kind(line: TreeLine, has_children: bool) -> str:
    if line.is_case:
        return "case"
    if line.is_choice:
        return "choice"
    if line.is_list or line.keys:
        return "list"
    if has_children:
        if line.is_presence:
            return "presence-container"
        return "container"
    return "leaf"


def _node_key(line: TreeLine) -> str:
    return line.local_name or line.name


def _has_child_lines(lines: list[TreeLine], index: int) -> bool:
    base_indent = lines[index].indent
    for other in lines[index + 1 :]:
        if other.indent <= base_indent:
            break
        if other.is_state:
            continue
        return True
    return False
