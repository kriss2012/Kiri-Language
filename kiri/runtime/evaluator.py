from __future__ import annotations
import math
import os
import sys
import time
from pathlib import Path
from typing import Any, Iterator

from ..compiler.ast import *
from ..compiler.tokens import SyntaxKind
from ..compiler.diagnostics import TextSpan
from .values import (
    KiriValue, KiriValueType, KiriFunction, KiriBuiltinFunction,
    KiriClass, KiriInstance, BoundMethod, KiriModule,
    ReturnSignal, BreakSignal, ContinueSignal, KiriRuntimeError, KiriException,
)
from .environment import KiriEnvironment


class Evaluator:
    """Tree-walking interpreter for Kiri Phase 2."""

    def __init__(self, source: Any, diagnostics: Any = None,
                 output: Any = None, global_env: KiriEnvironment | None = None,
                 kiri_home: Path | None = None) -> None:
        self._source = source
        self._diagnostics = diagnostics
        self._output = output or sys.stdout
        self._kiri_home = kiri_home or Path(__file__).resolve().parent.parent.parent
        self._loaded_modules: dict[str, KiriValue] = {}
        self.global_env: KiriEnvironment = global_env or self._create_default_env()
        self._start_time = time.perf_counter()

    # ─── Default environment ──────────────────────────────────────────────────

    def _create_default_env(self) -> KiriEnvironment:
        env = KiriEnvironment()
        b = KiriValue.from_builtin

        def _builtin(name: str, fn):
            env.define(name, b(KiriBuiltinFunction(name, fn)))

        # ── I/O ──────────────────────────────────────────────────────────────
        def _print(args, _):
            print(" ".join(v.to_str() for v in args), file=self._output)
            return KiriValue.null()
        _builtin("print", _print)

        def _input(args, _):
            prompt = args[0].to_str() if args else ""
            try:
                return KiriValue.from_str(input(prompt))
            except EOFError:
                return KiriValue.from_str("")
        _builtin("input", _input)

        # ── Type conversion ───────────────────────────────────────────────────
        def _int(args, _):
            if not args: return KiriValue.from_int(0)
            v = args[0]
            base = args[1].as_int() if len(args) > 1 else 10
            if v.type == KiriValueType.INT: return v
            if v.type == KiriValueType.FLOAT: return KiriValue.from_int(int(v.as_float()))
            if v.type == KiriValueType.BOOL: return KiriValue.from_int(1 if v.as_bool() else 0)
            if v.type == KiriValueType.STRING:
                try: return KiriValue.from_int(int(v.as_str(), base))
                except ValueError: raise KiriRuntimeError(f"ValueError: invalid literal for int(): '{v.as_str()}'", kiri_type="ValueError")
            raise KiriRuntimeError(f"TypeError: int() argument must be a string or number, not '{v.type_name}'", kiri_type="TypeError")
        _builtin("int", _int)

        def _float(args, _):
            if not args: return KiriValue.from_float(0.0)
            v = args[0]
            if v.type == KiriValueType.FLOAT: return v
            if v.type == KiriValueType.INT: return KiriValue.from_float(float(v.as_int()))
            if v.type == KiriValueType.BOOL: return KiriValue.from_float(1.0 if v.as_bool() else 0.0)
            if v.type == KiriValueType.STRING:
                try: return KiriValue.from_float(float(v.as_str()))
                except ValueError: raise KiriRuntimeError(f"ValueError: could not convert string to float: '{v.as_str()}'", kiri_type="ValueError")
            raise KiriRuntimeError(f"TypeError: float() argument must be a string or number, not '{v.type_name}'", kiri_type="TypeError")
        _builtin("float", _float)

        def _str(args, _):
            if not args: return KiriValue.from_str("")
            return KiriValue.from_str(args[0].to_str())
        _builtin("str", _str)

        def _bool(args, _):
            if not args: return KiriValue.from_bool(False)
            return KiriValue.from_bool(args[0].is_truthy)
        _builtin("bool", _bool)

        def _list(args, _):
            if not args: return KiriValue.from_list([])
            v = args[0]
            if v.type == KiriValueType.LIST: return KiriValue.from_list(list(v.as_list()))
            if v.type == KiriValueType.TUPLE: return KiriValue.from_list(list(v.as_tuple()))
            if v.type == KiriValueType.SET: return KiriValue.from_list(list(v.as_set()))
            if v.type == KiriValueType.RANGE: return KiriValue.from_list([KiriValue.from_int(i) for i in v.raw])
            if v.type == KiriValueType.STRING: return KiriValue.from_list([KiriValue.from_str(c) for c in v.as_str()])
            if v.type == KiriValueType.DICT: return KiriValue.from_list(list(v.as_dict().keys()))
            raise KiriRuntimeError(f"TypeError: '{v.type_name}' object is not iterable", kiri_type="TypeError")
        _builtin("list", _list)

        def _tuple(args, _):
            if not args: return KiriValue.from_tuple(())
            v = args[0]
            return KiriValue.from_tuple(tuple(_iterate_value(v)))
        _builtin("tuple", _tuple)

        def _set(args, _):
            if not args: return KiriValue.from_set(set())
            return KiriValue.from_set(set(_iterate_value(args[0])))
        _builtin("set", _set)

        def _dict(args, _):
            if not args: return KiriValue.from_dict({})
            v = args[0]
            if v.type == KiriValueType.DICT: return KiriValue.from_dict(dict(v.as_dict()))
            raise KiriRuntimeError("TypeError: dict() argument must be a mapping", kiri_type="TypeError")
        _builtin("dict", _dict)

        # ── Inspection ────────────────────────────────────────────────────────
        def _type(args, _):
            if not args: raise KiriRuntimeError("TypeError: type() requires 1 argument")
            return KiriValue.from_str(args[0].type_name)
        _builtin("type", _type)

        def _isinstance(args, _):
            if len(args) < 2: raise KiriRuntimeError("TypeError: isinstance() requires 2 arguments")
            obj, cls = args[0], args[1]
            if cls.type == KiriValueType.CLASS:
                if obj.type == KiriValueType.INSTANCE:
                    inst_klass = obj.as_instance().klass
                    return KiriValue.from_bool(_is_subclass(inst_klass, cls.as_class()))
                return KiriValue.from_bool(False)
            # Type names match
            return KiriValue.from_bool(obj.type_name == cls.to_str())
        _builtin("isinstance", _isinstance)

        def _hasattr(args, _):
            if len(args) < 2: raise KiriRuntimeError("TypeError: hasattr() requires 2 arguments")
            obj, name = args[0], args[1].to_str()
            if obj.type == KiriValueType.INSTANCE:
                return KiriValue.from_bool(obj.as_instance().get_attr(name) is not None)
            if obj.type == KiriValueType.MODULE:
                found, _ = obj.as_module().env.try_lookup(name)
                return KiriValue.from_bool(found)
            return KiriValue.from_bool(False)
        _builtin("hasattr", _hasattr)

        def _getattr(args, _):
            if len(args) < 2: raise KiriRuntimeError("TypeError: getattr() requires 2 or 3 arguments")
            obj, name = args[0], args[1].to_str()
            default = args[2] if len(args) >= 3 else None
            if obj.type == KiriValueType.INSTANCE:
                val = obj.as_instance().get_attr(name)
                if val is not None: return val
            if obj.type == KiriValueType.MODULE:
                found, val = obj.as_module().env.try_lookup(name)
                if found: return val
            if default is not None: return default
            raise KiriRuntimeError(f"AttributeError: '{obj.type_name}' has no attribute '{name}'", kiri_type="AttributeError")
        _builtin("getattr", _getattr)

        def _setattr(args, _):
            if len(args) < 3: raise KiriRuntimeError("TypeError: setattr() requires 3 arguments")
            obj, name, value = args[0], args[1].to_str(), args[2]
            if obj.type == KiriValueType.INSTANCE:
                obj.as_instance().set_attr(name, value)
                return KiriValue.null()
            raise KiriRuntimeError(f"TypeError: '{obj.type_name}' does not support attribute assignment", kiri_type="TypeError")
        _builtin("setattr", _setattr)

        # ── Collections ────────────────────────────────────────────────────────
        def _len(args, _):
            if len(args) != 1: raise KiriRuntimeError(f"TypeError: len() takes 1 argument ({len(args)} given)")
            v = args[0]
            if v.type == KiriValueType.STRING: return KiriValue.from_int(len(v.as_str()))
            if v.type in (KiriValueType.LIST, KiriValueType.TUPLE, KiriValueType.SET,
                          KiriValueType.DICT): return KiriValue.from_int(len(v.raw))
            if v.type == KiriValueType.RANGE: return KiriValue.from_int(len(v.raw))
            raise KiriRuntimeError(f"TypeError: object of type '{v.type_name}' has no len()", kiri_type="TypeError")
        _builtin("len", _len)

        def _range(args, _):
            if not args: raise KiriRuntimeError("TypeError: range() requires at least 1 argument")
            if len(args) == 1:
                stop = args[0].as_int()
                return KiriValue.from_range(0, stop)
            if len(args) == 2:
                return KiriValue.from_range(args[0].as_int(), args[1].as_int())
            return KiriValue.from_range(args[0].as_int(), args[1].as_int(), args[2].as_int())
        _builtin("range", _range)

        def _enumerate(args, _):
            if not args: raise KiriRuntimeError("TypeError: enumerate() requires at least 1 argument")
            start = args[1].as_int() if len(args) > 1 else 0
            items = list(_iterate_value(args[0]))
            result = [KiriValue.from_tuple((KiriValue.from_int(i + start), v))
                      for i, v in enumerate(items)]
            return KiriValue.from_list(result)
        _builtin("enumerate", _enumerate)

        def _zip(args, _):
            if not args: return KiriValue.from_list([])
            iters = [list(_iterate_value(a)) for a in args]
            min_len = min(len(it) for it in iters)
            result = [KiriValue.from_tuple(tuple(iters[j][i] for j in range(len(iters))))
                      for i in range(min_len)]
            return KiriValue.from_list(result)
        _builtin("zip", _zip)

        def _map(args, _):
            if len(args) < 2: raise KiriRuntimeError("TypeError: map() requires at least 2 arguments")
            fn, iterable = args[0], args[1]
            result = [self._call_value(fn, [v], None) for v in _iterate_value(iterable)]
            return KiriValue.from_list(result)
        _builtin("map", _map)

        def _filter(args, _):
            if len(args) < 2: raise KiriRuntimeError("TypeError: filter() requires 2 arguments")
            fn, iterable = args[0], args[1]
            result = [v for v in _iterate_value(iterable) if self._call_value(fn, [v], None).is_truthy]
            return KiriValue.from_list(result)
        _builtin("filter", _filter)

        def _sorted(args, _):
            if not args: raise KiriRuntimeError("TypeError: sorted() requires at least 1 argument")
            items = list(_iterate_value(args[0]))
            reverse = False
            key_fn = None
            for i in range(1, len(args)):
                if args[i].type_name == "Bool":
                    reverse = args[i].as_bool()
            try:
                items_sorted = sorted(items, reverse=reverse)
            except TypeError:
                items_sorted = items
            return KiriValue.from_list(items_sorted)
        _builtin("sorted", _sorted)

        def _reversed(args, _):
            if not args: raise KiriRuntimeError("TypeError: reversed() requires 1 argument")
            items = list(_iterate_value(args[0]))
            return KiriValue.from_list(list(reversed(items)))
        _builtin("reversed", _reversed)

        def _sum(args, _):
            if not args: raise KiriRuntimeError("TypeError: sum() requires at least 1 argument")
            items = list(_iterate_value(args[0]))
            start = args[1] if len(args) > 1 else KiriValue.from_int(0)
            total = start
            for item in items:
                total = _add(total, item, None)
            return total
        _builtin("sum", _sum)

        def _min(args, _):
            if not args: raise KiriRuntimeError("TypeError: min() requires at least 1 argument")
            if len(args) == 1:
                items = list(_iterate_value(args[0]))
            else:
                items = args
            if not items: raise KiriRuntimeError("ValueError: min() arg is an empty sequence", kiri_type="ValueError")
            result = items[0]
            for item in items[1:]:
                if _compare(item, result, None) < 0: result = item
            return result
        _builtin("min", _min)

        def _max(args, _):
            if not args: raise KiriRuntimeError("TypeError: max() requires at least 1 argument")
            if len(args) == 1:
                items = list(_iterate_value(args[0]))
            else:
                items = args
            if not items: raise KiriRuntimeError("ValueError: max() arg is an empty sequence", kiri_type="ValueError")
            result = items[0]
            for item in items[1:]:
                if _compare(item, result, None) > 0: result = item
            return result
        _builtin("max", _max)

        def _abs(args, _):
            if not args: raise KiriRuntimeError("TypeError: abs() requires 1 argument")
            v = args[0]
            if v.type == KiriValueType.INT: return KiriValue.from_int(abs(v.as_int()))
            if v.type == KiriValueType.FLOAT: return KiriValue.from_float(abs(v.as_float()))
            raise KiriRuntimeError(f"TypeError: bad operand type for abs(): '{v.type_name}'", kiri_type="TypeError")
        _builtin("abs", _abs)

        def _round(args, _):
            if not args: raise KiriRuntimeError("TypeError: round() requires at least 1 argument")
            v = args[0]
            n = args[1].as_int() if len(args) > 1 else 0
            num = v.as_float() if v.type == KiriValueType.FLOAT else float(v.as_int())
            result = round(num, n)
            if n <= 0: return KiriValue.from_int(int(result))
            return KiriValue.from_float(result)
        _builtin("round", _round)

        def _pow(args, _):
            if len(args) < 2: raise KiriRuntimeError("TypeError: pow() requires 2 or 3 arguments")
            base_v = args[0]
            exp_v = args[1]
            if base_v.type == KiriValueType.INT and exp_v.type == KiriValueType.INT:
                result = args[0].as_int() ** args[1].as_int()
                if len(args) > 2: result %= args[2].as_int()
                return KiriValue.from_int(result)
            b = float(base_v.as_int() if base_v.type == KiriValueType.INT else base_v.as_float())
            e = float(exp_v.as_int() if exp_v.type == KiriValueType.INT else exp_v.as_float())
            return KiriValue.from_float(b ** e)
        _builtin("pow", _pow)

        # ── Strings ───────────────────────────────────────────────────────────
        def _ord(args, _):
            if not args: raise KiriRuntimeError("TypeError: ord() requires 1 argument")
            s = args[0].to_str()
            if len(s) != 1: raise KiriRuntimeError("TypeError: ord() expected a character, but string of length != 1 found", kiri_type="TypeError")
            return KiriValue.from_int(ord(s))
        _builtin("ord", _ord)

        def _chr(args, _):
            if not args: raise KiriRuntimeError("TypeError: chr() requires 1 argument")
            return KiriValue.from_str(chr(args[0].as_int()))
        _builtin("chr", _chr)

        def _hex(args, _):
            if not args: raise KiriRuntimeError("TypeError: hex() requires 1 argument")
            return KiriValue.from_str(hex(args[0].as_int()))
        _builtin("hex", _hex)

        def _bin(args, _):
            if not args: raise KiriRuntimeError("TypeError: bin() requires 1 argument")
            return KiriValue.from_str(bin(args[0].as_int()))
        _builtin("bin", _bin)

        def _repr(args, _):
            if not args: raise KiriRuntimeError("TypeError: repr() requires 1 argument")
            return KiriValue.from_str(args[0].to_repr())
        _builtin("repr", _repr)

        # ── Assertions / debugging ─────────────────────────────────────────────
        def _assert(args, _):
            if len(args) < 1: raise KiriRuntimeError("TypeError: assert() requires at least 1 argument")
            if not args[0].is_truthy:
                msg = args[1].to_str() if len(args) > 1 else "Assertion failed."
                raise KiriRuntimeError(msg, kiri_type="AssertionError")
            return KiriValue.null()
        _builtin("assert", _assert)

        def _clock(args, _):
            return KiriValue.from_float(time.perf_counter() - self._start_time)
        _builtin("clock", _clock)

        # ── Misc ──────────────────────────────────────────────────────────────
        def _any(args, _):
            if not args: raise KiriRuntimeError("TypeError: any() requires 1 argument")
            return KiriValue.from_bool(any(v.is_truthy for v in _iterate_value(args[0])))
        _builtin("any", _any)

        def _all(args, _):
            if not args: raise KiriRuntimeError("TypeError: all() requires 1 argument")
            return KiriValue.from_bool(all(v.is_truthy for v in _iterate_value(args[0])))
        _builtin("all", _all)

        def _id(args, _):
            if not args: raise KiriRuntimeError("TypeError: id() requires 1 argument")
            return KiriValue.from_int(id(args[0]))
        _builtin("id", _id)

        def _hash_fn(args, _):
            if not args: raise KiriRuntimeError("TypeError: hash() requires 1 argument")
            try: return KiriValue.from_int(hash(args[0]))
            except KiriRuntimeError as e: raise e
        _builtin("hash", _hash_fn)

        def _iter(args, _):
            if not args: raise KiriRuntimeError("TypeError: iter() requires 1 argument")
            return KiriValue.from_iterator(iter(_iterate_value(args[0])))
        _builtin("iter", _iter)

        def _next(args, _):
            if not args: raise KiriRuntimeError("TypeError: next() requires 1 argument")
            it = args[0].raw
            try:
                return next(it)
            except StopIteration:
                if len(args) > 1: return args[1]
                raise KiriException(_make_exception_instance("StopIteration", "StopIteration"))
        _builtin("next", _next)

        def _exit(args, _):
            code = args[0].as_int() if args and args[0].type == KiriValueType.INT else 0
            sys.exit(code)
        _builtin("exit", _exit)
        _builtin("quit", _exit)

        # Exception constructors
        for exc_name in ["Exception", "RuntimeError", "ValueError", "TypeError",
                         "KeyError", "IndexError", "AttributeError", "NameError",
                         "NotImplementedError", "StopIteration", "IOError",
                         "OSError", "ImportError", "AssertionError", "ZeroDivisionError",
                         "OverflowError", "RecursionError"]:
            _register_exception_class(env, exc_name)

        return env

    # ─── Evaluation entry points ──────────────────────────────────────────────

    def evaluate(self, compilation_unit: CompilationUnit) -> KiriValue:
        last = KiriValue.null()
        try:
            for stmt in compilation_unit.statements:
                last = self.eval_statement(stmt, self.global_env)
        except ReturnSignal as r:
            self._report_error(TextSpan(0, 0), "SyntaxError: 'return' outside function.")
            return r.value
        except KiriRuntimeError as e:
            self._report_error(getattr(e, 'span', None) or TextSpan(0, 0), str(e))
        except KiriException as e:
            self._report_error(getattr(e, 'span', None) or TextSpan(0, 0),
                               f"Unhandled {e.value.type_name}: {e.value.to_str()}")
        return last

    def _report_error(self, span: Any, message: str) -> None:
        if self._diagnostics:
            self._diagnostics.report_error(span, message)
        else:
            print(f"Error: {message}", file=sys.stderr)

    # ─── Statements ───────────────────────────────────────────────────────────

    def eval_statement(self, stmt: StatementSyntax, env: KiriEnvironment) -> KiriValue:
        match stmt:
            case ExprStmt(_, expr):
                return self.eval_expr(expr, env)

            case VarDeclStmt(_, name_tok, name, _, initializer):
                val = self.eval_expr(initializer, env)
                env.set_or_assign(name, val)
                return val

            case AssignStmt(_, target, value):
                val = self.eval_expr(value, env)
                self._assign_target(target, val, env)
                return val

            case AugAssignStmt(_, target, op, value):
                return self._eval_aug_assign(target, op, value, env)

            case FuncDeclStmt(span, name_tok, name, params, return_type, body, decorators, is_async):
                fn = KiriFunction(name, params, return_type, body, env, is_async)
                fn_val = KiriValue.from_function(fn)
                # Apply decorators in reverse
                for dec_expr in reversed(decorators):
                    dec = self.eval_expr(dec_expr, env)
                    fn_val = self._call_value(dec, [fn_val], env)
                env.define(name, fn_val)
                return fn_val

            case ClassDeclStmt(span, name_tok, name, bases, body, decorators):
                return self._eval_class_decl(name, bases, body, decorators, env)

            case IfStmt(_, cond, then_block, elif_clauses, else_clause):
                return self._eval_if(cond, then_block, elif_clauses, else_clause, env)

            case WhileStmt(_, cond, body, else_clause):
                return self._eval_while(cond, body, else_clause, env)

            case ForStmt(_, target, target_tok, iterable, body, else_clause):
                return self._eval_for(target, iterable, body, else_clause, env)

            case ReturnStmt(_, ret_kw, expr):
                val = self.eval_expr(expr, env) if expr else KiriValue.null()
                raise ReturnSignal(val)

            case BreakStmt(_, _):
                raise BreakSignal()

            case ContinueStmt(_, _):
                raise ContinueSignal()

            case RaiseStmt(_, _, expr):
                if expr:
                    val = self.eval_expr(expr, env)
                    raise KiriException(val, stmt.span)
                raise KiriException(KiriValue.from_str("RuntimeError"), stmt.span)

            case TryStmt(_, try_body, except_clauses, else_clause, finally_body):
                return self._eval_try(try_body, except_clauses, else_clause, finally_body, env)

            case ImportStmt(_, _, module_name, _, alias_name):
                return self._eval_import(module_name, alias_name, env)

            case FromImportStmt(_, module_name, names, star):
                return self._eval_from_import(module_name, names, star, env)

            case DeleteStmt(_, target):
                self._eval_delete(target, env)
                return KiriValue.null()

            case AssertStmt(_, condition, message):
                cond_val = self.eval_expr(condition, env)
                if not cond_val.is_truthy:
                    msg = self.eval_expr(message, env).to_str() if message else "AssertionError"
                    raise KiriException(_make_exception_instance("AssertionError", msg), stmt.span)
                return KiriValue.null()

            case GlobalStmt(_, names):
                # Note global names — for now just mark in env (full global scoping in Phase 3)
                return KiriValue.null()

            case NonlocalStmt(_, names):
                return KiriValue.null()

            case WithStmt(_, ctx_expr, alias, body):
                return self._eval_with(ctx_expr, alias, body, env)

            case PassStmt(_, _):
                return KiriValue.null()

            case BlockStmt(_, stmts):
                return self._eval_block(stmt, env)

            case _:
                raise KiriRuntimeError(f"Unknown statement type: {type(stmt).__name__}", stmt.span)

    def _eval_block(self, block: BlockStmt, env: KiriEnvironment) -> KiriValue:
        last = KiriValue.null()
        for s in block.statements:
            last = self.eval_statement(s, env)
        return last

    def _assign_target(self, target: ExpressionSyntax, value: KiriValue, env: KiriEnvironment) -> None:
        if isinstance(target, IdentifierExpr):
            env.set_or_assign(target.name, value)
        elif isinstance(target, MemberAccessExpr):
            obj = self.eval_expr(target.target, env)
            if obj.type == KiriValueType.INSTANCE:
                obj.as_instance().set_attr(target.member_name, value)
            elif obj.type == KiriValueType.MODULE:
                obj.as_module().env.define(target.member_name, value)
            else:
                raise KiriRuntimeError(f"AttributeError: '{obj.type_name}' object has no attribute '{target.member_name}'",
                                        target.span, kiri_type="AttributeError")
        elif isinstance(target, IndexExpr):
            obj = self.eval_expr(target.target, env)
            idx = self.eval_expr(target.index, env)
            _set_index(obj, idx, value, target.span)
        else:
            raise KiriRuntimeError(f"SyntaxError: Cannot assign to {type(target).__name__}", target.span)

    def _eval_aug_assign(self, target: ExpressionSyntax, op: Any, value_expr: ExpressionSyntax,
                          env: KiriEnvironment) -> KiriValue:
        current = self.eval_expr(target, env)
        operand = self.eval_expr(value_expr, env)
        op_kind = op.kind
        result: KiriValue
        span = op.span

        if op_kind == SyntaxKind.PLUS_EQUAL:
            result = _add(current, operand, span)
        elif op_kind == SyntaxKind.MINUS_EQUAL:
            result = _subtract(current, operand, span)
        elif op_kind == SyntaxKind.STAR_EQUAL:
            result = _multiply(current, operand, span)
        elif op_kind == SyntaxKind.SLASH_EQUAL:
            result = _divide(current, operand, span)
        elif op_kind == SyntaxKind.PERCENT_EQUAL:
            result = _modulo(current, operand, span)
        elif op_kind == SyntaxKind.STAR_STAR_EQUAL:
            result = _power(current, operand, span)
        else:
            raise KiriRuntimeError(f"Unsupported augmented assignment operator '{op.text}'", span)

        self._assign_target(target, result, env)
        return result

    def _eval_if(self, cond_expr, then_block, elif_clauses, else_clause, env):
        cond = self.eval_expr(cond_expr, env)
        if cond.is_truthy:
            return self._eval_block(then_block, env)
        for elif_clause in elif_clauses:
            if self.eval_expr(elif_clause.condition, env).is_truthy:
                return self._eval_block(elif_clause.block, env)
        if else_clause:
            return self._eval_block(else_clause.block, env)
        return KiriValue.null()

    def _eval_while(self, cond_expr, body, else_clause, env):
        last = KiriValue.null()
        ran_once = False
        while self.eval_expr(cond_expr, env).is_truthy:
            ran_once = True
            try:
                last = self._eval_block(body, env)
            except BreakSignal:
                return last
            except ContinueSignal:
                continue
        if else_clause and not ran_once:
            last = self._eval_block(else_clause.block, env)
        return last

    def _eval_for(self, target_name: str, iterable_expr, body, else_clause, env):
        iterable = self.eval_expr(iterable_expr, env)
        last = KiriValue.null()
        broke = False
        try:
            for item in _iterate_value(iterable):
                loop_env = KiriEnvironment(env)
                loop_env.define(target_name, item)
                try:
                    last = self._eval_block(body, loop_env)
                except ContinueSignal:
                    continue
                except BreakSignal:
                    broke = True
                    break
        except KiriRuntimeError:
            raise
        if else_clause and not broke:
            last = self._eval_block(else_clause.block, env)
        return last

    def _eval_try(self, try_body, except_clauses, else_clause, finally_body, env):
        last = KiriValue.null()
        caught = False
        try:
            last = self._eval_block(try_body, env)
            if else_clause:
                last = self._eval_block(else_clause.block, env)
        except KiriException as e:
            caught = True
            for clause in except_clauses:
                if clause.exception_type is None or self._matches_exception(e.value, clause.exception_type, env):
                    handler_env = KiriEnvironment(env)
                    if clause.alias:
                        handler_env.define(clause.alias, e.value)
                    last = self._eval_block(clause.body, handler_env)
                    caught = True
                    break
            else:
                if not caught:
                    if finally_body:
                        self._eval_block(finally_body, env)
                    raise
        except KiriRuntimeError as e:
            caught = True
            exc_val = _make_exception_instance(e.kiri_type, str(e))
            for clause in except_clauses:
                if clause.exception_type is None or self._matches_exception(exc_val, clause.exception_type, env):
                    handler_env = KiriEnvironment(env)
                    if clause.alias:
                        handler_env.define(clause.alias, exc_val)
                    last = self._eval_block(clause.body, handler_env)
                    caught = True
                    break
            else:
                if not caught:
                    if finally_body:
                        self._eval_block(finally_body, env)
                    raise
        finally:
            if finally_body:
                self._eval_block(finally_body, env)
        return last

    def _matches_exception(self, exc_val: KiriValue, exc_type_expr: ExpressionSyntax, env: KiriEnvironment) -> bool:
        try:
            exc_type = self.eval_expr(exc_type_expr, env)
        except Exception:
            return True
        if exc_type.type == KiriValueType.CLASS:
            if exc_val.type == KiriValueType.INSTANCE:
                return _is_subclass(exc_val.as_instance().klass, exc_type.as_class())
        # Match by type name
        return exc_val.type_name == exc_type.to_str() or exc_val.type_name == "Exception"

    def _eval_class_decl(self, name, base_exprs, body, decorators, env):
        bases: list[KiriClass] = []
        for bexpr in base_exprs:
            bval = self.eval_expr(bexpr, env)
            if bval.type == KiriValueType.CLASS:
                bases.append(bval.as_class())

        # Execute class body in a fresh scope
        class_env = KiriEnvironment(env)
        for stmt in body.statements:
            try:
                self.eval_statement(stmt, class_env)
            except ReturnSignal:
                pass

        # Collect methods from class_env
        methods: dict[str, KiriValue] = {}
        for n, v in class_env._bindings.items():
            if v.type in (KiriValueType.FUNCTION, KiriValueType.BUILTIN_FUNCTION):
                methods[n] = v
            else:
                methods[n] = v  # class variables

        klass = KiriClass(name, bases, methods)
        klass_val = KiriValue.from_class(klass)

        # Apply decorators
        for dec_expr in reversed(decorators):
            dec = self.eval_expr(dec_expr, env)
            klass_val = self._call_value(dec, [klass_val], env)

        env.define(name, klass_val)
        return klass_val

    def _eval_import(self, module_name: str, alias: str | None, env: KiriEnvironment) -> KiriValue:
        mod_val = self._load_module(module_name)
        bind_name = alias if alias else module_name.split(".")[0]
        env.define(bind_name, mod_val)
        return mod_val

    def _eval_from_import(self, module_name: str, names: list[tuple[str, str | None]],
                           star: bool, env: KiriEnvironment) -> KiriValue:
        mod_val = self._load_module(module_name)
        if mod_val.type != KiriValueType.MODULE:
            raise KiriRuntimeError(f"ImportError: '{module_name}' is not a module", kiri_type="ImportError")
        mod_env = mod_val.as_module().env
        if star:
            for n, v in mod_env._bindings.items():
                if not n.startswith("_"):
                    env.define(n, v)
        else:
            for name, alias in names:
                found, val = mod_env.try_lookup(name)
                if not found:
                    raise KiriRuntimeError(f"ImportError: cannot import name '{name}' from '{module_name}'",
                                           kiri_type="ImportError")
                env.define(alias if alias else name, val)
        return KiriValue.null()

    def _load_module(self, module_name: str) -> KiriValue:
        if module_name in self._loaded_modules:
            return self._loaded_modules[module_name]
        # Standard library modules
        stdlib_mod = self._load_stdlib_module(module_name)
        if stdlib_mod is not None:
            self._loaded_modules[module_name] = stdlib_mod
            return stdlib_mod
        # File-based module
        file_mod = self._load_file_module(module_name)
        if file_mod is not None:
            self._loaded_modules[module_name] = file_mod
            return file_mod
        raise KiriRuntimeError(f"ImportError: No module named '{module_name}'", kiri_type="ImportError")

    def _load_stdlib_module(self, name: str) -> KiriValue | None:
        if name == "math":
            return _make_math_module()
        if name == "os" or name == "os.path":
            return _make_os_module()
        if name == "sys":
            return _make_sys_module()
        if name == "time":
            return _make_time_module()
        if name == "random":
            return _make_random_module()
        if name == "string":
            return _make_string_module()
        if name == "json":
            return _make_json_module()
        if name == "re":
            return _make_re_module()
        return None

    def _load_file_module(self, name: str) -> KiriValue | None:
        # Try stdlib dir
        stdlib_dir = self._kiri_home / "stdlib"
        candidates = [
            stdlib_dir / f"{name}.kiri",
            Path(name.replace('.', '/') + ".kiri"),
            Path(name + ".kiri"),
        ]
        for path in candidates:
            if path.exists():
                return self._exec_module_file(name, path)
        return None

    def _exec_module_file(self, name: str, path: Path) -> KiriValue:
        from ..compiler.diagnostics import SourceText, DiagnosticBag
        from ..compiler.parser import Parser as KiriParser
        source_text = path.read_text(encoding="utf-8")
        src = SourceText(source_text, str(path))
        diag = DiagnosticBag()
        parser = KiriParser(src, diag)
        unit = parser.parse_compilation_unit()
        mod_env = KiriEnvironment()
        sub_eval = Evaluator(src, diag, self._output, mod_env, self._kiri_home)
        sub_eval.evaluate(unit)
        mod = KiriModule(name, mod_env)
        return KiriValue.from_module(mod)

    def _eval_delete(self, target: ExpressionSyntax, env: KiriEnvironment) -> None:
        if isinstance(target, IdentifierExpr):
            if target.name in env._bindings:
                del env._bindings[target.name]
        elif isinstance(target, IndexExpr):
            obj = self.eval_expr(target.target, env)
            idx = self.eval_expr(target.index, env)
            if obj.type == KiriValueType.LIST:
                obj.as_list().pop(idx.as_int())
            elif obj.type == KiriValueType.DICT:
                obj.as_dict().pop(idx, None)

    def _eval_with(self, ctx_expr, alias: str | None, body, env: KiriEnvironment) -> KiriValue:
        ctx = self.eval_expr(ctx_expr, env)
        with_env = KiriEnvironment(env)
        # Call __enter__ if it exists
        enter_val = ctx
        if ctx.type == KiriValueType.INSTANCE:
            enter_m = ctx.as_instance().get_attr("__enter__")
            if enter_m:
                enter_val = self._call_value(enter_m, [], with_env)
        if alias:
            with_env.define(alias, enter_val)
        try:
            result = self._eval_block(body, with_env)
        except Exception as e:
            # Call __exit__ on exception
            if ctx.type == KiriValueType.INSTANCE:
                exit_m = ctx.as_instance().get_attr("__exit__")
                if exit_m:
                    self._call_value(exit_m, [KiriValue.null(), KiriValue.null(), KiriValue.null()], with_env)
            raise
        # Call __exit__ normally
        if ctx.type == KiriValueType.INSTANCE:
            exit_m = ctx.as_instance().get_attr("__exit__")
            if exit_m:
                self._call_value(exit_m, [KiriValue.null(), KiriValue.null(), KiriValue.null()], with_env)
        return result

    # ─── Expressions ─────────────────────────────────────────────────────────

    def eval_expr(self, expr: ExpressionSyntax, env: KiriEnvironment) -> KiriValue:
        match expr:
            case LiteralExpr(_, tok, value):
                return _literal_to_value(tok, value)

            case IdentifierExpr(_, tok, name):
                found, val = env.try_lookup(name)
                if found: return val
                raise KiriRuntimeError(f"NameError: Name '{name}' is not defined.", tok.span, "NameError")

            case SelfExpr(_, tok):
                found, val = env.try_lookup("self")
                if found: return val
                raise KiriRuntimeError("NameError: 'self' is not defined.", tok.span, "NameError")

            case SuperExpr(_, tok):
                found, val = env.try_lookup("self")
                if not found:
                    raise KiriRuntimeError("NameError: 'super' is not defined.", tok.span, "NameError")
                # Return a proxy for super() calls
                inst = val.as_instance()
                if inst.klass.bases:
                    return KiriValue.from_class(inst.klass.bases[0])
                return KiriValue.null()

            case ParenExpr(_, _, inner, _):
                return self.eval_expr(inner, env)

            case TupleExpr(_, elements):
                return KiriValue.from_tuple(tuple(self.eval_expr(e, env) for e in elements))

            case ListExpr(_, elements):
                result = []
                for e in elements:
                    if isinstance(e, SpreadExpr):
                        result.extend(_iterate_value(self.eval_expr(e.operand, env)))
                    else:
                        result.append(self.eval_expr(e, env))
                return KiriValue.from_list(result)

            case SetExpr(_, elements):
                return KiriValue.from_set({self.eval_expr(e, env) for e in elements})

            case DictExpr(_, pairs):
                d = {}
                for k_expr, v_expr in pairs:
                    k = self.eval_expr(k_expr, env)
                    v = self.eval_expr(v_expr, env)
                    d[k] = v
                return KiriValue.from_dict(d)

            case RangeExpr(_, start, stop, inclusive):
                s = self.eval_expr(start, env).as_int()
                e = self.eval_expr(stop, env).as_int()
                return KiriValue.from_range(s, e + (1 if inclusive else 0))

            case UnaryExpr(_, op, operand):
                return self._eval_unary(op, operand, env)

            case BinaryExpr(_, left, op, right):
                return self._eval_binary(left, op, right, env)

            case CallExpr(_, callee, arguments, keyword_args):
                return self._eval_call(callee, arguments, keyword_args, env)

            case MemberAccessExpr(_, target, member_tok, member_name):
                return self._eval_member_access(target, member_name, member_tok.span, env)

            case IndexExpr(_, target, index):
                obj = self.eval_expr(target, env)
                idx = self.eval_expr(index, env)
                return _get_index(obj, idx, expr.span)

            case SliceExpr(_, target, start, stop, step):
                obj = self.eval_expr(target, env)
                s = self.eval_expr(start, env).as_int() if start else None
                e = self.eval_expr(stop, env).as_int() if stop else None
                st = self.eval_expr(step, env).as_int() if step else None
                return _get_slice(obj, s, e, st, expr.span)

            case IfExpr(_, then_value, condition, else_value):
                cond = self.eval_expr(condition, env)
                return self.eval_expr(then_value if cond.is_truthy else else_value, env)

            case ListCompExpr(_, element, target, iterable, condition):
                iterable_val = self.eval_expr(iterable, env)
                result = []
                for item in _iterate_value(iterable_val):
                    comp_env = KiriEnvironment(env)
                    comp_env.define(target, item)
                    if condition is None or self.eval_expr(condition, comp_env).is_truthy:
                        result.append(self.eval_expr(element, comp_env))
                return KiriValue.from_list(result)

            case SetCompExpr(_, element, target, iterable, condition):
                iterable_val = self.eval_expr(iterable, env)
                result = set()
                for item in _iterate_value(iterable_val):
                    comp_env = KiriEnvironment(env)
                    comp_env.define(target, item)
                    if condition is None or self.eval_expr(condition, comp_env).is_truthy:
                        result.add(self.eval_expr(element, comp_env))
                return KiriValue.from_set(result)

            case DictCompExpr(_, key, value, target, iterable, condition):
                iterable_val = self.eval_expr(iterable, env)
                result = {}
                for item in _iterate_value(iterable_val):
                    comp_env = KiriEnvironment(env)
                    comp_env.define(target, item)
                    if condition is None or self.eval_expr(condition, comp_env).is_truthy:
                        k = self.eval_expr(key, comp_env)
                        v = self.eval_expr(value, comp_env)
                        result[k] = v
                return KiriValue.from_dict(result)

            case FStringExpr(_, parts):
                result = ""
                for part in parts:
                    if isinstance(part, str):
                        result += part
                    else:
                        val = self.eval_expr(part, env)
                        result += val.to_str()
                return KiriValue.from_str(result)

            case LambdaExpr(_, params, body_expr):
                fn = KiriFunction("<lambda>", params, None, body_expr, env)
                return KiriValue.from_function(fn)

            case SpreadExpr(_, operand):
                return self.eval_expr(operand, env)

            case AssignExpr(_, target, value, is_walrus):
                val = self.eval_expr(value, env)
                self._assign_target(target, val, env)
                return val

            case _:
                raise KiriRuntimeError(f"Unknown expression type: {type(expr).__name__}", expr.span)

    def _eval_unary(self, op, operand_expr, env):
        operand = self.eval_expr(operand_expr, env)
        kind = op.kind
        if kind in (SyntaxKind.NOT_KEYWORD, SyntaxKind.BANG):
            return KiriValue.from_bool(not operand.is_truthy)
        if kind == SyntaxKind.MINUS:
            if operand.type == KiriValueType.INT: return KiriValue.from_int(-operand.as_int())
            if operand.type == KiriValueType.FLOAT: return KiriValue.from_float(-operand.as_float())
            raise KiriRuntimeError(f"TypeError: bad operand type for unary -: '{operand.type_name}'", op.span, "TypeError")
        if kind == SyntaxKind.PLUS:
            if operand.type in (KiriValueType.INT, KiriValueType.FLOAT): return operand
            raise KiriRuntimeError(f"TypeError: bad operand type for unary +: '{operand.type_name}'", op.span, "TypeError")
        if kind == SyntaxKind.TILDE:
            if operand.type == KiriValueType.INT: return KiriValue.from_int(~operand.as_int())
            raise KiriRuntimeError(f"TypeError: bad operand type for unary ~: '{operand.type_name}'", op.span, "TypeError")
        raise KiriRuntimeError(f"Unsupported unary operator '{op.text}'", op.span)

    def _eval_binary(self, left_expr, op, right_expr, env):
        kind = op.kind

        # Short-circuit
        if kind in (SyntaxKind.AND_KEYWORD, SyntaxKind.AMP_AMP):
            left = self.eval_expr(left_expr, env)
            return left if not left.is_truthy else self.eval_expr(right_expr, env)
        if kind in (SyntaxKind.OR_KEYWORD, SyntaxKind.PIPE_PIPE):
            left = self.eval_expr(left_expr, env)
            return left if left.is_truthy else self.eval_expr(right_expr, env)

        left = self.eval_expr(left_expr, env)
        right = self.eval_expr(right_expr, env)
        span = op.span

        match kind:
            case SyntaxKind.PLUS: return _add(left, right, span)
            case SyntaxKind.MINUS: return _subtract(left, right, span)
            case SyntaxKind.STAR: return _multiply(left, right, span)
            case SyntaxKind.SLASH: return _divide(left, right, span)
            case SyntaxKind.SLASH_SLASH: return _floor_divide(left, right, span)
            case SyntaxKind.PERCENT: return _modulo(left, right, span)
            case SyntaxKind.STAR_STAR: return _power(left, right, span)
            case SyntaxKind.EQUAL_EQUAL: return KiriValue.from_bool(left == right)
            case SyntaxKind.BANG_EQUAL: return KiriValue.from_bool(left != right)
            case SyntaxKind.LESS: return KiriValue.from_bool(_compare(left, right, span) < 0)
            case SyntaxKind.LESS_EQUAL: return KiriValue.from_bool(_compare(left, right, span) <= 0)
            case SyntaxKind.GREATER: return KiriValue.from_bool(_compare(left, right, span) > 0)
            case SyntaxKind.GREATER_EQUAL: return KiriValue.from_bool(_compare(left, right, span) >= 0)
            case SyntaxKind.IS_KEYWORD: return KiriValue.from_bool(left is right or left == right)
            case SyntaxKind.IN_KEYWORD: return KiriValue.from_bool(_contains(right, left, span))
            case SyntaxKind.AMPERSAND:
                if left.type == KiriValueType.INT and right.type == KiriValueType.INT:
                    return KiriValue.from_int(left.as_int() & right.as_int())
                if left.type == KiriValueType.SET and right.type == KiriValueType.SET:
                    return KiriValue.from_set(left.as_set() & right.as_set())
                raise KiriRuntimeError(f"TypeError: unsupported operand types for &: '{left.type_name}' and '{right.type_name}'", span)
            case SyntaxKind.PIPE:
                if left.type == KiriValueType.INT and right.type == KiriValueType.INT:
                    return KiriValue.from_int(left.as_int() | right.as_int())
                if left.type == KiriValueType.SET and right.type == KiriValueType.SET:
                    return KiriValue.from_set(left.as_set() | right.as_set())
                raise KiriRuntimeError(f"TypeError: unsupported operand types for |: '{left.type_name}' and '{right.type_name}'", span)
            case SyntaxKind.CARET:
                if left.type == KiriValueType.INT and right.type == KiriValueType.INT:
                    return KiriValue.from_int(left.as_int() ^ right.as_int())
                if left.type == KiriValueType.SET and right.type == KiriValueType.SET:
                    return KiriValue.from_set(left.as_set() ^ right.as_set())
                raise KiriRuntimeError(f"TypeError: unsupported operand types for ^: '{left.type_name}' and '{right.type_name}'", span)
            case SyntaxKind.LSHIFT:
                if left.type == KiriValueType.INT and right.type == KiriValueType.INT:
                    return KiriValue.from_int(left.as_int() << right.as_int())
                raise KiriRuntimeError(f"TypeError: unsupported operand types for <<: '{left.type_name}' and '{right.type_name}'", span)
            case SyntaxKind.RSHIFT:
                if left.type == KiriValueType.INT and right.type == KiriValueType.INT:
                    return KiriValue.from_int(left.as_int() >> right.as_int())
                raise KiriRuntimeError(f"TypeError: unsupported operand types for >>: '{left.type_name}' and '{right.type_name}'", span)
            case _:
                raise KiriRuntimeError(f"Unsupported binary operator '{op.text}'", span)

    def _eval_call(self, callee_expr, arguments, keyword_args, env):
        callee = self.eval_expr(callee_expr, env)
        args = []
        for arg in arguments:
            if isinstance(arg, SpreadExpr):
                args.extend(_iterate_value(self.eval_expr(arg.operand, env)))
            else:
                args.append(self.eval_expr(arg, env))
        kwargs = {k: self.eval_expr(v, env) for k, v in keyword_args if k != "**"}
        for k, v in keyword_args:
            if k == "**":
                dval = self.eval_expr(v, env)
                if dval.type == KiriValueType.DICT:
                    for dk, dv in dval.as_dict().items():
                        kwargs[dk.to_str()] = dv

        return self._call_value(callee, args, env, kwargs, callee_expr.span)

    def _call_value(self, callee: KiriValue, args: list[KiriValue],
                    env: KiriEnvironment | None, kwargs: dict | None = None,
                    span: Any = None) -> KiriValue:
        if callee.type == KiriValueType.BUILTIN_FUNCTION:
            try:
                return callee.as_builtin().call(args, env)
            except KiriRuntimeError:
                raise
            except KiriException:
                raise
            except Exception as e:
                raise KiriRuntimeError(str(e), span)

        if callee.type == KiriValueType.FUNCTION:
            return self._call_function(callee.as_function(), args, kwargs or {}, span)

        if callee.type == KiriValueType.BOUND_METHOD:
            bm = callee.raw
            full_args = [bm.instance] + args
            if bm.method.type == KiriValueType.FUNCTION:
                return self._call_function(bm.method.as_function(), full_args, kwargs or {}, span)
            if bm.method.type == KiriValueType.BUILTIN_FUNCTION:
                return bm.method.as_builtin().call(full_args, env)

        if callee.type == KiriValueType.CLASS:
            klass = callee.as_class()
            inst = KiriInstance(klass)
            inst_val = KiriValue.from_instance(inst)
            init_method = klass.lookup_method("__init__")
            if init_method:
                self._call_value(KiriValue(KiriValueType.BOUND_METHOD, BoundMethod(inst_val, init_method)),
                                 args, env, kwargs, span)
            return inst_val

        raise KiriRuntimeError(f"TypeError: '{callee.type_name}' object is not callable.", span, "TypeError")

    def _call_function(self, fn: KiriFunction, args: list[KiriValue],
                       kwargs: dict, span: Any) -> KiriValue:
        fn_env = KiriEnvironment(fn.closure)
        params = fn.params
        pos_params = [p for p in params if not p.is_variadic and not p.is_keyword_variadic]
        var_param = next((p for p in params if p.is_variadic), None)
        kw_var_param = next((p for p in params if p.is_keyword_variadic), None)

        # Bind positional params
        for i, param in enumerate(pos_params):
            if i < len(args):
                fn_env.define(param.name, args[i])
            elif param.name in kwargs:
                fn_env.define(param.name, kwargs[param.name])
            elif param.default_value is not None:
                fn_env.define(param.name, self.eval_expr(param.default_value, fn.closure))
            else:
                raise KiriRuntimeError(
                    f"TypeError: {fn.name}() missing required argument: '{param.name}'", span, "TypeError")

        # Variadic *args
        if var_param:
            rest = list(args[len(pos_params):])
            fn_env.define(var_param.name, KiriValue.from_tuple(tuple(rest)))

        # Keyword variadic **kwargs
        if kw_var_param:
            kw_dict = {KiriValue.from_str(k): v for k, v in kwargs.items()
                       if k not in {p.name for p in pos_params}}
            fn_env.define(kw_var_param.name, KiriValue.from_dict(kw_dict))

        # Execute
        try:
            if isinstance(fn.body, BlockStmt):
                self._eval_block(fn.body, fn_env)
            else:
                # Lambda body is an expression
                return self.eval_expr(fn.body, fn_env)
            return KiriValue.null()
        except ReturnSignal as r:
            return r.value

    def _eval_member_access(self, target_expr, member_name: str, span, env):
        obj = self.eval_expr(target_expr, env)

        # Instance attribute / method
        if obj.type == KiriValueType.INSTANCE:
            attr = obj.as_instance().get_attr(member_name)
            if attr is not None:
                return attr
            raise KiriRuntimeError(
                f"AttributeError: '{obj.as_instance().klass.name}' has no attribute '{member_name}'",
                span, "AttributeError")

        # Module attribute
        if obj.type == KiriValueType.MODULE:
            found, val = obj.as_module().env.try_lookup(member_name)
            if found: return val
            raise KiriRuntimeError(
                f"AttributeError: module '{obj.as_module().name}' has no attribute '{member_name}'",
                span, "AttributeError")

        # Class attribute
        if obj.type == KiriValueType.CLASS:
            klass = obj.as_class()
            method = klass.lookup_method(member_name)
            if method: return method
            raise KiriRuntimeError(
                f"AttributeError: class '{klass.name}' has no attribute '{member_name}'",
                span, "AttributeError")

        # String methods
        if obj.type == KiriValueType.STRING:
            method = _get_string_method(obj, member_name, self)
            if method: return method

        # List methods
        if obj.type == KiriValueType.LIST:
            method = _get_list_method(obj, member_name, self)
            if method: return method

        # Dict methods
        if obj.type == KiriValueType.DICT:
            method = _get_dict_method(obj, member_name, self)
            if method: return method

        # Set methods
        if obj.type == KiriValueType.SET:
            method = _get_set_method(obj, member_name, self)
            if method: return method

        # Tuple methods
        if obj.type == KiriValueType.TUPLE:
            method = _get_tuple_method(obj, member_name, self)
            if method: return method

        raise KiriRuntimeError(
            f"AttributeError: '{obj.type_name}' has no attribute '{member_name}'",
            span, "AttributeError")


