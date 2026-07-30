"""Command-line interface for xml2cli."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from xml2cli.engine import convert_cli_to_xml, convert_xml_to_cli
from xml2cli.profiles.base import get_profile_by_folder, list_profile_folders, resolve_profile_name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NETCONF XML ↔ CLI converter")
    subparsers = parser.add_subparsers(dest="command", required=True)

    xml2cli_parser = subparsers.add_parser("xml2cli", help="Convert XML files to CLI")
    xml2cli_parser.add_argument("path", help="XML file or directory")
    xml2cli_parser.add_argument("-o", "--output", help="Output directory for .cli files")
    xml2cli_parser.add_argument(
        "--profile",
        help="Profile name or folder (required when input is pasted content via stdin)",
    )

    cli2xml_parser = subparsers.add_parser("cli2xml", help="Convert CLI to XML RPC")
    cli2xml_parser.add_argument("cli", nargs="?", help="CLI command string")
    cli2xml_parser.add_argument("--profile", required=True, help="Profile name or folder")
    cli2xml_parser.add_argument("-o", "--output", help="Output XML file")

    serve_parser = subparsers.add_parser("serve", help="Start web UI and API server")
    serve_parser.add_argument("--host", default="0.0.0.0")
    serve_parser.add_argument("--port", type=int, default=8888)

    args = parser.parse_args(argv)

    if args.command == "xml2cli":
        return _cmd_xml2cli(args)
    if args.command == "cli2xml":
        return _cmd_cli2xml(args)
    if args.command == "serve":
        return _cmd_serve(args)
    return 1


def _cmd_xml2cli(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if path.is_dir():
        return _convert_directory(path, args.output)
    if path.is_file():
        return _convert_file(path, args.output, args.profile)
    print(f"Error: path not found: {path}", file=sys.stderr)
    return 1


def _convert_directory(directory: Path, output_dir: str | None) -> int:
    exit_code = 0
    seen: set[Path] = set()
    for xml_file in directory.rglob("*"):
        if xml_file.suffix.lower() != ".xml" or xml_file in seen:
            continue
        seen.add(xml_file)
        code = _convert_file(xml_file, output_dir, profile_name=None)
        exit_code = max(exit_code, code)
    return exit_code


def _convert_file(xml_file: Path, output_dir: str | None, profile_name: str | None) -> int:
    content = xml_file.read_text(encoding="utf-8")
    folder = xml_file.parent.name
    try:
        if profile_name:
            profile = resolve_profile_name(profile_name)
            folder = profile_name
        else:
            get_profile_by_folder(folder)
    except ValueError as exc:
        print(f"Error [{xml_file}]: {exc}", file=sys.stderr)
        return 1

    cli_lines, errors = convert_xml_to_cli(content, folder)
    for error in errors:
        print(f"Error [{xml_file}]: {error}", file=sys.stderr)
        return 1

    output_text = "\n".join(cli_lines)
    if output_dir:
        out_path = Path(output_dir) / (xml_file.stem + ".cli")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_text + ("\n" if output_text else ""), encoding="utf-8")
        print(f"Wrote {out_path}")
    else:
        if output_text:
            print(output_text)
    return 0


def _cmd_cli2xml(args: argparse.Namespace) -> int:
    cli_text = args.cli
    if not cli_text:
        cli_text = sys.stdin.read()
    if not cli_text.strip():
        print("Error: no CLI input provided", file=sys.stderr)
        return 1

    xml_output, errors = convert_cli_to_xml(cli_text, args.profile)
    for error in errors:
        print(f"Warning: {error}", file=sys.stderr)
    if not xml_output:
        for error in errors:
            print(f"Error: {error}", file=sys.stderr)
        return 1

    if args.output:
        Path(args.output).write_text(xml_output, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(xml_output, end="")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from xml2cli.api import create_app

    app = create_app()
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
