from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
import bisect

@dataclass(frozen=True)
class TextSpan:
    start: int
    length: int

    @property
    def end(self) -> int:
        return self.start + self.length

    @classmethod
    def from_bounds(cls, start: int, end: int) -> TextSpan:
        return cls(start, max(0, end - start))

    def __str__(self) -> str:
        return f"[{self.start}..{self.end})"

class SourceText:
    def __init__(self, text: str, file_name: str = "<stdin>") -> None:
        self.text = text
        self.file_name = file_name
        self.line_starts = self._build_line_starts(text)

    @classmethod
    def from_str(cls, text: str, file_name: str = "<stdin>") -> SourceText:
        return cls(text, file_name)

    @property
    def length(self) -> int:
        return len(self.text)

    def _build_line_starts(self, text: str) -> list[int]:
        starts = [0]
        i = 0
        n = len(text)
        while i < n:
            c = text[i]
            if c == '\r':
                if i + 1 < n and text[i + 1] == '\n':
                    i += 1
                starts.append(i + 1)
            elif c == '\n':
                starts.append(i + 1)
            i += 1
        return starts

    def get_line_index(self, position: int) -> int:
        if position < 0:
            return 0
        idx = bisect.bisect_right(self.line_starts, position) - 1
        return max(0, idx)

    def get_line_and_column(self, position: int) -> tuple[int, int]:
        line_idx = self.get_line_index(position)
        line_start = self.line_starts[line_idx]
        col = max(1, position - line_start + 1)
        return (line_idx + 1, col)

    def get_line_text(self, line_idx: int) -> str:
        if line_idx < 0 or line_idx >= len(self.line_starts):
            return ""
        start = self.line_starts[line_idx]
        end = self.line_starts[line_idx + 1] if line_idx + 1 < len(self.line_starts) else len(self.text)
        line = self.text[start:end]
        return line.rstrip('\r\n')

class DiagnosticSeverity(Enum):
    INFO = auto()
    WARNING = auto()
    ERROR = auto()

@dataclass
class Diagnostic:
    span: TextSpan
    message: str
    severity: DiagnosticSeverity = DiagnosticSeverity.ERROR
    suggestion: str | None = None

    def __str__(self) -> str:
        return f"[{self.severity.name}] {self.message} at {self.span}"

class DiagnosticBag:
    def __init__(self) -> None:
        self.diagnostics: list[Diagnostic] = []

    @property
    def has_errors(self) -> bool:
        return any(d.severity == DiagnosticSeverity.ERROR for d in self.diagnostics)

    def report(self, span: TextSpan, message: str, severity: DiagnosticSeverity = DiagnosticSeverity.ERROR, suggestion: str | None = None) -> None:
        self.diagnostics.append(Diagnostic(span, message, severity, suggestion))

    def report_error(self, span: TextSpan, message: str, suggestion: str | None = None) -> None:
        self.report(span, message, DiagnosticSeverity.ERROR, suggestion)

    def report_warning(self, span: TextSpan, message: str, suggestion: str | None = None) -> None:
        self.report(span, message, DiagnosticSeverity.WARNING, suggestion)

    def extend(self, other: DiagnosticBag) -> None:
        self.diagnostics.extend(other.diagnostics)

    def format(self, source: SourceText) -> str:
        lines: list[str] = []
        for diag in self.diagnostics:
            line_num, col = source.get_line_and_column(diag.span.start)
            line_idx = source.get_line_index(diag.span.start)
            line_text = source.get_line_text(line_idx)

            prefix = "ERROR" if diag.severity == DiagnosticSeverity.ERROR else "WARNING"
            lines.append(f"[{prefix}] {diag.message}")
            lines.append(f"  --> {source.file_name}:{line_num}:{col}")
            lines.append("   |")
            lines.append(f"{line_num:3d} | {line_text}")

            indent = " " * (col - 1)
            caret_len = max(1, min(diag.span.length, max(1, len(line_text) - (col - 1))))
            carets = "^" * caret_len
            lines.append(f"   | {indent}{carets}")

            if diag.suggestion:
                lines.append(f"   = suggestion: {diag.suggestion}")
            lines.append("")
        return "\n".join(lines).rstrip()
