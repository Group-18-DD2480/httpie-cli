from __future__ import annotations
from dataclasses import dataclass
import re


@dataclass
class HttpFileRequest:
    method: str
    url: str
    headers: dict | None
    body: bytes | None
    dependencies: list[HttpFileRequest] | None
    name: str | None


def split_requests(http_file_contents: str) -> list[str]:
    """Splits an HTTP file into individual requests but keeps the '###' in each request."""
    parts = re.split(r"(^###.*)", http_file_contents, flags=re.MULTILINE)

    requests = []
    for part in parts:
        if part.startswith("###"):
            continue
        part = part.strip()
        if part:
            requests.append(part)

    return requests


def get_dependencies(raw_http_request: str, poss_names: list[str]) -> list[str] | None:
    """returns a list of all the names of the requests that must be fufilled before this one can be sent"""
    pattern = r"\{\{(.*?)\}\}"
    matches = re.findall(pattern, raw_http_request)
    if len(matches) == 0:
        return None
    names = [re.findall(r"^([A-Za-z0-9_]+).", match, re.MULTILINE) for match in matches]
    flat_names = [match for sublist in names for match in sublist]
    if not all(name in poss_names for name in flat_names):
        # TODO error not all dependencies exist
        return None
    return flat_names


def get_name(raw_http_request: str) -> str | None:
    """returns the name of the http request if it has one, None otherwise"""
    matches = re.findall(r"^((//)|(#)) @name (.+)", raw_http_request, re.MULTILINE)
    if len(matches) == 0:
        return None
    elif len(matches) == 1:
        return matches[0]
    else:
        # TODO error too many names
        return None


def replace_global(http_file_contents_raw: str) -> str:
    """finds and replaces all global variables by their values"""
    # possible error when @variable=value is in the body
    matches = re.findall(
        r"^@([A-Za-z0-9_]+)=(.+)$", http_file_contents_raw, re.MULTILINE
    )
    http_file_contents_cooking = http_file_contents_raw
    for variableName, value in matches:
        http_file_contents_cooking = re.sub(
            rf"{{{{({re.escape(variableName)})}}}}", value, http_file_contents_cooking
        )
    return http_file_contents_cooking


def extract_headers(raw_text: list[str]) -> dict:
    """
    Extract the headers of the .http file

    Args:
        raw_text: the lines of the .http file containing the headers

    Returns:
        dict: containing the parsed headers
    """
    headers = {}

    for line in raw_text:
        if not line.strip() or ":" not in line:
            continue

        header_name, header_value = line.split(":", 1)

        headers[header_name.strip()] = header_value.strip()

    return headers


def parse_body(raw_text: str) -> bytes:
    """
    parse the body of the .http file
    """
    return raw_text


def parse_single_request(raw_text: str) -> HttpFileRequest | None:
    """Parse a single request from .http file format to HttpFileRequest"""
    lines = raw_text.strip().splitlines()

    lines = [line.strip() for line in lines if not line.strip().startswith("#")]
    if not lines:
        return None
    method, url = lines[0].split(" ")

    raw_headers = []
    raw_body = []
    is_body = False

    for line in lines[1:]:
        if not line.strip():
            is_body = True
            continue
        if not is_body:
            raw_headers.append(line)
        else:
            raw_body.append(line)

    return HttpFileRequest(
        method=method,
        url=url,
        headers=extract_headers(raw_headers),
        body=parse_body("\n".join(raw_body)),
        dependencies={},
        name=get_name(raw_text),
    )
