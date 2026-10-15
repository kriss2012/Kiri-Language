import unittest
from kiri.compiler.diagnostics import SourceText, DiagnosticBag
from kiri.compiler.parser import Parser
from kiri.compiler.ast import (
    FuncDeclStmt, IfStmt, WhileStmt, BinaryExpr, CallExpr, LiteralExpr, IdentifierExpr
)
from kiri.compiler.tokens import SyntaxKind

class TestParser(unittest.TestCase):
    def test_parse_expression_precedence(self):
        source = SourceText.from_str("2 + 3 * 4 == 14")
        parser = Parser(source)
        expr = parser.parse_expression()
        self.assertIsInstance(expr, BinaryExpr)
        self.assertEqual(expr.op.kind, SyntaxKind.EQUAL_EQUAL)
        self.assertIsInstance(expr.left, BinaryExpr)
        self.assertEqual(expr.left.op.kind, SyntaxKind.PLUS)
        self.assertIsInstance(expr.left.right, BinaryExpr)
        self.assertEqual(expr.left.right.op.kind, SyntaxKind.STAR)

    def test_parse_function(self):
        code = """def add(a: Int, b: Int = 10) -> Int:
    return a + b
"""
        source = SourceText.from_str(code)
        parser = Parser(source)
        unit = parser.parse_compilation_unit()
        self.assertEqual(len(unit.statements), 1)
        fn = unit.statements[0]
        self.assertIsInstance(fn, FuncDeclStmt)
        self.assertEqual(fn.name, "add")
        self.assertEqual(len(fn.params), 2)
        self.assertEqual(fn.params[0].name, "a")
        self.assertEqual(fn.params[0].type_annotation.type_name, "Int")
        self.assertEqual(fn.params[1].name, "b")
        self.assertIsNotNone(fn.params[1].default_value)
        self.assertEqual(fn.return_type.type_name, "Int")

if __name__ == "__main__":
    unittest.main()
