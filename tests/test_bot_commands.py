"""
Test suite for BotGhast bot commands.

This module contains tests for the bot commands using mocking to avoid
requiring actual Discord connections.
"""

import pytest
import json
import os
import sys
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Add the bot source directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bot', 'src'))

# Import the bot module
import bot


class TestBotCommands:
    """Test cases for bot commands."""
    
    @pytest.fixture
    def mock_ctx(self):
        """Create a mock context for command testing."""
        ctx = Mock()
        ctx.message = Mock()
        ctx.message.reference = None
        ctx.message.channel = Mock()
        ctx.reply = AsyncMock()
        ctx.send = AsyncMock()
        ctx.guild = Mock()
        ctx.guild.me = Mock()
        ctx.channel = Mock()
        ctx.channel.permissions_for = Mock()
        return ctx
    
    @pytest.fixture
    def mock_referenced_message(self):
        """Create a mock referenced message."""
        message = Mock()
        message.reply = AsyncMock()
        return message
    
    @pytest_asyncio.fixture
    async def setup_donneavis_test(self, mock_ctx, mock_referenced_message):
        """Setup for donneavis command tests."""
        # Set up message reference
        mock_ctx.message.reference = Mock()
        mock_ctx.message.reference.message_id = 12345
        
        # Mock the channel's fetch_message method
        mock_ctx.message.channel.fetch_message = AsyncMock(return_value=mock_referenced_message)
        
        return mock_ctx, mock_referenced_message
    
    @pytest.mark.asyncio
    async def test_donneavis_no_reference(self, mock_ctx):
        """Test donneavis command with no message reference."""
        # Ensure no reference
        mock_ctx.message.reference = None
        
        # Mock os.path.exists to return True so it gets past file check
        with patch('os.path.exists', return_value=True):
            # Call the command
            await bot.donneavis(mock_ctx)
            
            # Verify it replied with the expected message
            mock_ctx.reply.assert_awaited_once()
            assert "Aucun message sélectionné" in mock_ctx.reply.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_donneavis_with_reference(self, setup_donneavis_test):
        """Test donneavis command with a valid message reference."""
        mock_ctx, mock_referenced_message = setup_donneavis_test
        
        # Mock file operations and environment
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data='{"gifs": ["https://example.com/test.gif"]}')), \
             patch('json.load', return_value={"gifs": ["https://example.com/test.gif"]}):
            # Call the command
            await bot.donneavis(mock_ctx)
            
            # Verify it replied to the referenced message with a GIF
            mock_referenced_message.reply.assert_awaited_once()
            reply_content = mock_referenced_message.reply.call_args[0][0]
            assert "https://example.com/test.gif" in reply_content
    
    @pytest.mark.asyncio
    async def test_donneavis_file_not_found(self, setup_donneavis_test):
        """Test donneavis command when gifs file doesn't exist."""
        mock_ctx, _ = setup_donneavis_test
        
        # Mock os.path.exists to return False
        with patch('os.path.exists', return_value=False):
            # Call the command
            await bot.donneavis(mock_ctx)
            
            # Verify it didn't try to reply to referenced message
            mock_ctx.message.channel.fetch_message.assert_not_awaited()
    
    @pytest.mark.asyncio
    async def test_citation_command(self, mock_ctx):
        """Test citation command."""
        # Mock file operations
        test_quote = {"citation": "Test quote", "author": "Test author"}
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps([test_quote]))), \
             patch('json.load', return_value=[test_quote]):
            # Mock permissions
            mock_ctx.channel.permissions_for.return_value.send_messages = True
            
            # Call the command
            await bot.citation(mock_ctx)
            
            # Verify it sent the expected quote
            mock_ctx.send.assert_awaited_once()
            sent_message = mock_ctx.send.call_args[0][0]
            assert "Test quote" in sent_message
            assert "Test author" in sent_message
    
    @pytest.mark.asyncio
    async def test_citation_no_permissions(self, mock_ctx):
        """Test citation command when bot has no permissions."""
        # Mock permissions to deny sending messages
        mock_ctx.channel.permissions_for.return_value.send_messages = False
        
        # Call the command
        await bot.citation(mock_ctx)
        
        # Verify it didn't send any message
        mock_ctx.send.assert_not_awaited()
    
    @pytest.mark.asyncio
    async def test_citation_file_not_found(self, mock_ctx):
        """Test citation command when quotes file doesn't exist."""
        # Mock os.path.exists to return False
        with patch('os.path.exists', return_value=False):
            # Call the command
            await bot.citation(mock_ctx)
            
            # Verify it replied with error message
            mock_ctx.reply.assert_awaited_once()
            assert "fichier de citations est introuvable" in mock_ctx.reply.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_search_quote_command(self, mock_ctx):
        """Test searchquote command."""
        # Mock file operations
        test_quotes = [
            {"citation": "quote about love", "author": "Author1"},
            {"citation": "another love quote", "author": "Author2"},
            {"citation": "unrelated quote", "author": "Author3"}
        ]
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(test_quotes))), \
             patch('json.load', return_value=test_quotes):
            # Call the command with search keyword
            await bot.search_quote(mock_ctx, keyword="love")
            
            # Verify it sent results
            mock_ctx.send.assert_awaited_once()
            sent_message = mock_ctx.send.call_args[0][0]
            assert "love" in sent_message
            assert "2" in sent_message  # Should find 2 results
    
    @pytest.mark.asyncio
    async def test_search_quote_no_keyword(self, mock_ctx):
        """Test searchquote command with no keyword."""
        # Call the command with empty keyword
        await bot.search_quote(mock_ctx, keyword="")
        
        # Verify it replied with error message
        mock_ctx.reply.assert_awaited_once()
        assert "mot-clé de recherche" in mock_ctx.reply.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_search_quote_no_results(self, mock_ctx):
        """Test searchquote command with no results."""
        # Mock file operations
        test_quotes = [
            {"citation": "unrelated quote", "author": "Author1"}
        ]
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(test_quotes))), \
             patch('json.load', return_value=test_quotes):
            # Call the command with search keyword that won't match
            await bot.search_quote(mock_ctx, keyword="nonexistent")
            
            # Verify it replied with no results message
            mock_ctx.reply.assert_awaited_once()
            sent_message = mock_ctx.reply.call_args[0][0]
            assert "Aucune citation trouvée" in sent_message


# Helper function to mock file opening
def mock_open(read_data=None):
    """Mock open function for testing file operations."""
    mock = MagicMock()
    mock.read.return_value = read_data
    return mock


if __name__ == "__main__":
    pytest.main([__file__, "-v"])