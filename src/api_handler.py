import requests
import json
import logging
import subprocess

logger = logging.getLogger(__name__)

def get_lmstudio_loaded_models(base_url: str) -> list[str]:
    """
    Get the list of loaded models from LM Studio.
    """
    try:
        response = requests.get(f"{base_url}/v1/models")
        if response.status_code == 200:
            data = response.json()
            return [model['id'] for model in data.get('data', [])]
        else:
            logger.warning(f"Failed to get loaded models: {response.status_code} {response.text}")
            return []
    except Exception as e:
        logger.warning(f"Error getting loaded models: {e}")
        return []

def load_lmstudio_model(base_url: str, model_name: str) -> bool:
    """
    Load a model in LM Studio using the CLI.
    """
    try:
        result = subprocess.run(['lms', 'load', model_name], capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            logger.info(f"Successfully loaded model {model_name} via CLI")
            return True
        else:
            logger.error(f"Failed to load model {model_name} via CLI: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout loading model {model_name} via CLI")
        return False
    except FileNotFoundError:
        logger.error("LM Studio CLI 'lms' not found. Please ensure LM Studio is installed and 'lms' is in PATH.")
        return False
    except Exception as e:
        logger.error(f"Error loading model {model_name} via CLI: {e}")
        return False

def call_llm_api(
    text_content: str, 
    api_url: str, 
    server_type: str,
    api_key: str | None = None, 
    timeout: int = 60, 
    model_identifier: str | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int | None = None
) -> str | None:
    """
    Calls the LLM API (LM Studio or Ollama) to convert text content to Markdown.

    Args:
        text_content: The text content to be converted.
        api_url: The API endpoint URL.
        server_type: 'lmstudio' or 'ollama'
        api_key: Optional API key (for LM Studio).
        timeout: Timeout for the API request in seconds.
        model_identifier: Optional model identifier to use.
        system_prompt: System prompt for the API. If None, uses a default.
        temperature: Temperature for response generation (0.0 to 1.0).
        max_tokens: Maximum tokens in the response. If None, omitted from payload.

    Returns:
        The Markdown content as a string if successful, otherwise None.
    """
    # Default system prompt if none provided
    if system_prompt is None:
        system_prompt = "You are a helpful assistant that converts text to well-structured Markdown."
    
    # For LM Studio, ensure the model is loaded
    if server_type.lower() == 'lmstudio' and model_identifier:
        base_url = api_url.replace('/v1/chat/completions', '')
        loaded_models = get_lmstudio_loaded_models(base_url)
        if model_identifier not in loaded_models:
            logger.info(f"Model {model_identifier} not loaded, attempting to load...")
            if not load_lmstudio_model(base_url, model_identifier):
                logger.warning(f"Failed to load model {model_identifier}, proceeding with API call anyway.")
    
    prompt_template = """I have attached a medical document scraped from the web. Please create a well-structured Markdown file, logically organized for use in a RAG environment with LLMs. Use headings (`#`, `##`, `###`) to separate sections and subsections. Use lists (`-` or `1.`) where appropriate for enumerated items. Format definitions as definition lists. Do not change any information or wording! Keep the original language (German). Only return the Markdown content and nothing else. Do not wrap the output in ```markdown...```

Document content:
{text_content}
"""
    formatted_prompt = prompt_template.format(text_content=text_content)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": formatted_prompt}
    ]

    if server_type.lower() == 'ollama':
        payload = {
            "model": model_identifier,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens if max_tokens else -1  # Ollama uses -1 for no limit
            }
        }
    else:  # lmstudio or default to OpenAI format
        payload = {
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }
        
        # Only add max_tokens if it's specified
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        if model_identifier: # Check if model_identifier is not None and not empty
            payload['model'] = model_identifier

    headers = {
        "Content-Type": "application/json"
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        logger.info(f"Calling {server_type} API at {api_url}...")
        response = requests.post(api_url, headers=headers, json=payload, timeout=timeout)

        if response.status_code == 200:
            try:
                response_data = response.json()
                if server_type.lower() == 'ollama':
                    if 'message' in response_data and 'content' in response_data['message']:
                        markdown_content = response_data['message']['content']
                        logger.info(f"API call to {server_type} API at {api_url} successful, content received.")
                        return markdown_content.strip()
                    else:
                        logger.error(f"Unexpected response structure from {server_type} API at {api_url}. Full response: {response.text}")
                        return None
                else:  # lmstudio or openai compatible
                    if 'choices' in response_data and \
                       isinstance(response_data['choices'], list) and \
                       len(response_data['choices']) > 0 and \
                       'message' in response_data['choices'][0] and \
                       'content' in response_data['choices'][0]['message']:

                        markdown_content = response_data['choices'][0]['message']['content']
                        logger.info(f"API call to {server_type} API at {api_url} successful, content received.")
                        return markdown_content.strip()
                    else:
                        logger.error(f"Unexpected response structure from {server_type} API at {api_url}. Full response: {response.text}")
                        return None
            except json.JSONDecodeError:
                logger.error(f"Could not decode JSON response from {server_type} API at {api_url}. Response text: {response.text}", exc_info=True)
                return None
        else:
            logger.error(f"API request to {server_type} API at {api_url} failed with status code {response.status_code}. Response: {response.text}")
            return None

    except requests.exceptions.Timeout:
        logger.error(f"API request to {server_type} API at {api_url} timed out after {timeout} seconds.", exc_info=True)
        return None
    except requests.exceptions.ConnectionError as e:
        # More specific and user-friendly error for connection issues
        logger.error(f"Cannot connect to {server_type} API at {api_url}")
        logger.error("Please ensure that:")
        if server_type.lower() == 'ollama':
            logger.error("  1. Ollama is running")
            logger.error("  2. A model is loaded in Ollama")
        else:
            logger.error("  1. LM Studio is running")
            logger.error("  2. A model is loaded in LM Studio")
        logger.error(f"  3. The API server is enabled and listening on {api_url}")
        logger.debug(f"Connection error details: {e}", exc_info=True)
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"API request to {server_type} API at {api_url} failed due to a network or request issue: {e}", exc_info=True)
        return None
    except Exception as e: # Catch any other unexpected errors during the API call process
        logger.error(f"An unexpected error occurred during the API call to {server_type} API at {api_url}: {e}", exc_info=True)
        return None

if __name__ == '__main__':
    # This basic setup is for testing api_handler.py directly.
    # For proper log output here, you'd need to call setup_logging from logger.py first.
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    logger.info("Testing api_handler.py independently...")
    sample_api_url = "http://localhost:1234/v1/chat/completions" # Default LM Studio URL
    sample_text = "Das ist ein Testdokument.\nEs hat mehrere Zeilen.\n- Erstens\n- Zweitens"

    logger.info("This example usage block will not make a real API call during automated execution.")
    logger.info("To test this, uncomment the call and ensure LM Studio is running at the specified URL.")
    # logger.info(f"Attempting to call API at {sample_api_url} with sample text...")
    # markdown = call_llm_api(sample_text, sample_api_url, 'lmstudio')
    # if markdown:
    #     logger.info("\n--- Markdown Output ---\n" + markdown + "\n--- End Markdown Output ---\n")
    # else:
    #     logger.warning("Failed to get Markdown from API in test block.")

    logger.info("api_handler.py test block finished. Manual testing with a live server is recommended.")
