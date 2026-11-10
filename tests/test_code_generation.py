import re

import pytest

from app.services import generate_code


def test_default_length():
    assert len(generate_code()) == 7


def test_custom_length():
    assert len(generate_code(12)) == 12


def test_charset_is_base62():
    code = generate_code(200)
    assert re.fullmatch(r"[A-Za-z0-9]+", code)


def test_uniqueness():
    codes = {generate_code() for _ in range(2000)}
    assert len(codes) == 2000


def test_rejects_non_positive_length():
    with pytest.raises(ValueError):
        generate_code(0)
    with pytest.raises(ValueError):
        generate_code(-1)