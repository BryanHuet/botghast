# BotGhast Tests

This directory contains the test suite for the BotGhast Discord bot.

## Test Structure

### `test_bot_functions.py`
Contains unit tests for the core validation functions:
- `validate_gifs_json()` - Tests for GIFs JSON structure validation
- `validate_quotes_json()` - Tests for quotes JSON structure validation
- Data file loading tests - Tests for loading actual data files

### `test_bot_commands.py`
Contains integration tests for bot commands using mocking:
- `donneavis` command tests - Tests for the GIF reply command
- `citation` command tests - Tests for the random quote command
- `searchquote` command tests - Tests for the quote search command

## Running Tests

### Prerequisites
- Python 3.14+
- pytest
- pytest-asyncio

### Installation
```bash
pip install -r requirements.txt
```

### Running All Tests
```bash
python -m pytest
```

### Running Specific Tests
```bash
# Run only validation tests
python -m pytest tests/test_bot_functions.py

# Run only command tests
python -m pytest tests/test_bot_commands.py

# Run with verbose output
python -m pytest -v
```

## Test Coverage

The test suite covers:

1. **Validation Functions**:
   - ✅ Valid JSON structures
   - ✅ Invalid JSON structures (missing keys, wrong types)
   - ✅ Real data file loading and validation

2. **Bot Commands**:
   - ✅ `donneavis` - No reference, with reference, file not found
   - ✅ `citation` - Successful quote, no permissions, file not found
   - ✅ `searchquote` - With results, no keyword, no results

3. **Error Handling**:
   - ✅ File not found scenarios
   - ✅ Permission errors
   - ✅ Invalid input handling
   - ✅ JSON parsing errors

## Test Design Principles

1. **Isolation**: Each test is independent and doesn't rely on external services
2. **Mocking**: Discord API calls are mocked to avoid requiring a real bot connection
3. **Comprehensive**: Tests cover both happy paths and error scenarios
4. **Maintainable**: Clear test names and organization
5. **Fast**: Tests run quickly for efficient development

## Adding New Tests

When adding new features to the bot:

1. Add unit tests for any new validation or utility functions
2. Add integration tests for new commands using the existing patterns
3. Follow the existing test naming conventions
4. Keep tests focused on one specific behavior per test

## Continuous Integration

The tests are configured to run automatically in GitHub Actions via the workflow defined in `.github/workflows/python-app.yml`.