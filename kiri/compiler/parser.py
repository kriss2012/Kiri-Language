from __future__ import annotations
from typing import Any
from .diagnostics import SourceText, DiagnosticBag, TextSpan
from .tokens import SyntaxKind, SyntaxToken, SyntaxFacts
from .lexer import Lexer
from .ast import (
    SyntaxNode, ExpressionSyntax, StatementSyntax, BlockStmt, CompilationUnit,
    ExprStmt, TypeAnnotation, ParameterNode, VarDeclStmt, FuncDeclStmt,
    ClassDeclStmt, ElifClause, ElseClause, IfStmt, WhileStmt, ForStmt,
    ReturnStmt, PassStmt, BreakStmt, ContinueStmt, RaiseStmt,
    ImportStmt, FromImportStmt, TryStmt, ExceptClause,
    AugAssignStmt, AssignStmt, DeleteStmt, AssertStmt, GlobalStmt, NonlocalStmt,
    WithStmt,
    LiteralExpr, IdentifierExpr, SelfExpr, SuperExpr, MemberAccessExpr,
    IndexExpr, SliceExpr, UnaryExpr, BinaryExpr, CallExpr, ParenExpr,
    ListExpr, TupleExpr, SetExpr, DictExpr, RangeExpr,
    LambdaExpr, IfExpr, ListCompExpr, DictCompExpr, SetCompExpr,
    FStringExpr, SpreadExpr, AssignExpr,
)

_AUG_ASSIGN_OPS = {
    SyntaxKind.PLUS_EQUAL, SyntaxKind.MINUS_EQUAL, SyntaxKind.STAR_EQUAL,
    SyntaxKind.SLASH_EQUAL, SyntaxKind.PERCENT_EQUAL, SyntaxKind.STAR_STAR_EQUAL,
}

