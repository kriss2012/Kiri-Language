# Kiri Programming Language

> **"Python-level simplicity with systems-language-level performance, safety, tooling, concurrency, and deployment."**

Kiri is a modern, high-performance programming language designed from first principles. It combines the clean readability, minimal ceremony, and expressiveness of Python with a redesigned compiler pipeline, unboxed runtime memory model, and free-threaded multi-core architecture.

---

## Key Features & Departures from Python

1. **Unboxed Value Semantics**:
   - `Int` (64-bit signed) and `Float` (64-bit IEEE 754) run unboxed without heap allocations.
2. **Safe Default Arguments**:
   - Default argument expressions are evaluated **fresh per call**, eliminating Python's mutable-default state leakage trap.
3. **By-Value Closure Capture**:
   - Closures capture loop/iteration variables by value by default, eliminating late-binding traps.
4. **Free-Threaded Multi-Core Concurrency**:
   - Designed from day one without a Global Interpreter Lock (GIL).
5. **Progressive Complexity**:
   - Standard dynamic execution for rapid prototyping, combined with an optional `strict` mode for compile-time verified guarantees.
6. **First-Class Diagnostics**:
   - High-precision source tracking with line/column pointers, visual code snippets, and actionable suggestions.

---

## Quickstart

### Running Kiri Scripts
```bash
# Direct file execution
kiri examples/factorial.kiri

# Explicit run command
kiri run examples/hello.kiri
```

### Interactive REPL
Launch the REPL by running:
```bash
kiri repl
```
Example session:
```kiri
>>> def greet(name: String) -> String:
...     return "Hello, " + name
>>> greet("Kiri")
"Hello, Kiri"
```

### Running the Test Suite
```bash
kiri test
```

---

## Example: Recursive Factorial

```kiri
def factorial(n: Int) -> Int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)

print(factorial(10))
```
**Output:**
```text
3628800
```

---

## Project Structure

```text
kiri/
├── docs/
│   ├── architecture.md       # Layered compiler & runtime architecture
│   ├── design-decisions.md   # Architectural departures from Python
│   ├── roadmap.md            # Phased roadmap from bootstrap to self-hosting
│   └── language-spec.md      # Formal lexical and syntax grammar
├── kiri/
│   ├── compiler/             # Lexer, Parser, AST, Diagnostics, Tokens
│   ├── runtime/              # Tagged values, Environment, Evaluator, Builtins
│   ├── cli.py                # Unified CLI interface
│   └── engine.py             # High-level compilation & execution pipeline
├── tests/                    # Unit, regression, and integration tests
├── examples/                 # Sample Kiri applications
├── kiri.cmd                  # Windows launcher
├── kiri.bat                  # Batch launcher
└── README.md
```

---

## Documentation

- [Architecture Specification](docs/architecture.md)
- [Design Decisions](docs/design-decisions.md)
- [Development Roadmap](docs/roadmap.md)
- [Language Specification](docs/language-spec.md)
