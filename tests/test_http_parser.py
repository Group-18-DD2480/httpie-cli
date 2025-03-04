import pytest
import re
import inspect

from httpie.http_parser import http_parser  # Import the main function containing split_requests

def extract_inner_function(outer, inner):
    """Extracts `inner` function from `outer` function."""
    source_code = inspect.getsource(outer)  # Get the source of http_parser
    function_definitions = source_code.split("def ")  # Split by function definitions

    for func in function_definitions:
        if func.startswith(inner):  # Find split_requests
            exec("def " + func, globals())  # Define it globally
            return globals()[inner]  # Return extracted function

    raise ValueError("inner function not found inside of outer")

def normalize_whitespace(text):
    """
    Normalizes whitespace by:
    - Stripping leading/trailing spaces
    - Collapsing multiple blank lines into a single newline
    """
    lines = text.splitlines()
    normalized_lines = [line.strip() for line in lines if line.strip() != ""]
    return "\n".join(normalized_lines)


# TESTS FOR split_requests

split_requests = extract_inner_function(http_parser, "split_requests")

# Test case: Splitting multiple HTTP requests
def test_split_multiple_requests():
    """
    This test verifies that split_requests correctly splits multiple HTTP requests
    while preserving the '###' headers.
    """
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

# Test case: Splitting a single HTTP request
def test_split_single_request():
    """
    This test ensures that a single HTTP request with a '###' header is correctly parsed
    without any unexpected modifications.
    """
    http_file = """### Only Request
GET /status"""

    expected_output = ["### Only Request\nGET /status"]

    assert list(map(normalize_whitespace, split_requests(http_file))) == list(map(normalize_whitespace, expected_output))

# Test case: Handling an empty input file
def test_split_empty_file():
    """
    This test checks if an empty input correctly returns an empty list,
    ensuring there are no errors when handling empty strings.
    """
    assert split_requests("") == []

# Test case: Splitting an HTTP request with no body
def test_split_request_no_body():
    """
    This test verifies that requests with no body (only headers and method)
    are parsed correctly without adding unnecessary spaces or newlines.
    """
    http_file = """### No Body Request
GET /ping"""

    expected_output = ["### No Body Request\nGET /ping"]

    assert list(map(normalize_whitespace, split_requests(http_file))) == list(map(normalize_whitespace, expected_output))

# Test case: Handling extra newlines within requests
def test_split_request_with_extra_newlines():
    """
    This test ensures that the function correctly handles requests that
    contain extra blank lines while preserving necessary formatting.
    """
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

# Test case: Handling requests without '###' header
def test_split_request_without_header():
    """
    This test ensures that requests without a '###' header are ignored and
    do not cause the function to fail. The function should return an empty list
    in such cases.
    """
    http_file = """GET /withoutHeader"""

    expected_output = []  # No '###' header means no valid requests should be returned

    assert split_requests(http_file) == expected_output

if __name__ == "__main__":
    pytest.main()