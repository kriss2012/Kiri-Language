from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from .lexer import Token


@dataclass
class Expression:
    pass


@dataclass
class Literal(Expression):
    value: object


@dataclass
class Variable(Expression):
    name: str


@dataclass
class Unary(Expression):
    operator: str
    right: Expression


@dataclass
class Binary(Expression):
    left: Expression
    operator: str
    right: Expression


@dataclass
class Call(Expression):
    callee: Expression
    arguments: List[Expression]


@dataclass
class Statement:
    pass


@dataclass
class ExpressionStatement(Statement):
    expression: Expression


@dataclass
class LetStatement(Statement):
    name: str
    initializer: Expression


@dataclass
class AssignStatement(Statement):
    name: str
    value: Expression


@dataclass
class BlockStatement(Statement):
    statements: List[Statement]


@dataclass
class IfStatement(Statement):
    condition: Expression
    then_branch: BlockStatement
    else_branch: Optional[BlockStatement] = None


@dataclass
class WhileStatement(Statement):
    condition: Expression
    body: BlockStatement


@dataclass
class FunctionStatement(Statement):
    name: str
    params: List[str]
    body: BlockStatement


@dataclass
class ReturnStatement(Statement):
    value: Optional[Expression]


class Parser:
    def __init__(self, tokens: Sequence[Token]):
        self.tokens = list(tokens)
        self.index = 0

    def parse(self) -> List[Statement]:
        statements: List[Statement] = []
        while not self.check("EOF"):
            statements.append(self.parse_statement())
        return statements

    def parse_statement(self) -> Statement:
        if self.match("LET"):
            return self.parse_let_statement()
        if self.match("IF"):
            return self.parse_if_statement()
        if self.match("WHILE"):
            return self.parse_while_statement()
        if self.match("FN"):
            return self.parse_function_statement()
        if self.match("RETURN"):
            return self.parse_return_statement()
        if self.check("LBRACE"):
            return self.parse_block()
        if self.check("IDENT") and self.peek_type() == "EQUAL":
            name = self.advance().value
            self.advance()  # consume '='
            value = self.parse_expression()
            self.match("SEMICOLON")
            return AssignStatement(name, value)

        expression = self.parse_expression()
        self.match("SEMICOLON")
        return ExpressionStatement(expression)

    def parse_let_statement(self) -> LetStatement:
        name = self.consume("IDENT", "Expected identifier after 'let'.").value
        self.consume("EQUAL", "Expected '=' after variable name.")
        initializer = self.parse_expression()
        self.match("SEMICOLON")
        return LetStatement(name, initializer)

    def parse_if_statement(self) -> IfStatement:
        condition = self.parse_expression()
        then_branch = self.parse_block()
        else_branch = None
        if self.match("ELSE"):
            else_branch = self.parse_block()
        return IfStatement(condition, then_branch, else_branch)

    def parse_while_statement(self) -> WhileStatement:
        condition = self.parse_expression()
        body = self.parse_block()
        return WhileStatement(condition, body)

    def parse_function_statement(self) -> FunctionStatement:
        name = self.consume("IDENT", "Expected function name.").value
        self.consume("LPAREN", "Expected '(' after function name.")
        params: List[str] = []
        if not self.check("RPAREN"):
            while True:
                params.append(self.consume("IDENT", "Expected parameter name.").value)
                if not self.match("COMMA"):
                    break
        self.consume("RPAREN", "Expected ')' after parameters.")
        body = self.parse_block()
        return FunctionStatement(name, params, body)

    def parse_return_statement(self) -> ReturnStatement:
        if self.check("SEMICOLON"):
            self.advance()
            return ReturnStatement(None)
        value = self.parse_expression()
        self.match("SEMICOLON")
        return ReturnStatement(value)

    def parse_block(self) -> BlockStatement:
        self.consume("LBRACE", "Expected '{'.")
        statements: List[Statement] = []
        while not self.check("RBRACE") and not self.check("EOF"):
            statements.append(self.parse_statement())
        self.consume("RBRACE", "Expected '}'.")
        return BlockStatement(statements)

    def parse_expression(self) -> Expression:
        return self.parse_or()

    def parse_or(self) -> Expression:
        expr = self.parse_and()
        while self.match("OR"):
            operator = "or"
            right = self.parse_and()
            expr = Binary(expr, operator, right)
        return expr

    def parse_and(self) -> Expression:
        expr = self.parse_equality()
        while self.match("AND"):
            operator = "and"
            right = self.parse_equality()
            expr = Binary(expr, operator, right)
        return expr

    def parse_equality(self) -> Expression:
        expr = self.parse_comparison()
        while self.match("EQ", "NEQ"):
            operator = self.previous().type
            right = self.parse_comparison()
            expr = Binary(expr, self.map_operator(operator), right)
        return expr

    def parse_comparison(self) -> Expression:
        expr = self.parse_term()
        while self.match("LT", "LTE", "GT", "GTE"):
            operator = self.previous().type
            right = self.parse_term()
            expr = Binary(expr, self.map_operator(operator), right)
        return expr

    def parse_term(self) -> Expression:
        expr = self.parse_factor()
        while self.match("PLUS", "MINUS"):
            operator = self.previous().type
            right = self.parse_factor()
            expr = Binary(expr, self.map_operator(operator), right)
        return expr

    def parse_factor(self) -> Expression:
        expr = self.parse_unary()
        while self.match("STAR", "SLASH", "PERCENT"):
            operator = self.previous().type
            right = self.parse_unary()
            expr = Binary(expr, self.map_operator(operator), right)
        return expr

    def parse_unary(self) -> Expression:
        if self.match("MINUS", "NOT"):
            operator = self.previous().type
            right = self.parse_unary()
            return Unary(self.map_operator(operator), right)
        return self.parse_call()

    def parse_call(self) -> Expression:
        expr = self.parse_primary()
        while True:
            if self.match("LPAREN"):
                arguments: List[Expression] = []
                if not self.check("RPAREN"):
                    while True:
                        arguments.append(self.parse_expression())
                        if not self.match("COMMA"):
                            break
                self.consume("RPAREN", "Expected ')' after arguments.")
                expr = Call(expr, arguments)
            else:
                break
        return expr

    def parse_primary(self) -> Expression:
        if self.match("NUMBER"):
            return Literal(self.previous().value)
        if self.match("STRING"):
            return Literal(self.previous().value)
        if self.match("TRUE"):
            return Literal(True)
        if self.match("FALSE"):
            return Literal(False)
        if self.match("NULL"):
            return Literal(None)
        if self.match("IDENT"):
            return Variable(self.previous().value)
        if self.match("LPAREN"):
            expr = self.parse_expression()
            self.consume("RPAREN", "Expected ')'.")
            return expr
        raise SyntaxError(f"Unexpected token '{self.current().type}' while parsing expression.")

    def match(self, *types: str) -> bool:
        if self.check(*types):
            self.index += 1
            return True
        return False

    def check(self, *types: str) -> bool:
        if self.current().type in types:
            return True
        return False

    def current(self) -> Token:
        return self.tokens[self.index]

    def previous(self) -> Token:
        return self.tokens[self.index - 1]

    def advance(self) -> Token:
        token = self.current()
        if token.type != "EOF":
            self.index += 1
        return token

    def consume(self, token_type: str, message: str) -> Token:
        if self.check(token_type):
            return self.advance()
        raise SyntaxError(message)

    def peek_type(self) -> str:
        if self.index + 1 < len(self.tokens):
            return self.tokens[self.index + 1].type
        return "EOF"

    @staticmethod
    def map_operator(token_type: str) -> str:
        mapping = {
            "PLUS": "+",
            "MINUS": "-",
            "STAR": "*",
            "SLASH": "/",
            "PERCENT": "%",
            "LT": "<",
            "LTE": "<=",
            "GT": ">",
            "GTE": ">=",
            "EQ": "==",
            "NEQ": "!=",
            "NOT": "not",
            "EQUAL": "=",
        }
        return mapping.get(token_type, token_type)
