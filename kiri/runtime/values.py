from __future__ import annotations
from enum import Enum, auto
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .environment import KiriEnvironment

class KiriValueType(Enum):
    NULL = auto()
    BOOL = auto()
    INT = auto()
    FLOAT = auto()
    STRING = auto()
    LIST = auto()
    TUPLE = auto()
    DICT = auto()
    SET = auto()
    RANGE = auto()
    FUNCTION = auto()
    BUILTIN_FUNCTION = auto()
    CLASS = auto()
    INSTANCE = auto()
    BOUND_METHOD = auto()
    MODULE = auto()
    ITERATOR = auto()

# ─── Signal exceptions for control flow ───────────────────────────────────────

class ReturnSignal(Exception):
    def __init__(self, value: KiriValue) -> None:
        self.value = value

class BreakSignal(Exception):
    pass

class ContinueSignal(Exception):
    pass

class KiriRuntimeError(Exception):
    def __init__(self, message: str, span: Any = None,
                 kiri_type: str = "RuntimeError") -> None:
        super().__init__(message)
        self.kiri_type = kiri_type
        self.span = span

class KiriException(Exception):
    """Raised by Kiri's `raise` statement. Carries a KiriValue (the exception object)."""
    def __init__(self, value: KiriValue, span: Any = None) -> None:
        super().__init__(str(value))
        self.value = value
        self.span = span

# ─── KiriValue ────────────────────────────────────────────────────────────────

