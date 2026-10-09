# Kiri-Language

Kiri-Language is a small, experimental programming language implemented in Python. It is designed as a readable, beginner-friendly language with a minimal interpreter that supports variables, arithmetic, conditionals, loops, and functions.

## Features

- Variables with `let` and reassignment
- Arithmetic operators: `+`, `-`, `*`, `/`, `%`
- Comparison and equality checks: `==`, `!=`, `<`, `<=`, `>`, `>=`
- `if` / `else` blocks
- `while` loops
- Function definitions with `fn`
- `return` statements
- Built-in `print` function

## Quick Start

```bash
cd Kiri-Language
python main.py examples/hello.kiri
```

You can also launch the interactive REPL:

```bash
cd Kiri-Language
python main.py
```

## Example

```kiri
let name = "Kiri";
print("Hello, " + name + "!");

fn greet(person) {
    print("Welcome, " + person + "!");
}

greet("Developer");
```

## Project Structure

```text
Kiri-Language/
├── kiri/             # Interpreter package
│   ├── __init__.py
│   ├── lexer.py      # Tokenizer
│   ├── parser.py     # Recursive-descent parser
│   └── interpreter.py# Runtime evaluator
├── examples/
│   └── hello.kiri
├── tests/
│   └── test_kiri.py
├── main.py          # CLI entry point
├── README.md
├── LICENSE
└── requirements.txt  # optional for future dependencies
```

## Testing

```bash
cd Kiri-Language
python -m pytest -q
```

## License

This project is licensed under the MIT License.
