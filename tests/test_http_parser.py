import pytest

from httpie.http_parser import (
    http_parser,
    split_requests,
    get_dependencies,
    get_name,
    replace_global,
    extract_headers,
    parse_body,
    parse_single_request,
)


def normalize_whitespace(text):
    """Removes excessive newlines and spaces for consistent comparison."""
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()


# TESTS FOR split_requests -->> REQ_002

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

    assert list(map(normalize_whitespace, split_requests(http_file))) == list(
        map(normalize_whitespace, expected_output)
    )


# Test case: Splitting a single HTTP request
def test_split_single_request():
    """
    This test ensures that a single HTTP request with a '###' header is correctly parsed
    without any unexpected modifications.
    """
    http_file = """### Only Request
GET /status"""

    expected_output = ["### Only Request\nGET /status"]

    assert list(map(normalize_whitespace, split_requests(http_file))) == list(
        map(normalize_whitespace, expected_output)
    )


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

    assert list(map(normalize_whitespace, split_requests(http_file))) == list(
        map(normalize_whitespace, expected_output)
    )


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

    assert list(map(normalize_whitespace, split_requests(http_file))) == list(
        map(normalize_whitespace, expected_output)
    )


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

def test_get_dependencies_no_placeholders():
    """
    This test verifies that if a request does not contain any {{placeholders}}, 
    the function correctly returns None.
    """
    raw_request = """GET /users"""
    possible_names = ["Request1", "Request2"]

    assert get_dependencies(raw_request, possible_names) is None


def test_get_dependencies_single_dependency():
    """
    This test checks that a single valid dependency is correctly extracted 
    from a request and returned in a list.
    """
    raw_request = """GET /users/{{Request1.id}}"""
    possible_names = ["Request1", "Request2"]

    expected_output = ["Request1"]
    assert get_dependencies(raw_request, possible_names) == expected_output


def test_get_dependencies_multiple_dependencies():
    """
    This test verifies that multiple dependencies are correctly identified 
    and returned in a list, regardless of order.
    """
    raw_request = """POST /orders/{{Request1.order_id}}/{{Request2.user_id}}"""
    possible_names = ["Request1", "Request2", "Request3"]

    expected_output = ["Request1", "Request2"]

    assert sorted(get_dependencies(raw_request, possible_names)) == sorted(expected_output)


def test_get_dependencies_invalid_dependency():
    """
    This test ensures that if the request references a dependency that is 
    not in the provided possible_names list, the function correctly returns None.
    """
    raw_request = """DELETE /items/{{InvalidRequest.item_id}}"""
    possible_names = ["Request1", "Request2"]

    assert get_dependencies(raw_request, possible_names) is None


def test_get_dependencies_complex_names():
    """
    This test checks that dependencies with numbers and underscores 
    are correctly extracted and returned, regardless of order.
    """
    raw_request = """PATCH /update/{{Request_1.field}}/{{Request2_2024.item}}"""
    possible_names = ["Request_1", "Request2_2024", "Request3"]

    expected_output = ["Request_1", "Request2_2024"]

    assert sorted(get_dependencies(raw_request, possible_names)) == sorted(expected_output)


def test_get_dependencies_repeated_dependency():
    """
    This test ensures that if the same dependency appears multiple times 
    in the request, it is still only listed once in the output.
    """
    raw_request = """PUT /update/{{Request1.id}}/{{Request1.name}}"""
    possible_names = ["Request1", "Request2"]

    expected_output = ["Request1"]  # Expect only one instance of "Request1"

    assert get_dependencies(raw_request, possible_names) == expected_output


def test_get_dependencies_empty_request():
    """
    This test checks that an empty request string returns None 
    since there are no placeholders.
    """
    raw_request = ""
    possible_names = ["Request1", "Request2"]

    assert get_dependencies(raw_request, possible_names) is None


# TESTS FOR get_name --> REQ_003

def test_get_name_with_hash_comment():
    """
    Ensures that get_name correctly extracts a request name 
    when defined with '#' as a comment.
    """
    raw_request = """# @name Request1
GET /users"""

    expected_output = "Request1"
    assert get_name(raw_request) == expected_output


def test_get_name_with_double_slash_comment():
    """
    Ensures that get_name correctly extracts a request name 
    when defined with '//' as a comment.
    """
    raw_request = """// @name GetUser
GET /users/{id}"""

    expected_output = "GetUser"
    assert get_name(raw_request) == expected_output


def test_get_name_no_name():
    """
    Ensures that if no '@name' is present, get_name returns None.
    """
    raw_request = """GET /users"""

    assert get_name(raw_request) is None


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


