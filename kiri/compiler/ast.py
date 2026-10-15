from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from .diagnostics import TextSpan
from .tokens import SyntaxToken

@dataclass(frozen=True)
class SyntaxNode:
    span: TextSpan

# ─────────────────────────────────────────────────────────────
# Expressions
# ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ExpressionSyntax(SyntaxNode):
    pass

@dataclass(frozen=True)
class LiteralExpr(ExpressionSyntax):
    token: SyntaxToken
    value: Any

@dataclass(frozen=True)
class IdentifierExpr(ExpressionSyntax):
    token: SyntaxToken
    name: str

@dataclass(frozen=True)
class SelfExpr(ExpressionSyntax):
    token: SyntaxToken

@dataclass(frozen=True)
class SuperExpr(ExpressionSyntax):
    token: SyntaxToken

@dataclass(frozen=True)
class MemberAccessExpr(ExpressionSyntax):
    target: ExpressionSyntax
    member_token: SyntaxToken
    member_name: str

@dataclass(frozen=True)
class IndexExpr(ExpressionSyntax):
    """target[index]"""
    target: ExpressionSyntax
    index: ExpressionSyntax

@dataclass(frozen=True)
class SliceExpr(ExpressionSyntax):
    """target[start:stop] or target[start:stop:step]"""
    target: ExpressionSyntax
    start: ExpressionSyntax | None
    stop: ExpressionSyntax | None
    step: ExpressionSyntax | None

@dataclass(frozen=True)
class UnaryExpr(ExpressionSyntax):
    op: SyntaxToken
    operand: ExpressionSyntax

@dataclass(frozen=True)
class BinaryExpr(ExpressionSyntax):
    left: ExpressionSyntax
    op: SyntaxToken
    right: ExpressionSyntax

@dataclass(frozen=True)
class CallExpr(ExpressionSyntax):
    callee: ExpressionSyntax
    arguments: list[ExpressionSyntax]
    keyword_args: list[tuple[str, ExpressionSyntax]]  # [(name, expr), ...]

@dataclass(frozen=True)
class ParenExpr(ExpressionSyntax):
    open_paren: SyntaxToken
    expr: ExpressionSyntax
    close_paren: SyntaxToken

@dataclass(frozen=True)
class ListExpr(ExpressionSyntax):
    """[a, b, c]"""
    elements: list[ExpressionSyntax]

@dataclass(frozen=True)
class TupleExpr(ExpressionSyntax):
    """(a, b, c)  —  distinguished from ParenExpr by having comma"""
    elements: list[ExpressionSyntax]

@dataclass(frozen=True)
class SetExpr(ExpressionSyntax):
    """{a, b, c}"""
    elements: list[ExpressionSyntax]

@dataclass(frozen=True)
class DictExpr(ExpressionSyntax):
    """{k1: v1, k2: v2}"""
    pairs: list[tuple[ExpressionSyntax, ExpressionSyntax]]

@dataclass(frozen=True)
class RangeExpr(ExpressionSyntax):
    """start..stop  or  start..=stop"""
    start: ExpressionSyntax
    stop: ExpressionSyntax
    inclusive: bool  # True means ..=

@dataclass(frozen=True)
class LambdaExpr(ExpressionSyntax):
    params: list[ParameterNode]
    body: ExpressionSyntax

@dataclass(frozen=True)
class IfExpr(ExpressionSyntax):
    """Ternary: value if condition else other"""
    then_value: ExpressionSyntax
    condition: ExpressionSyntax
    else_value: ExpressionSyntax

@dataclass(frozen=True)
class ListCompExpr(ExpressionSyntax):
    """[expr for var in iterable if condition]"""
    element: ExpressionSyntax
    target: str
    iterable: ExpressionSyntax
    condition: ExpressionSyntax | None

@dataclass(frozen=True)
class DictCompExpr(ExpressionSyntax):
    """{key: val for var in iterable}"""
    key: ExpressionSyntax
    value: ExpressionSyntax
    target: str
    iterable: ExpressionSyntax
    condition: ExpressionSyntax | None

@dataclass(frozen=True)
class SetCompExpr(ExpressionSyntax):
    element: ExpressionSyntax
    target: str
    iterable: ExpressionSyntax
    condition: ExpressionSyntax | None

@dataclass(frozen=True)
class FStringExpr(ExpressionSyntax):
    """f"Hello {name}!" """
    parts: list[str | ExpressionSyntax]  # str = literal text, expr = interpolated

@dataclass(frozen=True)
class SpreadExpr(ExpressionSyntax):
    """*expr in call/list"""
    operand: ExpressionSyntax

@dataclass(frozen=True)
class AssignExpr(ExpressionSyntax):
    """target = value — assignment-as-expression (walrus := also)"""
    target: ExpressionSyntax
    value: ExpressionSyntax
    is_walrus: bool = False

# ─────────────────────────────────────────────────────────────
# Type annotations
# ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TypeAnnotation(SyntaxNode):
    name_token: SyntaxToken
    type_name: str
    type_args: list[TypeAnnotation] = field(default_factory=list)  # for List[Int], etc.
    is_optional: bool = False   # for T?
    is_union: bool = False      # for T | U (stored as name_token of first, type_args for rest)

