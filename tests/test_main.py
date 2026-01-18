# Tests for src.main
import pytest
from pathlib import Path
from src.main import process_directory
import logging

# Add project root to sys.path for src imports
import sys
project_root_path = Path(__file__).resolve().parent.parent
if str(project_root_path) not in sys.path:
    sys.path.insert(0, str(project_root_path))

# Since main.py calls setup_logging() which configures root,
# ensure tests don't interfere if they also try to configure.
# logger.py's setup_logging has a guard against multiple handler additions.

@pytest.fixture
def mock_config_valid(tmp_path):
    """Provides a valid configuration pointing to temp directories."""
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir() # process_directory will also try to create it, exist_ok=True handles this
    return {
        'type': 'lmstudio',
        'api_url': 'http://fake-api.com',
        'api_key': None,
        'input_dir': str(input_dir),
        'output_dir': str(output_dir),
        'api_timeout': 60,
        'log_file': str(tmp_path / 'test_app.log'),
        'log_level': 'DEBUG',
        'model_identifier': None,
        'system_prompt': None,
        'temperature': 0.7,
        'max_tokens': None,
        'caching_enabled': True,
        'caching_force_reprocess_all': False
    }

@pytest.fixture
def mock_dependencies(mocker, mock_config_valid):
    """Mocks dependencies for process_directory."""
    m_load_config = mocker.patch('src.main.load_config', return_value=mock_config_valid)
    m_call_api = mocker.patch('src.main.call_llm_api', return_value="## Mocked Markdown")
    # No need to mock Path.rglob, Path.mkdir, open, etc. if using real tmp_path files for basic tests
    # unless specific error conditions for these need to be simulated.
    return m_load_config, m_call_api

def create_dummy_files(input_dir_path: Path, num_files: int, subdirs: bool = False):
    """Helper to create dummy .txt files."""
    files_created = []
    for i in range(num_files):
        if subdirs and i % 2 == 0: # Put half in a subdir
            subdir = input_dir_path / f"subdir{i}"
            subdir.mkdir(exist_ok=True)
            file_path = subdir / f"sample{i+1}.txt"
        else:
            file_path = input_dir_path / f"sample{i+1}.txt"

        file_path.write_text(f"Content of sample{i+1}.txt")
        files_created.append(file_path)
    return files_created

def test_process_directory_success(tmp_path, mock_dependencies, mock_config_valid, caplog, mocker): # Added mocker
    """Test successful processing of directory with .txt files."""
    caplog.set_level(logging.INFO)
    m_load_config, m_call_api = mock_dependencies

    input_dir = Path(mock_config_valid['input_dir'])
    output_dir = Path(mock_config_valid['output_dir'])

    # Create dummy input files explicitly for this test
    input_file1 = input_dir / "file1.txt"
    input_file1.write_text("Content file1")
    subdir_path = input_dir / "sub"
    subdir_path.mkdir()
    input_file2_in_subdir = subdir_path / "file2.txt"
    input_file2_in_subdir.write_text("Content file2")

    process_directory()

    # Assertions
    m_load_config.assert_called_once() # Path might differ slightly due to how it's resolved
                                       # project_root / 'config/config.ini' vs the one in test
                                       # This is fine as long as it's called.

    assert m_call_api.call_count == 2 # For file1.txt and sub/file2.txt

    # Check API calls (order might not be guaranteed by rglob)
    # call_llm_api(text_content, api_url, server_type, api_key, timeout, model_identifier, system_prompt, temperature, max_tokens)

    # Assert that call_llm_api was called with the correct arguments, including model_identifier
    # We check call_count and then inspect individual calls if order is not guaranteed or args vary.
    # For this test, model_identifier, system_prompt, and max_tokens are None from mock_config_valid.

    calls = [
        mocker.call(
            "Content file1", 
            mock_config_valid['api_url'], 
            mock_config_valid['type'],
            mock_config_valid['api_key'], 
            timeout=60, 
            model_identifier=None,
            system_prompt=None,
            temperature=0.7,
            max_tokens=None,
            context_length=8192
        ),
        mocker.call(
            "Content file2", 
            mock_config_valid['api_url'], 
            mock_config_valid['type'],
            mock_config_valid['api_key'], 
            timeout=60, 
            model_identifier=None,
            system_prompt=None,
            temperature=0.7,
            max_tokens=None,
            context_length=8192
        )
    ]
    m_call_api.assert_has_calls(calls, any_order=True)

    # Check output files
    output_file1 = output_dir / "file1.md"
    output_file2_in_subdir = output_dir / "sub" / "file2.md"

    assert output_file1.exists()
    assert output_file1.read_text() == "## Mocked Markdown"
    assert output_file2_in_subdir.exists()
    assert output_file2_in_subdir.read_text() == "## Mocked Markdown"

    assert "Processing complete." in caplog.text