def test_get_name_with_extra_whitespace():
    """
    Ensures that extra spaces around @name do not affect the extracted name.
    """
    raw_request = """  #   @name   MyRequest   
GET /data"""

    expected_output = "MyRequest"
    assert get_name(raw_request) == expected_output


def test_get_name_without_request():
    """
    Ensures that a request with only an @name definition still correctly extracts the name.
    """
    raw_request = """// @name LoneRequest"""

    expected_output = "LoneRequest"
    assert get_name(raw_request) == expected_output


def test_get_name_inline_invalid():
    """
    Ensures that @name only works when it starts a line, 
    and does not extract names from inline comments.
    """
    raw_request = """GET /users # @name InlineName"""

    assert get_name(raw_request) is None  # Inline @name should not be detected


def test_get_name_mixed_comment_styles():
    """
    Ensures that if multiple valid @name comments exist,
    the function returns None to indicate an error.
    """
    raw_request = """# @name FirstRequest
// @name SecondRequest
GET /items"""

    assert get_name(raw_request) is None


# TESTS FOR replace_global --> REQ_005

def test_replace_global_no_definitions():
    """
    Ensures that if no global variable definitions are present,
    the file contents remain unchanged.
    """
    raw_contents = "GET /users/{{id}}"
    expected_output = raw_contents  # No replacement should occur
    assert replace_global(raw_contents) == expected_output


def test_replace_global_single_variable():
    """
    Ensures that a single global variable definition is correctly used to replace
    all its corresponding placeholders in the file.
    """
    raw_contents = """@host=example.com
GET http://{{host}}/users"""
    expected_output = """@host=example.com
GET http://example.com/users"""
    assert replace_global(raw_contents) == expected_output


def test_replace_global_multiple_variables():
    """
    Ensures that multiple global variable definitions are correctly used to replace
    their corresponding placeholders in the file.
    """
    raw_contents = """@host=example.com
@port=8080
GET http://{{host}}:{{port}}/users"""
    expected_output = """@host=example.com
@port=8080
GET http://example.com:8080/users"""
    assert replace_global(raw_contents) == expected_output


def test_replace_global_multiple_occurrences():
    """
    Ensures that if a variable appears multiple times in the file,
    all occurrences are replaced.
    """
    raw_contents = """@name=Test
GET /api?param={{name}}&other={{name}}"""
    expected_output = """@name=Test
GET /api?param=Test&other=Test"""
    assert replace_global(raw_contents) == expected_output


def test_replace_global_value_with_spaces():
    """
    Ensures that global variable definitions with spaces in their values are handled correctly.
    """
    raw_contents = """@greeting=Hello World
GET /message?text={{greeting}}"""
    expected_output = """@greeting=Hello World
GET /message?text=Hello World"""
    assert replace_global(raw_contents) == expected_output


def test_replace_global_definition_without_placeholder():
    """
    Ensures that if a global variable is defined but its placeholder is not present,
    the file remains unchanged.
    """
    raw_contents = """@unused=Value
GET /info"""
    expected_output = raw_contents  # No replacement should occur
    assert replace_global(raw_contents) == expected_output


# TESTS FOR extract_headers --> REQ_003

def test_extract_headers_empty():
    """
    Test 1: Empty list should return an empty dictionary.
    """
    raw_text = []
    expected = {}
    assert extract_headers(raw_text) == expected


def test_extract_headers_only_empty_lines():
    """
    Test 2: Lines that are empty or only whitespace should be ignored.
    """
    raw_text = ["", "   ", "\t"]
    expected = {}
    assert extract_headers(raw_text) == expected


def test_extract_headers_single_header():
    """
    Test 3: A single valid header line.
    """
    raw_text = ["Content-Type: application/json"]
    expected = {"Content-Type": "application/json"}
    assert extract_headers(raw_text) == expected


def test_extract_headers_multiple_headers():
    """
    Test 4: Multiple header lines should be parsed into a dictionary.
    """
    raw_text = [
        "Content-Type: application/json",
        "Authorization: Bearer token123"
    ]
    expected = {
        "Content-Type": "application/json",
        "Authorization": "Bearer token123"
    }
    assert extract_headers(raw_text) == expected


def test_extract_headers_line_without_colon():
    """
    Test 5: Lines without a colon should be ignored.
    """
    raw_text = [
        "This is not a header",
        "Content-Length: 123"
    ]
    expected = {"Content-Length": "123"}
    assert extract_headers(raw_text) == expected


def test_extract_headers_extra_spaces():
    """
    Test 6: Extra whitespace around header names and values should be trimmed.
    """
    raw_text = [
        "  Accept : text/html  "
    ]
    expected = {"Accept": "text/html"}
    assert extract_headers(raw_text) == expected


