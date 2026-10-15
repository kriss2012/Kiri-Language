using Kiri.Core.Diagnostics;

namespace Kiri.Core.Syntax;

public sealed class SyntaxToken
{
    public SyntaxKind Kind { get; }
    public int Position { get; }
    public string Text { get; }
    public object? Value { get; }
    public TextSpan Span => new(Position, Text.Length);

    public SyntaxToken(SyntaxKind kind, int position, string text, object? value = null)
    {
        Kind = kind;
        Position = position;
        Text = text ?? string.Empty;
        Value = value;
    }

    public override string ToString() => $"{Kind}: '{Text}' ({Span})";
}
