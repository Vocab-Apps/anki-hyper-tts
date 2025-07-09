"""
Rewrite a Python AST to make name lookups, writes and deletes delegate to a single global variable.
"""

import ast
import contextlib
import dataclasses
import typing as t
from types import CodeType

T_AST = t.TypeVar("T_AST", bound=ast.AST)


def rewrite_expr_to_ast(source: str, lookup_target: str) -> "ast.Expression | ast.Module":
    expr = ast.parse(source, "<expr>", "eval")
    expr = DynamicLookupRewriter(lookup_target).visit(expr)
    ast.fix_missing_locations(expr)
    assert isinstance(expr, (ast.Expression, ast.Module)), type(expr)
    return expr


def rewrite_expr(source: str, lookup_target: str) -> CodeType:
    expr = rewrite_expr_to_ast(source, lookup_target)
    return t.cast(CodeType, compile(expr, "<expr>", "eval"))  # type: ignore[redundant-cast]  # Redundant in 3.7+


@dataclasses.dataclass
class DynamicLookupRewriter(ast.NodeTransformer):
    # TODO(NiklasRosenstein): Handle more nodes that define local variables and := operator.

    #: The variable name of the target object that name resolution should occur through.
    #: All names in the AST, with a few exceptions, will be replaced by a getitem/setitem/delitem
    #: expression on the variable name defined here.
    lookup_target: str

    #: Names to not replace. The #lookup_target does not need to be added here explicitly.
    pure_builtins: t.Collection[str] = dataclasses.field(default_factory=frozenset)

    #: A prefix to compare variable names for which, if it matches, they will not be replaced
    #: with a dynamic lookup, but instead the prefix will be trimmed.
    ignore_prefix: "str | None" = None

    def __post_init__(self) -> None:
        self._locals: t.List[t.Set[str]] = [set()]

    def _add_to_locals(self, varnames: t.Set[str]) -> None:
        assert self._locals, "no locals in current scope"
        self._locals[-1].update(varnames)

    @contextlib.contextmanager
    def _with_locals(self, varnames: t.Set[str]) -> t.Iterator[None]:
        self._locals.append(varnames)
        try:
            yield
        finally:
            self._locals.pop()

    @contextlib.contextmanager
    def _with_locals_from_target(self, target: ast.expr) -> t.Iterator[None]:
        names: t.Set[str] = set()
        if isinstance(target, ast.Name):
            names.add(target.id)
        elif isinstance(target, (ast.List, ast.Tuple)):
            names.update(n.id for n in target.elts)  # type: ignore  # TODO (@NiklasRosenstein)
        else:
            raise TypeError(f"expected Name/List/Tuple, got {type(target).__name__}")
        with self._with_locals(names):
            yield

    def _has_local(self, varname: str) -> bool:
        if self._locals:
            return varname in self._locals[-1]
        return False

    def _has_nonlocal(self, varname: str) -> bool:
        for locals in self._locals:
            if varname in locals:
                return True
        return varname == self.lookup_target or varname in self.pure_builtins

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if self._has_nonlocal(node.id):
            return node
        return ast.Subscript(
            value=ast.Name(id=self.lookup_target, ctx=ast.Load()),
            slice=ast.Index(value=ast.Constant(value=node.id)),
            ctx=node.ctx,
        )

    def visit_Assign(self, assign: ast.Assign) -> ast.AST:
        if len(assign.targets) == 1 and isinstance(assign.targets[0], ast.Name):
            name = assign.targets[0]
            if self.ignore_prefix is not None and name.id.startswith(self.ignore_prefix):
                name.id = name.id[len(self.ignore_prefix) :]  # noqa: E203
                self._add_to_locals({name.id})
        return self.generic_visit(assign)

    def visit_For(self, node: ast.For) -> ast.AST:
        with self._with_locals_from_target(node.target):
            return self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        self._add_to_locals({node.name})
        names: t.Set[str] = set()
        for arg in node.args.args:
            names.add(arg.arg)
        for arg in node.args.kwonlyargs:
            names.add(arg.arg)
        if node.args.vararg:
            names.add(node.args.vararg.arg)
        if node.args.kwarg:
            names.add(node.args.kwarg.arg)
        with self._with_locals(names):
            return self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        self._add_to_locals({node.name})
        return self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> ast.AST:
        names: t.Set[str] = set()
        for name in node.names:
            if name.asname:
                names.add(name.asname)
            elif "." in name.name:
                names.add(name.name.rpartition(".")[0])
            else:
                names.add(name.name)
        self._add_to_locals(names)
        return self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.AST:
        self.visit_Import(ast.Import(names=node.names))  # Dispatch name detection
        return self.generic_visit(node)

    def visit(self, node: T_AST) -> t.Any:
        return super().visit(node)
