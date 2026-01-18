import configparser
import os
import logging

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = 'config/config.ini'

def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> dict:
    """
    Loads configuration from the specified .ini file.

    Args:
        config_path: Path to the configuration file.
                     Defaults to 'config/config.ini'.

    Returns:
        A dictionary containing the configuration values.

    Raises:
        FileNotFoundError: If the configuration file is not found.
        ValueError: If essential keys are missing from the configuration file.
    """
    if not os.path.exists(config_path):
        logger.error(f"Configuration file not found: {config_path}")
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    config = configparser.ConfigParser()
    config.read(config_path)

    # Essential keys that must be present
    essential_sections = {
        'Server': ['type'],
        'Directories': ['input_dir', 'output_dir']
    }

    loaded_config = {}

    for section, keys in essential_sections.items():
        if section not in config:
            logger.error(f"Missing section [{section}] in configuration file: {config_path}")
            raise ValueError(f"Missing section [{section}] in configuration file: {config_path}")
        for key in keys:
            if key not in config[section]:
                logger.error(f"Missing key '{key}' in section [{section}] in configuration file: {config_path}")
                raise ValueError(f"Missing key '{key}' in section [{section}] in configuration file: {config_path}")
            loaded_config[key] = config[section][key]

    # Get server type and determine API section
    server_type = loaded_config['type'].lower()
    if server_type == 'lmstudio':
        api_section = 'LMStudio'
    elif server_type == 'ollama':
        api_section = 'Ollama'
    else:
        logger.error(f"Invalid server type '{server_type}' in configuration file: {config_path}")
        raise ValueError(f"Invalid server type '{server_type}' in configuration file: {config_path}")

    # Add API section to essential if not already
    if api_section not in essential_sections:
        essential_sections[api_section] = ['api_url']
        # Check it
        if api_section not in config:
            logger.error(f"Missing section [{api_section}] in configuration file: {config_path}")
            raise ValueError(f"Missing section [{api_section}] in configuration file: {config_path}")
        for key in essential_sections[api_section]:
            if key not in config[api_section]:
                logger.error(f"Missing key '{key}' in section [{api_section}] in configuration file: {config_path}")
                raise ValueError(f"Missing key '{key}' in section [{api_section}] in configuration file: {config_path}")
            loaded_config[key] = config[api_section][key]

    # Optional keys from API section
    # Optional keys from API section
    loaded_config['api_key'] = config.get(api_section, 'api_key', fallback=None)
    loaded_config['api_timeout'] = config.getint(api_section, 'api_timeout', fallback=60)
    loaded_config['model_identifier'] = config.get(api_section, 'model_identifier', fallback=None)
    loaded_config['system_prompt'] = config.get('General', 'system_prompt', fallback=config.get(api_section, 'system_prompt', fallback=None))
    loaded_config['user_prompt_template'] = config.get('General', 'user_prompt_template', fallback=config.get(api_section, 'user_prompt_template', fallback=None))
    loaded_config['temperature'] = config.getfloat(api_section, 'temperature', fallback=0.7)
    
    # max_tokens can be None (no limit) or an integer
    max_tokens_str = config.get(api_section, 'max_tokens', fallback=None)
    if max_tokens_str:
        try:
            loaded_config['max_tokens'] = int(max_tokens_str)
        except ValueError:
            loaded_config['max_tokens'] = None
    else:
        loaded_config['max_tokens'] = None

    # context_length
    context_length_str = config.get(api_section, 'context_length', fallback='8192')
    try:
        loaded_config['context_length'] = int(context_length_str)
    except ValueError:
        loaded_config['context_length'] = 8192

    # Directories (no optional keys specified for now beyond what's essential)

    # Logging
    if 'Logging' in config:
        loaded_config['log_file'] = config.get('Logging', 'log_file', fallback='app.log')
        loaded_config['log_level'] = config.get('Logging', 'log_level', fallback='INFO').upper()
    else: # Default logging section if not present
        loaded_config['log_file'] = 'app.log'
        loaded_config['log_level'] = 'INFO'

    # Validate log_level (optional, but good practice)
    valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if loaded_config['log_level'] not in valid_log_levels:
        # Default to INFO if an invalid level is provided, and maybe log a warning later if logging is set up
        # For now, let's be strict or default silently. Silently defaulting for now.
        # If an invalid log level is provided, we default to INFO,
        # and a message could be logged if logging was already set up.
        # However, this function is called BY setup_logging, so we can't log here about that yet.
        loaded_config['log_level'] = 'INFO'

    # Caching settings
    if 'Caching' in config:
        loaded_config['caching_enabled'] = config.getboolean('Caching', 'enabled', fallback=True)
        loaded_config['caching_force_reprocess_all'] = config.getboolean('Caching', 'force_reprocess_all', fallback=False)
    else: # Default caching section if not present
        loaded_config['caching_enabled'] = True
        loaded_config['caching_force_reprocess_all'] = False

    return loaded_config

if __name__ == '__main__':
    # This basic setup is for testing config_handler.py directly.
    # For proper log output here, you'd need to call setup_logging from logger.py first.
    # Or, temporarily set up a basicConfig for logging.
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger.info("Testing config_handler.py...")
    try:
        # Test with default path (assuming it exists relative to where this script is run)
        # For robust testing, provide an absolute path or ensure CWD.
        # This test might fail if config.ini is not found at 'config/config.ini' from CWD.
        # It's better to test this via main.py or a dedicated test script.
        # config_values = load_config()

        # Example: Test with a specific, known-good path if needed for direct testing
        # script_dir = os.path.dirname(__file__)
        # project_root_dir = os.path.abspath(os.path.join(script_dir, '..'))
        # test_config_path = os.path.join(project_root_dir, 'config', 'config.ini')
        # config_values = load_config(test_config_path)

        # print("Configuration loaded successfully:") # Using print for direct test output
        # for key, value in config_values.items():
        # print(f"  {key}: {value}")

        logger.info("Simulating call with a non-existent config file for testing error logging:")
        try:
            load_config('non_existent_config.ini')
        except FileNotFoundError:
            logger.info("Successfully caught FileNotFoundError as expected.")

    except (FileNotFoundError, ValueError) as e:
        # print(f"Error loading configuration during test: {e}") # Using print for direct test output
        logger.error(f"Error loading configuration during test: {e}", exc_info=True)