class KiriValue:
    __slots__ = ('type', 'raw')

    def __init__(self, typ: KiriValueType, raw: Any) -> None:
        self.type = typ
        self.raw = raw

    # ── Factories ────────────────────────────────────────────────────────────

    @staticmethod
    def null() -> KiriValue:
        return _NULL

    @staticmethod
    def from_bool(v: bool) -> KiriValue:
        return _TRUE if v else _FALSE

    @staticmethod
    def from_int(v: int) -> KiriValue:
        return KiriValue(KiriValueType.INT, v)

    @staticmethod
    def from_float(v: float) -> KiriValue:
        return KiriValue(KiriValueType.FLOAT, v)

    @staticmethod
    def from_str(v: str) -> KiriValue:
        return KiriValue(KiriValueType.STRING, v)

    @staticmethod
    def from_list(v: list) -> KiriValue:
        return KiriValue(KiriValueType.LIST, v)

    @staticmethod
    def from_tuple(v: tuple) -> KiriValue:
        return KiriValue(KiriValueType.TUPLE, v)

    @staticmethod
    def from_dict(v: dict) -> KiriValue:
        return KiriValue(KiriValueType.DICT, v)

    @staticmethod
    def from_set(v: set) -> KiriValue:
        return KiriValue(KiriValueType.SET, v)

    @staticmethod
    def from_range(start: int, stop: int, step: int = 1) -> KiriValue:
        return KiriValue(KiriValueType.RANGE, range(start, stop, step))

    @staticmethod
    def from_function(fn: KiriFunction) -> KiriValue:
        return KiriValue(KiriValueType.FUNCTION, fn)

    @staticmethod
    def from_builtin(fn: KiriBuiltinFunction) -> KiriValue:
        return KiriValue(KiriValueType.BUILTIN_FUNCTION, fn)

    @staticmethod
    def from_class(cls: KiriClass) -> KiriValue:
        return KiriValue(KiriValueType.CLASS, cls)

    @staticmethod
    def from_instance(inst: KiriInstance) -> KiriValue:
        return KiriValue(KiriValueType.INSTANCE, inst)

    @staticmethod
    def from_module(mod: KiriModule) -> KiriValue:
        return KiriValue(KiriValueType.MODULE, mod)

    @staticmethod
    def from_iterator(it: Any) -> KiriValue:
        return KiriValue(KiriValueType.ITERATOR, it)

    @staticmethod
    def from_python(obj: Any) -> KiriValue:
        """Convert arbitrary Python value to KiriValue."""
        if obj is None: return _NULL
        if isinstance(obj, bool): return KiriValue.from_bool(obj)
        if isinstance(obj, int): return KiriValue.from_int(obj)
        if isinstance(obj, float): return KiriValue.from_float(obj)
        if isinstance(obj, str): return KiriValue.from_str(obj)
        if isinstance(obj, KiriValue): return obj
        if isinstance(obj, list):
            return KiriValue.from_list([KiriValue.from_python(x) for x in obj])
        if isinstance(obj, tuple):
            return KiriValue.from_tuple(tuple(KiriValue.from_python(x) for x in obj))
        if isinstance(obj, dict):
            return KiriValue.from_dict({KiriValue.from_python(k): KiriValue.from_python(v) for k, v in obj.items()})
        if isinstance(obj, set):
            return KiriValue.from_set({KiriValue.from_python(x) for x in obj})
        return KiriValue.from_str(str(obj))

    # ── Truth ─────────────────────────────────────────────────────────────────

    @property
    def is_truthy(self) -> bool:
        t = self.type
        if t == KiriValueType.NULL: return False
        if t == KiriValueType.BOOL: return self.raw
        if t == KiriValueType.INT: return self.raw != 0
        if t == KiriValueType.FLOAT: return self.raw != 0.0
        if t == KiriValueType.STRING: return len(self.raw) > 0
        if t == KiriValueType.LIST: return len(self.raw) > 0
        if t == KiriValueType.TUPLE: return len(self.raw) > 0
        if t == KiriValueType.DICT: return len(self.raw) > 0
        if t == KiriValueType.SET: return len(self.raw) > 0
        if t == KiriValueType.RANGE: return len(self.raw) > 0
        return True

    # ── Type name ─────────────────────────────────────────────────────────────

    @property
    def type_name(self) -> str:
        t = self.type
        if t == KiriValueType.NULL: return "Null"
        if t == KiriValueType.BOOL: return "Bool"
        if t == KiriValueType.INT: return "Int"
        if t == KiriValueType.FLOAT: return "Float"
        if t == KiriValueType.STRING: return "String"
        if t == KiriValueType.LIST: return "List"
        if t == KiriValueType.TUPLE: return "Tuple"
        if t == KiriValueType.DICT: return "Dict"
        if t == KiriValueType.SET: return "Set"
        if t == KiriValueType.RANGE: return "Range"
        if t == KiriValueType.FUNCTION: return self.raw.name
        if t == KiriValueType.BUILTIN_FUNCTION: return self.raw.name
        if t == KiriValueType.CLASS: return self.raw.name
        if t == KiriValueType.INSTANCE: return self.raw.klass.name
        if t == KiriValueType.BOUND_METHOD: return "BoundMethod"
        if t == KiriValueType.MODULE: return f"Module({self.raw.name})"
        if t == KiriValueType.ITERATOR: return "Iterator"
        return "Unknown"

    # ── Accessors ─────────────────────────────────────────────────────────────

    def as_int(self) -> int: return self.raw
    def as_float(self) -> float: return self.raw
    def as_str(self) -> str: return self.raw
    def as_bool(self) -> bool: return self.raw
    def as_list(self) -> list: return self.raw
    def as_tuple(self) -> tuple: return self.raw
    def as_dict(self) -> dict: return self.raw
    def as_set(self) -> set: return self.raw
    def as_function(self) -> KiriFunction: return self.raw
    def as_builtin(self) -> KiriBuiltinFunction: return self.raw
    def as_class(self) -> KiriClass: return self.raw
    def as_instance(self) -> KiriInstance: return self.raw
    def as_module(self) -> KiriModule: return self.raw

    # ── Hash / Equality for use as dict keys ─────────────────────────────────

    def __hash__(self) -> int:
        try:
            return hash(self._hashable())
        except TypeError:
            raise KiriRuntimeError(f"TypeError: unhashable type: '{self.type_name}'")

    def _hashable(self) -> Any:
        t = self.type
        if t in (KiriValueType.NULL, KiriValueType.BOOL, KiriValueType.INT,
                 KiriValueType.FLOAT, KiriValueType.STRING):
            return self.raw
        if t == KiriValueType.TUPLE:
            return self.raw  # tuple of KiriValues must themselves be hashable
        raise TypeError(f"unhashable type: '{self.type_name}'")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, KiriValue):
            return False
        if self.type != other.type:
            # numeric cross-type equality
            if self.type in (KiriValueType.INT, KiriValueType.FLOAT) and \
               other.type in (KiriValueType.INT, KiriValueType.FLOAT):
                return self._as_numeric() == other._as_numeric()
            return False
        return self.raw == other.raw

    def _as_numeric(self) -> float:
        if self.type == KiriValueType.INT: return float(self.raw)
        return self.raw

    # ── String representations ────────────────────────────────────────────────

    def to_str(self) -> str:
        """User-facing str() conversion."""
        t = self.type
        if t == KiriValueType.NULL: return "null"
        if t == KiriValueType.BOOL: return "true" if self.raw else "false"
        if t == KiriValueType.INT: return str(self.raw)
        if t == KiriValueType.FLOAT:
            s = repr(self.raw)
            if '.' not in s and 'e' not in s: s += '.0'
            return s
        if t == KiriValueType.STRING: return self.raw
        if t == KiriValueType.LIST:
            return "[" + ", ".join(v.to_repr() for v in self.raw) + "]"
        if t == KiriValueType.TUPLE:
            if len(self.raw) == 1: return "(" + self.raw[0].to_repr() + ",)"
            return "(" + ", ".join(v.to_repr() for v in self.raw) + ")"
        if t == KiriValueType.DICT:
            pairs = ", ".join(f"{k.to_repr()}: {v.to_repr()}" for k, v in self.raw.items())
            return "{" + pairs + "}"
        if t == KiriValueType.SET:
            if not self.raw: return "set()"
            return "{" + ", ".join(v.to_repr() for v in self.raw) + "}"
        if t == KiriValueType.RANGE:
            r = self.raw
            if r.step == 1: return f"range({r.start}, {r.stop})"
            return f"range({r.start}, {r.stop}, {r.step})"
        if t == KiriValueType.INSTANCE:
            inst = self.raw
            if "__str__" in inst.fields:
                fn = inst.fields["__str__"]
                if fn.type in (KiriValueType.FUNCTION, KiriValueType.BOUND_METHOD, KiriValueType.BUILTIN_FUNCTION):
                    result = fn.raw.call([], None)
                    if isinstance(result, KiriValue):
                        return result.to_str()
            return f"<{inst.klass.name} instance>"
        if t == KiriValueType.CLASS: return f"<class '{self.raw.name}'>"
        if t == KiriValueType.FUNCTION: return f"<function '{self.raw.name}'>"
        if t == KiriValueType.BUILTIN_FUNCTION: return f"<builtin '{self.raw.name}'>"
        if t == KiriValueType.MODULE: return f"<module '{self.raw.name}'>"
        return repr(self.raw)

    def to_repr(self) -> str:
        """repr() — suitable for REPL display."""
        if self.type == KiriValueType.STRING:
            return repr(self.raw)
        return self.to_str()

    def __repr__(self) -> str:
        return self.to_str()

    def __str__(self) -> str:
        return self.to_str()


