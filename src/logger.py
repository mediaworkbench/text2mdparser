import logging
import sys
from pathlib import Path

# To avoid circular dependency if config_handler itself needs to log during its import phase,
# setup_logging should ideally be called after config_handler is imported.
# For this setup, we assume config_handler can be imported and used by setup_logging.
# If config_handler had complex setup that logged, we'd pass config values to setup_logging.

# Add project root to sys.path to allow for `from src.config_handler import load_config`
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config_handler import load_config

DEFAULT_LOG_FILE = 'app.log'
DEFAULT_LOG_LEVEL = 'INFO'

def setup_logging():
    """
    Configures the root logger for the application.
    Reads log file path and log level from config.ini.
    """
    try:
        # Determine config path relative to this file's project structure
        # logger.py is in src/, config/ is sibling to src/
        config_file_path = project_root / 'config' / 'config.ini'
        config = load_config(config_path=str(config_file_path))

        log_file_str = config.get('log_file', DEFAULT_LOG_FILE) # Use .get for safety
        log_level_str = config.get('log_level', DEFAULT_LOG_LEVEL).upper()
    except Exception as e:
        # Fallback if config loading fails during logging setup
        # This print is acceptable here as logging isn't set up yet.
        print(f"Error loading configuration for logging: {e}. Using default logging settings.", file=sys.stderr)
        log_file_str = DEFAULT_LOG_FILE
        log_level_str = DEFAULT_LOG_LEVEL

    log_file_path = project_root / log_file_str # Ensure log file is in project root if relative

    # Get the root logger
    logger = logging.getLogger()

    # Prevent adding multiple handlers if setup_logging is called more than once (e.g. in tests)
    if logger.hasHandlers():
        # Optionally, clear existing handlers if re-configuration is desired
        # for handler in logger.handlers[:]:
        #    logger.removeHandler(handler)
        # For now, if already configured, we assume it's fine and exit.
        # print("Logging already configured.", file=sys.stderr) # Or log this if possible
        return


    # Convert log level string to logging constant
    numeric_log_level = getattr(logging, log_level_str, logging.INFO)
    logger.setLevel(numeric_log_level)

    # Define formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s')

    # Create File Handler
    try:
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        # This print is acceptable here as logging isn't fully set up.
        print(f"Error setting up file handler for logging: {e}. Logs may not be written to file.", file=sys.stderr)

    # Create Console Handler
    console_handler = logging.StreamHandler(sys.stdout) # Use sys.stdout for info, sys.stderr for errors by default by level
    console_handler.setFormatter(formatter)
    # Optionally set a different (lower) level for console, e.g., only show INFO and above on console
    # console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    # Test log message
    # logger.info("Logging setup complete. Logging to file and console.")
    # (This might be too early if other modules haven't initialized their loggers yet)

if __name__ == '__main__':
    # This block is for testing logger.py directly
    print("Setting up logging from logger.py's main...")
    setup_logging()
    # Now, any module can get this logger
    test_logger = logging.getLogger("my_app_test") # Example of getting a specific logger
    test_logger.debug("This is a debug message from logger.py test.")
    test_logger.info("This is an info message from logger.py test.")
    test_logger.warning("This is a warning message from logger.py test.")
    test_logger.error("This is an error message from logger.py test.")

    root_logger_test = logging.getLogger() # Get root logger
    root_logger_test.info("This is an info message from root logger via logger.py test")

    # Test another module's logger
    other_module_logger = logging.getLogger("another.module")
    other_module_logger.info("Info from another module.")

    print(f"Check '{DEFAULT_LOG_FILE}' and console for log output.")
