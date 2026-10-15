using Kiri.Core.Diagnostics;
using Kiri.Core.Syntax.AST;

namespace Kiri.Core.Syntax;

public sealed class Parser
{
    private readonly SourceText _source;
    private readonly IReadOnlyList<SyntaxToken> _tokens;
    private readonly DiagnosticBag _diagnostics;
    private int _position;

    public DiagnosticBag Diagnostics => _diagnostics;

    public Parser(SourceText source, DiagnosticBag? diagnostics = null)
    {
        _source = source;
        _diagnostics = diagnostics ?? new DiagnosticBag();
        var lexer = new Lexer(source, _diagnostics);
        _tokens = lexer.LexAll();
    }

    private SyntaxToken Current => Peek(0);
    private SyntaxToken Next => Peek(1);

    private SyntaxToken Peek(int offset)
    {
        int index = _position + offset;
        return index >= _tokens.Count ? _tokens[^1] : _tokens[index];
    }

    private SyntaxToken Match(SyntaxKind kind)
    {
        if (Current.Kind == kind)
        {
            return NextToken();
        }

        string expected = SyntaxFacts.GetText(kind) ?? kind.ToString();
        _diagnostics.ReportError(
            Current.Span,
            $"SyntaxError: Unexpected token '{Current.Text}', expected '{expected}'.",
            $"Insert '{expected}' before '{Current.Text}'.");

        return new SyntaxToken(kind, Current.Position, string.Empty);
    }

    private SyntaxToken NextToken()
    {
        var current = Current;
        _position++;
        return current;
    }

    public CompilationUnitSyntax ParseCompilationUnit()
    {
        var statements = new List<StatementSyntax>();

        while (Current.Kind != SyntaxKind.EndOfFile)
        {
            if (Current.Kind == SyntaxKind.NewLine)
            {
                NextToken();
                continue;
            }

            var stmt = ParseStatement();
            if (stmt != null)
            {
                statements.Add(stmt);
            }
        }

        var eof = Match(SyntaxKind.EndOfFile);
        return new CompilationUnitSyntax(statements, eof);
    }

    private StatementSyntax? ParseStatement()
    {
        while (Current.Kind == SyntaxKind.NewLine)
        {
            NextToken();
        }

        if (Current.Kind == SyntaxKind.EndOfFile)
            return null;

        return Current.Kind switch
        {
            SyntaxKind.DefKeyword => ParseFunctionDeclaration(),
            SyntaxKind.IfKeyword => ParseIfStatement(),
            SyntaxKind.WhileKeyword => ParseWhileStatement(),
            SyntaxKind.ReturnKeyword => ParseReturnStatement(),
            SyntaxKind.PassKeyword => ParsePassStatement(),
            _ => ParseAssignmentOrExpressionStatement()
        };
    }

    private BlockSyntax ParseBlock()
    {
        Match(SyntaxKind.ColonToken);
        Match(SyntaxKind.NewLine);

        int startPos = Current.Position;
        Match(SyntaxKind.Indent);

        var statements = new List<StatementSyntax>();
        while (Current.Kind != SyntaxKind.Dedent && Current.Kind != SyntaxKind.EndOfFile)
        {
            if (Current.Kind == SyntaxKind.NewLine)
            {
                NextToken();
                continue;
            }

            var stmt = ParseStatement();
            if (stmt != null)
            {
                statements.Add(stmt);
            }
        }

        int endPos = Current.Position;
        Match(SyntaxKind.Dedent);

        return new BlockSyntax(statements, TextSpan.FromBounds(startPos, endPos));
    }