# ─── Free helper functions ────────────────────────────────────────────────────

def _literal_to_value(tok, value) -> KiriValue:
    kind = tok.kind
    if kind == SyntaxKind.INT_LITERAL: return KiriValue.from_int(int(value) if value is not None else 0)
    if kind == SyntaxKind.FLOAT_LITERAL: return KiriValue.from_float(float(value) if value is not None else 0.0)
    if kind == SyntaxKind.BOOL_LITERAL: return KiriValue.from_bool(bool(value))
    if kind == SyntaxKind.NULL_LITERAL: return KiriValue.null()
    if kind == SyntaxKind.STRING_LITERAL:
        if isinstance(value, tuple) and value[0] == "__fstring__":
            return KiriValue.from_str(value[1])
        return KiriValue.from_str(str(value) if value is not None else "")
    return KiriValue.null()

def _iterate_value(v: KiriValue):
    t = v.type
    if t == KiriValueType.LIST: return iter(v.as_list())
    if t == KiriValueType.TUPLE: return iter(v.as_tuple())
    if t == KiriValueType.SET: return iter(v.as_set())
    if t == KiriValueType.RANGE: return (KiriValue.from_int(i) for i in v.raw)
    if t == KiriValueType.STRING: return (KiriValue.from_str(c) for c in v.as_str())
    if t == KiriValueType.DICT: return iter(v.as_dict().keys())
    if t == KiriValueType.ITERATOR: return v.raw
    raise KiriRuntimeError(f"TypeError: '{v.type_name}' object is not iterable", kiri_type="TypeError")

