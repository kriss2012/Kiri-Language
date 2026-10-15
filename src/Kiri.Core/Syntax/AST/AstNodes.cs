using Kiri.Core.Diagnostics;

namespace Kiri.Core.Syntax.AST;

public abstract class SyntaxNode
{
    public abstract TextSpan Span { get; }
}

public abstract class ExpressionSyntax : SyntaxNode
{
}

public abstract class StatementSyntax : SyntaxNode
{
}

public sealed class BlockSyntax : StatementSyntax
{
    public IReadOnlyList<StatementSyntax> Statements { get; }
    public override TextSpan Span { get; }

    public BlockSyntax(IReadOnlyList<StatementSyntax> statements, TextSpan span)
    {
        Statements = statements;
        Span = span;
    }
}

public sealed class CompilationUnitSyntax : SyntaxNode
{
    public IReadOnlyList<StatementSyntax> Statements { get; }
    public SyntaxToken EndOfFileToken { get; }
    public override TextSpan Span => Statements.Count == 0 
        ? EndOfFileToken.Span 
        : TextSpan.FromBounds(Statements[0].Span.Start, EndOfFileToken.Span.End);

    public CompilationUnitSyntax(IReadOnlyList<StatementSyntax> statements, SyntaxToken endOfFileToken)
    {
        Statements = statements;
        EndOfFileToken = endOfFileToken;
    }
}

// Expressions
public sealed class LiteralExpressionSyntax : ExpressionSyntax
{
    public SyntaxToken Token { get; }
    public object? Value { get; }
    public override TextSpan Span => Token.Span;

    public LiteralExpressionSyntax(SyntaxToken token, object? value)
    {
        Token = token;
        Value = value;
    }
}

public sealed class IdentifierExpressionSyntax : ExpressionSyntax
{
    public SyntaxToken Identifier { get; }
    public string Name => Identifier.Text;
    public override TextSpan Span => Identifier.Span;

    public IdentifierExpressionSyntax(SyntaxToken identifier)
    {
        Identifier = identifier;
    }
}

public sealed class UnaryExpressionSyntax : ExpressionSyntax
{
    public SyntaxToken Operator { get; }
    public ExpressionSyntax Operand { get; }
    public override TextSpan Span => TextSpan.FromBounds(Operator.Span.Start, Operand.Span.End);

    public UnaryExpressionSyntax(SyntaxToken op, ExpressionSyntax operand)
    {
        Operator = op;
        Operand = operand;
    }
}

public sealed class BinaryExpressionSyntax : ExpressionSyntax
{
    public ExpressionSyntax Left { get; }
    public SyntaxToken Operator { get; }
    public ExpressionSyntax Right { get; }
    public override TextSpan Span => TextSpan.FromBounds(Left.Span.Start, Right.Span.End);

    public BinaryExpressionSyntax(ExpressionSyntax left, SyntaxToken op, ExpressionSyntax right)
    {
        Left = left;
        Operator = op;
        Right = right;
    }
}

public sealed class CallExpressionSyntax : ExpressionSyntax
{
    public ExpressionSyntax Callee { get; }
    public IReadOnlyList<ExpressionSyntax> Arguments { get; }
    public override TextSpan Span { get; }

    public CallExpressionSyntax(ExpressionSyntax callee, IReadOnlyList<ExpressionSyntax> arguments, TextSpan span)
    {
        Callee = callee;
        Arguments = arguments;
        Span = span;
    }
}

public sealed class ParenthesizedExpressionSyntax : ExpressionSyntax
{
    public SyntaxToken OpenParen { get; }
    public ExpressionSyntax Expression { get; }
    public SyntaxToken CloseParen { get; }
    public override TextSpan Span => TextSpan.FromBounds(OpenParen.Span.Start, CloseParen.Span.End);

    public ParenthesizedExpressionSyntax(SyntaxToken open, ExpressionSyntax expr, SyntaxToken close)
    {
        OpenParen = open;
        Expression = expr;
        CloseParen = close;
    }
}

// Statements
public sealed class ExpressionStatementSyntax : StatementSyntax
{
    public ExpressionSyntax Expression { get; }
    public override TextSpan Span => Expression.Span;

    public ExpressionStatementSyntax(ExpressionSyntax expression)
    {
        Expression = expression;
    }
}

public sealed class TypeAnnotationSyntax : SyntaxNode
{
    public SyntaxToken Identifier { get; }
    public string TypeName => Identifier.Text;
    public override TextSpan Span => Identifier.Span;

    public TypeAnnotationSyntax(SyntaxToken identifier)
    {
        Identifier = identifier;
    }
}

public sealed class VariableDeclarationOrAssignmentSyntax : StatementSyntax
{
    public SyntaxToken Identifier { get; }
    public string Name => Identifier.Text;
    public TypeAnnotationSyntax? TypeAnnotation { get; }
    public ExpressionSyntax Initializer { get; }
    public override TextSpan Span => TextSpan.FromBounds(Identifier.Span.Start, Initializer.Span.End);

    public VariableDeclarationOrAssignmentSyntax(
        SyntaxToken identifier, 
        TypeAnnotationSyntax? typeAnnotation, 
        ExpressionSyntax initializer)
    {
        Identifier = identifier;
        TypeAnnotation = typeAnnotation;
        Initializer = initializer;
    }
}

