"""Kiri-Language runtime and interpreter."""

from .interpreter import KiriInterpreter


def run_source(source: str) -> str:
    """Execute a Kiri source string and return captured output."""
    interpreter = KiriInterpreter()
    return interpreter.run_source(source)


__all__ = ["KiriInterpreter", "run_source"]
