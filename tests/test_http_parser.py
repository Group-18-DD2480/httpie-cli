import pytest
import re
import inspect

from httpie.http_parser import http_parser

def extract_inner_function(outer, inner):
    """Extracts `inner` function from `outer` function."""
    source_code = inspect.getsource(outer)  # Get the source of http_parser
    function_definitions = source_code.split("def ")  # Split by function definitions

    for func in function_definitions:
        if func.startswith(inner):  # Find split_requests
            exec("def " + func, globals())  # Define it globally
            return globals()[inner]  # Return extracted function

    raise ValueError("inner function not found inside of outer")

split_requests = extract_inner_function(http_parser, "split_requests")

def normalize_whitespace(text):
    """Removes excessive newlines and spaces for consistent comparison."""
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()

def test_split_requests():
    # Test case: Multiple HTTP requests
    http_file = """### Request 1
GET /users

### Request 2
POST /users
Content-Type: application/json

{"name": "John"}"""

    expected_output = [
        "### Request 1\nGET /users",
        "### Request 2\nPOST /users\nContent-Type: application/json\n\n{\"name\": \"John\"}"
    ]
    assert list(map(normalize_whitespace, split_requests(http_file))) == list(map(normalize_whitespace, expected_output))

    # Test case: Single HTTP request
    http_file = """### Only Request
GET /status"""

    expected_output = ["### Only Request\nGET /status"]
    assert list(map(normalize_whitespace, split_requests(http_file))) == list(map(normalize_whitespace, expected_output))

    # Test case: Empty file
    assert split_requests("") == []

    # Test case: Request with no body
    http_file = """### No Body Request
GET /ping"""

    expected_output = ["### No Body Request\nGET /ping"]
    assert list(map(normalize_whitespace, split_requests(http_file))) == list(map(normalize_whitespace, expected_output))

    # Test case: Request with extra newlines
    http_file = """### Request 1

GET /data


### Request 2

POST /submit

{"key": "value"}
"""

    expected_output = [
        "### Request 1\nGET /data",  # Normalized extra newline
        "### Request 2\nPOST /submit\n\n{\"key\": \"value\"}"  # Normalized newlines inside request
    ]
    assert list(map(normalize_whitespace, split_requests(http_file))) == list(map(normalize_whitespace, expected_output))

    # Test case: Request with no leading '###'
    http_file = """GET /withoutHeader"""

    expected_output = []  # Since no '###' header is present, it should return an empty list
    assert split_requests(http_file) == expected_output

if __name__ == "__main__":
    pytest.main()
