"""FastAPI application for xml2cli web UI."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from xml2cli.engine import (
    convert_cli_to_xml_auto,
    convert_xml_to_cli_auto,
    detect_profile_from_cli,
    detect_profile_from_xml,
)
from xml2cli.profiles.base import list_profile_folders


class ConvertRequest(BaseModel):
    content: str = Field(..., min_length=1)


class Xml2CliResponse(BaseModel):
    cli: list[str]
    errors: list[str]
    profile: str | None = None


class Cli2XmlResponse(BaseModel):
    xml: str
    errors: list[str]
    profile: str | None = None


class ProfilesResponse(BaseModel):
    profiles: list[str]


class DetectProfileResponse(BaseModel):
    profile: str | None


def create_app() -> FastAPI:
    app = FastAPI(title="xml2cli", version="0.1.0")
    web_dir = Path(__file__).resolve().parent.parent / "web"

    @app.get("/api/profiles", response_model=ProfilesResponse)
    def get_profiles() -> ProfilesResponse:
        return ProfilesResponse(profiles=list_profile_folders())

    @app.post("/api/xml2cli", response_model=Xml2CliResponse)
    def api_xml2cli(request: ConvertRequest) -> Xml2CliResponse:
        cli_lines, errors, profile = convert_xml_to_cli_auto(request.content)
        return Xml2CliResponse(cli=cli_lines, errors=errors, profile=profile)

    @app.post("/api/detect-profile", response_model=DetectProfileResponse)
    def api_detect_profile(request: ConvertRequest) -> DetectProfileResponse:
        profile = detect_profile_from_xml(request.content)
        if profile is None:
            profile = detect_profile_from_cli(request.content)
        return DetectProfileResponse(profile=profile)

    @app.post("/api/cli2xml", response_model=Cli2XmlResponse)
    def api_cli2xml(request: ConvertRequest) -> Cli2XmlResponse:
        xml_output, errors, profile = convert_cli_to_xml_auto(request.content)
        return Cli2XmlResponse(xml=xml_output, errors=errors, profile=profile)

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(web_dir / "index.html")

    app.mount("/static", StaticFiles(directory=web_dir), name="static")
    return app