def test_process_directory_no_txt_files(tmp_path, mock_dependencies, mock_config_valid, caplog):
    """Test behavior when no .txt files are found."""
    caplog.set_level(logging.INFO)
    m_load_config, m_call_api = mock_dependencies

    # No dummy files created in input_dir

    process_directory()

    m_load_config.assert_called_once()
    m_call_api.assert_not_called()
    assert f"No .txt files found in {mock_config_valid['input_dir']}." in caplog.text
    assert "Processing complete." not in caplog.text # As it returns early

def test_process_directory_api_failure(tmp_path, mock_dependencies, mock_config_valid, caplog):
    """Test behavior when API call fails for a file."""
    caplog.set_level(logging.INFO) # Changed to INFO to capture "Processing complete."
    m_load_config, m_call_api = mock_dependencies
    m_call_api.return_value = None # Simulate API failure

    input_dir = Path(mock_config_valid['input_dir'])
    output_dir = Path(mock_config_valid['output_dir'])

    input_file1 = input_dir / "error_file.txt"
    input_file1.write_text("Content for API failure")

    process_directory()

    m_call_api.assert_called_once_with(
        "Content for API failure",
        mock_config_valid['api_url'],
        mock_config_valid['type'],
        mock_config_valid['api_key'],
        timeout=mock_config_valid['api_timeout'],
        model_identifier=None,
        system_prompt=None,
        temperature=0.7,
        max_tokens=None,
        context_length=8192
    )

    output_file1 = output_dir / "error_file.md"
    assert not output_file1.exists() # File should not be created
    assert f"Failed to get Markdown from API for {input_file1.name}. Skipping this file." in caplog.text
    assert "Processing complete." in caplog.text # Should still complete for other files (if any)

def test_process_directory_input_dir_not_found(tmp_path, mocker, caplog):
    """Test behavior when input directory does not exist."""
    caplog.set_level(logging.ERROR)

    non_existent_input_dir = tmp_path / "non_existent_input"
    # This mock config also needs the new keys load_config would provide
    mock_config_non_existent_input = {
        'api_url': 'http://fake-api.com', 'api_key': None,
        'input_dir': str(non_existent_input_dir),
        'output_dir': str(tmp_path / "output"),
        'log_file': str(tmp_path / 'test_app.log'), 'log_level': 'DEBUG',
        'model_identifier': None,
        'caching_enabled': True,
        'caching_force_reprocess_all': False
    }
    mocker.patch('src.main.load_config', return_value=mock_config_non_existent_input)
    m_call_api = mocker.patch('src.main.call_llm_api') # Still need to mock this

    process_directory()

    assert f"Input directory not found or is not a directory: {non_existent_input_dir}" in caplog.text
    m_call_api.assert_not_called()