@dataclass(frozen=True)
class ParameterNode(SyntaxNode):
    name_token: SyntaxToken
    type_annotation: TypeAnnotation | None
    default_value: ExpressionSyntax | None
    is_variadic: bool = False    # *args
    is_keyword_only: bool = False
    is_keyword_variadic: bool = False  # **kwargs

    @property
    def name(self) -> str:
        return self.name_token.text

# ─────────────────────────────────────────────────────────────
# Statements
# ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class StatementSyntax(SyntaxNode):
    pass

@dataclass(frozen=True)
class BlockStmt(StatementSyntax):
    statements: list[StatementSyntax]

@dataclass(frozen=True)
class CompilationUnit(SyntaxNode):
    statements: list[StatementSyntax]
    eof: SyntaxToken

@dataclass(frozen=True)
class ExprStmt(StatementSyntax):
    expr: ExpressionSyntax

@dataclass(frozen=True)
class VarDeclStmt(StatementSyntax):
    name_token: SyntaxToken
    name: str
    type_annotation: TypeAnnotation | None
    initializer: ExpressionSyntax

@dataclass(frozen=True)
class AugAssignStmt(StatementSyntax):
    """target += expr, -= etc."""
    target: ExpressionSyntax   # may be ident, member, index
    op: SyntaxToken
    value: ExpressionSyntax

@dataclass(frozen=True)
class AssignStmt(StatementSyntax):
    """target = expr  (also handles a.b = v, a[i] = v)"""
    target: ExpressionSyntax
    value: ExpressionSyntax

@dataclass(frozen=True)
class FuncDeclStmt(StatementSyntax):
    name_token: SyntaxToken
    name: str
    params: list[ParameterNode]
    return_type: TypeAnnotation | None
    body: BlockStmt
    decorators: list[ExpressionSyntax] = field(default_factory=list)
    is_async: bool = False

@dataclass(frozen=True)
class ClassDeclStmt(StatementSyntax):
    name_token: SyntaxToken
    name: str
    bases: list[ExpressionSyntax]
    body: BlockStmt
    decorators: list[ExpressionSyntax] = field(default_factory=list)

@dataclass(frozen=True)
class ElifClause(SyntaxNode):
    condition: ExpressionSyntax
    block: BlockStmt

@dataclass(frozen=True)
class ElseClause(SyntaxNode):
    block: BlockStmt

@dataclass(frozen=True)
class IfStmt(StatementSyntax):
    condition: ExpressionSyntax
    then_block: BlockStmt
    elif_clauses: list[ElifClause]
    else_clause: ElseClause | None

@dataclass(frozen=True)
class WhileStmt(StatementSyntax):
    condition: ExpressionSyntax
    body: BlockStmt
    else_clause: ElseClause | None = None

@dataclass(frozen=True)
class ForStmt(StatementSyntax):
    target: str            # loop variable name
    target_token: SyntaxToken
    iterable: ExpressionSyntax
    body: BlockStmt
    else_clause: ElseClause | None = None

@dataclass(frozen=True)
class ReturnStmt(StatementSyntax):
    return_token: SyntaxToken
    expr: ExpressionSyntax | None

@dataclass(frozen=True)
class YieldStmt(StatementSyntax):
    yield_token: SyntaxToken
    expr: ExpressionSyntax | None

@dataclass(frozen=True)
class PassStmt(StatementSyntax):
    pass_token: SyntaxToken

@dataclass(frozen=True)
class BreakStmt(StatementSyntax):
    token: SyntaxToken

@dataclass(frozen=True)
class ContinueStmt(StatementSyntax):
    token: SyntaxToken

@dataclass(frozen=True)
class RaiseStmt(StatementSyntax):
    raise_token: SyntaxToken
    expr: ExpressionSyntax | None

@dataclass(frozen=True)
class ExceptClause(SyntaxNode):
    exception_type: ExpressionSyntax | None  # None = bare except
    alias: str | None
    body: BlockStmt

@dataclass(frozen=True)
class TryStmt(StatementSyntax):
    try_body: BlockStmt
    except_clauses: list[ExceptClause]
    else_clause: ElseClause | None
    finally_body: BlockStmt | None

@dataclass(frozen=True)
class ImportStmt(StatementSyntax):
    module_token: SyntaxToken
    module_name: str
    alias_token: SyntaxToken | None = None
    alias_name: str | None = None

@dataclass(frozen=True)
class FromImportStmt(StatementSyntax):
    module_name: str
    names: list[tuple[str, str | None]]  # [(name, alias), ...]
    star: bool = False  # from mod import *

@dataclass(frozen=True)
class DeleteStmt(StatementSyntax):
    target: ExpressionSyntax

@dataclass(frozen=True)
class AssertStmt(StatementSyntax):
    condition: ExpressionSyntax
    message: ExpressionSyntax | None

@dataclass(frozen=True)
class GlobalStmt(StatementSyntax):
    names: list[str]

@dataclass(frozen=True)
class NonlocalStmt(StatementSyntax):
    names: list[str]

@dataclass(frozen=True)
class WithStmt(StatementSyntax):
    context: ExpressionSyntax
    alias: str | None
    body: BlockStmt
