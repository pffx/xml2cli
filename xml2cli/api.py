"""FastAPI application for xml2cli web UI."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from xml2cli.conversion import (
    board_info_dict,
    convert_cli_to_xml,
    convert_cli_to_xml_auto,
    convert_xml_to_cli,
    convert_xml_to_cli_auto,
    detect_board_from_cli,
    detect_board_from_xml,
    list_boards,
)
from xml2cli.deploy import DeviceTarget, deploy_to_device


class ConvertRequest(BaseModel):
    content: str = Field(..., min_length=1)
    board: str | None = None
    yang_tree: Literal["standard", "all"] = "standard"


class Xml2CliResponse(BaseModel):
    cli: list[str]
    errors: list[str]
    board: str | None = None


class Cli2XmlResponse(BaseModel):
    xml: str
    errors: list[str]
    board: str | None = None


class BoardsResponse(BaseModel):
    boards: list[dict[str, Any]]


class DetectBoardResponse(BaseModel):
    board: str | None


class DeployRequest(BaseModel):
    content: str = Field(..., min_length=1)
    content_format: Literal["cli", "xml"]
    host: str = Field(..., min_length=1)
    port: int = Field(..., ge=1, le=65535)
    username: str = Field(..., min_length=1)
    password: str = ""
    transport: Literal["netconf", "cli"] = "netconf"
    board: str | None = None
    yang_tree: Literal["standard", "all"] = "standard"


class DeployResponse(BaseModel):
    success: bool
    message: str
    details: list[str] = Field(default_factory=list)


def create_app() -> FastAPI:
    app = FastAPI(title="xml2cli", version="0.2.0")
    web_dir = Path(__file__).resolve().parent.parent / "web"

    @app.get("/api/boards", response_model=BoardsResponse)
    def get_boards() -> BoardsResponse:
        return BoardsResponse(boards=[board_info_dict(board) for board in list_boards()])

    @app.get("/api/profiles", response_model=BoardsResponse)
    def get_profiles() -> BoardsResponse:
        return get_boards()

    @app.post("/api/xml2cli", response_model=Xml2CliResponse)
    def api_xml2cli(request: ConvertRequest) -> Xml2CliResponse:
        if request.board:
            board_id = request.board
        else:
            board_id = detect_board_from_xml(request.content)
            if board_id is None:
                return Xml2CliResponse(
                    cli=[],
                    errors=["无法根据 XML 内容自动识别板卡类型"],
                    board=None,
                )
        cli_lines, errors = convert_xml_to_cli(
            request.content,
            board_id,
            yang_tree=request.yang_tree,
        )
        return Xml2CliResponse(cli=cli_lines, errors=errors, board=board_id)

    @app.post("/api/detect-profile", response_model=DetectBoardResponse)
    def api_detect_profile(request: ConvertRequest) -> DetectBoardResponse:
        board = detect_board_from_xml(request.content)
        if board is None:
            board = detect_board_from_cli(request.content)
        return DetectBoardResponse(board=board)

    @app.post("/api/cli2xml", response_model=Cli2XmlResponse)
    def api_cli2xml(request: ConvertRequest) -> Cli2XmlResponse:
        if request.board:
            xml_output, errors = convert_cli_to_xml(
                request.content,
                request.board,
                yang_tree=request.yang_tree,
            )
            return Cli2XmlResponse(xml=xml_output, errors=errors, board=request.board)
        xml_output, errors, board = convert_cli_to_xml_auto(
            request.content,
            yang_tree=request.yang_tree,
        )
        return Cli2XmlResponse(xml=xml_output, errors=errors, board=board)

    @app.post("/api/deploy", response_model=DeployResponse)
    def api_deploy(request: DeployRequest) -> DeployResponse:
        target = DeviceTarget(
            host=request.host.strip(),
            port=request.port,
            username=request.username.strip(),
            password=request.password,
            transport=request.transport,
        )
        result = deploy_to_device(
            request.content,
            content_format=request.content_format,
            target=target,
            board=request.board,
            yang_tree=request.yang_tree,
        )
        return DeployResponse(
            success=result.success,
            message=result.message,
            details=list(result.details),
        )

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(web_dir / "index.html")

    app.mount("/static", StaticFiles(directory=web_dir), name="static")
    return app