    private FunctionDeclarationSyntax ParseFunctionDeclaration()
    {
        var defKeyword = Match(SyntaxKind.DefKeyword);
        var identifier = Match(SyntaxKind.Identifier);

        Match(SyntaxKind.OpenParenToken);
        var parameters = new List<ParameterSyntax>();

        while (Current.Kind != SyntaxKind.CloseParenToken && Current.Kind != SyntaxKind.EndOfFile)
        {
            var paramId = Match(SyntaxKind.Identifier);
            TypeAnnotationSyntax? typeAnnotation = null;
            if (Current.Kind == SyntaxKind.ColonToken)
            {
                NextToken();
                var typeId = Match(SyntaxKind.Identifier);
                typeAnnotation = new TypeAnnotationSyntax(typeId);
            }

            ExpressionSyntax? defaultVal = null;
            if (Current.Kind == SyntaxKind.EqualToken)
            {
                NextToken();
                defaultVal = ParseExpression();
            }

            parameters.Add(new ParameterSyntax(paramId, typeAnnotation, defaultVal));

            if (Current.Kind == SyntaxKind.CommaToken)
            {
                NextToken();
            }
            else
            {
                break;
            }
        }

        Match(SyntaxKind.CloseParenToken);

        TypeAnnotationSyntax? returnType = null;
        if (Current.Kind == SyntaxKind.ArrowToken)
        {
            NextToken();
            var returnTypeId = Match(SyntaxKind.Identifier);
            returnType = new TypeAnnotationSyntax(returnTypeId);
        }

        var body = ParseBlock();
        return new FunctionDeclarationSyntax(defKeyword, identifier, parameters, returnType, body);
    }

    private IfStatementSyntax ParseIfStatement()
    {
        var ifKeyword = Match(SyntaxKind.IfKeyword);
        var condition = ParseExpression();
        var thenBlock = ParseBlock();

        var elifClauses = new List<ElifClauseSyntax>();
        while (Current.Kind == SyntaxKind.ElifKeyword)
        {
            var elifKeyword = NextToken();
            var elifCond = ParseExpression();
            var elifBlock = ParseBlock();
            elifClauses.Add(new ElifClauseSyntax(elifKeyword, elifCond, elifBlock));
        }

        ElseClauseSyntax? elseClause = null;
        if (Current.Kind == SyntaxKind.ElseKeyword)
        {
            var elseKeyword = NextToken();
            var elseBlock = ParseBlock();
            elseClause = new ElseClauseSyntax(elseKeyword, elseBlock);
        }

        return new IfStatementSyntax(ifKeyword, condition, thenBlock, elifClauses, elseClause);
    }

    private WhileStatementSyntax ParseWhileStatement()
    {
        var whileKeyword = Match(SyntaxKind.WhileKeyword);
        var condition = ParseExpression();
        var body = ParseBlock();
        return new WhileStatementSyntax(whileKeyword, condition, body);
    }

    private ReturnStatementSyntax ParseReturnStatement()
    {
        var returnKeyword = Match(SyntaxKind.ReturnKeyword);
        ExpressionSyntax? expr = null;

        if (Current.Kind != SyntaxKind.NewLine && Current.Kind != SyntaxKind.EndOfFile && Current.Kind != SyntaxKind.Dedent)
        {
            expr = ParseExpression();
        }

        ConsumeTrailingNewlineOrDelimiter();
        return new ReturnStatementSyntax(returnKeyword, expr);
    }

    private PassStatementSyntax ParsePassStatement()
    {
        var passKeyword = Match(SyntaxKind.PassKeyword);
        ConsumeTrailingNewlineOrDelimiter();
        return new PassStatementSyntax(passKeyword);
    }

    private StatementSyntax ParseAssignmentOrExpressionStatement()
    {
        // Check for variable declaration or assignment:
        // x = expr OR x: Type = expr
        if (Current.Kind == SyntaxKind.Identifier)
        {
            if (Next.Kind == SyntaxKind.EqualToken)
            {
                var id = NextToken();
                Match(SyntaxKind.EqualToken);
                var expr = ParseExpression();
                ConsumeTrailingNewlineOrDelimiter();
                return new VariableDeclarationOrAssignmentSyntax(id, null, expr);
            }
            if (Next.Kind == SyntaxKind.ColonToken)
            {
                int colonIdx = _position + 1;
                if (colonIdx + 1 < _tokens.Count && _tokens[colonIdx + 1].Kind == SyntaxKind.Identifier)
                {
                    int afterTypeIdx = colonIdx + 2;
                    if (afterTypeIdx < _tokens.Count && _tokens[afterTypeIdx].Kind == SyntaxKind.EqualToken)
                    {
                        var id = NextToken();
                        Match(SyntaxKind.ColonToken);
                        var typeId = Match(SyntaxKind.Identifier);
                        Match(SyntaxKind.EqualToken);
                        var expr = ParseExpression();
                        ConsumeTrailingNewlineOrDelimiter();
                        return new VariableDeclarationOrAssignmentSyntax(id, new TypeAnnotationSyntax(typeId), expr);
                    }
                }
            }
        }

        var expression = ParseExpression();
        ConsumeTrailingNewlineOrDelimiter();
        return new ExpressionStatementSyntax(expression);
    }

