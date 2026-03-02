"""
Basic tests that verify the testing framework works.
"""
import pytest


def test_basic_math():
    """Test basic functionality to verify pytest works."""
    assert 1 + 1 == 2
    assert 2 * 3 == 6


def test_string_operations():
    """Test string operations."""
    text = "hello world"
    assert len(text) == 11
    assert text.upper() == "HELLO WORLD"


@pytest.mark.parametrize("input_value,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_multiply_by_two(input_value, expected):
    """Test parametrized function."""
    assert input_value * 2 == expected
