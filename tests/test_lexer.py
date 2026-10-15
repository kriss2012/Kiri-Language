import unittest
from kiri.compiler.diagnostics import SourceText, DiagnosticBag
from kiri.compiler.tokens import SyntaxKind
from kiri.compiler.lexer import Lexer

class TestLexer(unittest.TestCase):
    def test_numbers(self):
        source = SourceText.from_str("42 3.14 0xFF 0b1010 0o77")
        lexer = Lexer(source)
        tokens = lexer.lex_all()
        kinds = [t.kind for t in tokens if t.kind not in (SyntaxKind.NEWLINE, SyntaxKind.EOF)]
        self.assertEqual(kinds, [
            SyntaxKind.INT_LITERAL,
            SyntaxKind.FLOAT_LITERAL,
            SyntaxKind.INT_LITERAL,
            SyntaxKind.INT_LITERAL,
            SyntaxKind.INT_LITERAL,
        ])
        self.assertEqual(tokens[0].value, 42)
        self.assertAlmostEqual(tokens[1].value, 3.14)
        self.assertEqual(tokens[2].value, 255)
        self.assertEqual(tokens[3].value, 10)
        self.assertEqual(tokens[4].value, 63)

    def test_strings_and_escapes(self):
        source = SourceText.from_str(r'"hello\nworld" "quotes: \"inner\""')
        lexer = Lexer(source)
        tokens = lexer.lex_all()
        self.assertEqual(tokens[0].value, "hello\nworld")
        self.assertEqual(tokens[1].value, 'quotes: "inner"')

    def test_keywords_and_identifiers(self):
        source = SourceText.from_str("def my_func(a, b) -> Int: return true")
        lexer = Lexer(source)
        tokens = lexer.lex_all()
        kinds = [t.kind for t in tokens if t.kind not in (SyntaxKind.NEWLINE, SyntaxKind.EOF)]
        expected = [
            SyntaxKind.DEF_KEYWORD,
            SyntaxKind.IDENTIFIER,
            SyntaxKind.OPEN_PAREN,
            SyntaxKind.IDENTIFIER,
            SyntaxKind.COMMA,
            SyntaxKind.IDENTIFIER,
            SyntaxKind.CLOSE_PAREN,
            SyntaxKind.ARROW,
            SyntaxKind.IDENTIFIER,
            SyntaxKind.COLON,
            SyntaxKind.RETURN_KEYWORD,
            SyntaxKind.BOOL_LITERAL
        ]
        self.assertEqual(kinds, expected)

    def test_indentation_and_dedent(self):
        code = """if true:
    x = 1
    if false:
        y = 2
z = 3"""
        source = SourceText.from_str(code)
        lexer = Lexer(source)
        tokens = lexer.lex_all()
        kinds = [t.kind for t in tokens]
        self.assertIn(SyntaxKind.INDENT, kinds)
        self.assertIn(SyntaxKind.DEDENT, kinds)
        self.assertEqual(kinds.count(SyntaxKind.INDENT), 2)
        self.assertEqual(kinds.count(SyntaxKind.DEDENT), 2)

if __name__ == "__main__":
    unittest.main()
