from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any
from .diagnostics import TextSpan

class SyntaxKind(Enum):
    # Special
    BAD_TOKEN = auto()
    EOF = auto()
    NEWLINE = auto()
    INDENT = auto()
    DEDENT = auto()

    # Literals
    INT_LITERAL = auto()
    FLOAT_LITERAL = auto()
    STRING_LITERAL = auto()
    BOOL_LITERAL = auto()
    NULL_LITERAL = auto()

    # Identifiers & Keywords
    IDENTIFIER = auto()
    DEF_KEYWORD = auto()
    CLASS_KEYWORD = auto()
    RETURN_KEYWORD = auto()
    IF_KEYWORD = auto()
    ELIF_KEYWORD = auto()
    ELSE_KEYWORD = auto()
    WHILE_KEYWORD = auto()
    FOR_KEYWORD = auto()
    IN_KEYWORD = auto()
    PASS_KEYWORD = auto()
    BREAK_KEYWORD = auto()
    CONTINUE_KEYWORD = auto()
    TRUE_KEYWORD = auto()
    FALSE_KEYWORD = auto()
    NULL_KEYWORD = auto()
    AND_KEYWORD = auto()
    OR_KEYWORD = auto()
    NOT_KEYWORD = auto()
    STRICT_KEYWORD = auto()
    IMPORT_KEYWORD = auto()
    FROM_KEYWORD = auto()
    AS_KEYWORD = auto()
    TRY_KEYWORD = auto()
    EXCEPT_KEYWORD = auto()
    FINALLY_KEYWORD = auto()
    RAISE_KEYWORD = auto()
    IS_KEYWORD = auto()
    SELF_KEYWORD = auto()
    SUPER_KEYWORD = auto()
    LAMBDA_KEYWORD = auto()
    YIELD_KEYWORD = auto()
    ASYNC_KEYWORD = auto()
    AWAIT_KEYWORD = auto()
    MATCH_KEYWORD = auto()
    CASE_KEYWORD = auto()
    WITH_KEYWORD = auto()
    GLOBAL_KEYWORD = auto()
    NONLOCAL_KEYWORD = auto()
    DELETE_KEYWORD = auto()
    ASSERT_KEYWORD = auto()

    # Operators & Delimiters
    PLUS = auto()           # +
    MINUS = auto()          # -
    STAR = auto()           # *
    SLASH = auto()          # /
    SLASH_SLASH = auto()    # //
    PERCENT = auto()        # %
    STAR_STAR = auto()      # **
    EQUAL = auto()          # =
    PLUS_EQUAL = auto()     # +=
    MINUS_EQUAL = auto()    # -=
    STAR_EQUAL = auto()     # *=
    SLASH_EQUAL = auto()    # /=
    PERCENT_EQUAL = auto()  # %=
    EQUAL_EQUAL = auto()    # ==
    BANG_EQUAL = auto()     # !=
    LESS = auto()           # <
    LESS_EQUAL = auto()     # <=
    GREATER = auto()        # >
    GREATER_EQUAL = auto()  # >=
    AMP_AMP = auto()        # &&
    PIPE_PIPE = auto()      # ||
    BANG = auto()           # !
    AMPERSAND = auto()      # &
    PIPE = auto()           # |
    CARET = auto()          # ^
    TILDE = auto()          # ~
    LSHIFT = auto()         # <<
    RSHIFT = auto()         # >>
    DOT_DOT = auto()        # ..  (range)
    DOT_DOT_EQ = auto()     # ..= (inclusive range)
    WALRUS = auto()         # :=

    OPEN_PAREN = auto()     # (
    CLOSE_PAREN = auto()    # )
    OPEN_BRACKET = auto()   # [
    CLOSE_BRACKET = auto()  # ]
    OPEN_BRACE = auto()     # {
    CLOSE_BRACE = auto()    # }
    COLON = auto()          # :
    COMMA = auto()          # ,
    DOT = auto()            # .
    ARROW = auto()          # ->
    SEMICOLON = auto()      # ;
    AT = auto()             # @ (decorator)
    HASH = auto()           # # (comment)
    STAR_STAR_EQUAL = auto()  # **=

@dataclass(frozen=True)
class SyntaxToken:
    kind: SyntaxKind
    position: int
    text: str
    value: Any = None

    @property
    def span(self) -> TextSpan:
        return TextSpan(self.position, len(self.text))

    def __repr__(self) -> str:
        return f"SyntaxToken({self.kind.name}, '{self.text}', {self.span})"

