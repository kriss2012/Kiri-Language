# Kiri Language Specification (Draft v0.1)

## 1. Lexical Grammar

### 1.1 Character Encoding
Kiri source files are UTF-8 encoded text files with the extension `.kiri`.

### 1.2 Line Terminators and Whitespace
- Line terminators: `\n` or `\r\n`.
- Whitespace consists of spaces (` `) and horizontal tabs (`\t`). Standard style enforces 4 spaces per indentation level.
- Physical newlines outside of grouped expressions (`( )`, `[ ]`, `{ }`) emit logical `NEWLINE` tokens.
- Indentation depth is tracked via an internal indentation stack. An increase produces an `INDENT` token; a decrease produces one or more `DEDENT` tokens.

### 1.3 Comments
- Single-line comments start with `#` and continue to the end of the line:
  ```kiri
  # This is a comment in Kiri
  ```

### 1.4 Identifiers and Keywords
- Identifiers begin with an ASCII letter or underscore `[a-zA-Z_]` followed by alphanumeric characters or underscores `[a-zA-Z0-9_]*`.
- Keywords: `def`, `return`, `if`, `elif`, `else`, `while`, `for`, `in`, `class`, `import`, `from`, `as`, `try`, `except`, `finally`, `raise`, `with`, `async`, `await`, `parallel`, `strict`, `unsafe`, `native`, `true`, `false`, `null`, `and`, `or`, `not`, `is`.

### 1.5 Literals
- **Integer**: Decimal integers (`42`, `1_000_000`), hex (`0xFF`), binary (`0b1010`), octal (`0o755`).
- **Float**: Standard floating point (`3.14`, `1e-4`, `0.5d`, `0.5f`).
- **String**: Double-quoted (`"hello\n"`) or single-quoted (`'world'`), with standard escape sequences (`\n`, `\t`, `\"`, `\\`).
- **Boolean**: `true`, `false`.
- **Null**: `null` (singleton representing absence of value).

---

## 2. Syntax Grammar (EBNF Subset for Phase 1)

```ebnf
Program        ::= Statement* EOF ;
Statement      ::= FunctionDecl
                 | IfStmt
                 | WhileStmt
                 | ReturnStmt
                 | ExprStmt
                 | VarAssignStmt ;

Block          ::= NEWLINE INDENT Statement+ DEDENT ;

FunctionDecl   ::= "def" IDENTIFIER "(" ParameterList? ")" ( "->" TypeAnnotation )? ":" Block ;
ParameterList  ::= Parameter ( "," Parameter )* ;
Parameter      ::= IDENTIFIER ( ":" TypeAnnotation )? ( "=" Expression )? ;

IfStmt         ::= "if" Expression ":" Block
                   ( "elif" Expression ":" Block )*
                   ( "else" ":" Block )? ;

WhileStmt      ::= "while" Expression ":" Block ;

ReturnStmt     ::= "return" Expression? NEWLINE ;
VarAssignStmt  ::= IDENTIFIER ( ":" TypeAnnotation )? "=" Expression NEWLINE ;
ExprStmt       ::= Expression NEWLINE ;

Expression     ::= LogicalOr ;
LogicalOr      ::= LogicalAnd ( ( "or" | "||" ) LogicalAnd )* ;
LogicalAnd     ::= Equality ( ( "and" | "&&" ) Equality )* ;
Equality       ::= Relational ( ( "==" | "!=" ) Relational )* ;
Relational     ::= Additive ( ( "<" | "<=" | ">" | ">=" ) Additive )* ;
Additive       ::= Multiplicative ( ( "+" | "-" ) Multiplicative )* ;
Multiplicative ::= Unary ( ( "*" | "/" | "%" ) Unary )* ;
Unary          ::= ( "-" | "+" | "not" | "!" ) Unary | CallExpr ;
CallExpr       ::= Primary ( "(" ArgumentList? ")" )* ;
ArgumentList   ::= Expression ( "," Expression )* ;
Primary        ::= INTEGER | FLOAT | STRING | "true" | "false" | "null"
                 | IDENTIFIER
                 | "(" Expression ")" ;
```

---

## 3. Evaluation and Scopes

- **Scopes**: Lexical scoping. Inner blocks can read enclosing variables. Assigning to an identifier binds it in the current scope unless declared as `global` or `outer`.
- **Function Execution**: Functions execute with fresh activation frames. Recursive calls are supported without artificial limits beyond host stack depth.
- **Closures**: Functions capturing outer variables capture value snapshots by default for iteration variables, avoiding the classic late-binding loop traps.

---

## 4. Builtin Functions (Phase 1)

- `print(...)`: Writes formatted representations of arguments to standard output separated by spaces, followed by a newline.
- `len(x)`: Returns the integer length of a string or collection.
- `type(x)`: Returns the type name string of value `x` (`"Int"`, `"Float"`, `"String"`, `"Bool"`, `"Null"`, `"Function"`).
- `assert(condition, message?)`: Raises an assertion error if condition evaluates to false.