# ─── Singletons ───────────────────────────────────────────────────────────────
_NULL  = KiriValue(KiriValueType.NULL, None)
_TRUE  = KiriValue(KiriValueType.BOOL, True)
_FALSE = KiriValue(KiriValueType.BOOL, False)


# ─── Function types ───────────────────────────────────────────────────────────

class KiriFunction:
    def __init__(self, name: str, params: list, return_type: Any, body: Any,
                 closure: KiriEnvironment, is_async: bool = False) -> None:
        self.name = name
        self.params = params
        self.return_type = return_type
        self.body = body
        self.closure = closure
        self.is_async = is_async

class KiriBuiltinFunction:
    def __init__(self, name: str,
                 impl: Callable[[list[KiriValue], KiriEnvironment | None], KiriValue]) -> None:
        self.name = name
        self.impl = impl

    def call(self, args: list[KiriValue], env: KiriEnvironment | None) -> KiriValue:
        return self.impl(args, env)


# ─── Class & Instance ─────────────────────────────────────────────────────────

class KiriClass:
    def __init__(self, name: str, bases: list[KiriClass], methods: dict[str, KiriValue]) -> None:
        self.name = name
        self.bases = bases
        self.methods = methods  # method name -> KiriValue(FUNCTION)

    def lookup_method(self, name: str) -> KiriValue | None:
        if name in self.methods:
            return self.methods[name]
        for base in self.bases:
            m = base.lookup_method(name)
            if m is not None:
                return m
        return None

class KiriInstance:
    def __init__(self, klass: KiriClass) -> None:
        self.klass = klass
        self.fields: dict[str, KiriValue] = {}

    def get_attr(self, name: str) -> KiriValue | None:
        if name in self.fields:
            return self.fields[name]
        method = self.klass.lookup_method(name)
        if method is not None:
            # Return a bound method
            inst_val = KiriValue(KiriValueType.INSTANCE, self)
            return KiriValue(KiriValueType.BOUND_METHOD, BoundMethod(inst_val, method))
        return None

    def set_attr(self, name: str, value: KiriValue) -> None:
        self.fields[name] = value

class BoundMethod:
    def __init__(self, instance: KiriValue, method: KiriValue) -> None:
        self.instance = instance
        self.method = method
        self.name = getattr(getattr(method, 'raw', None), 'name', '<method>')


# ─── Module ───────────────────────────────────────────────────────────────────

class KiriModule:
    def __init__(self, name: str, env: KiriEnvironment) -> None:
        self.name = name
        self.env = env
