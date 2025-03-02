from dataclasses import dataclass
from pathlib import Path


@dataclass
class HttpFileRequest:
    method: str
    url: str
    headers: dict
    body: bytes


def http_parser(filename: str) -> list[HttpFileRequest]:
    http_file = Path(filename)
    if not http_file.exists():
        raise FileNotFoundError(f"File not found: {filename}")
    if not http_file.is_file():
        raise IsADirectoryError(f"Path is not a file: {filename}")
    http_contents = http_file.read_text()
    http_lines = [
        line for line in http_contents.splitlines() if not line.startswith("#")
    ]
    http_lines = [line for line in http_lines if line.strip()]
    first_line = http_lines[0]
    method, url = first_line.split(" ")

    return [
        HttpFileRequest(
            method=method,
            url=url,
            headers={},
            body=b"",
        )
    ]
