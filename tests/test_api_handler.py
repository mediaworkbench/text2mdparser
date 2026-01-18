# Tests for src.api_handler
import pytest
from src.api_handler import call_llm_api
import requests
import json
import logging # For caplog

# Add project root to sys.path for src imports
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

SAMPLE_API_URL = "http://fake-lmstudio-api.com/v1/chat/completions"
SAMPLE_TEXT_CONTENT = "This is a test document."
EXPECTED_PROMPT_START = "Convert the following text to well-structured Markdown." # from api_handler default
EXPECTED_SYSTEM_MESSAGE = "You are a helpful assistant that converts text to well-structured Markdown."

@pytest.fixture
def mock_requests_post(mocker):
    """Fixture to mock requests.post."""
    return mocker.patch('requests.post')

def test_call_lm_studio_api_success(mock_requests_post, caplog):
    """Test successful API call and Markdown content extraction."""
    caplog.set_level(logging.INFO)
    mock_response = mock_requests_post.return_value
    mock_response.status_code = 200
    expected_markdown = "## Test Markdown\n\n- Item 1"
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": expected_markdown
                }
            }
        ]
    }

    result = call_llm_api(SAMPLE_TEXT_CONTENT, SAMPLE_API_URL, 'lmstudio')

    assert result == expected_markdown
    mock_requests_post.assert_called_once()
    args, kwargs = mock_requests_post.call_args
    assert args[0] == SAMPLE_API_URL
    assert kwargs['headers']['Content-Type'] == 'application/json'
    assert 'Authorization' not in kwargs['headers'] # No API key by default

    payload = kwargs['json']
    assert payload['messages'][0]['role'] == 'system'
    assert payload['messages'][0]['content'] == EXPECTED_SYSTEM_MESSAGE
    assert payload['messages'][1]['role'] == 'user'
    assert EXPECTED_PROMPT_START in payload['messages'][1]['content']
    assert SAMPLE_TEXT_CONTENT in payload['messages'][1]['content']
    assert 'model' not in payload # By default, no model identifier

    assert f"Calling lmstudio API at {SAMPLE_API_URL}..." in caplog.text
    assert f"API call to lmstudio API at {SAMPLE_API_URL} successful, content received." in caplog.text

def test_call_lm_studio_api_with_model_identifier(mock_requests_post, mocker):
    """Test API call when model_identifier is provided."""
    mocker.patch('src.api_handler.get_lmstudio_loaded_models', return_value=['test-model-123'])
    mock_response = mock_requests_post.return_value
    mock_response.status_code = 200
    mock_response.json.return_value = {"choices": [{"message": {"content": "markdown"}}]}
    test_model_id = "test-model-123"

    call_llm_api(SAMPLE_TEXT_CONTENT, SAMPLE_API_URL, 'lmstudio', model_identifier=test_model_id)

    mock_requests_post.assert_called_once()
    _, kwargs = mock_requests_post.call_args
    payload = kwargs['json']
    assert payload['model'] == test_model_id

def test_call_lm_studio_api_with_empty_model_identifier(mock_requests_post):
    """Test API call when model_identifier is an empty string."""
    mock_response = mock_requests_post.return_value
    mock_response.status_code = 200
    mock_response.json.return_value = {"choices": [{"message": {"content": "markdown"}}]}

    call_llm_api(SAMPLE_TEXT_CONTENT, SAMPLE_API_URL, 'lmstudio', model_identifier="")

    mock_requests_post.assert_called_once()
    _, kwargs = mock_requests_post.call_args
    payload = kwargs['json']
    assert 'model' not in payload # Empty string should be treated as None/not provided

def test_call_lm_studio_api_with_custom_system_prompt(mock_requests_post):
    """Test API call with custom system prompt."""
    mock_response = mock_requests_post.return_value
    mock_response.status_code = 200
    mock_response.json.return_value = {"choices": [{"message": {"content": "markdown"}}]}
    custom_prompt = "You are a specialized medical document formatter."

    call_llm_api(SAMPLE_TEXT_CONTENT, SAMPLE_API_URL, 'lmstudio', system_prompt=custom_prompt)

    mock_requests_post.assert_called_once()
    _, kwargs = mock_requests_post.call_args
    payload = kwargs['json']
    assert payload['messages'][0]['role'] == 'system'
    assert payload['messages'][0]['content'] == custom_prompt

def test_call_lm_studio_api_with_custom_temperature(mock_requests_post):
    """Test API call with custom temperature."""
    mock_response = mock_requests_post.return_value
    mock_response.status_code = 200
    mock_response.json.return_value = {"choices": [{"message": {"content": "markdown"}}]}

    call_llm_api(SAMPLE_TEXT_CONTENT, SAMPLE_API_URL, 'lmstudio', temperature=0.3)

    mock_requests_post.assert_called_once()
    _, kwargs = mock_requests_post.call_args
    payload = kwargs['json']
    assert payload['temperature'] == 0.3

def test_call_lm_studio_api_with_max_tokens(mock_requests_post):
    """Test API call with max_tokens set."""
    mock_response = mock_requests_post.return_value
    mock_response.status_code = 200
    mock_response.json.return_value = {"choices": [{"message": {"content": "markdown"}}]}

    call_llm_api(SAMPLE_TEXT_CONTENT, SAMPLE_API_URL, 'lmstudio', max_tokens=2000)

    mock_requests_post.assert_called_once()
    _, kwargs = mock_requests_post.call_args
    payload = kwargs['json']
    assert payload['max_tokens'] == 2000