public sealed class ParameterSyntax : SyntaxNode
{
    public SyntaxToken Identifier { get; }
    public string Name => Identifier.Text;
    public TypeAnnotationSyntax? TypeAnnotation { get; }
    public ExpressionSyntax? DefaultValue { get; }
    public override TextSpan Span => DefaultValue != null
        ? TextSpan.FromBounds(Identifier.Span.Start, DefaultValue.Span.End)
        : TypeAnnotation != null
            ? TextSpan.FromBounds(Identifier.Span.Start, TypeAnnotation.Span.End)
            : Identifier.Span;

    public ParameterSyntax(SyntaxToken identifier, TypeAnnotationSyntax? typeAnnotation, ExpressionSyntax? defaultValue)
    {
        Identifier = identifier;
        TypeAnnotation = typeAnnotation;
        DefaultValue = defaultValue;
    }
}

public sealed class FunctionDeclarationSyntax : StatementSyntax
{
    public SyntaxToken DefKeyword { get; }
    public SyntaxToken Identifier { get; }
    public string Name => Identifier.Text;
    public IReadOnlyList<ParameterSyntax> Parameters { get; }
    public TypeAnnotationSyntax? ReturnType { get; }
    public BlockSyntax Body { get; }
    public override TextSpan Span => TextSpan.FromBounds(DefKeyword.Span.Start, Body.Span.End);

    public FunctionDeclarationSyntax(
        SyntaxToken defKeyword,
        SyntaxToken identifier,
        IReadOnlyList<ParameterSyntax> parameters,
        TypeAnnotationSyntax? returnType,
        BlockSyntax body)
    {
        DefKeyword = defKeyword;
        Identifier = identifier;
        Parameters = parameters;
        ReturnType = returnType;
        Body = body;
    }
}

public sealed class ReturnStatementSyntax : StatementSyntax
{
    public SyntaxToken ReturnKeyword { get; }
    public ExpressionSyntax? Expression { get; }
    public override TextSpan Span => Expression != null
        ? TextSpan.FromBounds(ReturnKeyword.Span.Start, Expression.Span.End)
        : ReturnKeyword.Span;

    public ReturnStatementSyntax(SyntaxToken returnKeyword, ExpressionSyntax? expression)
    {
        ReturnKeyword = returnKeyword;
        Expression = expression;
    }
}

public sealed class ElifClauseSyntax : SyntaxNode
{
    public SyntaxToken ElifKeyword { get; }
    public ExpressionSyntax Condition { get; }
    public BlockSyntax Block { get; }
    public override TextSpan Span => TextSpan.FromBounds(ElifKeyword.Span.Start, Block.Span.End);

    public ElifClauseSyntax(SyntaxToken elifKeyword, ExpressionSyntax condition, BlockSyntax block)
    {
        ElifKeyword = elifKeyword;
        Condition = condition;
        Block = block;
    }
}

public sealed class ElseClauseSyntax : SyntaxNode
{
    public SyntaxToken ElseKeyword { get; }
    public BlockSyntax Block { get; }
    public override TextSpan Span => TextSpan.FromBounds(ElseKeyword.Span.Start, Block.Span.End);

    public ElseClauseSyntax(SyntaxToken elseKeyword, BlockSyntax block)
    {
        ElseKeyword = elseKeyword;
        Block = block;
    }
}

public sealed class IfStatementSyntax : StatementSyntax
{
    public SyntaxToken IfKeyword { get; }
    public ExpressionSyntax Condition { get; }
    public BlockSyntax ThenBlock { get; }
    public IReadOnlyList<ElifClauseSyntax> ElifClauses { get; }
    public ElseClauseSyntax? ElseClause { get; }
    public override TextSpan Span => TextSpan.FromBounds(
        IfKeyword.Span.Start,
        ElseClause != null ? ElseClause.Span.End : (ElifClauses.Count > 0 ? ElifClauses[^1].Span.End : ThenBlock.Span.End));

    public IfStatementSyntax(
        SyntaxToken ifKeyword,
        ExpressionSyntax condition,
        BlockSyntax thenBlock,
        IReadOnlyList<ElifClauseSyntax> elifClauses,
        ElseClauseSyntax? elseClause)
    {
        IfKeyword = ifKeyword;
        Condition = condition;
        ThenBlock = thenBlock;
        ElifClauses = elifClauses;
        ElseClause = elseClause;
    }
}

public sealed class WhileStatementSyntax : StatementSyntax
{
    public SyntaxToken WhileKeyword { get; }
    public ExpressionSyntax Condition { get; }
    public BlockSyntax Body { get; }
    public override TextSpan Span => TextSpan.FromBounds(WhileKeyword.Span.Start, Body.Span.End);

    public WhileStatementSyntax(SyntaxToken whileKeyword, ExpressionSyntax condition, BlockSyntax body)
    {
        WhileKeyword = whileKeyword;
        Condition = condition;
        Body = body;
    }
}

public sealed class PassStatementSyntax : StatementSyntax
{
    public SyntaxToken PassKeyword { get; }
    public override TextSpan Span => PassKeyword.Span;

    public PassStatementSyntax(SyntaxToken passKeyword)
    {
        PassKeyword = passKeyword;
    }
}
