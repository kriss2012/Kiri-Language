namespace Kiri.Core.Diagnostics;

public enum DiagnosticSeverity
{
    Info,
    Warning,
    Error
}

public sealed record Diagnostic(
    TextSpan Span,
    string Message,
    DiagnosticSeverity Severity = DiagnosticSeverity.Error,
    string? Suggestion = null,
    string? CodeSnippet = null)
{
    public override string ToString() => $"{Severity}: {Message} at {Span}";
}
