using Kiri.Core.Syntax.AST;

namespace Kiri.Core.Runtime;

public sealed class KiriFunction
{
    public string Name { get; }
    public IReadOnlyList<ParameterSyntax> Parameters { get; }
    public TypeAnnotationSyntax? ReturnType { get; }
    public BlockSyntax Body { get; }
    public KiriEnvironment Closure { get; }

    public KiriFunction(
        string name,
        IReadOnlyList<ParameterSyntax> parameters,
        TypeAnnotationSyntax? returnType,
        BlockSyntax body,
        KiriEnvironment closure)
    {
        Name = name;
        Parameters = parameters;
        ReturnType = returnType;
        Body = body;
        Closure = closure;
    }
}

public sealed class KiriBuiltinFunction
{
    public string Name { get; }
    public Func<IReadOnlyList<KiriValue>, KiriEnvironment, KiriValue> Implementation { get; }

    public KiriBuiltinFunction(string name, Func<IReadOnlyList<KiriValue>, KiriEnvironment, KiriValue> implementation)
    {
        Name = name;
        Implementation = implementation;
    }
}

public sealed class ReturnSignalException : Exception
{
    public KiriValue Value { get; }

    public ReturnSignalException(KiriValue value)
    {
        Value = value;
    }
}

public sealed class KiriRuntimeException : Exception
{
    public Diagnostics.TextSpan? Span { get; }

    public KiriRuntimeException(string message, Diagnostics.TextSpan? span = null) : base(message)
    {
        Span = span;
    }
}
