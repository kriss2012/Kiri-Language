from __future__ import annotations
import sys
from pathlib import Path
from ..compiler.diagnostics import SourceText, DiagnosticBag
from ..compiler.parser import Parser
from ..compiler.tokens import SyntaxKind
from ..compiler.ast import (
    CompilationUnit, StatementSyntax, ExpressionSyntax, VarDeclStmt,
    FuncDeclStmt, IdentifierExpr, BinaryExpr
)

def lint_file(path: Path) -> int:
    code = path.read_text(encoding="utf-8")
    src = SourceText.from_str(code, path.name)
    diags = DiagnosticBag()
    parser = Parser(src, diags)
    unit = parser.parse_compilation_unit()

    if diags.has_errors:
        print(diags.format(src))
        return 1

    issues = 0
    declared_vars: set[str] = set()
    used_vars: set[str] = set()

    def check_node(node: Any):
        nonlocal issues
        if isinstance(node, VarDeclStmt):
            declared_vars.add(node.name)
        elif isinstance(node, IdentifierExpr):
            used_vars.add(node.name)
        elif isinstance(node, BinaryExpr):
            # Check suspicious comparisons e.g. x == x
            if isinstance(node.left, IdentifierExpr) and isinstance(node.right, IdentifierExpr):
                if node.left.name == node.right.name and node.op.kind == SyntaxKind.EQUAL_EQUAL:
                    diags.report_warning(
                        node.span,
                        f"Suspicious comparison: '{node.left.name} == {node.right.name}' is always true.",
                        "Remove redundant self-comparison."
                    )
                    issues += 1

    for stmt in unit.statements:
        check_node(stmt)

    if issues > 0:
        print(diags.format(src))
        return 1

    return 0

def run_linter(target_path: str = ".") -> int:
    target = Path(target_path).resolve()
    files = [target] if target.is_file() else list(target.rglob("*.kiri"))
    failed = 0

    for f in files:
        if lint_file(f) != 0:
            failed += 1

    if failed == 0:
        print(f"✓ Linting passed for {len(files)} file(s). No issues found.")
        return 0
    else:
        print(f"✗ Found lint issues in {failed} file(s).")
        return 1