    private void ConsumeTrailingNewlineOrDelimiter()
    {
        if (Current.Kind == SyntaxKind.NewLine)
        {
            NextToken();
        }
    }

    // Expressions: Precedence Climbing
    public ExpressionSyntax ParseExpression()
    {
        return ParseBinaryExpression(0);
    }

    private ExpressionSyntax ParseBinaryExpression(int parentPrecedence)
    {
        ExpressionSyntax left;
        int unaryPrecedence = Current.Kind.GetUnaryOperatorPrecedence();
        if (unaryPrecedence > 0 && unaryPrecedence >= parentPrecedence)
        {
            var opToken = NextToken();
            var operand = ParseBinaryExpression(unaryPrecedence);
            left = new UnaryExpressionSyntax(opToken, operand);
        }
        else
        {
            left = ParsePostfixExpression();
        }

        while (true)
        {
            int precedence = Current.Kind.GetBinaryOperatorPrecedence();
            if (precedence == 0 || precedence <= parentPrecedence)
                break;

            var opToken = NextToken();
            // Power operator ** is right-associative
            int nextPrecedence = (opToken.Kind == SyntaxKind.DoubleStarToken) ? precedence - 1 : precedence;
            var right = ParseBinaryExpression(nextPrecedence);
            left = new BinaryExpressionSyntax(left, opToken, right);
        }

        return left;
    }

    private ExpressionSyntax ParsePostfixExpression()
    {
        var expr = ParsePrimaryExpression();

        while (true)
        {
            if (Current.Kind == SyntaxKind.OpenParenToken)
            {
                var openParen = NextToken();
                var arguments = new List<ExpressionSyntax>();

                while (Current.Kind != SyntaxKind.CloseParenToken && Current.Kind != SyntaxKind.EndOfFile)
                {
                    arguments.Add(ParseExpression());
                    if (Current.Kind == SyntaxKind.CommaToken)
                    {
                        NextToken();
                    }
                    else
                    {
                        break;
                    }
                }

                var closeParen = Match(SyntaxKind.CloseParenToken);
                var span = TextSpan.FromBounds(expr.Span.Start, closeParen.Span.End);
                expr = new CallExpressionSyntax(expr, arguments, span);
            }
            else
            {
                break;
            }
        }

        return expr;
    }

    private ExpressionSyntax ParsePrimaryExpression()
    {
        switch (Current.Kind)
        {
            case SyntaxKind.IntegerLiteral:
            case SyntaxKind.FloatLiteral:
            case SyntaxKind.StringLiteral:
            case SyntaxKind.BooleanLiteral:
            case SyntaxKind.NullLiteral:
            {
                var token = NextToken();
                return new LiteralExpressionSyntax(token, token.Value);
            }

            case SyntaxKind.Identifier:
            {
                var token = NextToken();
                return new IdentifierExpressionSyntax(token);
            }

            case SyntaxKind.OpenParenToken:
            {
                var open = NextToken();
                var inner = ParseExpression();
                var close = Match(SyntaxKind.CloseParenToken);
                return new ParenthesizedExpressionSyntax(open, inner, close);
            }

            default:
            {
                _diagnostics.ReportError(
                    Current.Span,
                    $"SyntaxError: Unexpected token '{Current.Text}' in expression.",
                    "Expected literal, identifier, or '(' expression ')'.");
                var bad = NextToken();
                return new LiteralExpressionSyntax(bad, null);
            }
        }
    }
}