def _get_index(obj: KiriValue, idx: KiriValue, span) -> KiriValue:
    if obj.type == KiriValueType.LIST:
        lst = obj.as_list()
        i = idx.as_int()
        if i < 0: i += len(lst)
        if not (0 <= i < len(lst)):
            raise KiriRuntimeError(f"IndexError: list index {i} out of range", span, "IndexError")
        return lst[i]
    if obj.type == KiriValueType.TUPLE:
        tup = obj.as_tuple()
        i = idx.as_int()
        if i < 0: i += len(tup)
        if not (0 <= i < len(tup)):
            raise KiriRuntimeError(f"IndexError: tuple index {i} out of range", span, "IndexError")
        return tup[i]
    if obj.type == KiriValueType.STRING:
        s = obj.as_str()
        i = idx.as_int()
        if i < 0: i += len(s)
        if not (0 <= i < len(s)):
            raise KiriRuntimeError(f"IndexError: string index {i} out of range", span, "IndexError")
        return KiriValue.from_str(s[i])
    if obj.type == KiriValueType.DICT:
        d = obj.as_dict()
        if idx not in d:
            raise KiriRuntimeError(f"KeyError: {idx.to_repr()}", span, "KeyError")
        return d[idx]
    if obj.type == KiriValueType.RANGE:
        i = idx.as_int()
        r = list(obj.raw)
        if not (0 <= i < len(r)):
            raise KiriRuntimeError(f"IndexError: range index {i} out of range", span, "IndexError")
        return KiriValue.from_int(r[i])
    raise KiriRuntimeError(f"TypeError: '{obj.type_name}' object is not subscriptable", span, "TypeError")