class SyntaxFacts:
    KEYWORDS: dict[str, SyntaxKind] = {
        "def": SyntaxKind.DEF_KEYWORD,
        "class": SyntaxKind.CLASS_KEYWORD,
        "return": SyntaxKind.RETURN_KEYWORD,
        "if": SyntaxKind.IF_KEYWORD,
        "elif": SyntaxKind.ELIF_KEYWORD,
        "else": SyntaxKind.ELSE_KEYWORD,
        "while": SyntaxKind.WHILE_KEYWORD,
        "for": SyntaxKind.FOR_KEYWORD,
        "in": SyntaxKind.IN_KEYWORD,
        "pass": SyntaxKind.PASS_KEYWORD,
        "break": SyntaxKind.BREAK_KEYWORD,
        "continue": SyntaxKind.CONTINUE_KEYWORD,
        "true": SyntaxKind.TRUE_KEYWORD,
        "false": SyntaxKind.FALSE_KEYWORD,
        "null": SyntaxKind.NULL_KEYWORD,
        "and": SyntaxKind.AND_KEYWORD,
        "or": SyntaxKind.OR_KEYWORD,
        "not": SyntaxKind.NOT_KEYWORD,
        "strict": SyntaxKind.STRICT_KEYWORD,
        "import": SyntaxKind.IMPORT_KEYWORD,
        "from": SyntaxKind.FROM_KEYWORD,
        "as": SyntaxKind.AS_KEYWORD,
        "try": SyntaxKind.TRY_KEYWORD,
        "except": SyntaxKind.EXCEPT_KEYWORD,
        "finally": SyntaxKind.FINALLY_KEYWORD,
        "raise": SyntaxKind.RAISE_KEYWORD,
        "is": SyntaxKind.IS_KEYWORD,
        "self": SyntaxKind.SELF_KEYWORD,
        "super": SyntaxKind.SUPER_KEYWORD,
        "lambda": SyntaxKind.LAMBDA_KEYWORD,
        "yield": SyntaxKind.YIELD_KEYWORD,
        "async": SyntaxKind.ASYNC_KEYWORD,
        "await": SyntaxKind.AWAIT_KEYWORD,
        "match": SyntaxKind.MATCH_KEYWORD,
        "case": SyntaxKind.CASE_KEYWORD,
        "with": SyntaxKind.WITH_KEYWORD,
        "global": SyntaxKind.GLOBAL_KEYWORD,
        "nonlocal": SyntaxKind.NONLOCAL_KEYWORD,
        "del": SyntaxKind.DELETE_KEYWORD,
        "assert": SyntaxKind.ASSERT_KEYWORD,
    }

    @classmethod
    def get_keyword_kind(cls, text: str) -> SyntaxKind:
        return cls.KEYWORDS.get(text, SyntaxKind.IDENTIFIER)

    @classmethod
    def get_unary_precedence(cls, kind: SyntaxKind) -> int:
        if kind in (SyntaxKind.PLUS, SyntaxKind.MINUS, SyntaxKind.BANG,
                    SyntaxKind.NOT_KEYWORD, SyntaxKind.TILDE):
            return 9
        return 0

    @classmethod
    def get_binary_precedence(cls, kind: SyntaxKind) -> int:
        if kind == SyntaxKind.STAR_STAR:
            return 8
        if kind in (SyntaxKind.STAR, SyntaxKind.SLASH, SyntaxKind.SLASH_SLASH, SyntaxKind.PERCENT):
            return 7
        if kind in (SyntaxKind.PLUS, SyntaxKind.MINUS):
            return 6
        if kind in (SyntaxKind.LSHIFT, SyntaxKind.RSHIFT):
            return 5
        if kind == SyntaxKind.AMPERSAND:
            return 4
        if kind == SyntaxKind.CARET:
            return 3
        if kind in (SyntaxKind.EQUAL_EQUAL, SyntaxKind.BANG_EQUAL,
                    SyntaxKind.LESS, SyntaxKind.LESS_EQUAL,
                    SyntaxKind.GREATER, SyntaxKind.GREATER_EQUAL,
                    SyntaxKind.IS_KEYWORD, SyntaxKind.IN_KEYWORD):
            return 2
        if kind in (SyntaxKind.AND_KEYWORD, SyntaxKind.AMP_AMP):
            return 1
        if kind in (SyntaxKind.OR_KEYWORD, SyntaxKind.PIPE_PIPE, SyntaxKind.PIPE):
            return 0
        return -1

    @classmethod
    def get_text(cls, kind: SyntaxKind) -> str | None:
        table = {
            SyntaxKind.PLUS: "+",
            SyntaxKind.MINUS: "-",
            SyntaxKind.STAR: "*",
            SyntaxKind.SLASH: "/",
            SyntaxKind.SLASH_SLASH: "//",
            SyntaxKind.PERCENT: "%",
            SyntaxKind.STAR_STAR: "**",
            SyntaxKind.EQUAL: "=",
            SyntaxKind.PLUS_EQUAL: "+=",
            SyntaxKind.MINUS_EQUAL: "-=",
            SyntaxKind.STAR_EQUAL: "*=",
            SyntaxKind.SLASH_EQUAL: "/=",
            SyntaxKind.PERCENT_EQUAL: "%=",
            SyntaxKind.EQUAL_EQUAL: "==",
            SyntaxKind.BANG_EQUAL: "!=",
            SyntaxKind.LESS: "<",
            SyntaxKind.LESS_EQUAL: "<=",
            SyntaxKind.GREATER: ">",
            SyntaxKind.GREATER_EQUAL: ">=",
            SyntaxKind.AMP_AMP: "&&",
            SyntaxKind.PIPE_PIPE: "||",
            SyntaxKind.BANG: "!",
            SyntaxKind.AMPERSAND: "&",
            SyntaxKind.PIPE: "|",
            SyntaxKind.CARET: "^",
            SyntaxKind.TILDE: "~",
            SyntaxKind.LSHIFT: "<<",
            SyntaxKind.RSHIFT: ">>",
            SyntaxKind.OPEN_PAREN: "(",
            SyntaxKind.CLOSE_PAREN: ")",
            SyntaxKind.OPEN_BRACKET: "[",
            SyntaxKind.CLOSE_BRACKET: "]",
            SyntaxKind.OPEN_BRACE: "{",
            SyntaxKind.CLOSE_BRACE: "}",
            SyntaxKind.COLON: ":",
            SyntaxKind.COMMA: ",",
            SyntaxKind.DOT: ".",
            SyntaxKind.ARROW: "->",
            SyntaxKind.DOT_DOT: "..",
            SyntaxKind.DOT_DOT_EQ: "..=",
            SyntaxKind.WALRUS: ":=",
            SyntaxKind.AT: "@",
            SyntaxKind.SEMICOLON: ";",
        }
        return table.get(kind)
