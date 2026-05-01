from __future__ import annotations

import pytest

from src.extensions.loader import load_class


class _SampleClass:
    pass


def test_load_class_valid_builtin():
    cls = load_class("pathlib.Path")
    import pathlib

    assert cls is pathlib.Path


def test_load_class_function_not_class():
    # load_class itself is a function — should raise because it's not a type
    with pytest.raises(ValueError, match="not a class"):
        load_class("src.extensions.loader.load_class")


def test_load_class_stdlib_class():
    cls = load_class("collections.OrderedDict")
    import collections

    assert cls is collections.OrderedDict


def test_load_class_missing_module():
    with pytest.raises(ValueError, match="Cannot import module"):
        load_class("nonexistent_module_xyz.SomeClass")


def test_load_class_missing_attribute():
    with pytest.raises(ValueError, match="has no attribute"):
        load_class("pathlib.NonExistentClass")


def test_load_class_non_class_attribute():
    # pathlib.Path.home is a method, not a type
    with pytest.raises(ValueError, match="not a class"):
        load_class("os.path.join")


def test_load_class_no_dot_raises():
    with pytest.raises(ValueError, match="must be 'module.ClassName'"):
        load_class("NoDotAtAll")


def test_load_class_returns_type():
    cls = load_class("pathlib.Path")
    assert isinstance(cls, type)
