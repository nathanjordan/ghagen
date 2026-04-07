"""Fluent builder for GitHub Actions ``${{ }}`` expressions.

Use the module-level :data:`expr` singleton as the entry point::

    from ghagen import expr

    expr.github.ref              # "${{ github.ref }}"
    expr.secrets["PYPI_TOKEN"]   # "${{ secrets.PYPI_TOKEN }}"
    expr.contains(expr.github.ref, "refs/tags/")
    # "${{ contains(github.ref, 'refs/tags/') }}"
"""

from __future__ import annotations

from typing import Any

from ghagen.models.common import ExpressionStr


class _ExprBuilder:
    """Accumulates path segments and renders as a GitHub Actions expression.

    Usage::

        from ghagen.helpers.expressions import expr

        expr.github.ref              # "${{ github.ref }}"
        expr.secrets["PYPI_TOKEN"]   # "${{ secrets.PYPI_TOKEN }}"
        expr.contains(expr.github.ref, "refs/tags/")
        # "${{ contains(github.ref, 'refs/tags/') }}"
    """

    __slots__ = ("_segments",)
    __hash__ = None  # type: ignore[assignment]

    def __init__(self, segments: tuple[str, ...] = ()) -> None:
        self._segments = segments

    # --- path building ---

    def __getattr__(self, name: str) -> _ExprBuilder:
        if name.startswith("_"):
            raise AttributeError(name)
        return _ExprBuilder((*self._segments, name))

    def __getitem__(self, key: str) -> _ExprBuilder:
        return _ExprBuilder((*self._segments, key))

    # --- rendering ---

    def _path(self) -> str:
        return ".".join(self._segments)

    def _bare(self) -> str:
        return self._path()

    def __str__(self) -> str:
        return ExpressionStr.wrap(self._path())

    def __repr__(self) -> str:
        return f"expr({self._path()!r})"

    # --- function calls ---

    def __call__(self, *args: Any) -> _LiteralExpr:
        func_name = self._path()
        formatted_args = ", ".join(_format_arg(a) for a in args)
        return _LiteralExpr(f"{func_name}({formatted_args})")

    # --- comparison operators ---

    def __eq__(self, other: object) -> _LiteralExpr:  # type: ignore[override]
        return _LiteralExpr(f"{self._bare()} == {_format_arg(other)}")

    def __ne__(self, other: object) -> _LiteralExpr:  # type: ignore[override]
        return _LiteralExpr(f"{self._bare()} != {_format_arg(other)}")

    def __gt__(self, other: object) -> _LiteralExpr:
        return _LiteralExpr(f"{self._bare()} > {_format_arg(other)}")

    def __ge__(self, other: object) -> _LiteralExpr:
        return _LiteralExpr(f"{self._bare()} >= {_format_arg(other)}")

    def __lt__(self, other: object) -> _LiteralExpr:
        return _LiteralExpr(f"{self._bare()} < {_format_arg(other)}")

    def __le__(self, other: object) -> _LiteralExpr:
        return _LiteralExpr(f"{self._bare()} <= {_format_arg(other)}")

    # --- boolean operators ---

    def __and__(self, other: _ExprBuilder) -> _LiteralExpr:
        return _LiteralExpr(f"{self._bare()} && {other._bare()}")

    def __or__(self, other: _ExprBuilder) -> _LiteralExpr:
        return _LiteralExpr(f"{self._bare()} || {other._bare()}")

    def __invert__(self) -> _LiteralExpr:
        return _LiteralExpr(f"!{self._bare()}")

    # --- safety guards ---

    def __bool__(self) -> bool:
        msg = (
            "Cannot use expression builder in boolean context — "
            "use str() to get the expression string"
        )
        raise TypeError(msg)


class _LiteralExpr(_ExprBuilder):
    """An expression builder holding a pre-formatted expression string."""

    __slots__ = ("_expr_str",)

    def __init__(self, expr_str: str) -> None:
        super().__init__()
        self._expr_str = expr_str

    def _path(self) -> str:
        return self._expr_str

    def _bare(self) -> str:
        return self._expr_str


def _format_arg(arg: Any) -> str:
    """Format a function argument for a GitHub Actions expression."""
    if isinstance(arg, _ExprBuilder):
        return arg._bare()
    if isinstance(arg, bool):
        return "true" if arg else "false"
    if isinstance(arg, str):
        return f"'{arg}'"
    return str(arg)


# Module-level entry point
expr = _ExprBuilder()
