from pathlib import Path

from xml2cli.yang.tree_parser import parse_tree_file, parse_tree_text


def test_parse_tree_text_parses_list_keys_and_local_name():
    text = "module: demo\n  +--rw classifier-entry* [name]\n"

    modules = parse_tree_text(text, mode="standard")

    assert [module.name for module in modules] == ["demo"]
    line = modules[0].lines[0]
    assert line.keys == ["name"]
    assert line.local_name == "classifier-entry"
    assert line.is_config is True


def test_parse_tree_text_splits_prefix_and_local_name():
    text = "module: demo\n  +--rw nokia-xpon-acc-dr4:xpon-access-loop-characteristics*   identityref\n"

    modules = parse_tree_text(text, mode="standard")

    line = modules[0].lines[0]
    assert line.prefix == "nokia-xpon-acc-dr4"
    assert line.local_name == "xpon-access-loop-characteristics"


def test_skip_x_marked_lines_in_standard_mode():
    text = "module: demo\n  x--rw hidden-node?   string\n  +--rw visible   string\n"

    modules = parse_tree_text(text, mode="standard")

    assert [line.local_name for line in modules[0].lines] == ["visible"]


def test_parse_tree_file_returns_modules_from_fixture():
    fixture = Path(__file__).parent / "fixtures" / "yang_tree_sample.txt"

    modules = parse_tree_file(fixture, mode="standard")

    assert [module.name for module in modules[:2]] == [
        "bbf-l2-dhcpv4-relay-forwarding",
        "bbf-l2-dhcpv4-relay",
    ]