def test_call_lm_studio_api_without_max_tokens(mock_requests_post):
    """Test API call without max_tokens (should not be in payload)."""
    mock_response = mock_requests_post.return_value
    mock_response.status_code = 200
    mock_response.json.return_value = {"choices": [{"message": {"content": "markdown"}}]}

    call_llm_api(SAMPLE_TEXT_CONTENT, SAMPLE_API_URL, 'lmstudio', max_tokens=None)

    mock_requests_post.assert_called_once()
    _, kwargs = mock_requests_post.call_args
    payload = kwargs['json']
    assert 'max_tokens' not in payload

def test_call_lm_studio_api_success_with_api_key(mock_requests_post):
    """Test successful API call with an API key."""
    api_key = "test_api_key_123"
    mock_response = mock_requests_post.return_value
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "markdown"}}]
    }

    call_llm_api(SAMPLE_TEXT_CONTENT, SAMPLE_API_URL, 'lmstudio', api_key=api_key)

    mock_requests_post.assert_called_once()
    _, kwargs = mock_requests_post.call_args
    assert kwargs['headers']['Authorization'] == f"Bearer {api_key}"

def test_call_lm_studio_api_http_error(mock_requests_post, caplog):
    """Test handling of HTTP non-200 status codes."""
    caplog.set_level(logging.ERROR)
    mock_response = mock_requests_post.return_value
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    result = call_llm_api(SAMPLE_TEXT_CONTENT, SAMPLE_API_URL, 'lmstudio')

    assert result is None
    assert f"API request to lmstudio API at {SAMPLE_API_URL} failed with status code 500. Response: Internal Server Error" in caplog.text

def test_call_lm_studio_api_request_exception_timeout(mock_requests_post, caplog):
    """Test handling of requests.exceptions.Timeout."""
    caplog.set_level(logging.ERROR)
    mock_requests_post.side_effect = requests.exceptions.Timeout("Request timed out")

    result = call_llm_api(SAMPLE_TEXT_CONTENT, SAMPLE_API_URL, 'lmstudio')

    assert result is None
    assert f"API request to lmstudio API at {SAMPLE_API_URL} timed out after 60 seconds." in caplog.text
    assert "Request timed out" in caplog.text # Check if the original exception message is part of the log

def test_call_lm_studio_api_connection_error(mock_requests_post, caplog):
    """Test handling of requests.exceptions.ConnectionError (LM Studio not running)."""
    caplog.set_level(logging.ERROR)
    mock_requests_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

    result = call_llm_api(SAMPLE_TEXT_CONTENT, SAMPLE_API_URL, 'lmstudio')

    assert result is None
    assert f"Cannot connect to lmstudio API at {SAMPLE_API_URL}" in caplog.text
    assert "Please ensure that:" in caplog.text
    assert "1. LM Studio is running" in caplog.text
    assert "2. A model is loaded in LM Studio" in caplog.text

def test_call_lm_studio_api_request_exception_generic(mock_requests_post, caplog):
    """Test handling of generic requests.exceptions.RequestException."""
    caplog.set_level(logging.ERROR)
    mock_requests_post.side_effect = requests.exceptions.RequestException("Generic network error")

    result = call_llm_api(SAMPLE_TEXT_CONTENT, SAMPLE_API_URL, 'lmstudio')

    assert result is None
    assert f"API request to lmstudio API at {SAMPLE_API_URL} failed due to a network or request issue: Generic network error" in caplog.text

def test_call_lm_studio_api_json_decode_error(mock_requests_post, caplog):
    """Test handling of JSONDecodeError when parsing API response."""
    caplog.set_level(logging.ERROR)
    mock_response = mock_requests_post.return_value
    mock_response.status_code = 200
    mock_response.text = "This is not valid JSON"
    mock_response.json.side_effect = json.JSONDecodeError("Error decoding JSON", "doc", 0)

    result = call_llm_api(SAMPLE_TEXT_CONTENT, SAMPLE_API_URL, 'lmstudio')

    assert result is None
    assert f"Could not decode JSON response from lmstudio API at {SAMPLE_API_URL}. Response text: This is not valid JSON" in caplog.text

def test_call_lm_studio_api_unexpected_response_structure(mock_requests_post, caplog):
    """Test handling of unexpected (but valid JSON) API response structure."""
    caplog.set_level(logging.ERROR)
    mock_response = mock_requests_post.return_value
    mock_response.status_code = 200
    response_json_data = {"not_choices": []}
    mock_response.json.return_value = response_json_data
    # Set .text attribute for when it's logged
    mock_response.text = json.dumps(response_json_data)

    result = call_llm_api(SAMPLE_TEXT_CONTENT, SAMPLE_API_URL, 'lmstudio')

    assert result is None
    assert f"Unexpected response structure from lmstudio API at {SAMPLE_API_URL}. Full response: {json.dumps({'not_choices': []})}" in caplog.text

def test_call_lm_studio_api_unexpected_exception(mock_requests_post, caplog):
    """Test handling of truly unexpected exceptions during the API call process."""
    caplog.set_level(logging.ERROR)
    mock_requests_post.side_effect = Exception("A totally unexpected error!")

    result = call_llm_api(SAMPLE_TEXT_CONTENT, SAMPLE_API_URL, 'lmstudio')

    assert result is None
    assert f"An unexpected error occurred during the API call to lmstudio API at {SAMPLE_API_URL}: A totally unexpected error!" in caplog.text
