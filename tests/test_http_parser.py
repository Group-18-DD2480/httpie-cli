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


# TESTS FOR split_requests -->> REQ_002

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

# TESTS FOR get_dependencies  -->> REQ_007

get_dependencies = extract_inner_function(http_parser, "get_dependencies")

# Test case: No dependencies in request
def test_get_dependencies_no_placeholders():
    """
    This test verifies that if a request does not contain any {{placeholders}}, 
    the function correctly returns None.
    """
    raw_request = """GET /users"""
    possible_names = ["Request1", "Request2"]
    
    assert get_dependencies(raw_request, possible_names) is None

# Test case: Extracting single valid dependency
def test_get_dependencies_single_dependency():
    """
    This test checks that a single valid dependency is correctly extracted 
    from a request and returned in a list.
    """
    raw_request = """GET /users/{{Request1.id}}"""
    possible_names = ["Request1", "Request2"]
    
    expected_output = ["Request1"]
    assert get_dependencies(raw_request, possible_names) == expected_output

# Test case: Extracting multiple valid dependencies
def test_get_dependencies_multiple_dependencies():
    """
    This test verifies that multiple dependencies are correctly identified 
    and returned in a list, regardless of order.
    """
    raw_request = """POST /orders/{{Request1.order_id}}/{{Request2.user_id}}"""
    possible_names = ["Request1", "Request2", "Request3"]
    
    expected_output = ["Request1", "Request2"]
    
    assert sorted(get_dependencies(raw_request, possible_names)) == sorted(expected_output)


# Test case: Handling dependencies that do not exist
def test_get_dependencies_invalid_dependency():
    """
    This test ensures that if the request references a dependency that is 
    not in the provided possible_names list, the function correctly returns None.
    """
    raw_request = """DELETE /items/{{InvalidRequest.item_id}}"""
    possible_names = ["Request1", "Request2"]
    
    assert get_dependencies(raw_request, possible_names) is None

# Test case: Dependencies with complex formatting (numbers, underscores)
def test_get_dependencies_complex_names():
    """
    This test checks that dependencies with numbers and underscores 
    are correctly extracted and returned, regardless of order.
    """
    raw_request = """PATCH /update/{{Request_1.field}}/{{Request2_2024.item}}"""
    possible_names = ["Request_1", "Request2_2024", "Request3"]
    
    expected_output = ["Request_1", "Request2_2024"]
    
    assert sorted(get_dependencies(raw_request, possible_names)) == sorted(expected_output)


# Test case: Request with multiple occurrences of the same dependency
def test_get_dependencies_repeated_dependency():
    """
    This test ensures that if the same dependency appears multiple times 
    in the request, it is still only listed once in the output.
    """
    raw_request = """PUT /update/{{Request1.id}}/{{Request1.name}}"""
    possible_names = ["Request1", "Request2"]
    
    expected_output = ["Request1"]  # Expect only one instance of "Request1"

    assert get_dependencies(raw_request, possible_names) == expected_output


# Test case: Empty input request
def test_get_dependencies_empty_request():
    """
    This test checks that an empty request string returns None 
    since there are no placeholders.
    """
    raw_request = ""
    possible_names = ["Request1", "Request2"]
    
    assert get_dependencies(raw_request, possible_names) is None


# TESTS FOR get_name --> REQ_003

get_name = extract_inner_function(http_parser, "get_name")

# Test: Valid request name with '#' comment
def test_get_name_with_hash_comment():
    """
    Ensures that get_name correctly extracts a request name 
    when defined with '#' as a comment.
    """
    raw_request = """# @name Request1
GET /users"""
    
    expected_output = "Request1"
    assert get_name(raw_request) == expected_output

# Test: Valid request name with '//' comment
def test_get_name_with_double_slash_comment():
    """
    Ensures that get_name correctly extracts a request name 
    when defined with '//' as a comment.
    """
    raw_request = """// @name GetUser
GET /users/{id}"""
    
    expected_output = "GetUser"
    assert get_name(raw_request) == expected_output

# Test: Request without a name
def test_get_name_no_name():
    """
    Ensures that if no '@name' is present, get_name returns None.
    """
    raw_request = """GET /users"""
    
    assert get_name(raw_request) is None

# Test: Multiple @name occurrences (invalid case)
def test_get_name_multiple_names():
    """
    Ensures that if multiple '@name' occurrences exist, 
    the function returns None to indicate an error.
    """
    raw_request = """# @name FirstName
GET /users
# @name SecondName
POST /users"""
    
    assert get_name(raw_request) is None  # Multiple names should result in None

# Test: Request with extra whitespace
def test_get_name_with_extra_whitespace():
    """
    Ensures that extra spaces around @name do not affect the extracted name.
    """
    raw_request = """  #   @name   MyRequest   
GET /data"""
    
    expected_output = "MyRequest"
    assert get_name(raw_request) == expected_output

# Test: Request with name but no actual request content
def test_get_name_without_request():
    """
    Ensures that a request with only an @name definition still correctly extracts the name.
    """
    raw_request = """// @name LoneRequest"""
    
    expected_output = "LoneRequest"
    assert get_name(raw_request) == expected_output

# Test: Request with an inline @name (invalid case)
def test_get_name_inline_invalid():
    """
    Ensures that @name only works when it starts a line, 
    and does not extract names from inline comments.
    """
    raw_request = """GET /users # @name InlineName"""
    
    assert get_name(raw_request) is None  # Inline @name should not be detected

# Test: Request with mixed comment styles
def test_get_name_mixed_comment_styles():
    """
    Ensures that if multiple valid @name comments exist,
    the function returns None to indicate an error.
    """
    raw_request = """# @name FirstRequest
// @name SecondRequest
GET /items"""
    
    assert get_name(raw_request) is None


if __name__ == "__main__":
    pytest.main()