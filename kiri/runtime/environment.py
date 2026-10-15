from __future__ import annotations
from typing import Any
from .values import KiriValue, KiriValueType

class KiriEnvironment:
    """Lexical scope / environment frame."""

    def __init__(self, parent: KiriEnvironment | None = None) -> None:
        self._bindings: dict[str, KiriValue] = {}
        self.parent = parent

    def define(self, name: str, value: KiriValue) -> None:
        """Define a new binding in this scope."""
        self._bindings[name] = value

    def assign(self, name: str, value: KiriValue) -> bool:
        """Walk up scope chain and assign to existing binding. Returns True if found."""
        if name in self._bindings:
            self._bindings[name] = value
            return True
        if self.parent is not None:
            return self.parent.assign(name, value)
        return False

    def set_or_assign(self, name: str, value: KiriValue) -> None:
        """Assign if exists anywhere in scope chain, otherwise define locally."""
        if not self.assign(name, value):
            self._bindings[name] = value

    def lookup(self, name: str) -> KiriValue | None:
        if name in self._bindings:
            return self._bindings[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        return None

    def try_lookup(self, name: str) -> tuple[bool, KiriValue]:
        v = self.lookup(name)
        if v is None:
            return False, KiriValue.null()
        return True, v

    def define_global(self, name: str, value: KiriValue) -> None:
        """Find root scope and define there."""
        root = self
        while root.parent is not None:
            root = root.parent
        root._bindings[name] = value

    def all_names(self) -> list[str]:
        names = list(self._bindings.keys())
        if self.parent:
            names.extend(self.parent.all_names())
        return list(set(names))