def test_extract_headers_multiple_colons():
    """
    Test 7: Only the first colon should be used to split the header name and value.
    """
    raw_text = [
        "Custom-Header: value:with:colons"
    ]
    expected = {"Custom-Header": "value:with:colons"}
    assert extract_headers(raw_text) == expected


def test_extract_headers_duplicate_headers():
    """
    Test 8: If a header appears more than once, the last occurrence should overwrite previous ones.
    """
    raw_text = [
        "X-Header: one",
        "X-Header: two"
    ]
    expected = {"X-Header": "two"}
    assert extract_headers(raw_text) == expected


# TESTS FOR parse_body -->> REQ_002
# TODO: create tests after function definition is done


# TESTS FOR parse_single_request -->> REQ_002

def test_parse_single_request_minimal():
    """
    A minimal HTTP request that only contains the request line (method and URL).
    Expected:
      - method and URL are parsed correctly.
      - headers is an empty dict.
      - body is empty (after processing by parse_body).
      - dependencies is an empty dict.
      - name is None (since no @name comment exists).
    """
    raw_text = "GET http://example.com"
    result = parse_single_request(raw_text)
    assert result.method == "GET"
    assert result.url == "http://example.com"
    assert result.headers == {}
    expected_body = parse_body("")
    assert result.body == expected_body
    assert result.dependencies == {}
    assert result.name is None


def test_parse_single_request_with_headers_and_body():
    """
    Tests a request that includes a request line, headers, and a body.
    Expected:
      - Correctly parsed method and URL.
      - Headers are extracted into a dictionary.
      - The body is passed through parse_body and matches the expected output.
      - No @name is defined, so name is None.
    """
    raw_text = """POST http://example.com/api
Content-Type: application/json
Authorization: Bearer token

{
  "key": "value"
}"""
    result = parse_single_request(raw_text)
    assert result.method == "POST"
    assert result.url == "http://example.com/api"
    assert result.headers == {
        "Content-Type": "application/json",
        "Authorization": "Bearer token"
    }
    expected_body = parse_body("{\n  \"key\": \"value\"\n}")
    assert result.body == expected_body
    assert result.dependencies == {}
    assert result.name is None


def test_parse_single_request_with_name():
    """
    Tests a request that includes a @name comment.
    The @name line is removed from the parsed lines (since lines starting with '#' are filtered out)
    but get_name is still applied on the original raw text.
    Expected:
      - name is extracted as defined by get_name.
      - Other fields (method, URL, headers, body) are parsed normally.
    """
    raw_text = """# @name MyTestRequest
GET http://example.com
Content-Type: text/plain

Hello, world!
"""
    result = parse_single_request(raw_text)
    assert result.method == "GET"
    assert result.url == "http://example.com"
    assert result.headers == {"Content-Type": "text/plain"}
    expected_body = parse_body("Hello, world!")
    assert result.body == expected_body
    assert result.dependencies == {}
    assert result.name == "MyTestRequest"


def test_parse_single_request_extra_blank_lines():
    """
    Tests that multiple blank lines (which trigger the switch from headers to body)
    are handled properly.
    Expected:
      - The request line is parsed.
      - Headers are extracted before the first blank line.
      - Everything after the blank lines is treated as the body.
    """
    raw_text = """PUT http://example.com/update
Accept: application/json


Line one of the body.
Line two of the body.
"""
    result = parse_single_request(raw_text)
    assert result.method == "PUT"
    assert result.url == "http://example.com/update"
    assert result.headers == {"Accept": "application/json"}
    expected_body = parse_body("Line one of the body.\nLine two of the body.")
    assert result.body == expected_body
    assert result.dependencies == {}
    assert result.name is None


def test_parse_single_request_ignore_comments():
    """
    Tests that lines starting with '#' (comments) are removed from the parsed headers.
    Note: Even if the @name line is a comment, get_name is called on the original raw text,
    so it may still extract a name.
    Expected:
      - Headers only include valid header lines.
      - The @name is still extracted if present in the raw text.
    """
    raw_text = """# @name CommentedRequest
GET http://example.com/data
# This comment should be ignored
Content-Length: 123

"""
    result = parse_single_request(raw_text)
    assert result.method == "GET"
    assert result.url == "http://example.com/data"
    assert result.headers == {"Content-Length": "123"}
    expected_body = parse_body("")
    assert result.body == expected_body
    assert result.dependencies == {}
    assert result.name == "CommentedRequest"


if __name__ == "__main__":
    pytest.main()
