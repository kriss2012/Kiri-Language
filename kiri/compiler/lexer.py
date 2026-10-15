from __future__ import annotations
from collections import deque
from typing import Any
from .diagnostics import SourceText, DiagnosticBag, TextSpan
from .tokens import SyntaxKind, SyntaxToken, SyntaxFacts

class Lexer:
    def __init__(self, source: SourceText, diagnostics: DiagnosticBag | None = None) -> None:
        self.source = source
        self.diagnostics = diagnostics if diagnostics is not None else DiagnosticBag()
        self.text = source.text
        self.pos = 0
        self.indent_stack: list[int] = [0]
        self.pending_tokens: deque[SyntaxToken] = deque()
        self.bracket_depth = 0
        self.at_line_start = True
        self.emitted_token_on_line = False

    def peek(self, offset: int = 0) -> str:
        idx = self.pos + offset
        if idx >= len(self.text):
            return '\0'
        return self.text[idx]

    @property
    def current(self) -> str:
        return self.peek(0)

    @property
    def lookahead(self) -> str:
        return self.peek(1)

    def lex_all(self) -> list[SyntaxToken]:
        tokens: list[SyntaxToken] = []
        while True:
            token = self.next_token()
            tokens.append(token)
            if token.kind == SyntaxKind.EOF:
                break
        return tokens

    def next_token(self) -> SyntaxToken:
        if self.pending_tokens:
            return self.pending_tokens.popleft()

        n = len(self.text)
        while self.pos < n:
            if self.at_line_start:
                indent_start = self.pos
                spaces = 0
                while self.pos < n and self.text[self.pos] in (' ', '\t'):
                    spaces += 4 if self.text[self.pos] == '\t' else 1
                    self.pos += 1

                # Empty or whitespace-only line
                if self.pos < n and self.text[self.pos] in ('\r', '\n'):
                    self._consume_physical_newline()
                    continue

                # Comment line
                if self.pos < n and self.text[self.pos] == '#':
                    while self.pos < n and self.text[self.pos] not in ('\r', '\n'):
                        self.pos += 1
                    if self.pos < n:
                        self._consume_physical_newline()
                    continue

                self.at_line_start = False

                if self.bracket_depth == 0:
                    current_indent = self.indent_stack[-1]
                    if spaces > current_indent:
                        self.indent_stack.append(spaces)
                        self.pending_tokens.append(SyntaxToken(SyntaxKind.INDENT, indent_start, " " * spaces))
                    elif spaces < current_indent:
                        while len(self.indent_stack) > 1 and self.indent_stack[-1] > spaces:
                            self.indent_stack.pop()
                            self.pending_tokens.append(SyntaxToken(SyntaxKind.DEDENT, indent_start, ""))

                        if self.indent_stack[-1] != spaces:
                            span = TextSpan(indent_start, max(1, self.pos - indent_start))
                            self.diagnostics.report_error(
                                span,
                                "IndentationError: Unindent does not match any outer indentation level.",
                                "Ensure line indentation matches an outer block (e.g. 4 spaces)."
                            )

                    if self.pending_tokens:
                        return self.pending_tokens.popleft()

            c = self.current

            # Whitespace
            if c in (' ', '\t'):
                self.pos += 1
                continue

            # Comment
            if c == '#':
                while self.pos < n and self.text[self.pos] not in ('\r', '\n'):
                    self.pos += 1
                continue

            # Line continuation with backslash \
            if c == '\\' and self.lookahead in ('\r', '\n'):
                self.pos += 1
                self._consume_physical_newline()
                continue

            # Physical Newline
            if c in ('\r', '\n'):
                nl_pos = self.pos
                self._consume_physical_newline()
                self.at_line_start = True
                if self.bracket_depth == 0 and self.emitted_token_on_line:
                    self.emitted_token_on_line = False
                    return SyntaxToken(SyntaxKind.NEWLINE, nl_pos, "\n")
                continue

            self.emitted_token_on_line = True

            # Numbers
            if c.isdigit():
                return self._scan_number()

            # Identifiers / Keywords
            if c.isalpha() or c == '_':
                return self._scan_identifier()

            # Strings (including f-strings and triple-quoted)
            if c in ('"', "'"):
                return self._scan_string()
            if (c == 'f' or c == 'F') and self.lookahead in ('"', "'"):
                return self._scan_fstring()
            if (c == 'r' or c == 'R') and self.lookahead in ('"', "'"):
                self.pos += 1  # skip r prefix, treat as raw
                return self._scan_string(raw=True)
            if (c == 'b' or c == 'B') and self.lookahead in ('"', "'"):
                self.pos += 1  # skip b prefix, treat as bytes (string for now)
                return self._scan_string()

            # Multi-character operators
            start = self.pos

            # 3-char operators first
            c2 = self.peek(1)
            c3 = self.peek(2)

            if c == '.' and c2 == '.' and c3 == '=':
                self.pos += 3
                return SyntaxToken(SyntaxKind.DOT_DOT_EQ, start, "..=")
            if c == '*' and c2 == '*' and c3 == '=':
                self.pos += 3
                return SyntaxToken(SyntaxKind.STAR_STAR_EQUAL, start, "**=")
            if c == '<' and c2 == '<':
                self.pos += 2
                return SyntaxToken(SyntaxKind.LSHIFT, start, "<<")
            if c == '>' and c2 == '>':
                self.pos += 2
                return SyntaxToken(SyntaxKind.RSHIFT, start, ">>")

            # 2-char operators
            if c == '=' and c2 == '=':
                self.pos += 2
                return SyntaxToken(SyntaxKind.EQUAL_EQUAL, start, "==")
            if c == '!' and c2 == '=':
                self.pos += 2
                return SyntaxToken(SyntaxKind.BANG_EQUAL, start, "!=")
            if c == '<' and c2 == '=':
                self.pos += 2
                return SyntaxToken(SyntaxKind.LESS_EQUAL, start, "<=")
            if c == '>' and c2 == '=':
                self.pos += 2
                return SyntaxToken(SyntaxKind.GREATER_EQUAL, start, ">=")
            if c == '-' and c2 == '>':
                self.pos += 2
                return SyntaxToken(SyntaxKind.ARROW, start, "->")
            if c == '*' and c2 == '*':
                self.pos += 2
                return SyntaxToken(SyntaxKind.STAR_STAR, start, "**")
            if c == '&' and c2 == '&':
                self.pos += 2
                return SyntaxToken(SyntaxKind.AMP_AMP, start, "&&")
            if c == '|' and c2 == '|':
                self.pos += 2
                return SyntaxToken(SyntaxKind.PIPE_PIPE, start, "||")
            if c == '.' and c2 == '.':
                self.pos += 2
                return SyntaxToken(SyntaxKind.DOT_DOT, start, "..")
            if c == ':' and c2 == '=':
                self.pos += 2
                return SyntaxToken(SyntaxKind.WALRUS, start, ":=")
            if c == '+' and c2 == '=':
                self.pos += 2
                return SyntaxToken(SyntaxKind.PLUS_EQUAL, start, "+=")
            if c == '-' and c2 == '=':
                self.pos += 2
                return SyntaxToken(SyntaxKind.MINUS_EQUAL, start, "-=")
            if c == '*' and c2 == '=':
                self.pos += 2
                return SyntaxToken(SyntaxKind.STAR_EQUAL, start, "*=")
            if c == '/' and c2 == '=':
                self.pos += 2
                return SyntaxToken(SyntaxKind.SLASH_EQUAL, start, "/=")
            if c == '%' and c2 == '=':
                self.pos += 2
                return SyntaxToken(SyntaxKind.PERCENT_EQUAL, start, "%=")
            if c == '/' and c2 == '/':
                self.pos += 2
                return SyntaxToken(SyntaxKind.SLASH_SLASH, start, "//")

            # Single-character tokens
            self.pos += 1
            if c == '+': return SyntaxToken(SyntaxKind.PLUS, start, "+")
            if c == '-': return SyntaxToken(SyntaxKind.MINUS, start, "-")
            if c == '*': return SyntaxToken(SyntaxKind.STAR, start, "*")
            if c == '/': return SyntaxToken(SyntaxKind.SLASH, start, "/")
            if c == '%': return SyntaxToken(SyntaxKind.PERCENT, start, "%")
            if c == '=': return SyntaxToken(SyntaxKind.EQUAL, start, "=")
            if c == '<': return SyntaxToken(SyntaxKind.LESS, start, "<")
            if c == '>': return SyntaxToken(SyntaxKind.GREATER, start, ">")
            if c == '!': return SyntaxToken(SyntaxKind.BANG, start, "!")
            if c == ':': return SyntaxToken(SyntaxKind.COLON, start, ":")
            if c == ',': return SyntaxToken(SyntaxKind.COMMA, start, ",")
            if c == '.': return SyntaxToken(SyntaxKind.DOT, start, ".")
            if c == '@': return SyntaxToken(SyntaxKind.AT, start, "@")
            if c == '~': return SyntaxToken(SyntaxKind.TILDE, start, "~")
            if c == '^': return SyntaxToken(SyntaxKind.CARET, start, "^")
            if c == '&': return SyntaxToken(SyntaxKind.AMPERSAND, start, "&")
            if c == '|': return SyntaxToken(SyntaxKind.PIPE, start, "|")
            if c == ';': return SyntaxToken(SyntaxKind.SEMICOLON, start, ";")

            if c == '(':
                self.bracket_depth += 1
                return SyntaxToken(SyntaxKind.OPEN_PAREN, start, "(")
            if c == ')':
                if self.bracket_depth > 0: self.bracket_depth -= 1
                return SyntaxToken(SyntaxKind.CLOSE_PAREN, start, ")")
            if c == '[':
                self.bracket_depth += 1
                return SyntaxToken(SyntaxKind.OPEN_BRACKET, start, "[")
            if c == ']':
                if self.bracket_depth > 0: self.bracket_depth -= 1
                return SyntaxToken(SyntaxKind.CLOSE_BRACKET, start, "]")
            if c == '{':
                self.bracket_depth += 1
                return SyntaxToken(SyntaxKind.OPEN_BRACE, start, "{")
            if c == '}':
                if self.bracket_depth > 0: self.bracket_depth -= 1
                return SyntaxToken(SyntaxKind.CLOSE_BRACE, start, "}")

            self.diagnostics.report_error(TextSpan(start, 1), f"Unexpected character '{c}'.")
            return SyntaxToken(SyntaxKind.BAD_TOKEN, start, c)

        # EOF Handling
        if self.emitted_token_on_line:
            self.emitted_token_on_line = False
            self.pending_tokens.append(SyntaxToken(SyntaxKind.NEWLINE, self.pos, "\n"))

        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            self.pending_tokens.append(SyntaxToken(SyntaxKind.DEDENT, self.pos, ""))

        if self.pending_tokens:
            return self.pending_tokens.popleft()

        return SyntaxToken(SyntaxKind.EOF, self.pos, "")

    def _consume_physical_newline(self) -> None:
        if self.current == '\r' and self.lookahead == '\n':
            self.pos += 2
        elif self.current in ('\r', '\n'):
            self.pos += 1

    def _scan_number(self) -> SyntaxToken:
        start = self.pos
        n = len(self.text)
        is_hex = False
        is_bin = False
        is_oct = False

        if self.current == '0' and self.pos + 1 < n:
            nxt = self.lookahead.lower()
            if nxt == 'x': is_hex = True; self.pos += 2
            elif nxt == 'b': is_bin = True; self.pos += 2
            elif nxt == 'o': is_oct = True; self.pos += 2

        if is_hex:
            while self.pos < n and (self.text[self.pos] in "0123456789abcdefABCDEF_"):
                self.pos += 1
            raw = self.text[start:self.pos].replace('_', '')
            val = int(raw[2:], 16)
            return SyntaxToken(SyntaxKind.INT_LITERAL, start, self.text[start:self.pos], val)

        if is_bin:
            while self.pos < n and (self.text[self.pos] in "01_"):
                self.pos += 1
            raw = self.text[start:self.pos].replace('_', '')
            val = int(raw[2:], 2)
            return SyntaxToken(SyntaxKind.INT_LITERAL, start, self.text[start:self.pos], val)

        if is_oct:
            while self.pos < n and (self.text[self.pos] in "01234567_"):
                self.pos += 1
            raw = self.text[start:self.pos].replace('_', '')
            val = int(raw[2:], 8)
            return SyntaxToken(SyntaxKind.INT_LITERAL, start, self.text[start:self.pos], val)

        has_dot = False
        has_exp = False
        while self.pos < n:
            ch = self.text[self.pos]
            if ch.isdigit() or ch == '_':
                self.pos += 1
            elif ch == '.' and not has_dot and not has_exp and self.lookahead.isdigit():
                has_dot = True
                self.pos += 1
            elif (ch == 'e' or ch == 'E') and not has_exp:
                has_exp = True
                self.pos += 1
                if self.pos < n and self.text[self.pos] in ('+', '-'):
                    self.pos += 1
            else:
                break

        raw_str = self.text[start:self.pos]
        clean_str = raw_str.replace('_', '')

        if has_dot or has_exp:
            try:
                val_f = float(clean_str)
                return SyntaxToken(SyntaxKind.FLOAT_LITERAL, start, raw_str, val_f)
            except ValueError:
                self.diagnostics.report_error(TextSpan(start, len(raw_str)), f"Invalid float literal '{raw_str}'.")
                return SyntaxToken(SyntaxKind.FLOAT_LITERAL, start, raw_str, 0.0)
        else:
            try:
                val_i = int(clean_str)
                return SyntaxToken(SyntaxKind.INT_LITERAL, start, raw_str, val_i)
            except ValueError:
                self.diagnostics.report_error(TextSpan(start, len(raw_str)), f"Invalid integer literal '{raw_str}'.")
                return SyntaxToken(SyntaxKind.INT_LITERAL, start, raw_str, 0)

    def _scan_identifier(self) -> SyntaxToken:
        start = self.pos
        n = len(self.text)
        while self.pos < n and (self.text[self.pos].isalnum() or self.text[self.pos] == '_'):
            self.pos += 1

        text = self.text[start:self.pos]
        kind = SyntaxFacts.get_keyword_kind(text)

        if kind == SyntaxKind.TRUE_KEYWORD:
            return SyntaxToken(SyntaxKind.BOOL_LITERAL, start, text, True)
        if kind == SyntaxKind.FALSE_KEYWORD:
            return SyntaxToken(SyntaxKind.BOOL_LITERAL, start, text, False)
        if kind == SyntaxKind.NULL_KEYWORD:
            return SyntaxToken(SyntaxKind.NULL_LITERAL, start, text, None)

        return SyntaxToken(kind, start, text)

    def _scan_string(self, raw: bool = False) -> SyntaxToken:
        quote = self.current
        start = self.pos
        n = len(self.text)

        # Triple-quoted string?
        if self.peek(1) == quote and self.peek(2) == quote:
            self.pos += 3  # consume opening triple quote
            chars: list[str] = []
            closed = False
            while self.pos < n:
                if self.peek(0) == quote and self.peek(1) == quote and self.peek(2) == quote:
                    self.pos += 3
                    closed = True
                    break
                c = self.text[self.pos]
                if c == '\\' and not raw:
                    self.pos += 1
                    if self.pos >= n: break
                    esc = self.text[self.pos]
                    self.pos += 1
                    table = {'n': '\n', 'r': '\r', 't': '\t', '\\': '\\', '"': '"', "'": "'", '0': '\0'}
                    chars.append(table.get(esc, esc))
                else:
                    chars.append(c)
                    self.pos += 1
            if not closed:
                self.diagnostics.report_error(TextSpan(start, self.pos - start), "Unclosed triple-quoted string.")
            return SyntaxToken(SyntaxKind.STRING_LITERAL, start, self.text[start:self.pos], "".join(chars))

        # Single-quoted string
        self.pos += 1
        chars2: list[str] = []
        closed2 = False
        while self.pos < n:
            c = self.text[self.pos]
            if c == quote:
                self.pos += 1
                closed2 = True
                break
            if c == '\\' and not raw:
                self.pos += 1
                if self.pos >= n:
                    break
                esc = self.text[self.pos]
                self.pos += 1
                table = {'n': '\n', 'r': '\r', 't': '\t', '\\': '\\', '"': '"', "'": "'", '0': '\0', 'a': '\a', 'b': '\b', 'f': '\f', 'v': '\v'}
                if esc == 'u':
                    # \uXXXX
                    hex_str = self.text[self.pos:self.pos+4]
                    if len(hex_str) == 4:
                        try:
                            chars2.append(chr(int(hex_str, 16)))
                            self.pos += 4
                            continue
                        except ValueError:
                            pass
                chars2.append(table.get(esc, esc))
            elif c in ('\r', '\n'):
                self.diagnostics.report_error(TextSpan(start, self.pos - start), "Unterminated string literal.")
                break
            else:
                chars2.append(c)
                self.pos += 1
        if not closed2:
            self.diagnostics.report_error(TextSpan(start, self.pos - start), "Unclosed string literal.", "Add closing quote.")
        return SyntaxToken(SyntaxKind.STRING_LITERAL, start, self.text[start:self.pos], "".join(chars2))

    def _scan_fstring(self) -> SyntaxToken:
        """Scan f"...{expr}..." — produces a STRING_LITERAL with special marker for the parser.
        For simplicity in Phase 2, we lex f-strings as a single token carrying the raw template string.
        The parser/evaluator handles interpolation.
        """
        start = self.pos
        self.pos += 1  # skip f/F prefix
        raw_tok = self._scan_string()
        # Mark as f-string by using a special value: tuple ("__fstring__", raw_string)
        return SyntaxToken(SyntaxKind.STRING_LITERAL, start, self.text[start:self.pos],
                           ("__fstring__", raw_tok.value if raw_tok.value is not None else ""))