def _set_index(obj: KiriValue, idx: KiriValue, value: KiriValue, span) -> None:
    if obj.type == KiriValueType.LIST:
        lst = obj.as_list()
        i = idx.as_int()
        if i < 0: i += len(lst)
        if not (0 <= i < len(lst)):
            raise KiriRuntimeError(f"IndexError: list index {i} out of range", span, "IndexError")
        lst[i] = value
        return
    if obj.type == KiriValueType.DICT:
        obj.as_dict()[idx] = value
        return
    raise KiriRuntimeError(f"TypeError: '{obj.type_name}' does not support item assignment", span, "TypeError")

def _get_slice(obj: KiriValue, start, stop, step, span) -> KiriValue:
    if obj.type == KiriValueType.LIST:
        return KiriValue.from_list(obj.as_list()[start:stop:step])
    if obj.type == KiriValueType.TUPLE:
        return KiriValue.from_tuple(obj.as_tuple()[start:stop:step])
    if obj.type == KiriValueType.STRING:
        return KiriValue.from_str(obj.as_str()[start:stop:step])
    raise KiriRuntimeError(f"TypeError: '{obj.type_name}' object is not sliceable", span, "TypeError")

def _contains(container: KiriValue, item: KiriValue, span) -> bool:
    if container.type == KiriValueType.LIST: return item in container.as_list()
    if container.type == KiriValueType.TUPLE: return item in container.as_tuple()
    if container.type == KiriValueType.SET: return item in container.as_set()
    if container.type == KiriValueType.DICT: return item in container.as_dict()
    if container.type == KiriValueType.STRING:
        if item.type == KiriValueType.STRING: return item.as_str() in container.as_str()
    if container.type == KiriValueType.RANGE: return item.as_int() in container.raw
    raise KiriRuntimeError(f"TypeError: argument of type '{container.type_name}' is not iterable", span, "TypeError")

