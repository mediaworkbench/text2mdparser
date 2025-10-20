import requests
import json
import logging

logger = logging.getLogger(__name__)

def call_lm_studio_api(
    text_content: str, 
    api_url: str, 
    api_key: str | None = None, 
    timeout: int = 60, 
    model_identifier: str | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int | None = None
) -> str | None:
    """
    Calls the LM Studio API to convert text content to Markdown.

    Args:
        text_content: The text content to be converted.
        api_url: The API endpoint URL for LM Studio.
        api_key: Optional API key for LM Studio.
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
    
    prompt_template = """I have attached a medical document scraped from the web. Please create a well-structured Markdown file, logically organized for use in a RAG environment with LLMs. Use headings (`#`, `##`, `###`) to separate sections and subsections. Use lists (`-` or `1.`) where appropriate for enumerated items. Format definitions as definition lists. Do not change any information or wording! Keep the original language (German). Only return the Markdown content and nothing else. Do not wrap the output in ```markdown...```

Document content:
{text_content}
"""
    formatted_prompt = prompt_template.format(text_content=text_content)

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": formatted_prompt}
        ],
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
        logger.info(f"Calling LM Studio API at {api_url}...")
        response = requests.post(api_url, headers=headers, json=payload, timeout=timeout)

        if response.status_code == 200:
            try:
                response_data = response.json()
                if 'choices' in response_data and \
                   isinstance(response_data['choices'], list) and \
                   len(response_data['choices']) > 0 and \
                   'message' in response_data['choices'][0] and \
                   'content' in response_data['choices'][0]['message']:

                    markdown_content = response_data['choices'][0]['message']['content']
                    logger.info(f"API call to {api_url} successful, content received.")
                    return markdown_content.strip()
                else:
                    logger.error(f"Unexpected response structure from {api_url}. Full response: {response.text}")
                    return None
            except json.JSONDecodeError:
                logger.error(f"Could not decode JSON response from {api_url}. Response text: {response.text}", exc_info=True)
                return None
        else:
            logger.error(f"API request to {api_url} failed with status code {response.status_code}. Response: {response.text}")
            return None

    except requests.exceptions.Timeout:
        logger.error(f"API request to {api_url} timed out after {timeout} seconds.", exc_info=True)
        return None
    except requests.exceptions.ConnectionError as e:
        # More specific and user-friendly error for connection issues
        logger.error(f"Cannot connect to LM Studio API at {api_url}")
        logger.error("Please ensure that:")
        logger.error("  1. LM Studio is running")
        logger.error("  2. A model is loaded in LM Studio")
        logger.error(f"  3. The API server is enabled and listening on {api_url}")
        logger.debug(f"Connection error details: {e}", exc_info=True)
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"API request to {api_url} failed due to a network or request issue: {e}", exc_info=True)
        return None
    except Exception as e: # Catch any other unexpected errors during the API call process
        logger.error(f"An unexpected error occurred during the API call to {api_url}: {e}", exc_info=True)
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
    # markdown = call_lm_studio_api(sample_text, sample_api_url)
    # if markdown:
    #     logger.info("\n--- Markdown Output ---\n" + markdown + "\n--- End Markdown Output ---\n")
    # else:
    #     logger.warning("Failed to get Markdown from API in test block.")

    logger.info("api_handler.py test block finished. Manual testing with a live LM Studio server is recommended.")