def test_process_directory_read_error(tmp_path, mock_dependencies, mock_config_valid, mocker, caplog):
    """Test behavior when reading an input file fails."""
    caplog.set_level(logging.INFO) # Changed to INFO to capture "Processing complete."
    m_load_config, m_call_api = mock_dependencies

    input_dir = Path(mock_config_valid['input_dir'])
    file_path = input_dir / "read_error.txt"
    file_path.write_text("Initial content") # File exists

    # Mock open to raise IOError for this specific file when read
    # This is a bit more involved; need to mock Path.open or the global open
    # For simplicity, let's mock Path.read_text which is used by main.py's open() context manager
    # Actually, main.py uses `with open(file_path, 'r', encoding='utf-8') as f: file_content = f.read()`
    # So we mock `builtins.open`

    original_open = open
    def mock_open_with_read_error(path, *args, **kwargs):
        if str(path) == str(file_path): # Only for the target file
            m = mocker.mock_open(mocker.MagicMock(spec=open))
            m.return_value.read.side_effect = IOError("Cannot read this file")
            return m()
        return original_open(path, *args, **kwargs) # Use real open for other files (e.g. config)

    mocker.patch('builtins.open', mock_open_with_read_error)

    process_directory()

    m_call_api.assert_not_called() # API should not be called for this file
    assert f"Error reading file {file_path}: Cannot read this file" in caplog.text
    assert "Processing complete." in caplog.text # Process should complete

# Note: Testing logger.py's setup_logging being called from main's __name__ == "__main__"
# is an integration test usually done by running the script. Unit tests for main typically
# focus on functions like process_directory. We assume setup_logging() is called correctly
# if main.py is run as a script. The caplog fixture works because setup_logging() in main.py
# configures the root logger which pytest's caplog then captures.

def test_main_passes_timeout_to_api_handler(tmp_path, mocker, caplog):
    """Test that process_directory passes the configured api_timeout to call_llm_api."""
    caplog.set_level(logging.INFO)

    custom_timeout = 180
    input_dir = tmp_path / "input_timeout_test"
    output_dir = tmp_path / "output_timeout_test"
    input_dir.mkdir()
    output_dir.mkdir()

    mock_config_with_custom_timeout = {
        'type': 'lmstudio',
        'api_url': 'http://fake-api-for-timeout.com',
        'api_key': 'fake_key_timeout',
        'input_dir': str(input_dir),
        'output_dir': str(output_dir),
        'api_timeout': custom_timeout, # Custom timeout for this test
        'log_file': str(tmp_path / 'timeout_test_app.log'),
        'log_level': 'DEBUG',
        'model_identifier': 'test-model-for-timeout',
        'system_prompt': None,
        'temperature': 0.7,
        'max_tokens': None,
        'caching_enabled': True,
        'caching_force_reprocess_all': False
    }

    m_load_config = mocker.patch('src.main.load_config', return_value=mock_config_with_custom_timeout)
    m_call_api = mocker.patch('src.main.call_llm_api', return_value="## Markdown with custom timeout")

    # Create a dummy input file
    test_file = input_dir / "test_timeout.txt"
    test_file.write_text("Test content for timeout")

    process_directory()

    m_load_config.assert_called_once()
    assert m_call_api.call_count == 1

    # Assert that call_llm_api was called with the custom timeout
    m_call_api.assert_called_once_with(
        "Test content for timeout",
        mock_config_with_custom_timeout['api_url'],
        mock_config_with_custom_timeout['type'],
        mock_config_with_custom_timeout['api_key'],
        timeout=custom_timeout,
        model_identifier='test-model-for-timeout',
        system_prompt=None,
        temperature=0.7,
        max_tokens=None,
        context_length=8192
    )

    # Check that the output file was created
    output_file = output_dir / "test_timeout.md"
    assert output_file.exists()
    assert output_file.read_text() == "## Markdown with custom timeout"
    assert "Processing complete." in caplog.text


# --- Caching Logic Tests ---
# Using unittest.mock for more granular control over Path objects if needed,
# but pytest-mock (mocker) should largely suffice.
from unittest.mock import MagicMock, mock_open as unittest_mock_open

