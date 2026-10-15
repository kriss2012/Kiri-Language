# Kiri Language Architecture Specification

## 1. Overview and Core Philosophy

Kiri is a modern, high-performance programming language designed with the principle:
> **"Python-level simplicity with systems-language-level performance, safety, tooling, concurrency, and deployment."**

Kiri provides progressive complexity:
- Rapid prototyping and scripting feel as lightweight, natural, and expressive as Python.
- Advanced capabilities (`strict`, `parallel`, `async`, `unsafe`, `native`) allow systems-level control over memory, concurrency, execution, and types without sacrificing syntax elegance.

---

## 2. Layered Architecture

```text
       .kiri Source Code
              │
              ▼
    SourceText & Diagnostics
              │
              ▼
   Lexer (Indentation-Aware)
    [Tokens + INDENT / DEDENT]
              │
              ▼
     Recursive-Descent Parser
              │
              ▼
      Abstract Syntax Tree (AST)
              │
              ▼
      Semantic Analysis
    ├── Name & Scope Resolution
    ├── Type Inference & Check
    ├── Effect & Lifetime Analysis
    └── Capture Analysis (by-value defaults)
              │
              ▼
     Kiri Intermediate Representation (KIR)
              │
       ┌──────┴──────┬───────────────┐
       ▼             ▼               ▼
AST / Tree Evaluator  Bytecode VM     AOT / JIT Native
(Instant dev / REPL)  (Inline Cache)  (Optimized machine code)
       │             │               │
       └──────┬──────┴───────────────┘
              ▼
        Kiri Runtime
    ├── Object System & Value Layout
    ├── Memory Management & GC
    ├── Free-Threaded Scheduler
    └── Native Interop (FFI)
              │
              ▼
       Host Operating System
```

---

## 3. Compiler Subsystems

### 3.1 Lexer and Indentation Engine
The lexer transforms UTF-8 source into a token stream.
- **Indentation Handling**: Implements a dedicated indentation stack. Emits synthetic `NEWLINE`, `INDENT`, and `DEDENT` tokens.
- **Smart Continuation**: Automatically ignores newlines inside unclosed parentheses `(...)`, brackets `[...]`, and braces `{...}`, or immediately following binary operators (`+`, `-`, `*`, `/`, `&&`, `||`).
- **Source Locations**: Every token preserves exact byte offsets, line numbers, and column positions for diagnostic reporting.

### 3.2 Parser and AST
- Hand-written recursive descent with precedence climbing for binary expressions.
- Produces an immutable, typed Abstract Syntax Tree (AST).
- Preserves full span metadata on every AST node for error reporting and tooling.

### 3.3 Semantic Analyzer
- **Scope Hierarchy**: Global scope, module scope, function scope, and block scope.
- **Variable Resolution**: Differentiates lexical reads and writes. Prevents late-binding bugs by binding closures cleanly.
- **Type Checking**:
  - In *Dynamic Mode* (default): Types are inferred or tracked dynamically; runtime tag checks are generated only where required.
  - In *Strict Mode* (`strict`): Compile-time validation enforces type safety, prevents invalid member access, and disallows unannotated ambiguous operations.

---

## 4. Runtime Architecture

### 4.1 Value Representation
Kiri uses a high-efficiency tagged value representation:
- **Primitives**: `Int` (64-bit signed integer), `Float` (64-bit IEEE 754), `Bool`, and `Null` require **zero heap allocation**.
- **Heap Objects**: Strings, Lists, Dicts, Objects, and Functions carry an object header with Shape/Class descriptor and reference/GC metadata.

### 4.2 Object Model
- Objects are structured around **Shapes** (hidden classes).
- Property access utilizes Shape transitions and Inline Caches (IC), eliminating dictionary lookups on repeated property reads.

---

## 5. Memory Model

- **Dual-Track Resource Management**:
  - Automatic memory reclamation for general heap objects via generational/tracing GC.
  - Deterministic resource reclamation via `with` statements for OS resources (files, sockets, mutexes, GPU handles).
- **Escape Analysis**: Allows stack allocation of short-lived objects and closures where lifetimes do not escape the calling frame.

---

## 6. Concurrency Model

- **No Global Interpreter Lock (GIL)**: The Kiri runtime is designed from day one for free-threaded execution across multi-core processors.
- **Structured Concurrency**: Async tasks operate in task scopes/nurseries; parent tasks do not terminate until child tasks complete or cancel.
- **Safe State Sharing**: Message-passing via channels is favored; shared mutable memory requires explicit synchronizers (`Mutex`, `RwLock`, `Atomic`).
