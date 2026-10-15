using Kiri.Core.Diagnostics;
using Kiri.Core.Runtime;
using Kiri.Core.Syntax;

namespace Kiri.Core;

public sealed class ExecutionResult
{
    public bool Success { get; }
    public KiriValue Value { get; }
    public DiagnosticBag Diagnostics { get; }
    public string FormattedErrors { get; }

    public ExecutionResult(bool success, KiriValue value, DiagnosticBag diagnostics, string formattedErrors)
    {
        Success = success;
        Value = value;
        Diagnostics = diagnostics;
        FormattedErrors = formattedErrors;
    }
}

public sealed class KiriEngine
{
    private readonly KiriEnvironment _globalEnvironment;
    private readonly TextWriter _output;

    public KiriEngine(TextWriter? output = null, KiriEnvironment? globalEnv = null)
    {
        _output = output ?? Console.Out;
        _globalEnvironment = globalEnv ?? new Evaluator(SourceText.From(string.Empty), null, _output).CreateDefaultEnvironment();
    }

    public ExecutionResult Execute(string code, string fileName = "<stdin>")
    {
        var source = SourceText.From(code, fileName);
        var diagnostics = new DiagnosticBag();

        var parser = new Parser(source, diagnostics);
        var compilationUnit = parser.ParseCompilationUnit();

        if (diagnostics.HasErrors)
        {
            return new ExecutionResult(false, KiriValue.Null, diagnostics, diagnostics.Format(source));
        }

        var evaluator = new Evaluator(source, diagnostics, _output, _globalEnvironment);
        var value = evaluator.Evaluate(compilationUnit);

        if (diagnostics.HasErrors)
        {
            return new ExecutionResult(false, KiriValue.Null, diagnostics, diagnostics.Format(source));
        }

        return new ExecutionResult(true, value, diagnostics, string.Empty);
    }
}
