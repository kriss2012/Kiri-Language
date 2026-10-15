# Kiri Design Decisions: Departures from Python

This document outlines intentional departures from Python syntax and runtime semantics, detailing the problem in Python, Kiri's solution, the technical rationale, and the tradeoffs involved.

---

## 1. Mutable Default Arguments

### Python Behavior
Default argument expressions are evaluated once when the function definition is executed at module load time.
```python
def append_to(item, target=[]):
    target.append(item)
    return target
```
Subsequent calls without providing `target` share the identical list instance across invocations.

### Problem
This is one of Python's most notorious beginner and production pitfalls. State accidentally leaks across distinct function calls, causing insidious bugs.

### Kiri Solution
In Kiri, default argument expressions are evaluated **fresh per call** at the point of invocation:
```kiri
def append_to(item, target = []):
    target.append(item)
    return target
```
Each call without `target` creates a new `[]` instance. If a shared singleton default is explicitly desired, it must be marked with `shared`:
```kiri
def configure(cache = shared GlobalCache()):
    ...
```

### Reason
Code behaves according to intuitive developer expectations. Zero accidental state leakage between call sites.

### Tradeoff
A minor allocation occurs on invocation when default is exercised (which can be optimized by escape analysis or compiler-generated factories).

---

## 2. Closure Variable Capture (Late Binding)

### Python Behavior
Python closures capture variables by reference/scope slot (late binding).
```python
funcs = [lambda: i for i in range(3)]
print([f() for f in funcs])  # Prints [2, 2, 2]!
```

### Problem
Developers are routinely bitten when creating closures in loops, event handlers, UI callbacks, and concurrent tasks. Workarounds like `lambda i=i: ...` are awkward hacks.

### Kiri Solution
In Kiri, loop variables and local variables captured by lambda/closure are **captured by value at the point of closure creation** by default:
```kiri
funcs = []
for i in 0..3:
    funcs.append(() => i)
# Result: [0, 1, 2]
```
If reference sharing is deliberately required across mutations, it must be marked explicitly:
```kiri
count = 0
inc = () => ref count += 1
```

### Reason
Eliminates one of the most common asynchronous and loop bugs in dynamic programming.

### Tradeoff
Closures intended to observe subsequent mutations of local primitives must use explicit reference syntax.

---

## 3. Global Interpreter Lock (GIL) and Free-Threading

### Python Behavior
CPython relies on a coarse-grained Global Interpreter Lock (GIL) that prevents concurrent execution of Python bytecode across multiple CPU cores in a single process.

### Problem
CPU-bound tasks cannot scale across multi-core processors without resorting to multi-process architectures (which introduce heavy inter-process serialization and memory duplication).

### Kiri Solution
Kiri is designed from the ground up for **free-threaded multi-core execution**:
- Thread-safe object model with atomic reference counting / concurrent garbage collection.
- Per-thread local allocation arenas for fast allocations.
- First-class concurrency abstractions (`parallel`, `async`/`await`, channels, actors).

### Reason
Modern processors scale horizontally via CPU cores. A modern systems and data language must utilize available hardware cores natively.

### Tradeoff
Slightly higher synchronization overhead on cross-thread object sharing, mitigated by immutability, thread-local allocation, and compiler ownership analysis.

---

## 4. Number Types and Arithmetic Overhead

### Python Behavior
Python integers are arbitrary-precision objects (`PyLongObject`) allocated on the heap (with small-integer caching). Arithmetic operations incur boxing, unboxing, and dynamic dispatch.

### Problem
Massive overhead in numeric algorithms and tight loops; arithmetic in CPython is up to 50x slower than compiled systems languages.

### Kiri Solution
Kiri provides **unboxed native numeric primitives**:
- `Int`: 64-bit signed two's-complement integer by default (unboxed value type).
- `Float`: 64-bit IEEE 754 floating point (unboxed value type).
- Explicit numeric types: `UInt`, `Float32`, `BigInt`, `Decimal`, `Rational`, `Complex`.
- Explicit syntax for intent: `0.1f` (Float32), `1/3r` (Rational).

### Reason
Allows Kiri numeric code to run near native CPU speeds while preserving clean mathematical syntax.

### Tradeoff
`Int` operations use 64-bit machine arithmetic. In `strict` mode or debug builds, overflow is detected, with options for automatic promotion or wrapping.

---

## 5. Type System: Optional Gradual vs. Strict Mode

### Python Behavior
Python type annotations are syntactic sugar ignored by the runtime (`typing` module). Type checking requires third-party tools (mypy, pyright). Runtime errors like `AttributeError` or `TypeError` still happen frequently in production.

### Problem
Absence of compile-time guarantees; optimizer cannot reliably specialize code because types can mutate arbitrarily.

### Kiri Solution
Kiri supports two coordinated modes:
- **Dynamic Mode** (default): Expressive, duck-typed, rapid prototyping like Python.
- **Strict Mode** (`strict` file header or configuration): Enforces compile-time type validation, disallows calling undeclared attributes, and proves correctness before execution.
- Types in Kiri are first-class compiler entities used directly for JIT and AOT specialization.

### Reason
Combines rapid experimentation with enterprise-grade safety and high performance.

### Tradeoff
Developers writing `strict` code must satisfy compiler type contracts.

---

## 6. Deterministic Resource Management vs. Finalizers

### Python Behavior
Python developers often rely on `__del__` or CPython's reference counting to close files and sockets immediately upon falling out of scope. This fails unpredictably in alternate runtimes (PyPy, free-threaded CPython).

### Problem
File descriptor exhaustion, leaked locks, delayed buffer flushes.

### Kiri Solution
Explicit separation of **Memory Management** (handled by GC) and **Resource Management** (handled by `with` statement blocks and deterministic scope cleanup).

### Reason
Ensures uniform, predictable behavior across all platforms and execution tiers (Interpreted, JIT, AOT).

### Tradeoff
Resources like files and sockets require explicit scoping blocks.