def _compare(a: KiriValue, b: KiriValue, span) -> int:
    if a.type == b.type == KiriValueType.INT: return (a.as_int() > b.as_int()) - (a.as_int() < b.as_int())
    if a.type == b.type == KiriValueType.FLOAT: return (a.as_float() > b.as_float()) - (a.as_float() < b.as_float())
    if a.type == KiriValueType.INT and b.type == KiriValueType.FLOAT:
        x, y = float(a.as_int()), b.as_float()
        return (x > y) - (x < y)
    if a.type == KiriValueType.FLOAT and b.type == KiriValueType.INT:
        x, y = a.as_float(), float(b.as_int())
        return (x > y) - (x < y)
    if a.type == b.type == KiriValueType.STRING:
        return (a.as_str() > b.as_str()) - (a.as_str() < b.as_str())
    if a.type == b.type == KiriValueType.BOOL:
        return (a.as_bool() > b.as_bool()) - (a.as_bool() < b.as_bool())
    raise KiriRuntimeError(f"TypeError: '<' not supported between instances of '{a.type_name}' and '{b.type_name}'", span, "TypeError")

def _add(a: KiriValue, b: KiriValue, span) -> KiriValue:
    if a.type == KiriValueType.INT and b.type == KiriValueType.INT:
        return KiriValue.from_int(a.as_int() + b.as_int())
    if a.type in (KiriValueType.INT, KiriValueType.FLOAT) and b.type in (KiriValueType.INT, KiriValueType.FLOAT):
        x = float(a.as_int()) if a.type == KiriValueType.INT else a.as_float()
        y = float(b.as_int()) if b.type == KiriValueType.INT else b.as_float()
        return KiriValue.from_float(x + y)
    if a.type == KiriValueType.STRING:
        return KiriValue.from_str(a.as_str() + b.to_str())
    if b.type == KiriValueType.STRING:
        return KiriValue.from_str(a.to_str() + b.as_str())
    if a.type == KiriValueType.LIST and b.type == KiriValueType.LIST:
        return KiriValue.from_list(a.as_list() + b.as_list())
    if a.type == KiriValueType.TUPLE and b.type == KiriValueType.TUPLE:
        return KiriValue.from_tuple(a.as_tuple() + b.as_tuple())
    # Check for __add__ method on instances
    if a.type == KiriValueType.INSTANCE:
        add_m = a.as_instance().get_attr("__add__")
        if add_m:
            from .evaluator import Evaluator as Ev
            return KiriValue.null()  # placeholder; real dispatch done in eval
    raise KiriRuntimeError(f"TypeError: unsupported operand types for +: '{a.type_name}' and '{b.type_name}'", span, "TypeError")

