from __future__ import annotations
import sys
from typing import TextIO
from .compiler.diagnostics import SourceText, DiagnosticBag
from .compiler.parser import Parser
from .runtime.values import KiriValue, KiriValueType
from .runtime.environment import KiriEnvironment
from .runtime.evaluator import Evaluator

class ExecutionResult:
    def __init__(self, success: bool, value: KiriValue, diagnostics: DiagnosticBag, formatted_errors: str) -> None:
        self.success = success
        self.value = value
        self.diagnostics = diagnostics
        self.formatted_errors = formatted_errors

class KiriEngine:
    def __init__(self, output: TextIO | None = None, global_env: KiriEnvironment | None = None) -> None:
        self.output = output if output is not None else sys.stdout
        dummy_src = SourceText.from_str("")
        evaluator = Evaluator(dummy_src, None, self.output)
        self.global_env = global_env if global_env is not None else evaluator.create_default_environment()

    def execute(self, code: str, file_name: str = "<stdin>") -> ExecutionResult:
        source = SourceText.from_str(code, file_name)
        diagnostics = DiagnosticBag()

        parser = Parser(source, diagnostics)
        unit = parser.parse_compilation_unit()

        if diagnostics.has_errors:
            return ExecutionResult(False, KiriValue.null(), diagnostics, diagnostics.format(source))

        evaluator = Evaluator(source, diagnostics, self.output, self.global_env)
        val = evaluator.evaluate(unit)

        if diagnostics.has_errors:
            return ExecutionResult(False, KiriValue.null(), diagnostics, diagnostics.format(source))

        return ExecutionResult(True, val, diagnostics, "")
