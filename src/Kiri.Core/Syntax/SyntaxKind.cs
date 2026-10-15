namespace Kiri.Core.Syntax;

public enum SyntaxKind
{
    // Special
    BadToken,
    EndOfFile,
    NewLine,
    Indent,
    Dedent,

    // Literals
    IntegerLiteral,
    FloatLiteral,
    StringLiteral,
    BooleanLiteral,
    NullLiteral,

    // Identifiers & Keywords
    Identifier,
    DefKeyword,
    ReturnKeyword,
    IfKeyword,
    ElifKeyword,
    ElseKeyword,
    WhileKeyword,
    ForKeyword,
    InKeyword,
    PassKeyword,
    BreakKeyword,
    ContinueKeyword,
    TrueKeyword,
    FalseKeyword,
    NullKeyword,
    AndKeyword,
    OrKeyword,
    NotKeyword,
    StrictKeyword,

    // Operators & Delimiters
    PlusToken,          // +
    MinusToken,         // -
    StarToken,          // *
    SlashToken,         // /
    PercentToken,       // %
    DoubleStarToken,    // **
    EqualToken,         // =
    EqualEqualToken,    // ==
    BangEqualToken,     // !=
    LessToken,          // <
    LessOrEqualToken,   // <=
    GreaterToken,       // >
    GreaterOrEqualToken,// >=
    AmpersandAmpersandToken, // &&
    PipePipeToken,      // ||
    BangToken,          // !

    OpenParenToken,     // (
    CloseParenToken,    // )
    OpenBracketToken,   // [
    CloseBracketToken,  // ]
    OpenBraceToken,     // {
    CloseBraceToken,    // }
    ColonToken,         // :
    CommaToken,         // ,
    DotToken,           // .
    ArrowToken,         // ->
}
