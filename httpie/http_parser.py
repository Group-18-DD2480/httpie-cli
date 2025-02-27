from dataclasses import dataclass
from pathlib import Path


@dataclass
class HttpFileRequest:
    method: str
    url: str
    headers: dict
    body: bytes


def http_parser(filename: str) -> list[HttpFileRequest]:
    
    def extract_headers(raw_text: list[str]) -> dict :
        '''
        Extract the headers of the .http file
        
        Args:
            raw_text: the lines of the .http file containing the headers
        
        Returns:
            dict: containing the parsed headers
        '''
        return {}
    
    def parse_body(raw_text: str) -> bytes :
        '''
        parse the body of the .http file
        '''
        return b""
    
    def parse_single_request(raw_text: str) -> HttpFileRequest:
        '''Parse a single request from .http file format to HttpFileRequest '''
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
        )
    
    http_file = Path(filename)
    if not http_file.exists():
        raise FileNotFoundError(f"File not found: {filename}")
    if not http_file.is_file():
        raise IsADirectoryError(f"Path is not a file: {filename}")
    http_contents = http_file.read_text()
    
    raw_requests = http_contents.split("###")
    parsed_requests = []
    
    for raw_req in raw_requests:
        parsed_requests.append(parse_single_request(raw_req))

    return parsed_requests