class TestCachingLogic:
    @pytest.fixture(autouse=True)
    def common_mocks(self, mocker): # Add mocker here explicitly
        self.m_load_config = mocker.patch('src.main.load_config')
        self.m_call_api = mocker.patch('src.main.call_llm_api', return_value="## Mocked Markdown")

        # Mock Path methods that are used in process_directory
        self.m_path_class = mocker.patch('src.main.Path', autospec=True)

        # Configure the mock Path class to handle path-like operations and specific method calls
        # This setup makes self.m_path_class behave like the Path class for instantiation
        # and allows mocking instance methods on the results of Path(...) calls.

        # Mock for input_dir_path.rglob, input_file_path.relative_to, input_file_path.stat
        # output_dir_path.mkdir, output_file_path.exists, output_file_path.stat, output_file_path.parent.mkdir

        # Default input file
        self.mock_input_file = MagicMock(spec=Path)
        self.mock_input_file.name = "sample1.txt"
        self.mock_input_file.__str__.return_value = "fake_input/sample1.txt" # for logging

        # Mock rglob to return a list containing our mock input file
        self.m_path_class.return_value.rglob.return_value = [self.mock_input_file]

        # Mock relative_to to return a new mock Path object for the relative path
        # This relative path object then needs a with_suffix method
        mock_relative_path = MagicMock(spec=Path)
        mock_relative_path.with_suffix.return_value = Path("sample1.md") # Path for joining
        self.mock_input_file.relative_to.return_value = mock_relative_path

        # Mock stat results for input and output files (can be overridden per test)
        self.mock_input_file_stat = MagicMock()
        self.mock_input_file.stat.return_value = self.mock_input_file_stat

        self.mock_output_file_stat = MagicMock()
        # We need to ensure that when Path('fake_output/sample1.md') is created,
        # its stat() method returns self.mock_output_file_stat.
        # This requires a bit more sophisticated Path mock.

        # Let Path() constructor return a mock that can then have specific methods like
        # exists(), stat(), mkdir() mocked.
        # The instance returned by Path() will be used for input_dir_path, output_dir_path, etc.

        self.mock_path_instance = self.m_path_class.return_value
        self.mock_path_instance.is_dir.return_value = True # for input_dir_path.is_dir()
        self.mock_path_instance.mkdir.return_value = None # for output_dir_path.mkdir()

        # Specific mock for output_file_path object
        self.mock_output_file_path_obj = MagicMock(spec=Path)
        self.mock_output_file_path_obj.name = "sample1.md" # for logging
        self.mock_output_file_path_obj.__str__.return_value = "fake_output/sample1.md"
        self.mock_output_file_path_obj.stat.return_value = self.mock_output_file_stat

        # Ensure that when output_dir_path / "relative.md" is called, it returns self.mock_output_file_path_obj
        # This means the __truediv__ method of the mock_path_instance needs to be configured.
        self.mock_path_instance.__truediv__.return_value = self.mock_output_file_path_obj

        # Mock for output_file_path.parent.mkdir()
        mock_output_parent_dir = MagicMock(spec=Path)
        mock_output_parent_dir.mkdir.return_value = None
        self.mock_output_file_path_obj.parent = mock_output_parent_dir

        # Mock open for reading input and writing output
        self.m_open = mocker.patch('builtins.open', unittest_mock_open())


    def _run_process_directory(self, config_override):
        base_config = {
            'input_dir': 'fake_input',
            'output_dir': 'fake_output',
            'api_url': 'fake_api_url',
            'api_key': None,
            'api_timeout': 60,
            'model_identifier': None, # Added to base_config for completeness
            'type': 'lmstudio',  # Added for server type
            'context_length': 8192,  # Added context length
            # Default logging setup for tests, actual log content not primary focus here
            'log_file': 'test_cache.log',
            'log_level': 'DEBUG'
        }
        # config_override might change caching_enabled, caching_force_reprocess_all, or model_identifier
        current_config = {**base_config, **config_override}
        # Ensure caching flags are present if not in override, using defaults from base_config or new ones
        current_config.setdefault('caching_enabled', True)
        current_config.setdefault('caching_force_reprocess_all', False)

        self.m_load_config.return_value = current_config
        process_directory()

    # Scenario 1: Standard Caching (enabled=True, force_reprocess_all=False)
    def test_std_caching_output_newer_skips(self, caplog):
        caplog.set_level(logging.INFO)
        self.mock_input_file_stat.st_mtime = 1000 # Input older
        self.mock_output_file_stat.st_mtime = 2000 # Output newer
        self.mock_output_file_path_obj.exists.return_value = True

        self._run_process_directory({
            'caching_enabled': True,
            'caching_force_reprocess_all': False,
            'model_identifier': 'test-skip-model' # Can be specific for test if needed
        })

        self.m_call_api.assert_not_called()
        assert "Skipping (up-to-date): fake_input/sample1.txt -> fake_output/sample1.md" in caplog.text

    def test_std_caching_output_older_processes(self, caplog):
        caplog.set_level(logging.INFO)
        self.mock_input_file_stat.st_mtime = 2000 # Input newer
        self.mock_output_file_stat.st_mtime = 1000 # Output older
        self.mock_output_file_path_obj.exists.return_value = True

        self._run_process_directory({
            'caching_enabled': True,
            'caching_force_reprocess_all': False,
            'model_identifier': 'test-process-older-model'
        })

        self.m_call_api.assert_called_once()
        # Verify model_identifier was passed to the mock_call_api
        args, kwargs = self.m_call_api.call_args
        assert kwargs.get('model_identifier') == 'test-process-older-model'
        assert "Processing (output older): fake_input/sample1.txt -> fake_output/sample1.md" in caplog.text

    def test_std_caching_output_missing_processes(self, caplog):
        caplog.set_level(logging.INFO)
        self.mock_output_file_path_obj.exists.return_value = False
        # st_mtime for input doesn't matter if output is missing, API should be called

        self._run_process_directory({
            'caching_enabled': True,
            'caching_force_reprocess_all': False,
            'model_identifier': 'test-process-missing-model'
        })

        self.m_call_api.assert_called_once()
        args, kwargs = self.m_call_api.call_args
        assert kwargs.get('model_identifier') == 'test-process-missing-model'
        assert "Processing (output missing): fake_output/sample1.md for input fake_input/sample1.txt" in caplog.text

    # Scenario 2: Caching Disabled (enabled=False, force_reprocess_all=False)
    def test_caching_disabled_processes_even_if_output_newer(self, caplog):
        caplog.set_level(logging.INFO)
        self.mock_input_file_stat.st_mtime = 1000 # Input older
        self.mock_output_file_stat.st_mtime = 2000 # Output newer
        self.mock_output_file_path_obj.exists.return_value = True # Output exists and is newer

        self._run_process_directory({
            'caching_enabled': False,
            'caching_force_reprocess_all': False,
            'model_identifier': 'test-disabled-cache-model'
        })

        self.m_call_api.assert_called_once()
        args, kwargs = self.m_call_api.call_args
        assert kwargs.get('model_identifier') == 'test-disabled-cache-model'
        assert "Processing (caching disabled): fake_input/sample1.txt" in caplog.text

    # Scenario 3: Force Reprocess (enabled=True, force_reprocess_all=True)
    # Note: enabled flag could be False as well, force_reprocess_all should take precedence.
    def test_force_reprocess_processes_even_if_output_newer(self, caplog):
        caplog.set_level(logging.INFO)
        self.mock_input_file_stat.st_mtime = 1000 # Input older
        self.mock_output_file_stat.st_mtime = 2000 # Output newer
        self.mock_output_file_path_obj.exists.return_value = True # Output exists and is newer

        self._run_process_directory({
            'caching_enabled': True, # Could be False too
            'caching_force_reprocess_all': True,
            'model_identifier': 'test-force-reprocess-model'
        })

        self.m_call_api.assert_called_once()
        args, kwargs = self.m_call_api.call_args
        assert kwargs.get('model_identifier') == 'test-force-reprocess-model'
        assert "Processing (forced by force_reprocess_all): fake_input/sample1.txt" in caplog.text
