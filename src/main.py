import os
from pathlib import Path
import shutil # For safely creating output directory later, though mkdir can do it.
from tqdm import tqdm
import sys

# Add project root to sys.path to allow for `from src.config_handler import load_config`
# This makes the import robust regardless of how the script is run.
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config_handler import load_config
from src.api_handler import call_lm_studio_api
from src.logger import setup_logging # Import setup_logging
import logging # Import logging

# Module-level logger for main.py
logger = logging.getLogger(__name__)


def process_directory():
    """
    Loads configuration, scans the input directory for .txt files,
    processes them (calling API for markdown conversion), and saves
    them to the output directory, preserving subdirectory structure.
    """
    try:
        config = load_config(config_path=str(project_root / 'config/config.ini'))
        logger.info("Configuration loaded successfully.")
    except FileNotFoundError as e:
        logger.error(f"Critical: Configuration file not found. {e}", exc_info=True)
        return
    except ValueError as e:
        logger.error(f"Critical: Invalid or missing configuration. {e}", exc_info=True)
        return

    # Caching flags from config
    enabled_flag = config['caching_enabled']
    force_reprocess_all_flag = config['caching_force_reprocess_all']
    logger.info(f"Caching enabled: {enabled_flag}, Force reprocess all: {force_reprocess_all_flag}")

    model_identifier = config.get('model_identifier')
    if model_identifier:
        logger.info(f"Using Model Identifier: {model_identifier}")
    else:
        logger.info("No Model Identifier configured, using API default.")

    input_dir_path = Path(config['input_dir'])
    output_dir_path = Path(config['output_dir'])

    if not input_dir_path.is_dir():
        logger.error(f"Input directory not found or is not a directory: {input_dir_path}")
        return

    output_dir_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory ensured at: {output_dir_path}")

    logger.info(f"Scanning for .txt files in: {input_dir_path}")
    try:
        txt_files = list(input_dir_path.rglob('*.txt'))
        if not txt_files:
            logger.info(f"No .txt files found in {input_dir_path}.")
            return
    except Exception as e:
        logger.error(f"Error scanning for files in {input_dir_path}: {e}", exc_info=True)
        return

    logger.info(f"Found {len(txt_files)} .txt files. Starting processing...")

    processed_count = 0
    skipped_count = 0
    failed_count = 0
    connection_error_encountered = False

    for file_path in tqdm(txt_files, desc="Processing files"):
        logger.info(f"Checking file: {file_path}") # Changed log message

        # Determine output_file_path early for caching
        try:
            relative_path = file_path.relative_to(input_dir_path)
            output_file_path = output_dir_path / relative_path.with_suffix('.md')
        except ValueError as e:
            logger.error(f"Error determining relative path for {file_path}: {e}. Using fallback name.", exc_info=True)
            # Fallback name for output file if relative path fails
            output_file_path = output_dir_path / file_path.name.replace(".txt", ".md")

        # Caching logic implementation
        if force_reprocess_all_flag:
            logger.info(f"Processing (forced by force_reprocess_all): {file_path}")
        elif not enabled_flag:
            logger.info(f"Processing (caching disabled): {file_path}")
        else:
            # Caching is enabled and not forcing all, proceed with mtime checks
            logger.info(f"Checking cache for output file (caching enabled): {output_file_path}")
            if output_file_path.exists():
                try:
                    input_mtime = file_path.stat().st_mtime
                    output_mtime = output_file_path.stat().st_mtime
                    if output_mtime >= input_mtime:
                        logger.info(f"Skipping (up-to-date): {file_path} -> {output_file_path}. Input mtime: {input_mtime}, Output mtime: {output_mtime}")
                        skipped_count += 1
                        continue
                    else:
                        logger.info(f"Processing (output older): {file_path} -> {output_file_path}. Input mtime: {input_mtime}, Output mtime: {output_mtime}")
                except FileNotFoundError:
                    logger.warning(f"File not found during mtime check for {file_path} or {output_file_path}. Processing.", exc_info=True)
            else:
                logger.info(f"Processing (output missing): {output_file_path} for input {file_path}")

        # Proceed with reading input and calling API
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
        except (IOError, UnicodeDecodeError) as e:
            logger.error(f"Error reading file {file_path}: {e}", exc_info=True)
            continue

        logger.debug(f"Calling API for file: {file_path.name}")
        api_timeout = config.get('api_timeout', 60) # Ensure a default here as well
        markdown_output = call_lm_studio_api(
            file_content,
            config['api_url'],
            config.get('api_key'),
            timeout=api_timeout,
            model_identifier=model_identifier,
            system_prompt=config.get('system_prompt'),
            temperature=config.get('temperature', 0.7),
            max_tokens=config.get('max_tokens')
        )

        if markdown_output is None:
            logger.warning(f"Failed to get Markdown from API for {file_path.name}. Skipping this file.")
            failed_count += 1
            # Check if this looks like a connection error (first failure)
            if failed_count == 1:
                connection_error_encountered = True
            continue

        try:
            relative_path = file_path.relative_to(input_dir_path)
            output_file_path = output_dir_path / relative_path.with_suffix('.md')
        except ValueError as e:
            logger.error(f"Error determining relative path for {file_path}: {e}. Using fallback name.", exc_info=True)
            # This part is already handled above when output_file_path is defined for caching
            # output_file_path = output_dir_path / file_path.name.replace(".txt", ".md")
            # However, we still need to ensure the parent directory exists before writing.
            pass # output_file_path is already defined

        output_file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(markdown_output)
            logger.info(f"Successfully wrote Markdown to: {output_file_path}")
            processed_count += 1
        except IOError as e:
            logger.error(f"Error writing Markdown file {output_file_path}: {e}", exc_info=True)
            failed_count += 1

    # Summary
    logger.info("Processing complete.")
    logger.info(f"Summary: {processed_count} files processed, {skipped_count} files skipped (up-to-date), {failed_count} files failed")
    
    if connection_error_encountered and failed_count > 0:
        logger.error("")
        logger.error("=" * 70)
        logger.error("CONNECTION ERROR: Unable to reach LM Studio API")
        logger.error("=" * 70)
        logger.error("It appears LM Studio is not running or not accessible.")
        logger.error("")
        logger.error("To resolve this issue:")
        logger.error("  1. Start LM Studio application")
        logger.error("  2. Load a model (e.g., Gemma 3)")
        logger.error("  3. Enable the local server in LM Studio")
        logger.error(f"  4. Verify the API URL in config.ini: {config.get('api_url')}")
        logger.error("")
        logger.error("Then run this script again.")
        logger.error("=" * 70)

if __name__ == "__main__":
    # Setup logging as the first step
    setup_logging()

    logger.info("Starting main process...")
    process_directory()
