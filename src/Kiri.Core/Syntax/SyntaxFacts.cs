namespace Kiri.Core.Syntax;

public static class SyntaxFacts
{
    public static SyntaxKind GetKeywordKind(string text) => text switch
    {
        "def" => SyntaxKind.DefKeyword,
        "return" => SyntaxKind.ReturnKeyword,
        "if" => SyntaxKind.IfKeyword,
        "elif" => SyntaxKind.ElifKeyword,
        "else" => SyntaxKind.ElseKeyword,
        "while" => SyntaxKind.WhileKeyword,
        "for" => SyntaxKind.ForKeyword,
        "in" => SyntaxKind.InKeyword,
        "pass" => SyntaxKind.PassKeyword,
        "break" => SyntaxKind.BreakKeyword,
        "continue" => SyntaxKind.ContinueKeyword,
        "true" => SyntaxKind.TrueKeyword,
        "false" => SyntaxKind.FalseKeyword,
        "null" => SyntaxKind.NullKeyword,
        "and" => SyntaxKind.AndKeyword,
        "or" => SyntaxKind.OrKeyword,
        "not" => SyntaxKind.NotKeyword,
        "strict" => SyntaxKind.StrictKeyword,
        _ => SyntaxKind.Identifier
    };

    public static int GetUnaryOperatorPrecedence(this SyntaxKind kind) => kind switch
    {
        SyntaxKind.PlusToken or
        SyntaxKind.MinusToken or
        SyntaxKind.BangToken or
        SyntaxKind.NotKeyword => 7,
        _ => 0
    };

    public static int GetBinaryOperatorPrecedence(this SyntaxKind kind) => kind switch
    {
        SyntaxKind.DoubleStarToken => 6,
        SyntaxKind.StarToken or SyntaxKind.SlashToken or SyntaxKind.PercentToken => 5,
        SyntaxKind.PlusToken or SyntaxKind.MinusToken => 4,
        SyntaxKind.EqualEqualToken or SyntaxKind.BangEqualToken or
        SyntaxKind.LessToken or SyntaxKind.LessOrEqualToken or
        SyntaxKind.GreaterToken or SyntaxKind.GreaterOrEqualToken => 3,
        SyntaxKind.AndKeyword or SyntaxKind.AmpersandAmpersandToken => 2,
        SyntaxKind.OrKeyword or SyntaxKind.PipePipeToken => 1,
        _ => 0
    };

    public static string? GetText(SyntaxKind kind) => kind switch
    {
        SyntaxKind.PlusToken => "+",
        SyntaxKind.MinusToken => "-",
        SyntaxKind.StarToken => "*",
        SyntaxKind.SlashToken => "/",
        SyntaxKind.PercentToken => "%",
        SyntaxKind.DoubleStarToken => "**",
        SyntaxKind.EqualToken => "=",
        SyntaxKind.EqualEqualToken => "==",
        SyntaxKind.BangEqualToken => "!=",
        SyntaxKind.LessToken => "<",
        SyntaxKind.LessOrEqualToken => "<=",
        SyntaxKind.GreaterToken => ">",
        SyntaxKind.GreaterOrEqualToken => ">=",
        SyntaxKind.AmpersandAmpersandToken => "&&",
        SyntaxKind.PipePipeToken => "||",
        SyntaxKind.BangToken => "!",
        SyntaxKind.OpenParenToken => "(",
        SyntaxKind.CloseParenToken => ")",
        SyntaxKind.OpenBracketToken => "[",
        SyntaxKind.CloseBracketToken => "]",
        SyntaxKind.OpenBraceToken => "{",
        SyntaxKind.CloseBraceToken => "}",
        SyntaxKind.ColonToken => ":",
        SyntaxKind.CommaToken => ",",
        SyntaxKind.DotToken => ".",
        SyntaxKind.ArrowToken => "->",
        SyntaxKind.DefKeyword => "def",
        SyntaxKind.ReturnKeyword => "return",
        SyntaxKind.IfKeyword => "if",
        SyntaxKind.ElifKeyword => "elif",
        SyntaxKind.ElseKeyword => "else",
        SyntaxKind.WhileKeyword => "while",
        SyntaxKind.ForKeyword => "for",
        SyntaxKind.InKeyword => "in",
        SyntaxKind.PassKeyword => "pass",
        SyntaxKind.BreakKeyword => "break",
        SyntaxKind.ContinueKeyword => "continue",
        SyntaxKind.TrueKeyword => "true",
        SyntaxKind.FalseKeyword => "false",
        SyntaxKind.NullKeyword => "null",
        SyntaxKind.AndKeyword => "and",
        SyntaxKind.OrKeyword => "or",
        SyntaxKind.NotKeyword => "not",
        SyntaxKind.StrictKeyword => "strict",
        _ => null
    };
}
