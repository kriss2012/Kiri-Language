from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .lexer import tokenize
from .parser import (
    AssignStatement,
    Binary,
    BlockStatement,
    Expression,
    ExpressionStatement,
    FunctionStatement,
    IfStatement,
    LetStatement,
    Literal,
    ReturnStatement,
    Unary,
    Variable,
    WhileStatement,
    Call,
    Parser,
)


class ReturnSignal(Exception):
    def __init__(self, value: Any):
        self.value = value


@dataclass
class BuiltinFunction:
    name: str
    fn: Any


@dataclass
class KiriFunction:
    name: str
    params: List[str]
    body: BlockStatement
    closure: "Environment"


class Environment:
    def __init__(self, enclosing: Optional["Environment"] = None):
        self.values: Dict[str, Any] = {}
        self.enclosing = enclosing

    def define(self, name: str, value: Any) -> None:
        self.values[name] = value

    def assign(self, name: str, value: Any) -> None:
        if name in self.values:
            self.values[name] = value
            return
        if self.enclosing is not None:
            self.enclosing.assign(name, value)
            return
        raise RuntimeError(f"Undefined variable '{name}'.")

    def get(self, name: str) -> Any:
        if name in self.values:
            return self.values[name]
        if self.enclosing is not None:
            return self.enclosing.get(name)
        raise RuntimeError(f"Undefined variable '{name}'.")


class KiriInterpreter:
    def __init__(self):
        self.global_environment = Environment()
        self.environment = self.global_environment
        self.stdout: List[str] = []
        self._register_builtins()

    def _register_builtins(self) -> None:
        self.global_environment.define("print", BuiltinFunction("print", self._builtin_print))
        self.global_environment.define("len", BuiltinFunction("len", self._builtin_len))

    def _builtin_print(self, *values: Any) -> Any:
        text = " ".join(str(value) for value in values)
        self.stdout.append(text)
        return text

    def _builtin_len(self, value: Any) -> int:
        if isinstance(value, (str, list, tuple, dict)):
            return len(value)
        raise TypeError("len() expects a string, list, tuple, or dictionary.")

    def run_source(self, source: str) -> str:
        tokens = tokenize(source)
        statements = Parser(tokens).parse()
        self.stdout = []
        self.environment = self.global_environment
        for statement in statements:
            self.execute(statement)
        return "\n".join(self.stdout)

    def execute(self, statement: Any) -> Any:
        if isinstance(statement, LetStatement):
            self.environment.define(statement.name, self.evaluate(statement.initializer))
            return None
        if isinstance(statement, AssignStatement):
            self.environment.assign(statement.name, self.evaluate(statement.value))
            return None
        if isinstance(statement, ExpressionStatement):
            return self.evaluate(statement.expression)
        if isinstance(statement, BlockStatement):
            env = Environment(self.environment)
            previous = self.environment
            self.environment = env
            try:
                for item in statement.statements:
                    self.execute(item)
            finally:
                self.environment = previous
            return None
        if isinstance(statement, IfStatement):
            if self.is_truthy(self.evaluate(statement.condition)):
                self.execute(statement.then_branch)
            elif statement.else_branch is not None:
                self.execute(statement.else_branch)
            return None
        if isinstance(statement, WhileStatement):
            while self.is_truthy(self.evaluate(statement.condition)):
                self.execute(statement.body)
            return None
        if isinstance(statement, FunctionStatement):
            self.environment.define(statement.name, KiriFunction(statement.name, statement.params, statement.body, self.environment))
            return None
        if isinstance(statement, ReturnStatement):
            value = self.evaluate(statement.value) if statement.value is not None else None
            raise ReturnSignal(value)
        raise TypeError(f"Unsupported statement type: {type(statement).__name__}")

    def evaluate(self, expression: Any) -> Any:
        if isinstance(expression, Literal):
            return expression.value
        if isinstance(expression, Variable):
            return self.environment.get(expression.name)
        if isinstance(expression, Unary):
            value = self.evaluate(expression.right)
            if expression.operator == "-":
                return -value
            if expression.operator == "not":
                return not self.is_truthy(value)
            raise ValueError(f"Unsupported unary operator: {expression.operator}")
        if isinstance(expression, Binary):
            return self.evaluate_binary(expression)
        if isinstance(expression, Call):
            callee = self.evaluate(expression.callee)
            arguments = [self.evaluate(arg) for arg in expression.arguments]
            if isinstance(callee, BuiltinFunction):
                return callee.fn(*arguments)
            if isinstance(callee, KiriFunction):
                local_env = Environment(callee.closure)
                for name, value in zip(callee.params, arguments):
                    local_env.define(name, value)
                previous = self.environment
                self.environment = local_env
                try:
                    for stmt in callee.body.statements:
                        try:
                            self.execute(stmt)
                        except ReturnSignal as signal:
                            return signal.value
                    return None
                finally:
                    self.environment = previous
            raise TypeError(f"Attempted to call a non-callable value: {callee!r}")
        raise TypeError(f"Unsupported expression type: {type(expression).__name__}")

    def evaluate_binary(self, expression: Binary) -> Any:
        left = self.evaluate(expression.left)
        operator = expression.operator

        if operator == "and":
            return self.is_truthy(left) and self.is_truthy(self.evaluate(expression.right))
        if operator == "or":
            return self.is_truthy(left) or self.is_truthy(self.evaluate(expression.right))

        right = self.evaluate(expression.right)

        if operator == "+":
            return left + right
        if operator == "-":
            return left - right
        if operator == "*":
            return left * right
        if operator == "/":
            return left / right
        if operator == "%":
            return left % right
        if operator == "==":
            return left == right
        if operator == "!=":
            return left != right
        if operator == "<":
            return left < right
        if operator == "<=":
            return left <= right
        if operator == ">":
            return left > right
        if operator == ">=":
            return left >= right
        raise ValueError(f"Unsupported binary operator: {operator}")

    @staticmethod
    def is_truthy(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        return bool(value)