class Parser:
    def __init__(self, source: SourceText, diagnostics: DiagnosticBag | None = None) -> None:
        self.source = source
        self.diagnostics = diagnostics if diagnostics is not None else DiagnosticBag()
        lexer = Lexer(source, self.diagnostics)
        self.tokens: list[SyntaxToken] = lexer.lex_all()
        self.pos = 0

    def peek(self, offset: int = 0) -> SyntaxToken:
        idx = self.pos + offset
        if idx >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[idx]

    @property
    def current(self) -> SyntaxToken:
        return self.peek(0)

    @property
    def next(self) -> SyntaxToken:
        return self.peek(1)

    def next_token(self) -> SyntaxToken:
        tok = self.current
        self.pos += 1
        return tok

    def match(self, kind: SyntaxKind) -> SyntaxToken:
        if self.current.kind == kind:
            return self.next_token()
        expected = SyntaxFacts.get_text(kind) or kind.name
        self.diagnostics.report_error(
            self.current.span,
            f"SyntaxError: Unexpected token '{self.current.text}', expected '{expected}'.",
            f"Insert '{expected}' before '{self.current.text}'."
        )
        return SyntaxToken(kind, self.current.position, "")

    def _consume_newlines(self) -> None:
        while self.current.kind == SyntaxKind.NEWLINE:
            self.next_token()

    def _consume_trailing_newline(self) -> None:
        if self.current.kind == SyntaxKind.NEWLINE:
            self.next_token()

    # ─── Top-level ─────────────────────────────────────────────────────────────

    def parse_compilation_unit(self) -> CompilationUnit:
        statements: list[StatementSyntax] = []
        while self.current.kind != SyntaxKind.EOF:
            if self.current.kind == SyntaxKind.NEWLINE:
                self.next_token()
                continue
            stmt = self.parse_statement()
            if stmt is not None:
                statements.append(stmt)

        eof = self.match(SyntaxKind.EOF)
        span = TextSpan.from_bounds(statements[0].span.start, eof.span.end) if statements else eof.span
        return CompilationUnit(span, statements, eof)

    # ─── Block ─────────────────────────────────────────────────────────────────

    def parse_block(self) -> BlockStmt:
        self.match(SyntaxKind.COLON)
        self.match(SyntaxKind.NEWLINE)
        start_pos = self.current.position
        self.match(SyntaxKind.INDENT)

        statements: list[StatementSyntax] = []
        while self.current.kind not in (SyntaxKind.DEDENT, SyntaxKind.EOF):
            if self.current.kind == SyntaxKind.NEWLINE:
                self.next_token()
                continue
            stmt = self.parse_statement()
            if stmt is not None:
                statements.append(stmt)

        end_pos = self.current.position
        self.match(SyntaxKind.DEDENT)
        return BlockStmt(TextSpan.from_bounds(start_pos, end_pos), statements)

    def _parse_else_clause(self) -> ElseClause | None:
        if self.current.kind == SyntaxKind.ELSE_KEYWORD:
            else_kw = self.next_token()
            block = self.parse_block()
            return ElseClause(TextSpan.from_bounds(else_kw.span.start, block.span.end), block)
        return None

    # ─── Statements ────────────────────────────────────────────────────────────

    def parse_statement(self) -> StatementSyntax | None:
        self._consume_newlines()
        if self.current.kind == SyntaxKind.EOF:
            return None

        cur = self.current.kind

        if cur == SyntaxKind.IMPORT_KEYWORD:
            return self.parse_import_statement()
        if cur == SyntaxKind.FROM_KEYWORD:
            return self.parse_from_import_statement()
        if cur == SyntaxKind.DEF_KEYWORD:
            return self.parse_function_declaration()
        if cur == SyntaxKind.CLASS_KEYWORD:
            return self.parse_class_declaration()
        if cur == SyntaxKind.IF_KEYWORD:
            return self.parse_if_statement()
        if cur == SyntaxKind.WHILE_KEYWORD:
            return self.parse_while_statement()
        if cur == SyntaxKind.FOR_KEYWORD:
            return self.parse_for_statement()
        if cur == SyntaxKind.RETURN_KEYWORD:
            return self.parse_return_statement()
        if cur == SyntaxKind.PASS_KEYWORD:
            return self.parse_pass_statement()
        if cur == SyntaxKind.BREAK_KEYWORD:
            tok = self.next_token(); self._consume_trailing_newline()
            return BreakStmt(tok.span, tok)
        if cur == SyntaxKind.CONTINUE_KEYWORD:
            tok = self.next_token(); self._consume_trailing_newline()
            return ContinueStmt(tok.span, tok)
        if cur == SyntaxKind.RAISE_KEYWORD:
            return self.parse_raise_statement()
        if cur == SyntaxKind.TRY_KEYWORD:
            return self.parse_try_statement()
        if cur == SyntaxKind.DELETE_KEYWORD:
            return self.parse_delete_statement()
        if cur == SyntaxKind.ASSERT_KEYWORD:
            return self.parse_assert_statement()
        if cur == SyntaxKind.GLOBAL_KEYWORD:
            return self.parse_global_statement()
        if cur == SyntaxKind.NONLOCAL_KEYWORD:
            return self.parse_nonlocal_statement()
        if cur == SyntaxKind.WITH_KEYWORD:
            return self.parse_with_statement()
        if cur == SyntaxKind.AT:
            return self.parse_decorated_statement()

        return self.parse_assignment_or_expression_statement()

    # ─── Import ────────────────────────────────────────────────────────────────

    def parse_import_statement(self) -> ImportStmt:
        import_kw = self.match(SyntaxKind.IMPORT_KEYWORD)
        mod_tok = self.match(SyntaxKind.IDENTIFIER)
        # handle dotted names: import a.b.c
        mod_name = mod_tok.text
        while self.current.kind == SyntaxKind.DOT:
            self.next_token()
            part = self.match(SyntaxKind.IDENTIFIER)
            mod_name += "." + part.text
        alias_tok: SyntaxToken | None = None
        if self.current.kind == SyntaxKind.AS_KEYWORD:
            self.next_token()
            alias_tok = self.match(SyntaxKind.IDENTIFIER)
        self._consume_trailing_newline()
        end_pos = alias_tok.span.end if alias_tok else mod_tok.span.end
        span = TextSpan.from_bounds(import_kw.span.start, end_pos)
        return ImportStmt(span, mod_tok, mod_name, alias_tok, alias_tok.text if alias_tok else None)

    def parse_from_import_statement(self) -> FromImportStmt:
        from_kw = self.match(SyntaxKind.FROM_KEYWORD)
        # module name (possibly dotted or relative: from . import)
        dots = 0
        while self.current.kind == SyntaxKind.DOT:
            self.next_token(); dots += 1
        mod_name = ""
        if self.current.kind == SyntaxKind.IDENTIFIER:
            mod_name = self.next_token().text
            while self.current.kind == SyntaxKind.DOT:
                self.next_token()
                mod_name += "." + self.match(SyntaxKind.IDENTIFIER).text
        self.match(SyntaxKind.IMPORT_KEYWORD)

        names: list[tuple[str, str | None]] = []
        star = False
        if self.current.kind == SyntaxKind.STAR:
            self.next_token(); star = True
        elif self.current.kind == SyntaxKind.OPEN_PAREN:
            self.next_token()
            while self.current.kind not in (SyntaxKind.CLOSE_PAREN, SyntaxKind.EOF):
                name = self.match(SyntaxKind.IDENTIFIER).text
                alias = None
                if self.current.kind == SyntaxKind.AS_KEYWORD:
                    self.next_token(); alias = self.match(SyntaxKind.IDENTIFIER).text
                names.append((name, alias))
                if self.current.kind == SyntaxKind.COMMA: self.next_token()
                else: break
            self.match(SyntaxKind.CLOSE_PAREN)
        else:
            while self.current.kind not in (SyntaxKind.NEWLINE, SyntaxKind.EOF):
                name = self.match(SyntaxKind.IDENTIFIER).text
                alias = None
                if self.current.kind == SyntaxKind.AS_KEYWORD:
                    self.next_token(); alias = self.match(SyntaxKind.IDENTIFIER).text
                names.append((name, alias))
                if self.current.kind == SyntaxKind.COMMA: self.next_token()
                else: break
        self._consume_trailing_newline()
        span = TextSpan.from_bounds(from_kw.span.start, self.current.position)
        return FromImportStmt(span, mod_name, names, star)

    # ─── Function & Class declarations ─────────────────────────────────────────

    def _parse_decorators(self) -> list[ExpressionSyntax]:
        decorators: list[ExpressionSyntax] = []
        while self.current.kind == SyntaxKind.AT:
            self.next_token()
            decorators.append(self._parse_postfix_expression())
            self._consume_trailing_newline()
        return decorators

    def parse_decorated_statement(self) -> StatementSyntax:
        decorators = self._parse_decorators()
        is_async = False
        if self.current.kind == SyntaxKind.ASYNC_KEYWORD:
            self.next_token(); is_async = True
        if self.current.kind == SyntaxKind.DEF_KEYWORD:
            fn = self.parse_function_declaration(decorators=decorators, is_async=is_async)
            return fn
        if self.current.kind == SyntaxKind.CLASS_KEYWORD:
            cls = self.parse_class_declaration(decorators=decorators)
            return cls
        self.diagnostics.report_error(self.current.span, "SyntaxError: Expected 'def' or 'class' after decorator.")
        return self.parse_statement()  # recover

    def _parse_type_annotation(self) -> TypeAnnotation:
        name_tok = self.match(SyntaxKind.IDENTIFIER)
        type_args: list[TypeAnnotation] = []
        is_optional = False
        if self.current.kind == SyntaxKind.OPEN_BRACKET:
            self.next_token()
            while self.current.kind not in (SyntaxKind.CLOSE_BRACKET, SyntaxKind.EOF):
                type_args.append(self._parse_type_annotation())
                if self.current.kind == SyntaxKind.COMMA: self.next_token()
                else: break
            self.match(SyntaxKind.CLOSE_BRACKET)
        # T? optional shorthand
        if self.current.kind == SyntaxKind.BANG:
            pass  # skip
        span = TextSpan.from_bounds(name_tok.span.start, self.current.position)
        return TypeAnnotation(span, name_tok, name_tok.text, type_args)

    def _parse_param_list(self) -> list[ParameterNode]:
        params: list[ParameterNode] = []
        while self.current.kind not in (SyntaxKind.CLOSE_PAREN, SyntaxKind.EOF):
            is_variadic = False
            is_kw_variadic = False
            if self.current.kind == SyntaxKind.STAR_STAR:
                self.next_token(); is_kw_variadic = True
            elif self.current.kind == SyntaxKind.STAR:
                self.next_token(); is_variadic = True

            param_id = self.match(SyntaxKind.IDENTIFIER)
            type_ann: TypeAnnotation | None = None
            if self.current.kind == SyntaxKind.COLON:
                self.next_token()
                type_ann = self._parse_type_annotation()
            default_val: ExpressionSyntax | None = None
            if self.current.kind == SyntaxKind.EQUAL:
                self.next_token()
                default_val = self.parse_expression()

            p_end = default_val.span.end if default_val else (type_ann.span.end if type_ann else param_id.span.end)
            p_span = TextSpan.from_bounds(param_id.span.start, p_end)
            params.append(ParameterNode(p_span, param_id, type_ann, default_val, is_variadic, False, is_kw_variadic))

            if self.current.kind == SyntaxKind.COMMA: self.next_token()
            else: break
        return params

    def parse_function_declaration(self, decorators: list[ExpressionSyntax] | None = None,
                                    is_async: bool = False) -> FuncDeclStmt:
        def_kw = self.match(SyntaxKind.DEF_KEYWORD)
        name_tok = self.match(SyntaxKind.IDENTIFIER)
        self.match(SyntaxKind.OPEN_PAREN)
        params = self._parse_param_list()
        self.match(SyntaxKind.CLOSE_PAREN)
        return_type: TypeAnnotation | None = None
        if self.current.kind == SyntaxKind.ARROW:
            self.next_token()
            return_type = self._parse_type_annotation()
        body = self.parse_block()
        span = TextSpan.from_bounds(def_kw.span.start, body.span.end)
        return FuncDeclStmt(span, name_tok, name_tok.text, params, return_type, body,
                            decorators or [], is_async)

    def parse_class_declaration(self, decorators: list[ExpressionSyntax] | None = None) -> ClassDeclStmt:
        class_kw = self.match(SyntaxKind.CLASS_KEYWORD)
        name_tok = self.match(SyntaxKind.IDENTIFIER)
        bases: list[ExpressionSyntax] = []
        if self.current.kind == SyntaxKind.OPEN_PAREN:
            self.next_token()
            while self.current.kind not in (SyntaxKind.CLOSE_PAREN, SyntaxKind.EOF):
                bases.append(self.parse_expression())
                if self.current.kind == SyntaxKind.COMMA: self.next_token()
                else: break
            self.match(SyntaxKind.CLOSE_PAREN)
        body = self.parse_block()
        span = TextSpan.from_bounds(class_kw.span.start, body.span.end)
        return ClassDeclStmt(span, name_tok, name_tok.text, bases, body, decorators or [])

    # ─── Control flow ──────────────────────────────────────────────────────────

    def parse_if_statement(self) -> IfStmt:
        if_kw = self.match(SyntaxKind.IF_KEYWORD)
        cond = self.parse_expression()
        then_block = self.parse_block()
        elifs: list[ElifClause] = []
        while self.current.kind == SyntaxKind.ELIF_KEYWORD:
            elif_kw = self.next_token()
            elif_cond = self.parse_expression()
            elif_block = self.parse_block()
            elifs.append(ElifClause(TextSpan.from_bounds(elif_kw.span.start, elif_block.span.end), elif_cond, elif_block))
        else_clause = self._parse_else_clause()
        end_pos = else_clause.span.end if else_clause else (elifs[-1].span.end if elifs else then_block.span.end)
        return IfStmt(TextSpan.from_bounds(if_kw.span.start, end_pos), cond, then_block, elifs, else_clause)

    def parse_while_statement(self) -> WhileStmt:
        while_kw = self.match(SyntaxKind.WHILE_KEYWORD)
        cond = self.parse_expression()
        body = self.parse_block()
        else_clause = self._parse_else_clause()
        end_pos = else_clause.span.end if else_clause else body.span.end
        return WhileStmt(TextSpan.from_bounds(while_kw.span.start, end_pos), cond, body, else_clause)

    def parse_for_statement(self) -> ForStmt:
        for_kw = self.match(SyntaxKind.FOR_KEYWORD)
        target_tok = self.match(SyntaxKind.IDENTIFIER)
        self.match(SyntaxKind.IN_KEYWORD)
        iterable = self.parse_expression()
        body = self.parse_block()
        else_clause = self._parse_else_clause()
        end_pos = else_clause.span.end if else_clause else body.span.end
        return ForStmt(TextSpan.from_bounds(for_kw.span.start, end_pos),
                       target_tok.text, target_tok, iterable, body, else_clause)

    def parse_return_statement(self) -> ReturnStmt:
        ret_kw = self.match(SyntaxKind.RETURN_KEYWORD)
        expr: ExpressionSyntax | None = None
        if self.current.kind not in (SyntaxKind.NEWLINE, SyntaxKind.EOF, SyntaxKind.DEDENT):
            expr = self.parse_expression()
        self._consume_trailing_newline()
        end_pos = expr.span.end if expr else ret_kw.span.end
        return ReturnStmt(TextSpan.from_bounds(ret_kw.span.start, end_pos), ret_kw, expr)

    def parse_pass_statement(self) -> PassStmt:
        pass_kw = self.match(SyntaxKind.PASS_KEYWORD)
        self._consume_trailing_newline()
        return PassStmt(pass_kw.span, pass_kw)

    def parse_raise_statement(self) -> RaiseStmt:
        raise_kw = self.match(SyntaxKind.RAISE_KEYWORD)
        expr: ExpressionSyntax | None = None
        if self.current.kind not in (SyntaxKind.NEWLINE, SyntaxKind.EOF, SyntaxKind.DEDENT):
            expr = self.parse_expression()
        self._consume_trailing_newline()
        end_pos = expr.span.end if expr else raise_kw.span.end
        return RaiseStmt(TextSpan.from_bounds(raise_kw.span.start, end_pos), raise_kw, expr)

    def parse_try_statement(self) -> TryStmt:
        try_kw = self.match(SyntaxKind.TRY_KEYWORD)
        try_body = self.parse_block()
        except_clauses: list[ExceptClause] = []
        while self.current.kind == SyntaxKind.EXCEPT_KEYWORD:
            exc_kw = self.next_token()
            exc_type: ExpressionSyntax | None = None
            alias: str | None = None
            if self.current.kind not in (SyntaxKind.COLON, SyntaxKind.NEWLINE):
                exc_type = self._parse_postfix_expression()
                if self.current.kind == SyntaxKind.AS_KEYWORD:
                    self.next_token()
                    alias = self.match(SyntaxKind.IDENTIFIER).text
            body = self.parse_block()
            span = TextSpan.from_bounds(exc_kw.span.start, body.span.end)
            except_clauses.append(ExceptClause(span, exc_type, alias, body))
        else_clause: ElseClause | None = None
        if self.current.kind == SyntaxKind.ELSE_KEYWORD:
            else_clause = self._parse_else_clause()
        finally_body: BlockStmt | None = None
        if self.current.kind == SyntaxKind.FINALLY_KEYWORD:
            self.next_token()
            finally_body = self.parse_block()
        end_pos = (finally_body.span.end if finally_body else
                   (else_clause.span.end if else_clause else
                    (except_clauses[-1].span.end if except_clauses else try_body.span.end)))
        return TryStmt(TextSpan.from_bounds(try_kw.span.start, end_pos), try_body, except_clauses, else_clause, finally_body)

    def parse_delete_statement(self) -> DeleteStmt:
        del_kw = self.match(SyntaxKind.DELETE_KEYWORD)
        target = self.parse_expression()
        self._consume_trailing_newline()
        return DeleteStmt(TextSpan.from_bounds(del_kw.span.start, target.span.end), target)

    def parse_assert_statement(self) -> AssertStmt:
        assert_kw = self.match(SyntaxKind.ASSERT_KEYWORD)
        cond = self.parse_expression()
        msg: ExpressionSyntax | None = None
        if self.current.kind == SyntaxKind.COMMA:
            self.next_token(); msg = self.parse_expression()
        self._consume_trailing_newline()
        end_pos = msg.span.end if msg else cond.span.end
        return AssertStmt(TextSpan.from_bounds(assert_kw.span.start, end_pos), cond, msg)

    def parse_global_statement(self) -> GlobalStmt:
        kw = self.match(SyntaxKind.GLOBAL_KEYWORD)
        names = [self.match(SyntaxKind.IDENTIFIER).text]
        while self.current.kind == SyntaxKind.COMMA:
            self.next_token(); names.append(self.match(SyntaxKind.IDENTIFIER).text)
        self._consume_trailing_newline()
        return GlobalStmt(kw.span, names)

    def parse_nonlocal_statement(self) -> NonlocalStmt:
        kw = self.match(SyntaxKind.NONLOCAL_KEYWORD)
        names = [self.match(SyntaxKind.IDENTIFIER).text]
        while self.current.kind == SyntaxKind.COMMA:
            self.next_token(); names.append(self.match(SyntaxKind.IDENTIFIER).text)
        self._consume_trailing_newline()
        return NonlocalStmt(kw.span, names)

    def parse_with_statement(self) -> WithStmt:
        with_kw = self.match(SyntaxKind.WITH_KEYWORD)
        ctx = self.parse_expression()
        alias: str | None = None
        if self.current.kind == SyntaxKind.AS_KEYWORD:
            self.next_token(); alias = self.match(SyntaxKind.IDENTIFIER).text
        body = self.parse_block()
        return WithStmt(TextSpan.from_bounds(with_kw.span.start, body.span.end), ctx, alias, body)

    # ─── Assignment / expression statement ─────────────────────────────────────

    def parse_assignment_or_expression_statement(self) -> StatementSyntax:
        expr = self.parse_expression()

        # Augmented assignment: target += value, etc.
        if self.current.kind in _AUG_ASSIGN_OPS:
            op = self.next_token()
            value = self.parse_expression()
            self._consume_trailing_newline()
            span = TextSpan.from_bounds(expr.span.start, value.span.end)
            return AugAssignStmt(span, expr, op, value)

        # Regular assignment: target = value
        if self.current.kind == SyntaxKind.EQUAL:
            self.next_token()
            value = self.parse_expression()
            self._consume_trailing_newline()
            span = TextSpan.from_bounds(expr.span.start, value.span.end)
            # Detect simple variable declarations
            if isinstance(expr, IdentifierExpr):
                return VarDeclStmt(span, expr.token, expr.name, None, value)
            return AssignStmt(span, expr, value)

        self._consume_trailing_newline()
        return ExprStmt(expr.span, expr)

    # ─── Expressions ───────────────────────────────────────────────────────────

    def parse_expression(self) -> ExpressionSyntax:
        return self._parse_binary_expression(0)

    def _parse_binary_expression(self, parent_precedence: int) -> ExpressionSyntax:
        # Lambda shorthand
        if self.current.kind == SyntaxKind.LAMBDA_KEYWORD:
            return self._parse_lambda()

        unary_prec = SyntaxFacts.get_unary_precedence(self.current.kind)
        if unary_prec > 0 and unary_prec > parent_precedence:
            op_tok = self.next_token()
            operand = self._parse_binary_expression(unary_prec)
            span = TextSpan.from_bounds(op_tok.span.start, operand.span.end)
            left = UnaryExpr(span, op_tok, operand)
        else:
            left = self._parse_postfix_expression()

        while True:
            prec = SyntaxFacts.get_binary_precedence(self.current.kind)
            if prec < 0 or prec <= parent_precedence:
                break
            op_tok = self.next_token()
            # Right-associative: **
            next_prec = prec - 1 if op_tok.kind == SyntaxKind.STAR_STAR else prec
            right = self._parse_binary_expression(next_prec)
            span = TextSpan.from_bounds(left.span.start, right.span.end)
            left = BinaryExpr(span, left, op_tok, right)

        # Ternary / if-expression: value if condition else other
        if self.current.kind == SyntaxKind.IF_KEYWORD and parent_precedence == 0:
            self.next_token()
            cond = self._parse_binary_expression(0)
            self.match(SyntaxKind.ELSE_KEYWORD)
            else_val = self._parse_binary_expression(0)
            span = TextSpan.from_bounds(left.span.start, else_val.span.end)
            return IfExpr(span, left, cond, else_val)

        # Range expression: expr..expr or expr..=expr
        if self.current.kind == SyntaxKind.DOT_DOT and parent_precedence == 0:
            self.next_token()
            inclusive = self.current.kind == SyntaxKind.EQUAL
            if inclusive: self.next_token()  # consume = of ..=
            stop = self._parse_binary_expression(0)
            span = TextSpan.from_bounds(left.span.start, stop.span.end)
            return RangeExpr(span, left, stop, inclusive)
        if self.current.kind == SyntaxKind.DOT_DOT_EQ and parent_precedence == 0:
            self.next_token()
            stop = self._parse_binary_expression(0)
            span = TextSpan.from_bounds(left.span.start, stop.span.end)
            return RangeExpr(span, left, stop, True)

        return left

    def _parse_lambda(self) -> LambdaExpr:
        lam_kw = self.match(SyntaxKind.LAMBDA_KEYWORD)
        params: list[ParameterNode] = []
        while self.current.kind not in (SyntaxKind.COLON, SyntaxKind.NEWLINE, SyntaxKind.EOF):
            p = self.match(SyntaxKind.IDENTIFIER)
            default_val = None
            if self.current.kind == SyntaxKind.EQUAL:
                self.next_token(); default_val = self.parse_expression()
            p_span = TextSpan.from_bounds(p.span.start, default_val.span.end if default_val else p.span.end)
            params.append(ParameterNode(p_span, p, None, default_val))
            if self.current.kind == SyntaxKind.COMMA: self.next_token()
            else: break
        self.match(SyntaxKind.COLON)
        body = self.parse_expression()
        span = TextSpan.from_bounds(lam_kw.span.start, body.span.end)
        return LambdaExpr(span, params, body)

    def _parse_postfix_expression(self) -> ExpressionSyntax:
        expr = self._parse_primary_expression()
        while True:
            if self.current.kind == SyntaxKind.DOT:
                self.next_token()
                member_tok = self.match(SyntaxKind.IDENTIFIER)
                span = TextSpan.from_bounds(expr.span.start, member_tok.span.end)
                expr = MemberAccessExpr(span, expr, member_tok, member_tok.text)

            elif self.current.kind == SyntaxKind.OPEN_PAREN:
                open_paren = self.next_token()
                args: list[ExpressionSyntax] = []
                kwargs: list[tuple[str, ExpressionSyntax]] = []
                while self.current.kind not in (SyntaxKind.CLOSE_PAREN, SyntaxKind.EOF):
                    # Check for spread: *expr or **expr
                    if self.current.kind == SyntaxKind.STAR_STAR:
                        self.next_token()
                        val = self.parse_expression()
                        kwargs.append(("**", val))
                    elif self.current.kind == SyntaxKind.STAR:
                        self.next_token()
                        val = self.parse_expression()
                        args.append(SpreadExpr(val.span, val))
                    elif (self.current.kind == SyntaxKind.IDENTIFIER and
                          self.next.kind == SyntaxKind.EQUAL):
                        # keyword argument
                        kw_name = self.next_token().text
                        self.next_token()  # consume =
                        val = self.parse_expression()
                        kwargs.append((kw_name, val))
                    else:
                        args.append(self.parse_expression())
                    if self.current.kind == SyntaxKind.COMMA: self.next_token()
                    else: break
                close_paren = self.match(SyntaxKind.CLOSE_PAREN)
                span = TextSpan.from_bounds(expr.span.start, close_paren.span.end)
                expr = CallExpr(span, expr, args, kwargs)

            elif self.current.kind == SyntaxKind.OPEN_BRACKET:
                self.next_token()
                # Slice: [start:stop] or [start:stop:step]
                start_e: ExpressionSyntax | None = None
                if self.current.kind != SyntaxKind.COLON:
                    start_e = self.parse_expression()
                if self.current.kind == SyntaxKind.COLON:
                    self.next_token()
                    stop_e: ExpressionSyntax | None = None
                    if self.current.kind not in (SyntaxKind.COLON, SyntaxKind.CLOSE_BRACKET):
                        stop_e = self.parse_expression()
                    step_e: ExpressionSyntax | None = None
                    if self.current.kind == SyntaxKind.COLON:
                        self.next_token()
                        if self.current.kind != SyntaxKind.CLOSE_BRACKET:
                            step_e = self.parse_expression()
                    close_b = self.match(SyntaxKind.CLOSE_BRACKET)
                    span = TextSpan.from_bounds(expr.span.start, close_b.span.end)
                    expr = SliceExpr(span, expr, start_e, stop_e, step_e)
                else:
                    idx = start_e  # must have been set (not a slice)
                    close_b = self.match(SyntaxKind.CLOSE_BRACKET)
                    span = TextSpan.from_bounds(expr.span.start, close_b.span.end)
                    if idx is None:
                        self.diagnostics.report_error(span, "SyntaxError: Expected index expression.")
                        idx = LiteralExpr(span, self.current, None)
                    expr = IndexExpr(span, expr, idx)
            else:
                break
        return expr

    def _parse_primary_expression(self) -> ExpressionSyntax:
        cur = self.current

        # Literals
        if cur.kind in (SyntaxKind.INT_LITERAL, SyntaxKind.FLOAT_LITERAL,
                        SyntaxKind.BOOL_LITERAL, SyntaxKind.NULL_LITERAL):
            tok = self.next_token()
            return LiteralExpr(tok.span, tok, tok.value)

        # String / f-string
        if cur.kind == SyntaxKind.STRING_LITERAL:
            tok = self.next_token()
            # Concatenate adjacent string literals
            parts = [tok]
            while self.current.kind == SyntaxKind.STRING_LITERAL:
                parts.append(self.next_token())
            if len(parts) == 1 and isinstance(tok.value, tuple) and tok.value[0] == "__fstring__":
                return self._build_fstring(tok)
            # Merge
            merged = ""
            for p in parts:
                if isinstance(p.value, str):
                    merged += p.value
                elif isinstance(p.value, tuple):
                    merged += str(p.value[1])
                elif p.value is None:
                    merged += ""
            return LiteralExpr(tok.span, tok, merged)

        # self / super
        if cur.kind == SyntaxKind.SELF_KEYWORD:
            tok = self.next_token()
            return SelfExpr(tok.span, tok)
        if cur.kind == SyntaxKind.SUPER_KEYWORD:
            tok = self.next_token()
            return SuperExpr(tok.span, tok)

        # Identifier
        if cur.kind == SyntaxKind.IDENTIFIER:
            tok = self.next_token()
            return IdentifierExpr(tok.span, tok, tok.text)

        # Parenthesized, tuple, or generator
        if cur.kind == SyntaxKind.OPEN_PAREN:
            open_p = self.next_token()
            if self.current.kind == SyntaxKind.CLOSE_PAREN:
                close_p = self.next_token()
                span = TextSpan.from_bounds(open_p.span.start, close_p.span.end)
                return TupleExpr(span, [])  # empty tuple ()
            first = self.parse_expression()
            if self.current.kind == SyntaxKind.COMMA:
                # Tuple
                elements = [first]
                while self.current.kind == SyntaxKind.COMMA:
                    self.next_token()
                    if self.current.kind == SyntaxKind.CLOSE_PAREN: break
                    elements.append(self.parse_expression())
                close_p = self.match(SyntaxKind.CLOSE_PAREN)
                span = TextSpan.from_bounds(open_p.span.start, close_p.span.end)
                return TupleExpr(span, elements)
            close_p = self.match(SyntaxKind.CLOSE_PAREN)
            span = TextSpan.from_bounds(open_p.span.start, close_p.span.end)
            return ParenExpr(span, open_p, first, close_p)

        # List literal or comprehension: [...]
        if cur.kind == SyntaxKind.OPEN_BRACKET:
            return self._parse_list_expression()

        # Dict, set, or dict/set comprehension: {...}
        if cur.kind == SyntaxKind.OPEN_BRACE:
            return self._parse_dict_or_set_expression()

        # Lambda
        if cur.kind == SyntaxKind.LAMBDA_KEYWORD:
            return self._parse_lambda()

        # Spread *expr (in list, call)
        if cur.kind == SyntaxKind.STAR:
            self.next_token()
            operand = self._parse_postfix_expression()
            span = TextSpan.from_bounds(cur.span.start, operand.span.end)
            return SpreadExpr(span, operand)

        self.diagnostics.report_error(
            cur.span,
            f"SyntaxError: Unexpected token '{cur.text}' in expression.",
            "Expected literal, identifier, or '(' expression ')'."
        )
        bad = self.next_token()
        return LiteralExpr(bad.span, bad, None)

    def _parse_list_expression(self) -> ExpressionSyntax:
        open_b = self.match(SyntaxKind.OPEN_BRACKET)
        if self.current.kind == SyntaxKind.CLOSE_BRACKET:
            close_b = self.next_token()
            return ListExpr(TextSpan.from_bounds(open_b.span.start, close_b.span.end), [])
        first = self.parse_expression()
        # List comprehension: [expr for var in iter if cond]
        if self.current.kind == SyntaxKind.FOR_KEYWORD:
            self.next_token()
            target = self.match(SyntaxKind.IDENTIFIER).text
            self.match(SyntaxKind.IN_KEYWORD)
            iterable = self.parse_expression()
            cond: ExpressionSyntax | None = None
            if self.current.kind == SyntaxKind.IF_KEYWORD:
                self.next_token(); cond = self.parse_expression()
            close_b = self.match(SyntaxKind.CLOSE_BRACKET)
            span = TextSpan.from_bounds(open_b.span.start, close_b.span.end)
            return ListCompExpr(span, first, target, iterable, cond)
        # Plain list
        elements = [first]
        while self.current.kind == SyntaxKind.COMMA:
            self.next_token()
            if self.current.kind == SyntaxKind.CLOSE_BRACKET: break
            if self.current.kind == SyntaxKind.STAR:
                self.next_token()
                e = self.parse_expression()
                elements.append(SpreadExpr(e.span, e))
            else:
                elements.append(self.parse_expression())
        close_b = self.match(SyntaxKind.CLOSE_BRACKET)
        return ListExpr(TextSpan.from_bounds(open_b.span.start, close_b.span.end), elements)

    def _parse_dict_or_set_expression(self) -> ExpressionSyntax:
        open_b = self.match(SyntaxKind.OPEN_BRACE)
        if self.current.kind == SyntaxKind.CLOSE_BRACE:
            close_b = self.next_token()
            return DictExpr(TextSpan.from_bounds(open_b.span.start, close_b.span.end), [])
        first = self.parse_expression()
        # dict
        if self.current.kind == SyntaxKind.COLON:
            self.next_token()
            first_val = self.parse_expression()
            # dict comprehension?
            if self.current.kind == SyntaxKind.FOR_KEYWORD:
                self.next_token()
                target = self.match(SyntaxKind.IDENTIFIER).text
                self.match(SyntaxKind.IN_KEYWORD)
                iterable = self.parse_expression()
                cond = None
                if self.current.kind == SyntaxKind.IF_KEYWORD:
                    self.next_token(); cond = self.parse_expression()
                close_b = self.match(SyntaxKind.CLOSE_BRACE)
                return DictCompExpr(TextSpan.from_bounds(open_b.span.start, close_b.span.end),
                                     first, first_val, target, iterable, cond)
            pairs = [(first, first_val)]
            while self.current.kind == SyntaxKind.COMMA:
                self.next_token()
                if self.current.kind == SyntaxKind.CLOSE_BRACE: break
                k = self.parse_expression()
                self.match(SyntaxKind.COLON)
                v = self.parse_expression()
                pairs.append((k, v))
            close_b = self.match(SyntaxKind.CLOSE_BRACE)
            return DictExpr(TextSpan.from_bounds(open_b.span.start, close_b.span.end), pairs)
        # set
        if self.current.kind == SyntaxKind.FOR_KEYWORD:
            self.next_token()
            target = self.match(SyntaxKind.IDENTIFIER).text
            self.match(SyntaxKind.IN_KEYWORD)
            iterable = self.parse_expression()
            cond = None
            if self.current.kind == SyntaxKind.IF_KEYWORD:
                self.next_token(); cond = self.parse_expression()
            close_b = self.match(SyntaxKind.CLOSE_BRACE)
            return SetCompExpr(TextSpan.from_bounds(open_b.span.start, close_b.span.end),
                                first, target, iterable, cond)
        elements = [first]
        while self.current.kind == SyntaxKind.COMMA:
            self.next_token()
            if self.current.kind == SyntaxKind.CLOSE_BRACE: break
            elements.append(self.parse_expression())
        close_b = self.match(SyntaxKind.CLOSE_BRACE)
        return SetExpr(TextSpan.from_bounds(open_b.span.start, close_b.span.end), elements)

    def _build_fstring(self, tok: SyntaxToken) -> ExpressionSyntax:
        """Parse f-string template into FStringExpr."""
        _, template = tok.value
        parts: list[str | ExpressionSyntax] = []
        i = 0
        text_buf = ""
        while i < len(template):
            if template[i] == '{':
                if i + 1 < len(template) and template[i+1] == '{':
                    text_buf += '{'; i += 2; continue
                # Find matching }
                depth = 1; j = i + 1
                while j < len(template) and depth > 0:
                    if template[j] == '{': depth += 1
                    elif template[j] == '}': depth -= 1
                    j += 1
                if text_buf: parts.append(text_buf); text_buf = ""
                expr_src = template[i+1:j-1]
                try:
                    sub_parser = Parser(self.source.__class__(expr_src, "<fstring>"), self.diagnostics)
                    sub_expr = sub_parser.parse_expression()
                    parts.append(sub_expr)
                except Exception:
                    parts.append(expr_src)  # fallback: treat as raw
                i = j
            elif template[i] == '}' and i + 1 < len(template) and template[i+1] == '}':
                text_buf += '}'; i += 2
            else:
                text_buf += template[i]; i += 1
        if text_buf: parts.append(text_buf)
        return FStringExpr(tok.span, parts)
