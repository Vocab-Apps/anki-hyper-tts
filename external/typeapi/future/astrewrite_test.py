import ast
import re

import astor  # type: ignore[import]

from typeapi.future.astrewrite import rewrite_expr_to_ast


def to_source(ast: ast.AST) -> str:
    # We can't set the line width of the generated code, so we use this to narrow expressions
    # down into a single line. We're still left with some space for example when a line break
    # occurred after a parentheses, `[\n    0]` will result in `[ 0]`.
    return re.sub(r" +", " ", astor.to_source(ast).replace("\n", ""))


def test__rewrite_expr__deals_with_literals() -> None:
    assert (
        to_source(rewrite_expr_to_ast("Annotated[int | str, 0, '42', Decimal(...)]", "__dict__"))
        == "__dict__['Annotated'][__dict__['int'] | __dict__['str'], 0, '42', __dict__[ 'Decimal'](...)]"
    )
