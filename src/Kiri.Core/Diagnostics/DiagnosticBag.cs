using System.Collections;
using System.Text;

namespace Kiri.Core.Diagnostics;

public sealed class DiagnosticBag : IEnumerable<Diagnostic>
{
    private readonly List<Diagnostic> _diagnostics = [];

    public bool HasErrors => _diagnostics.Exists(d => d.Severity == DiagnosticSeverity.Error);
    public int Count => _diagnostics.Count;

    public void Report(TextSpan span, string message, DiagnosticSeverity severity = DiagnosticSeverity.Error, string? suggestion = null)
    {
        _diagnostics.Add(new Diagnostic(span, message, severity, suggestion));
    }

    public void ReportError(TextSpan span, string message, string? suggestion = null)
    {
        Report(span, message, DiagnosticSeverity.Error, suggestion);
    }

    public void ReportWarning(TextSpan span, string message, string? suggestion = null)
    {
        Report(span, message, DiagnosticSeverity.Warning, suggestion);
    }

    public void AddRange(IEnumerable<Diagnostic> diagnostics)
    {
        _diagnostics.AddRange(diagnostics);
    }

    public IEnumerator<Diagnostic> GetEnumerator() => _diagnostics.GetEnumerator();
    IEnumerator IEnumerable.GetEnumerator() => GetEnumerator();

    public string Format(SourceText source)
    {
        var sb = new StringBuilder();
        foreach (var diag in _diagnostics)
        {
            var (line, col) = source.GetLineAndColumn(diag.Span.Start);
            int lineIndex = source.GetLineIndex(diag.Span.Start);
            string lineText = source.GetLineText(lineIndex);

            string colorPrefix = diag.Severity switch
            {
                DiagnosticSeverity.Error => "ERROR",
                DiagnosticSeverity.Warning => "WARNING",
                _ => "INFO"
            };

            sb.AppendLine($"[{colorPrefix}] {diag.Message}");
            sb.AppendLine($"  --> {source.FileName}:{line}:{col}");
            sb.AppendLine("   |");

            string lineNumStr = line.ToString().PadLeft(3);
            sb.AppendLine($"{lineNumStr} | {lineText}");

            // Create squiggly pointer
            int indentLen = Math.Max(0, col - 1);
            int squigglyLen = Math.Max(1, Math.Min(diag.Span.Length, Math.Max(1, lineText.Length - indentLen)));
            string pointer = new string(' ', indentLen) + new string('^', squigglyLen);
            sb.AppendLine($"   | {pointer}");

            if (!string.IsNullOrWhiteSpace(diag.Suggestion))
            {
                sb.AppendLine($"   = suggestion: {diag.Suggestion}");
            }
            sb.AppendLine();
        }
        return sb.ToString().TrimEnd();
    }
}
