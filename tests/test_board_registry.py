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
