import ast
import inspect

from hypertts_addon.services import service_windows


def test_windows_service_does_not_import_comtypes():
    """SAPI must stay on pywin32 to avoid comtypes' corruptible code cache."""
    module_ast = ast.parse(inspect.getsource(service_windows))
    imported_modules = []

    for node in ast.walk(module_ast):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.append(node.module)

    assert not any(
        module_name == 'comtypes' or module_name.startswith('comtypes.')
        for module_name in imported_modules
    )
