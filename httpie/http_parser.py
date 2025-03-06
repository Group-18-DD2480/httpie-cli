from __future__ import annotations
from dataclasses import dataclass
import re
from re import Match
from .client import RequestsMessage
from typing import Iterable
import json
from jsonpath_ng import parse as jsonpath_parse
from lxml import etree


@dataclass
class HttpFileRequest:
    method: str
    url: str
    headers: dict | None
    body: bytes | None
    name: str | None


def split_requests(http_file_contents: str) -> list[str]:
    """Splits an HTTP file into individual requests but keeps the '###' in each request."""
    parts = re.split(r"(^###.*)", http_file_contents, flags=re.MULTILINE)
    requests = []

    for i in range(1, len(parts), 2):
        header = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        requests.append(f"{header}\n{body}")

    return requests


def replace_dependencies(raw_http_request: str, responses: dict[str, Iterable[RequestsMessage]]) -> str | None:
    """Returns a list of all unique request names that must be fulfilled before this request can be sent."""
    def replace(match:Match[str]):
        """gives the string which should replaces the one given as a parameter"""
        str = match.group(0)
        print(str)
        var = str.lstrip("{").rstrip("}")
        splitter = re.match(r"(?P<name>\w+)\.(?P<type>request|response)\.(?P<section>body|headers)\.(?P<extractor>.+)", var)
        if not splitter:
            raise ValueError(f"Difficulties replacing {str} in {raw_http_request}")
        dict = splitter.groupdict()
        req_name = dict["name"]
        req_type = dict["type"]  
        section = dict["section"]
        extractor = dict["extractor"]

        if responses.get(req_name) is None:
            raise ValueError(f"{req_name} is not an existing request's name")
        if req_type == "request":
            msg = responses[req_name][0]
        elif req_type == "response":
            msg:RequestsMessage = responses[req_name][1]
        
        
        if section == "body":
            if extractor == "*":
                return msg.body  # Return full body
            elif extractor.startswith("$."):  # JSONPath
                try:
                    json_data = msg.json()  # Convert response to JSON
                    jsonpath_expr = jsonpath_parse(extractor)
                    parsed_data = jsonpath_expr.find(json_data)
                    return [matched.value for matched in parsed_data] if parsed_data else None
                except json.JSONDecodeError:
                    return None  # Not a valid JSON
            elif extractor.startswith("/"):  # XPath
                try:
                    xml_tree = etree.fromstring(msg.content)  # Parse XML
                    return xml_tree.xpath(extractor)
                except etree.XMLSyntaxError:
                    return None  # Not a valid XML

        elif section == "headers":
            print(msg.headers[extractor])
            return msg.headers[extractor]
        
        return 
    pattern = r"\{\{(.*?)\}\}"
    return re.sub(pattern, replace, raw_http_request)

    


def get_name(raw_http_request: str) -> str | None:
    """
    Returns the name of the HTTP request if it has one, None otherwise.
    The expected pattern is either a comment starting with '//' or '#' (optionally preceded by whitespace)
    followed by '@name' and the name.
    """
    # Allow leading whitespace before the comment marker.
    matches = re.findall(r"^\s*(?://|#)\s*@name\s+(.+)$", raw_http_request, re.MULTILINE)

    if len(matches) == 0:
        return None
    elif len(matches) == 1:
        return matches[0].strip()  # strip extra whitespace if any
    else:
        # TODO: Handle error for multiple names found. Currently returns None.
        return None


def replace_global(http_file_contents_raw: str) -> str:
    """finds and replaces all global variables by their values"""
    # possible error when @variable=value is in the body
    matches = re.findall(r"^@([A-Za-z0-9_]+)=(.+)$", http_file_contents_raw, flags=re.MULTILINE)
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
        if not line.strip() or ':' not in line:
            continue

        header_name, header_value = line.split(':', 1)

        headers[header_name.strip()] = header_value.strip()

    return headers


def parse_body(raw_text: str) -> bytes:
    """
    parse the body of the .http file
    """
    return b""


def parse_single_request(raw_text: str) -> HttpFileRequest:
    """Parse a single request from .http file format to HttpFileRequest """
    lines = raw_text.strip().splitlines()

    lines = [line.strip() for line in lines if not line.strip().startswith("#")]

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
        name=get_name(raw_text)
    )
