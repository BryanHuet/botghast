"""
Test suite for BotGhast bot functions.

This module contains unit tests for the validation functions and core bot logic.
"""

import pytest
import json
import os
import sys

# Add the bot source directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bot', 'src'))

from bot import validate_gifs_json, validate_quotes_json


class TestValidationFunctions:
    """Test cases for JSON validation functions."""
    
    def test_validate_gifs_json_valid(self):
        """Test valid gifs.json structure."""
        valid_data = {
            "gifs": [
                "https://example.com/gif1.gif",
                "https://example.com/gif2.gif"
            ]
        }
        # Should not raise any exception
        validate_gifs_json(valid_data)
    
    def test_validate_gifs_json_missing_gifs_key(self):
        """Test gifs.json with missing 'gifs' key."""
        invalid_data = {
            "images": ["https://example.com/gif1.gif"]
        }
        with pytest.raises(ValueError, match=r"expected {'gifs': \[\.\.\.\]}"):
            validate_gifs_json(invalid_data)
    
    def test_validate_gifs_json_gifs_not_list(self):
        """Test gifs.json where 'gifs' is not a list."""
        invalid_data = {
            "gifs": "not_a_list"
        }
        with pytest.raises(ValueError, match="'gifs' should be an array"):
            validate_gifs_json(invalid_data)
    
    def test_validate_gifs_json_not_dict(self):
        """Test gifs.json that is not a dictionary."""
        invalid_data = ["not", "a", "dict"]
        with pytest.raises(ValueError, match=r"expected {'gifs': \[\.\.\.\]}"):
            validate_gifs_json(invalid_data)
    
    def test_validate_quotes_json_valid(self):
        """Test valid quotes.json structure."""
        valid_data = [
            {
                "citation": "Test quote",
                "author": "Test author"
            },
            {
                "citation": "Another quote",
                "author": "Another author"
            }
        ]
        # Should not raise any exception
        validate_quotes_json(valid_data)
    
    def test_validate_quotes_json_not_list(self):
        """Test quotes.json that is not a list."""
        invalid_data = {
            "quotes": [
                {"citation": "Test", "author": "Author"}
            ]
        }
        with pytest.raises(ValueError, match="expected array of quotes"):
            validate_quotes_json(invalid_data)
    
    def test_validate_quotes_json_missing_citation(self):
        """Test quote missing 'citation' field."""
        invalid_data = [
            {
                "author": "Test author"
                # Missing 'citation' field
            }
        ]
        with pytest.raises(ValueError, match="Invalid quote structure"):
            validate_quotes_json(invalid_data)
    
    def test_validate_quotes_json_missing_author(self):
        """Test quote missing 'author' field."""
        invalid_data = [
            {
                "citation": "Test quote"
                # Missing 'author' field
            }
        ]
        with pytest.raises(ValueError, match="Invalid quote structure"):
            validate_quotes_json(invalid_data)
    
    def test_validate_quotes_json_not_dict_item(self):
        """Test quotes.json with non-dict items."""
        invalid_data = [
            "not_a_dict",
            123,
            None
        ]
        with pytest.raises(ValueError, match="Invalid quote structure"):
            validate_quotes_json(invalid_data)


class TestDataFiles:
    """Test cases for loading and validating actual data files."""
    
    def test_load_gifs_file(self):
        """Test loading the actual gifs.json file."""
        gifs_file = os.path.join(os.path.dirname(__file__), '..', 'bot', 'data', 'gifs.json')
        
        with open(gifs_file, 'r', encoding='utf-8') as file:
            gifs_data = json.load(file)
        
        # Should not raise any exception
        validate_gifs_json(gifs_data)
        
        # Verify we have some gifs
        assert isinstance(gifs_data['gifs'], list)
        assert len(gifs_data['gifs']) > 0
    
    def test_load_quotes_file(self):
        """Test loading the actual quotes.json file."""
        quotes_file = os.path.join(os.path.dirname(__file__), '..', 'bot', 'data', 'quotes.json')
        
        with open(quotes_file, 'r', encoding='utf-8') as file:
            quotes_data = json.load(file)
        
        # Should not raise any exception
        validate_quotes_json(quotes_data)
        
        # Verify we have some quotes
        assert isinstance(quotes_data, list)
        assert len(quotes_data) > 0
        
        # Verify each quote has required fields
        for quote in quotes_data:
            assert 'citation' in quote
            assert 'author' in quote
            assert isinstance(quote['citation'], str)
            assert isinstance(quote['author'], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])