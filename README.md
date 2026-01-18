# Text-to-Markdown Conversion Agent

This agent converts text files from an input directory to Markdown files in an output directory using a large language model (LLM) via LM Studio or Ollama APIs.

## Features

*   **Recursive Directory Traversal:** Scans the specified input directory and its subdirectories for `.txt` files.
*   **Text-to-Markdown Conversion:** For each found text file, its content is sent to an LLM API (e.g., Gemma 3 running in LM Studio or Ollama) to generate Markdown.
*   **Mirrored Output Structure:** Creates corresponding Markdown (`.md`) files in a specified output directory, preserving the original folder hierarchy.
*   **Intelligent Caching:** Automatically skips processing files when the output is already up-to-date (based on modification time comparison). This dramatically speeds up subsequent runs when only a few files have changed.
*   **Configuration Driven:** Uses a `config.ini` file for easy setup of API endpoint, directories, model parameters, caching behavior, and logging preferences.
*   **Error Handling & Logging:** Robust error handling for API communication, file operations, and configuration issues. Detailed logs are saved to a file (e.g., `app.log`) and also output to the console.
*   **Progress Tracking:** Displays a progress bar using `tqdm` during file processing.
*   **Unit Tested:** Core functionalities are covered by unit tests using `pytest` and `pytest-mock`.

## Prerequisites

*   **Python 3.x:** (Developed with Python 3.10)
*   **LM Studio or Ollama:**
    *   An instance of LM Studio or Ollama providing an OpenAI-compatible chat completions API must be running and accessible.
    *   A model (e.g., Gemma 3) should be loaded and served through the API endpoint.
*   **API Endpoint URL:** You need the URL for the chat completions endpoint (e.g., `http://localhost:1234/v1/chat/completions` for LM Studio or `http://localhost:11434/api/chat` for Ollama).

## Setup & Installation

1.  **Clone the Repository:**
    ```bash
    git clone git@github.com:mediaworkbench/text2mdparser.git
    cd text2mdparser
    ```

### 2. Create and Activate a Virtual Environment (Recommended)

It's highly recommended to use a virtual environment to manage project dependencies and avoid conflicts with global Python packages.

**On macOS and Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```
*(You should see `(venv)` at the beginning of your terminal prompt after activation.)*

**On Windows (Command Prompt/PowerShell):**
```bash
python -m venv venv
.\venv\Scripts\activate
```
*(You should see `(venv)` at the beginning of your terminal prompt after activation.)*

### 3. Install Dependencies

Once your virtual environment is activated, install the required packages:
```bash
pip install -r requirements.txt
```

### 4. Configure the Application
    *   Copy or rename the `config/config.ini.example` to `config/config.ini`.
    *   Edit `config/config.ini` with your settings.

    **Setting Explanations:**
    
    **[LMStudio] Section:**
    *   `api_url`: The full URL to your LM Studio (or compatible) chat completions API endpoint.
    *   `api_key`: (Optional) Your API key if the endpoint requires authentication. Leave commented out or blank if not needed.
    *   `model_identifier`: (Optional) Model identifier to use (e.g., `google/gemma-3-4b`). If not specified, LM Studio will use its currently loaded model.
    *   `api_timeout`: Timeout for API requests in seconds. Default is 60 seconds if not specified.
    *   `system_prompt`: (Optional) The system prompt sent to the LLM. If not specified, uses a default prompt.
    *   `temperature`: (Optional) Controls randomness in responses (0.0 = deterministic, 1.0 = very random). Default is 0.7.
    *   `max_tokens`: (Optional) Maximum tokens in the response. If not specified, no limit is set.
    *   `context_length`: (Optional) Context length for the model. For LM Studio, this is configured in the server settings, not via this config. Default is 8192.
    
    **[Ollama] Section:**
    *   `api_url`: The full URL to your Ollama API endpoint (e.g., `http://localhost:11434/api/chat`).
    *   `model_identifier`: (Optional) Model identifier to use (e.g., `gemma3:4b`). If not specified, Ollama will use its default.
    *   `api_timeout`: Timeout for API requests in seconds. Default is 60 seconds if not specified.
    *   `system_prompt`: (Optional) The system prompt sent to the LLM. If not specified, uses a default prompt.
    *   `temperature`: (Optional) Controls randomness in responses (0.0 = deterministic, 1.0 = very random). Default is 0.7.
    *   `max_tokens`: (Optional) Maximum tokens in the response. If not specified, no limit is set.
    *   `context_length`: (Optional) Context length for the model in tokens. Default is 8192.
    
    **[Directories] Section:**
    *   `input_dir`: Path to the directory containing your input `.txt` files. Relative paths are typically from the project root.
    *   `output_dir`: Path to the directory where generated `.md` files will be saved.
    
    **[Logging] Section:**
    *   `log_file`: Name of the log file to be created in the project root.
    *   `log_level`: Logging verbosity. Options: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.
    
    **[Caching] Section:**
    *   `enabled`: When `true`, the system checks if output files are up-to-date by comparing modification times. Only processes files when the input is newer than the output.
    *   `force_reprocess_all`: When `true`, ignores cache and reprocesses all files regardless of modification times. Useful for updating all outputs with a new prompt or model.

## Usage

1.  Ensure your LM Studio (or compatible API) is running and the `api_url` in `config/config.ini` is correctly set.
2.  Place your `.txt` files into the directory specified as `input_dir` in `config.ini` (default: `data/input/`). You can create subdirectories within `input_dir`.
3.  Run the script from the project root:
    ```bash
    python3 src/main.py
    ```
4.  Converted `.md` files will appear in the directory specified as `output_dir` (default: `data/output/`), mirroring the structure of `input_dir`.
5.  Logs will be written to the console and to the file specified as `log_file` (default: `app.log` in the project root).

## Demo Samples

The repository includes two sample text files in `data/input/` to demonstrate the converter's capabilities.

**Demonstrates:**
- Complex hierarchical structure with multiple heading levels
- Mixed content types (definitions, scientific facts, lists, numerical data)
- Numbered and bulleted lists

## Running Tests

To run the unit tests:
```bash
pytest -v
```
Tests are located in the `tests/` directory and use `pytest` with `pytest-mock`.

## Project Structure

```
.
├── config/
│   └── config.example.ini        # Configuration file
├── data/
│   ├── input/            # Default input directory for .txt files
│   └── output/           # Default output directory for .md files
├── src/
│   ├── __init__.py
│   ├── api_handler.py    # Handles communication with LM Studio API
│   ├── config_handler.py # Loads and validates configuration
│   ├── logger.py         # Sets up logging
│   └── main.py           # Main script for directory traversal and processing
├── tests/
│   ├── __init__.py
│   ├── test_api_handler.py
│   ├── test_config_handler.py
│   └── test_main.py
├── README.md             # This file
└── requirements.txt      # Python dependencies
```

## License

This project is provided as-is, free to use and modify.