def _subtract(a: KiriValue, b: KiriValue, span) -> KiriValue:
    if a.type == KiriValueType.INT and b.type == KiriValueType.INT:
        return KiriValue.from_int(a.as_int() - b.as_int())
    if a.type in (KiriValueType.INT, KiriValueType.FLOAT) and b.type in (KiriValueType.INT, KiriValueType.FLOAT):
        x = float(a.as_int()) if a.type == KiriValueType.INT else a.as_float()
        y = float(b.as_int()) if b.type == KiriValueType.INT else b.as_float()
        return KiriValue.from_float(x - y)
    if a.type == KiriValueType.SET and b.type == KiriValueType.SET:
        return KiriValue.from_set(a.as_set() - b.as_set())
    raise KiriRuntimeError(f"TypeError: unsupported operand types for -: '{a.type_name}' and '{b.type_name}'", span, "TypeError")

def _multiply(a: KiriValue, b: KiriValue, span) -> KiriValue:
    if a.type == KiriValueType.INT and b.type == KiriValueType.INT:
        return KiriValue.from_int(a.as_int() * b.as_int())
    if a.type in (KiriValueType.INT, KiriValueType.FLOAT) and b.type in (KiriValueType.INT, KiriValueType.FLOAT):
        x = float(a.as_int()) if a.type == KiriValueType.INT else a.as_float()
        y = float(b.as_int()) if b.type == KiriValueType.INT else b.as_float()
        return KiriValue.from_float(x * y)
    if a.type == KiriValueType.STRING and b.type == KiriValueType.INT:
        return KiriValue.from_str(a.as_str() * b.as_int())
    if a.type == KiriValueType.INT and b.type == KiriValueType.STRING:
        return KiriValue.from_str(b.as_str() * a.as_int())
    if a.type == KiriValueType.LIST and b.type == KiriValueType.INT:
        return KiriValue.from_list(a.as_list() * b.as_int())
    raise KiriRuntimeError(f"TypeError: unsupported operand types for *: '{a.type_name}' and '{b.type_name}'", span, "TypeError")

def _divide(a: KiriValue, b: KiriValue, span) -> KiriValue:
    if b.type == KiriValueType.INT and b.as_int() == 0:
        raise KiriRuntimeError("ZeroDivisionError: division by zero", span, "ZeroDivisionError")
    if b.type == KiriValueType.FLOAT and b.as_float() == 0.0:
        raise KiriRuntimeError("ZeroDivisionError: float division by zero", span, "ZeroDivisionError")
    x = float(a.as_int()) if a.type == KiriValueType.INT else a.as_float()
    y = float(b.as_int()) if b.type == KiriValueType.INT else b.as_float()
    if a.type not in (KiriValueType.INT, KiriValueType.FLOAT) or b.type not in (KiriValueType.INT, KiriValueType.FLOAT):
        raise KiriRuntimeError(f"TypeError: unsupported operand types for /: '{a.type_name}' and '{b.type_name}'", span, "TypeError")
    return KiriValue.from_float(x / y)

