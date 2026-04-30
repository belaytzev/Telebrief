from __future__ import annotations

import importlib


def load_class(dotted_path: str) -> type:
    """Resolve a dotted-path string to a class.

    Args:
        dotted_path: e.g. ``pkg.module.ClassName``

    Returns:
        The resolved class object.

    Raises:
        ValueError: if the module cannot be imported, the attribute is missing,
                    or the resolved object is not a class.
    """
    if "." not in dotted_path:
        raise ValueError(f"Invalid dotted path {dotted_path!r}: must be 'module.ClassName'")

    module_path, class_name = dotted_path.rsplit(".", 1)

    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise ValueError(
            f"Cannot import module {module_path!r} from path {dotted_path!r}: {exc}"
        ) from exc

    if not hasattr(module, class_name):
        raise ValueError(
            f"Module {module_path!r} has no attribute {class_name!r} " f"(path: {dotted_path!r})"
        )

    obj = getattr(module, class_name)
    if not isinstance(obj, type):
        raise ValueError(f"{dotted_path!r} resolves to {type(obj).__name__!r}, not a class")

    return obj
