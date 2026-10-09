from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class Token:
    type: str
    value: object
    position: int


KEYWORDS = {
    "let": "LET",
    "if": "IF",
    "else": "ELSE",
    "while": "WHILE",
    "fn": "FN",
    "return": "RETURN",
    "true": "TRUE",
    "false": "FALSE",
    "null": "NULL",
    "and": "AND",
    "or": "OR",
    "not": "NOT",
}


SINGLE_CHAR_TOKENS = {
    "(": "LPAREN",
    ")": "RPAREN",
    "{": "LBRACE",
    "}": "RBRACE",
    "[": "LBRACKET",
    "]": "RBRACKET",
    ",": "COMMA",
    ";": "SEMICOLON",
    ":": "COLON",
    "+": "PLUS",
    "-": "MINUS",
    "*": "STAR",
    "/": "SLASH",
    "%": "PERCENT",
    "=": "EQUAL",
    "<": "LT",
    ">": "GT",
}

MULTI_CHAR_TOKENS = {
    "==": "EQ",
    "!=": "NEQ",
    "<=": "LTE",
    ">=": "GTE",
}


def tokenize(source: str) -> List[Token]:
    tokens: List[Token] = []
    index = 0
    length = len(source)

    while index < length:
        ch = source[index]

        if ch.isspace():
            index += 1
            continue

        if ch == "/" and index + 1 < length and source[index + 1] == "/":
            index += 2
            while index < length and source[index] != "\n":
                index += 1
            continue

        if ch in ('"', "'"):
            start = index
            quote = ch
            index += 1
            text = ""
            while index < length:
                current = source[index]
                if current == "\\":
                    index += 1
                    if index >= length:
                        raise SyntaxError("Unterminated string literal.")
                    escaped = source[index]
                    escape_map = {
                        'n': '\n',
                        't': '\t',
                        'r': '\r',
                        '"': '"',
                        "'": "'",
                        '\\': '\\',
                    }
                    text += escape_map.get(escaped, escaped)
                    index += 1
                    continue
                if current == quote:
                    index += 1
                    break
                text += current
                index += 1
            else:
                raise SyntaxError("Unterminated string literal.")
            tokens.append(Token("STRING", text, start))
            continue

        if ch.isdigit():
            start = index
            while index < length and source[index].isdigit():
                index += 1
            if index < length and source[index] == ".":
                index += 1
                if index >= length or not source[index].isdigit():
                    raise SyntaxError("Invalid numeric literal.")
                while index < length and source[index].isdigit():
                    index += 1
                tokens.append(Token("NUMBER", float(source[start:index]), start))
            else:
                tokens.append(Token("NUMBER", int(source[start:index]), start))
            continue

        if ch.isalpha() or ch == "_":
            start = index
            while index < length and (source[index].isalnum() or source[index] == "_"):
                index += 1
            word = source[start:index]
            if word in KEYWORDS:
                tokens.append(Token(KEYWORDS[word], word, start))
            else:
                tokens.append(Token("IDENT", word, start))
            continue

        if index + 1 < length:
            two_char = source[index:index + 2]
            if two_char in MULTI_CHAR_TOKENS:
                tokens.append(Token(MULTI_CHAR_TOKENS[two_char], two_char, index))
                index += 2
                continue

        if ch in SINGLE_CHAR_TOKENS:
            tokens.append(Token(SINGLE_CHAR_TOKENS[ch], ch, index))
            index += 1
            continue

        if ch in "!":
            tokens.append(Token("NOT", ch, index))
            index += 1
            continue

        raise SyntaxError(f"Unexpected character '{ch}' at position {index}.")

    tokens.append(Token("EOF", None, length))
    return tokens