def _floor_divide(a: KiriValue, b: KiriValue, span) -> KiriValue:
    if b.type == KiriValueType.INT and b.as_int() == 0:
        raise KiriRuntimeError("ZeroDivisionError: integer division or modulo by zero", span, "ZeroDivisionError")
    if a.type == KiriValueType.INT and b.type == KiriValueType.INT:
        return KiriValue.from_int(a.as_int() // b.as_int())
    x = float(a.as_int()) if a.type == KiriValueType.INT else a.as_float()
    y = float(b.as_int()) if b.type == KiriValueType.INT else b.as_float()
    return KiriValue.from_float(math.floor(x / y))

def _modulo(a: KiriValue, b: KiriValue, span) -> KiriValue:
    if b.type == KiriValueType.INT and b.as_int() == 0:
        raise KiriRuntimeError("ZeroDivisionError: integer division or modulo by zero", span, "ZeroDivisionError")
    if a.type == KiriValueType.INT and b.type == KiriValueType.INT:
        return KiriValue.from_int(a.as_int() % b.as_int())
    if a.type in (KiriValueType.INT, KiriValueType.FLOAT) and b.type in (KiriValueType.INT, KiriValueType.FLOAT):
        x = float(a.as_int()) if a.type == KiriValueType.INT else a.as_float()
        y = float(b.as_int()) if b.type == KiriValueType.INT else b.as_float()
        return KiriValue.from_float(x % y)
    if a.type == KiriValueType.STRING:
        # Python-style % formatting (simplified)
        try:
            s = a.as_str()
            if b.type == KiriValueType.TUPLE:
                py_args = tuple(_kiri_to_py(x) for x in b.as_tuple())
                return KiriValue.from_str(s % py_args)
            return KiriValue.from_str(s % _kiri_to_py(b))
        except Exception as e:
            raise KiriRuntimeError(str(e), span)
    raise KiriRuntimeError(f"TypeError: unsupported operand types for %: '{a.type_name}' and '{b.type_name}'", span, "TypeError")

def _power(a: KiriValue, b: KiriValue, span) -> KiriValue:
    if a.type == KiriValueType.INT and b.type == KiriValueType.INT and b.as_int() >= 0:
        return KiriValue.from_int(a.as_int() ** b.as_int())
    x = float(a.as_int()) if a.type == KiriValueType.INT else a.as_float()
    y = float(b.as_int()) if b.type == KiriValueType.INT else b.as_float()
    if a.type not in (KiriValueType.INT, KiriValueType.FLOAT) or b.type not in (KiriValueType.INT, KiriValueType.FLOAT):
        raise KiriRuntimeError(f"TypeError: unsupported operand types for **: '{a.type_name}' and '{b.type_name}'", span, "TypeError")
    return KiriValue.from_float(x ** y)

def _kiri_to_py(v: KiriValue) -> Any:
    if v.type == KiriValueType.INT: return v.as_int()
    if v.type == KiriValueType.FLOAT: return v.as_float()
    if v.type == KiriValueType.STRING: return v.as_str()
    if v.type == KiriValueType.BOOL: return v.as_bool()
    return v.to_str()

def _is_subclass(klass: KiriClass, target: KiriClass) -> bool:
    if klass is target or klass.name == target.name: return True
    return any(_is_subclass(base, target) for base in klass.bases)

def _make_exception_instance(exc_type: str, message: str) -> KiriValue:
    klass = KiriClass(exc_type, [], {})
    inst = KiriInstance(klass)
    inst.fields["message"] = KiriValue.from_str(message)
    inst.fields["args"] = KiriValue.from_tuple((KiriValue.from_str(message),))
    return KiriValue.from_instance(inst)

def _register_exception_class(env: KiriEnvironment, name: str) -> None:
    klass = KiriClass(name, [], {})
    klass_val = KiriValue.from_class(klass)

    def constructor(args, _env):
        inst = KiriInstance(klass)
        msg = args[0].to_str() if args else ""
        inst.fields["message"] = KiriValue.from_str(msg)
        inst.fields["args"] = KiriValue.from_tuple((KiriValue.from_str(msg),) if args else ())
        return KiriValue.from_instance(inst)

    # Replace class constructor
    klass.methods["__init__"] = KiriValue.from_builtin(KiriBuiltinFunction("__init__", lambda a, e: KiriValue.null()))

    class _ExcCallable:
        def __init__(self): self.name = name
        def call(self, args, env): return constructor(args, env)
    env.define(name, KiriValue(KiriValueType.BUILTIN_FUNCTION, _ExcCallable()))

# ─── Built-in method implementations ─────────────────────────────────────────

def _get_string_method(obj: KiriValue, name: str, evaluator: Evaluator) -> KiriValue | None:
    s = obj.as_str()
    b = KiriValue.from_builtin
    methods = {
        "upper": lambda a, e: KiriValue.from_str(s.upper()),
        "lower": lambda a, e: KiriValue.from_str(s.lower()),
        "strip": lambda a, e: KiriValue.from_str(s.strip(a[0].as_str() if a else None)),
        "lstrip": lambda a, e: KiriValue.from_str(s.lstrip(a[0].as_str() if a else None)),
        "rstrip": lambda a, e: KiriValue.from_str(s.rstrip(a[0].as_str() if a else None)),
        "split": lambda a, e: KiriValue.from_list([KiriValue.from_str(x) for x in (s.split(a[0].as_str() if a else None))]),
        "join": lambda a, e: KiriValue.from_str(s.join(x.to_str() for x in _iterate_value(a[0]))) if a else KiriValue.from_str(""),
        "replace": lambda a, e: KiriValue.from_str(s.replace(a[0].as_str(), a[1].as_str()) if len(a) >= 2 else s),
        "startswith": lambda a, e: KiriValue.from_bool(s.startswith(a[0].as_str()) if a else KiriValue.from_bool(False)),
        "endswith": lambda a, e: KiriValue.from_bool(s.endswith(a[0].as_str()) if a else KiriValue.from_bool(False)),
        "find": lambda a, e: KiriValue.from_int(s.find(a[0].as_str()) if a else -1),
        "index": lambda a, e: KiriValue.from_int(s.index(a[0].as_str()) if a else 0),
        "count": lambda a, e: KiriValue.from_int(s.count(a[0].as_str()) if a else 0),
        "format": lambda a, e: KiriValue.from_str(s.format(*(_kiri_to_py(x) for x in a))),
        "isdigit": lambda a, e: KiriValue.from_bool(s.isdigit()),
        "isalpha": lambda a, e: KiriValue.from_bool(s.isalpha()),
        "isalnum": lambda a, e: KiriValue.from_bool(s.isalnum()),
        "isspace": lambda a, e: KiriValue.from_bool(s.isspace()),
        "isupper": lambda a, e: KiriValue.from_bool(s.isupper()),
        "islower": lambda a, e: KiriValue.from_bool(s.islower()),
        "capitalize": lambda a, e: KiriValue.from_str(s.capitalize()),
        "title": lambda a, e: KiriValue.from_str(s.title()),
        "center": lambda a, e: KiriValue.from_str(s.center(a[0].as_int(), a[1].as_str() if len(a) > 1 else " ")),
        "ljust": lambda a, e: KiriValue.from_str(s.ljust(a[0].as_int(), a[1].as_str() if len(a) > 1 else " ")),
        "rjust": lambda a, e: KiriValue.from_str(s.rjust(a[0].as_int(), a[1].as_str() if len(a) > 1 else " ")),
        "zfill": lambda a, e: KiriValue.from_str(s.zfill(a[0].as_int()) if a else s),
        "encode": lambda a, e: KiriValue.from_str(s),
        "splitlines": lambda a, e: KiriValue.from_list([KiriValue.from_str(x) for x in s.splitlines()]),
    }
    if name in methods:
        return b(KiriBuiltinFunction(name, methods[name]))
    return None

def _get_list_method(obj: KiriValue, name: str, evaluator: Evaluator) -> KiriValue | None:
    lst = obj.as_list()
    b = KiriValue.from_builtin
    def _append(a, e): lst.append(a[0] if a else KiriValue.null()); return KiriValue.null()
    def _extend(a, e):
        if a: lst.extend(_iterate_value(a[0]))
        return KiriValue.null()
    def _insert(a, e):
        if len(a) >= 2: lst.insert(a[0].as_int(), a[1])
        return KiriValue.null()
    def _remove(a, e):
        if a:
            try: lst.remove(a[0])
            except ValueError: raise KiriRuntimeError("ValueError: list.remove(x): x not in list", kiri_type="ValueError")
        return KiriValue.null()
    def _pop(a, e):
        idx = a[0].as_int() if a else -1
        try: return lst.pop(idx)
        except IndexError: raise KiriRuntimeError("IndexError: pop from empty list or index out of range", kiri_type="IndexError")
    def _sort(a, e):
        reverse = a[0].is_truthy if a else False
        try: lst.sort(reverse=reverse)
        except TypeError: pass
        return KiriValue.null()
    def _reverse(a, e): lst.reverse(); return KiriValue.null()
    def _index(a, e):
        if not a: raise KiriRuntimeError("TypeError: list.index() requires 1 argument")
        try: return KiriValue.from_int(lst.index(a[0]))
        except ValueError: raise KiriRuntimeError(f"ValueError: {a[0].to_repr()} is not in list", kiri_type="ValueError")
    def _count(a, e): return KiriValue.from_int(lst.count(a[0]) if a else 0)
    def _copy(a, e): return KiriValue.from_list(list(lst))
    def _clear(a, e): lst.clear(); return KiriValue.null()
    methods = {
        "append": _append, "extend": _extend, "insert": _insert,
        "remove": _remove, "pop": _pop, "sort": _sort,
        "reverse": _reverse, "index": _index, "count": _count,
        "copy": _copy, "clear": _clear,
    }
    if name in methods:
        return b(KiriBuiltinFunction(name, methods[name]))
    return None

def _get_dict_method(obj: KiriValue, name: str, evaluator: Evaluator) -> KiriValue | None:
    d = obj.as_dict()
    b = KiriValue.from_builtin
    def _keys(a, e): return KiriValue.from_list(list(d.keys()))
    def _values(a, e): return KiriValue.from_list(list(d.values()))
    def _items(a, e):
        return KiriValue.from_list([KiriValue.from_tuple((k, v)) for k, v in d.items()])
    def _get(a, e):
        key = a[0] if a else KiriValue.null()
        default = a[1] if len(a) > 1 else KiriValue.null()
        return d.get(key, default)
    def _pop(a, e):
        if not a: raise KiriRuntimeError("TypeError: dict.pop() requires at least 1 argument")
        default = a[1] if len(a) > 1 else None
        if default is not None: return d.pop(a[0], default)
        try: return d.pop(a[0])
        except KeyError: raise KiriRuntimeError(f"KeyError: {a[0].to_repr()}", kiri_type="KeyError")
    def _update(a, e):
        if a and a[0].type == KiriValueType.DICT:
            d.update(a[0].as_dict())
        return KiriValue.null()
    def _clear(a, e): d.clear(); return KiriValue.null()
    def _copy(a, e): return KiriValue.from_dict(dict(d))
    def _setdefault(a, e):
        if not a: return KiriValue.null()
        key = a[0]
        default = a[1] if len(a) > 1 else KiriValue.null()
        if key not in d: d[key] = default
        return d[key]
    methods = {
        "keys": _keys, "values": _values, "items": _items,
        "get": _get, "pop": _pop, "update": _update,
        "clear": _clear, "copy": _copy, "setdefault": _setdefault,
    }
    if name in methods:
        return b(KiriBuiltinFunction(name, methods[name]))
    return None

def _get_set_method(obj: KiriValue, name: str, evaluator: Evaluator) -> KiriValue | None:
    s = obj.as_set()
    b = KiriValue.from_builtin
    def _add(a, e): s.add(a[0] if a else KiriValue.null()); return KiriValue.null()
    def _remove(a, e):
        if a:
            try: s.remove(a[0])
            except KeyError: raise KiriRuntimeError(f"KeyError: {a[0].to_repr()}", kiri_type="KeyError")
        return KiriValue.null()
    def _discard(a, e): s.discard(a[0] if a else KiriValue.null()); return KiriValue.null()
    def _pop(a, e):
        try: return s.pop()
        except KeyError: raise KiriRuntimeError("KeyError: 'pop from an empty set'", kiri_type="KeyError")
    def _clear(a, e): s.clear(); return KiriValue.null()
    def _union(a, e): return KiriValue.from_set(s.union(a[0].as_set() if a else set()))
    def _intersection(a, e): return KiriValue.from_set(s.intersection(a[0].as_set() if a else set()))
    def _difference(a, e): return KiriValue.from_set(s.difference(a[0].as_set() if a else set()))
    def _issubset(a, e): return KiriValue.from_bool(s.issubset(a[0].as_set() if a else set()))
    def _issuperset(a, e): return KiriValue.from_bool(s.issuperset(a[0].as_set() if a else set()))
    def _copy(a, e): return KiriValue.from_set(set(s))
    methods = {
        "add": _add, "remove": _remove, "discard": _discard, "pop": _pop,
        "clear": _clear, "union": _union, "intersection": _intersection,
        "difference": _difference, "issubset": _issubset,
        "issuperset": _issuperset, "copy": _copy,
    }
    if name in methods:
        return b(KiriBuiltinFunction(name, methods[name]))
    return None

def _get_tuple_method(obj: KiriValue, name: str, evaluator: Evaluator) -> KiriValue | None:
    t = obj.as_tuple()
    b = KiriValue.from_builtin
    methods = {
        "count": lambda a, e: KiriValue.from_int(t.count(a[0]) if a else 0),
        "index": lambda a, e: KiriValue.from_int(t.index(a[0]) if a else 0),
    }
    if name in methods:
        return b(KiriBuiltinFunction(name, methods[name]))
    return None

# ─── Built-in modules ─────────────────────────────────────────────────────────

def _make_module(name: str, bindings: dict[str, Any]) -> KiriValue:
    env = KiriEnvironment()
    for k, v in bindings.items():
        if isinstance(v, KiriValue):
            env.define(k, v)
        elif callable(v):
            env.define(k, KiriValue.from_builtin(KiriBuiltinFunction(k, v)))
        else:
            env.define(k, KiriValue.from_python(v))
    return KiriValue.from_module(KiriModule(name, env))

def _make_math_module() -> KiriValue:
    import math as _math
    def _wrap1(fn): return lambda a, e: KiriValue.from_float(fn(a[0].as_float() if a[0].type == KiriValueType.FLOAT else float(a[0].as_int())) if a else KiriValue.from_float(0.0))
    return _make_module("math", {
        "pi": KiriValue.from_float(_math.pi),
        "e": KiriValue.from_float(_math.e),
        "inf": KiriValue.from_float(_math.inf),
        "nan": KiriValue.from_float(_math.nan),
        "sqrt": _wrap1(_math.sqrt),
        "sin": _wrap1(_math.sin), "cos": _wrap1(_math.cos), "tan": _wrap1(_math.tan),
        "asin": _wrap1(_math.asin), "acos": _wrap1(_math.acos), "atan": _wrap1(_math.atan),
        "log": lambda a, e: KiriValue.from_float(_math.log(a[0].as_float() if a[0].type == KiriValueType.FLOAT else float(a[0].as_int()), a[1].as_float() if len(a) > 1 else _math.e)),
        "log2": _wrap1(_math.log2), "log10": _wrap1(_math.log10),
        "exp": _wrap1(_math.exp),
        "floor": lambda a, e: KiriValue.from_int(_math.floor(a[0].as_float() if a[0].type == KiriValueType.FLOAT else a[0].as_int())),
        "ceil": lambda a, e: KiriValue.from_int(_math.ceil(a[0].as_float() if a[0].type == KiriValueType.FLOAT else a[0].as_int())),
        "fabs": _wrap1(_math.fabs),
        "factorial": lambda a, e: KiriValue.from_int(_math.factorial(a[0].as_int())),
        "gcd": lambda a, e: KiriValue.from_int(_math.gcd(a[0].as_int(), a[1].as_int()) if len(a) >= 2 else 0),
        "lcm": lambda a, e: KiriValue.from_int(abs(a[0].as_int() * a[1].as_int()) // _math.gcd(a[0].as_int(), a[1].as_int()) if len(a) >= 2 else 0),
        "pow": lambda a, e: KiriValue.from_float(_math.pow(a[0].as_float() if a[0].type == KiriValueType.FLOAT else float(a[0].as_int()), a[1].as_float() if a[1].type == KiriValueType.FLOAT else float(a[1].as_int()))) if len(a) >= 2 else KiriValue.from_float(0.0),
        "hypot": lambda a, e: KiriValue.from_float(_math.hypot(*(x.as_float() if x.type == KiriValueType.FLOAT else float(x.as_int()) for x in a))),
        "degrees": _wrap1(_math.degrees), "radians": _wrap1(_math.radians),
        "atan2": lambda a, e: KiriValue.from_float(_math.atan2(a[0].as_float() if a[0].type == KiriValueType.FLOAT else float(a[0].as_int()), a[1].as_float() if a[1].type == KiriValueType.FLOAT else float(a[1].as_int()))) if len(a) >= 2 else KiriValue.from_float(0.0),
        "isnan": lambda a, e: KiriValue.from_bool(_math.isnan(a[0].as_float() if a else 0)),
        "isinf": lambda a, e: KiriValue.from_bool(_math.isinf(a[0].as_float() if a else 0)),
        "isfinite": lambda a, e: KiriValue.from_bool(_math.isfinite(a[0].as_float() if a else 0)),
        "copysign": lambda a, e: KiriValue.from_float(_math.copysign(a[0].as_float() if a[0].type == KiriValueType.FLOAT else float(a[0].as_int()), a[1].as_float() if a[1].type == KiriValueType.FLOAT else float(a[1].as_int()))) if len(a) >= 2 else KiriValue.from_float(0.0),
        "trunc": lambda a, e: KiriValue.from_int(int(_math.trunc(a[0].as_float() if a[0].type == KiriValueType.FLOAT else a[0].as_int()))) if a else KiriValue.from_int(0),
    })

def _make_os_module() -> KiriValue:
    import os as _os
    return _make_module("os", {
        "sep": KiriValue.from_str(_os.sep),
        "linesep": KiriValue.from_str(_os.linesep),
        "getcwd": lambda a, e: KiriValue.from_str(_os.getcwd()),
        "listdir": lambda a, e: KiriValue.from_list([KiriValue.from_str(x) for x in _os.listdir(a[0].as_str() if a else ".")]),
        "path_join": lambda a, e: KiriValue.from_str(_os.path.join(*[x.as_str() for x in a])),
        "path_exists": lambda a, e: KiriValue.from_bool(_os.path.exists(a[0].as_str()) if a else False),
        "path_isfile": lambda a, e: KiriValue.from_bool(_os.path.isfile(a[0].as_str()) if a else False),
        "path_isdir": lambda a, e: KiriValue.from_bool(_os.path.isdir(a[0].as_str()) if a else False),
        "path_basename": lambda a, e: KiriValue.from_str(_os.path.basename(a[0].as_str()) if a else ""),
        "path_dirname": lambda a, e: KiriValue.from_str(_os.path.dirname(a[0].as_str()) if a else ""),
        "environ": KiriValue.from_dict({KiriValue.from_str(k): KiriValue.from_str(v) for k, v in _os.environ.items()}),
        "getenv": lambda a, e: KiriValue.from_str(_os.getenv(a[0].as_str(), a[1].as_str() if len(a) > 1 else "") if a else KiriValue.from_str("")),
        "system": lambda a, e: KiriValue.from_int(_os.system(a[0].as_str()) if a else 0),
        "makedirs": lambda a, e: (KiriValue.null(), _os.makedirs(a[0].as_str(), exist_ok=True))[0] if a else KiriValue.null(),
        "remove": lambda a, e: (KiriValue.null(), _os.remove(a[0].as_str()))[0] if a else KiriValue.null(),
        "rename": lambda a, e: (KiriValue.null(), _os.rename(a[0].as_str(), a[1].as_str()))[0] if len(a) >= 2 else KiriValue.null(),
    })

def _make_sys_module() -> KiriValue:
    import sys as _sys
    return _make_module("sys", {
        "argv": KiriValue.from_list([KiriValue.from_str(x) for x in _sys.argv]),
        "version": KiriValue.from_str(_sys.version),
        "platform": KiriValue.from_str(_sys.platform),
        "path": KiriValue.from_list([KiriValue.from_str(x) for x in _sys.path]),
        "exit": lambda a, e: (_sys.exit(a[0].as_int() if a and a[0].type == KiriValueType.INT else 0)),
        "stdin": KiriValue.from_module(KiriModule("stdin", KiriEnvironment())),
        "stdout": KiriValue.from_module(KiriModule("stdout", KiriEnvironment())),
        "stderr": KiriValue.from_module(KiriModule("stderr", KiriEnvironment())),
        "maxsize": KiriValue.from_int(_sys.maxsize),
    })

def _make_time_module() -> KiriValue:
    import time as _time
    return _make_module("time", {
        "time": lambda a, e: KiriValue.from_float(_time.time()),
        "sleep": lambda a, e: (KiriValue.null(), _time.sleep(a[0].as_float() if a[0].type == KiriValueType.FLOAT else float(a[0].as_int())))[0] if a else KiriValue.null(),
        "perf_counter": lambda a, e: KiriValue.from_float(_time.perf_counter()),
        "monotonic": lambda a, e: KiriValue.from_float(_time.monotonic()),
        "strftime": lambda a, e: KiriValue.from_str(_time.strftime(a[0].as_str()) if a else ""),
        "gmtime": lambda a, e: KiriValue.from_tuple(tuple(KiriValue.from_int(x) for x in _time.gmtime())),
        "localtime": lambda a, e: KiriValue.from_tuple(tuple(KiriValue.from_int(x) for x in _time.localtime())),
    })

def _make_random_module() -> KiriValue:
    import random as _random
    return _make_module("random", {
        "random": lambda a, e: KiriValue.from_float(_random.random()),
        "randint": lambda a, e: KiriValue.from_int(_random.randint(a[0].as_int(), a[1].as_int())) if len(a) >= 2 else KiriValue.from_int(0),
        "uniform": lambda a, e: KiriValue.from_float(_random.uniform(a[0].as_float() if a[0].type == KiriValueType.FLOAT else float(a[0].as_int()), a[1].as_float() if a[1].type == KiriValueType.FLOAT else float(a[1].as_int()))) if len(a) >= 2 else KiriValue.from_float(0.0),
        "choice": lambda a, e: _random.choice(list(_iterate_value(a[0]))) if a else KiriValue.null(),
        "shuffle": lambda a, e: (_random.shuffle(a[0].as_list()), KiriValue.null())[1] if a else KiriValue.null(),
        "sample": lambda a, e: KiriValue.from_list(_random.sample(list(_iterate_value(a[0])), a[1].as_int())) if len(a) >= 2 else KiriValue.from_list([]),
        "seed": lambda a, e: (_random.seed(a[0].as_int() if a else None), KiriValue.null())[1],
        "gauss": lambda a, e: KiriValue.from_float(_random.gauss(a[0].as_float() if a[0].type == KiriValueType.FLOAT else float(a[0].as_int()), a[1].as_float() if a[1].type == KiriValueType.FLOAT else float(a[1].as_int()))) if len(a) >= 2 else KiriValue.from_float(0.0),
        "randrange": lambda a, e: KiriValue.from_int(_random.randrange(*[x.as_int() for x in a])) if a else KiriValue.from_int(0),
    })

def _make_string_module() -> KiriValue:
    import string as _string
    return _make_module("string", {
        "ascii_letters": KiriValue.from_str(_string.ascii_letters),
        "ascii_lowercase": KiriValue.from_str(_string.ascii_lowercase),
        "ascii_uppercase": KiriValue.from_str(_string.ascii_uppercase),
        "digits": KiriValue.from_str(_string.digits),
        "punctuation": KiriValue.from_str(_string.punctuation),
        "whitespace": KiriValue.from_str(_string.whitespace),
    })

def _make_json_module() -> KiriValue:
    import json as _json
    def _dumps(a, e):
        if not a: return KiriValue.from_str("{}")
        def _convert(v):
            if v.type == KiriValueType.NULL: return None
            if v.type == KiriValueType.BOOL: return v.as_bool()
            if v.type == KiriValueType.INT: return v.as_int()
            if v.type == KiriValueType.FLOAT: return v.as_float()
            if v.type == KiriValueType.STRING: return v.as_str()
            if v.type == KiriValueType.LIST: return [_convert(x) for x in v.as_list()]
            if v.type == KiriValueType.DICT: return {k.to_str(): _convert(v2) for k, v2 in v.as_dict().items()}
            return v.to_str()
        indent = a[1].as_int() if len(a) > 1 else None
        return KiriValue.from_str(_json.dumps(_convert(a[0]), indent=indent))
    def _loads(a, e):
        if not a: return KiriValue.null()
        def _parse(v):
            if v is None: return KiriValue.null()
            if isinstance(v, bool): return KiriValue.from_bool(v)
            if isinstance(v, int): return KiriValue.from_int(v)
            if isinstance(v, float): return KiriValue.from_float(v)
            if isinstance(v, str): return KiriValue.from_str(v)
            if isinstance(v, list): return KiriValue.from_list([_parse(x) for x in v])
            if isinstance(v, dict): return KiriValue.from_dict({KiriValue.from_str(k): _parse(v2) for k, v2 in v.items()})
            return KiriValue.from_str(str(v))
        try:
            return _parse(_json.loads(a[0].as_str()))
        except _json.JSONDecodeError as ex:
            raise KiriRuntimeError(f"JSONDecodeError: {ex}", kiri_type="ValueError")
    return _make_module("json", {"dumps": _dumps, "loads": _loads})

def _make_re_module() -> KiriValue:
    import re as _re
    def _match(a, e):
        if len(a) < 2: return KiriValue.null()
        m = _re.match(a[0].as_str(), a[1].as_str())
        if m: return KiriValue.from_str(m.group(0))
        return KiriValue.null()
    def _search(a, e):
        if len(a) < 2: return KiriValue.null()
        m = _re.search(a[0].as_str(), a[1].as_str())
        if m: return KiriValue.from_str(m.group(0))
        return KiriValue.null()
    def _findall(a, e):
        if len(a) < 2: return KiriValue.from_list([])
        return KiriValue.from_list([KiriValue.from_str(x) for x in _re.findall(a[0].as_str(), a[1].as_str())])
    def _sub(a, e):
        if len(a) < 3: return KiriValue.from_str("")
        return KiriValue.from_str(_re.sub(a[0].as_str(), a[1].as_str(), a[2].as_str()))
    def _split(a, e):
        if len(a) < 2: return KiriValue.from_list([])
        return KiriValue.from_list([KiriValue.from_str(x) for x in _re.split(a[0].as_str(), a[1].as_str())])
    return _make_module("re", {"match": _match, "search": _search, "findall": _findall, "sub": _sub, "split": _split})
