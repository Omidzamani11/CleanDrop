from __future__ import annotations

import ast
from pathlib import Path


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_domain_has_no_framework_or_adapter_dependencies() -> None:
    domain = Path(__file__).parents[2] / "src" / "cleandrop" / "domain"
    forbidden = ("PySide6", "PIL", "fitz", "pikepdf", "cleandrop.adapters")
    violations = {
        str(path): sorted(name for name in _imports(path) if name.startswith(forbidden))
        for path in domain.rglob("*.py")
    }
    assert not {path: names for path, names in violations.items() if names}


def test_application_depends_on_ports_and_domain_not_concrete_adapters() -> None:
    application = Path(__file__).parents[2] / "src" / "cleandrop" / "application"
    violations = {
        str(path): sorted(name for name in _imports(path) if name.startswith("cleandrop.adapters"))
        for path in application.rglob("*.py")
    }
    assert not {path: names for path, names in violations.items() if names}
