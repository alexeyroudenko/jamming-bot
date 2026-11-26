"""
Unit tests for _snippet_for_analyze_semantic fix (PYTHON-BZ).

Tests that the function handles non-string 'text' values from Redis
deserialization without raising TypeError.
"""
import json
import pytest
from unittest.mock import patch, MagicMock


def test_snippet_handles_integer_text_field():
    """
    Test that _snippet_for_analyze_semantic handles an integer 'text' field
    without raising TypeError: 'int' object is not subscriptable.
    
    This reproduces the PYTHON-BZ Sentry issue where Redis deserialization
    returns an integer for the 'text' field instead of a string.
    """
    from app import _snippet_for_analyze_semantic
    
    # Mock _read_step_hash to return an integer for 'text'
    with patch('app._read_step_hash') as mock_read:
        mock_read.return_value = {
            'text': 12345,  # Integer instead of string
            'number': '1234',
            'url': 'http://example.com'
        }
        
        # Should not raise TypeError
        result = _snippet_for_analyze_semantic('step:1234', {})
        
        # Should return empty string when text is not a string
        assert result == ""


def test_snippet_handles_none_text_field():
    """Test handling of None 'text' field."""
    from app import _snippet_for_analyze_semantic
    
    with patch('app._read_step_hash') as mock_read:
        mock_read.return_value = {
            'text': None,
            'number': '1234',
            'url': 'http://example.com'
        }
        
        result = _snippet_for_analyze_semantic('step:1234', {})
        assert result == ""


def test_snippet_handles_list_text_field():
    """Test handling of list 'text' field (another non-string type)."""
    from app import _snippet_for_analyze_semantic
    
    with patch('app._read_step_hash') as mock_read:
        mock_read.return_value = {
            'text': ['some', 'list'],
            'number': '1234',
            'url': 'http://example.com'
        }
        
        result = _snippet_for_analyze_semantic('step:1234', {})
        assert result == ""


def test_snippet_handles_dict_text_field():
    """Test handling of dict 'text' field."""
    from app import _snippet_for_analyze_semantic
    
    with patch('app._read_step_hash') as mock_read:
        mock_read.return_value = {
            'text': {'nested': 'dict'},
            'number': '1234',
            'url': 'http://example.com'
        }
        
        result = _snippet_for_analyze_semantic('step:1234', {})
        assert result == ""


def test_snippet_works_with_valid_string_text():
    """Test that valid string text still works correctly."""
    from app import _snippet_for_analyze_semantic
    
    with patch('app._read_step_hash') as mock_read:
        with patch('app._first_two_sentences') as mock_first:
            mock_read.return_value = {
                'text': 'This is a valid text string. It has multiple sentences.',
                'number': '1234',
                'url': 'http://example.com'
            }
            mock_first.return_value = 'This is a valid text string.'
            
            result = _snippet_for_analyze_semantic('step:1234', {})
            
            # Should call _first_two_sentences with truncated text
            mock_first.assert_called_once()
            call_args = mock_first.call_args[0][0]
            assert isinstance(call_args, str)
            assert len(call_args) <= 12000


def test_snippet_falls_back_to_noun_phrases():
    """Test fallback to noun_phrases when text is empty."""
    from app import _snippet_for_analyze_semantic
    
    with patch('app._read_step_hash') as mock_read:
        with patch('app._first_two_sentences') as mock_first:
            mock_read.return_value = {'text': ''}
            mock_first.return_value = ''
            
            analyze_result = {
                'noun_phrases': ['test phrase', 'another phrase', 'third phrase']
            }
            
            result = _snippet_for_analyze_semantic('step:1234', analyze_result)
            
            # Should return joined noun phrases
            assert 'test phrase' in result
            assert 'another phrase' in result


def test_snippet_handles_integer_noun_phrases():
    """Test that integer noun_phrases is handled (from PR #59)."""
    from app import _snippet_for_analyze_semantic
    
    with patch('app._read_step_hash') as mock_read:
        with patch('app._first_two_sentences') as mock_first:
            mock_read.return_value = {'text': ''}
            mock_first.return_value = ''
            
            # Integer instead of list
            analyze_result = {'noun_phrases': 123}
            
            # Should not raise TypeError
            result = _snippet_for_analyze_semantic('step:1234', analyze_result)
            assert result == ""


def test_snippet_handles_integer_words():
    """Test that integer words is handled (from PR #59)."""
    from app import _snippet_for_analyze_semantic
    
    with patch('app._read_step_hash') as mock_read:
        with patch('app._first_two_sentences') as mock_first:
            mock_read.return_value = {'text': ''}
            mock_first.return_value = ''
            
            # Integer instead of list
            analyze_result = {'words': 456}
            
            # Should not raise TypeError
            result = _snippet_for_analyze_semantic('step:1234', analyze_result)
            assert result == ""


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
