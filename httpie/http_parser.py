from dataclasses import dataclass
from pathlib import Path


@dataclass
class HttpFileRequest:
    method: str
    url: str
    headers: dict
    body: bytes


def http_parser(filename: str) -> list[HttpFileRequest]:
    
    def extract_headers(raw_text: str) -> dict :
        '''
        Extract the headers of the .http file
        
        Args:
            raw_text: the lines of the .http file containing the headers
        
        Returns:
            dict: containing the parsed headers
        '''
        return None
    
    def parse_body(raw_text: str) -> dict :
        '''
        parse the body of the .http file
        '''
        return None
    
    def parse_single_request(raw_text: str) -> HttpFileRequest:
        '''Parse a single request from .http file format to HttpFileRequest '''
        
        return HttpFileRequest(
            method=method,
            url=url,
            headers={},
            body=b"",
        )
    
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
