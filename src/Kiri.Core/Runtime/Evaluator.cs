using System.Diagnostics;
using System.Text;
using Kiri.Core.Diagnostics;
using Kiri.Core.Syntax;
using Kiri.Core.Syntax.AST;

namespace Kiri.Core.Runtime;

public sealed class Evaluator
{
    private readonly SourceText _source;
    private readonly DiagnosticBag _diagnostics;
    private readonly TextWriter _output;
    private readonly Stopwatch _stopwatch = Stopwatch.StartNew();

    public KiriEnvironment GlobalEnvironment { get; }

    public Evaluator(SourceText source, DiagnosticBag? diagnostics = null, TextWriter? output = null, KiriEnvironment? globalEnv = null)
    {
        _source = source;
        _diagnostics = diagnostics ?? new DiagnosticBag();
        _output = output ?? Console.Out;
        GlobalEnvironment = globalEnv ?? CreateDefaultEnvironment();
    }

    public KiriEnvironment CreateDefaultEnvironment()
    {
        var env = new KiriEnvironment();

        // Builtin: print
        env.Define("print", KiriValue.FromBuiltin(new KiriBuiltinFunction("print", (args, _) =>
        {
            var sb = new StringBuilder();
            for (int i = 0; i < args.Count; i++)
            {
                if (i > 0) sb.Append(' ');
                sb.Append(args[i].ToString());
            }
            _output.WriteLine(sb.ToString());
            return KiriValue.Null;
        })));

        // Builtin: len
        env.Define("len", KiriValue.FromBuiltin(new KiriBuiltinFunction("len", (args, _) =>
        {
            if (args.Count != 1)
                throw new KiriRuntimeException($"len() takes exactly 1 argument ({args.Count} given).");

            if (args[0].Type == KiriValueType.String)
                return KiriValue.FromInt(args[0].AsString().Length);

            throw new KiriRuntimeException($"Object of type '{args[0].TypeName}' has no len().");
        })));

        // Builtin: type
        env.Define("type", KiriValue.FromBuiltin(new KiriBuiltinFunction("type", (args, _) =>
        {
            if (args.Count != 1)
                throw new KiriRuntimeException($"type() takes exactly 1 argument ({args.Count} given).");
            return KiriValue.FromString(args[0].TypeName);
        })));

        // Builtin: assert
        env.Define("assert", KiriValue.FromBuiltin(new KiriBuiltinFunction("assert", (args, _) =>
        {
            if (args.Count < 1 || args.Count > 2)
                throw new KiriRuntimeException($"assert() takes 1 or 2 arguments ({args.Count} given).");

            if (!args[0].IsTruthy)
            {
                string msg = args.Count == 2 ? args[1].ToString() : "Assertion failed.";
                throw new KiriRuntimeException(msg);
            }
            return KiriValue.True;
        })));

        // Builtin: clock
        env.Define("clock", KiriValue.FromBuiltin(new KiriBuiltinFunction("clock", (_, _) =>
        {
            return KiriValue.FromFloat(_stopwatch.Elapsed.TotalSeconds);
        })));

        return env;
    }

    public KiriValue Evaluate(CompilationUnitSyntax compilationUnit)
    {
        KiriValue lastValue = KiriValue.Null;
        try
        {
            foreach (var stmt in compilationUnit.Statements)
            {
                lastValue = EvaluateStatement(stmt, GlobalEnvironment);
            }
        }
        catch (ReturnSignalException ret)
        {
            _diagnostics.ReportError(TextSpan.FromBounds(0, 0), "SyntaxError: 'return' outside function.");
            return ret.Value;
        }
        catch (KiriRuntimeException ex)
        {
            var span = ex.Span ?? new TextSpan(0, 0);
            _diagnostics.ReportError(span, ex.Message);
        }

        return lastValue;
    }

    public KiriValue EvaluateStatement(StatementSyntax statement, KiriEnvironment env)
    {
        switch (statement)
        {
            case ExpressionStatementSyntax exprStmt:
                return EvaluateExpression(exprStmt.Expression, env);

            case VariableDeclarationOrAssignmentSyntax varStmt:
            {
                var val = EvaluateExpression(varStmt.Initializer, env);
                env.SetOrAssign(varStmt.Name, val);
                return val;
            }

            case FunctionDeclarationSyntax fnStmt:
            {
                var fn = new KiriFunction(fnStmt.Name, fnStmt.Parameters, fnStmt.ReturnType, fnStmt.Body, env);
                var fnVal = KiriValue.FromFunction(fn);
                env.Define(fnStmt.Name, fnVal);
                return fnVal;
            }

            case ReturnStatementSyntax retStmt:
            {
                var val = retStmt.Expression != null ? EvaluateExpression(retStmt.Expression, env) : KiriValue.Null;
                throw new ReturnSignalException(val);
            }

            case IfStatementSyntax ifStmt:
            {
                var cond = EvaluateExpression(ifStmt.Condition, env);
                if (cond.IsTruthy)
                {
                    return EvaluateBlock(ifStmt.ThenBlock, env);
                }

                foreach (var elif in ifStmt.ElifClauses)
                {
                    var elifCond = EvaluateExpression(elif.Condition, env);
                    if (elifCond.IsTruthy)
                    {
                        return EvaluateBlock(elif.Block, env);
                    }
                }

                if (ifStmt.ElseClause != null)
                {
                    return EvaluateBlock(ifStmt.ElseClause.Block, env);
                }

                return KiriValue.Null;
            }

            case WhileStatementSyntax whileStmt:
            {
                KiriValue last = KiriValue.Null;
                while (EvaluateExpression(whileStmt.Condition, env).IsTruthy)
                {
                    last = EvaluateBlock(whileStmt.Body, env);
                }
                return last;
            }

            case BlockSyntax blockStmt:
                return EvaluateBlock(blockStmt, env);

            case PassStatementSyntax:
                return KiriValue.Null;

            default:
                throw new KiriRuntimeException($"Unknown statement type: {statement.GetType().Name}", statement.Span);
        }
    }

    public KiriValue EvaluateBlock(BlockSyntax block, KiriEnvironment env)
    {
        // Block shares current lexical scope for variables unless it's a function boundary
        KiriValue last = KiriValue.Null;
        foreach (var stmt in block.Statements)
        {
            last = EvaluateStatement(stmt, env);
        }
        return last;
    }

    public KiriValue EvaluateExpression(ExpressionSyntax expression, KiriEnvironment env)
    {
        switch (expression)
        {
            case LiteralExpressionSyntax lit:
                return EvaluateLiteral(lit);

            case IdentifierExpressionSyntax id:
            {
                if (env.TryLookup(id.Name, out var val))
                {
                    return val;
                }
                throw new KiriRuntimeException($"NameError: Name '{id.Name}' is not defined.", id.Span);
            }

            case ParenthesizedExpressionSyntax paren:
                return EvaluateExpression(paren.Expression, env);

            case UnaryExpressionSyntax unary:
            {
                var operand = EvaluateExpression(unary.Operand, env);
                return unary.Operator.Kind switch
                {
                    SyntaxKind.MinusToken => Negate(operand, unary.Span),
                    SyntaxKind.PlusToken => Plus(operand, unary.Span),
                    SyntaxKind.NotKeyword or SyntaxKind.BangToken => KiriValue.FromBool(!operand.IsTruthy),
                    _ => throw new KiriRuntimeException($"Unsupported unary operator '{unary.Operator.Text}'.", unary.Span)
                };
            }

            case BinaryExpressionSyntax binary:
                return EvaluateBinary(binary, env);

            case CallExpressionSyntax call:
                return EvaluateCall(call, env);

            default:
                throw new KiriRuntimeException($"Unknown expression type: {expression.GetType().Name}", expression.Span);
        }
    }

    private static KiriValue EvaluateLiteral(LiteralExpressionSyntax lit)
    {
        return lit.Token.Kind switch
        {
            SyntaxKind.IntegerLiteral => KiriValue.FromInt((long)(lit.Value ?? 0L)),
            SyntaxKind.FloatLiteral => KiriValue.FromFloat((double)(lit.Value ?? 0.0)),
            SyntaxKind.StringLiteral => KiriValue.FromString((string)(lit.Value ?? string.Empty)),
            SyntaxKind.BooleanLiteral => KiriValue.FromBool((bool)(lit.Value ?? false)),
            SyntaxKind.NullLiteral => KiriValue.Null,
            _ => KiriValue.Null
        };
    }

    private static KiriValue Negate(KiriValue v, TextSpan span)
    {
        if (v.Type == KiriValueType.Int) return KiriValue.FromInt(-v.AsInt());
        if (v.Type == KiriValueType.Float) return KiriValue.FromFloat(-v.AsFloat());
        throw new KiriRuntimeException($"TypeError: Bad operand type for unary -: '{v.TypeName}'.", span);
    }

    private static KiriValue Plus(KiriValue v, TextSpan span)
    {
        if (v.Type == KiriValueType.Int || v.Type == KiriValueType.Float) return v;
        throw new KiriRuntimeException($"TypeError: Bad operand type for unary +: '{v.TypeName}'.", span);
    }

    private KiriValue EvaluateBinary(BinaryExpressionSyntax binary, KiriEnvironment env)
    {
        // Handle short-circuiting logical operators
        if (binary.Operator.Kind == SyntaxKind.OrKeyword || binary.Operator.Kind == SyntaxKind.PipePipeToken)
        {
            var left = EvaluateExpression(binary.Left, env);
            if (left.IsTruthy) return left;
            return EvaluateExpression(binary.Right, env);
        }

        if (binary.Operator.Kind == SyntaxKind.AndKeyword || binary.Operator.Kind == SyntaxKind.AmpersandAmpersandToken)
        {
            var left = EvaluateExpression(binary.Left, env);
            if (!left.IsTruthy) return left;
            return EvaluateExpression(binary.Right, env);
        }

        var leftVal = EvaluateExpression(binary.Left, env);
        var rightVal = EvaluateExpression(binary.Right, env);

        return binary.Operator.Kind switch
        {
            // Arithmetic
            SyntaxKind.PlusToken => Add(leftVal, rightVal, binary.Span),
            SyntaxKind.MinusToken => Subtract(leftVal, rightVal, binary.Span),
            SyntaxKind.StarToken => Multiply(leftVal, rightVal, binary.Span),
            SyntaxKind.SlashToken => Divide(leftVal, rightVal, binary.Span),
            SyntaxKind.PercentToken => Modulo(leftVal, rightVal, binary.Span),
            SyntaxKind.DoubleStarToken => Power(leftVal, rightVal, binary.Span),

            // Equality
            SyntaxKind.EqualEqualToken => KiriValue.FromBool(leftVal == rightVal),
            SyntaxKind.BangEqualToken => KiriValue.FromBool(leftVal != rightVal),

            // Comparison
            SyntaxKind.LessToken => KiriValue.FromBool(Compare(leftVal, rightVal, binary.Span) < 0),
            SyntaxKind.LessOrEqualToken => KiriValue.FromBool(Compare(leftVal, rightVal, binary.Span) <= 0),
            SyntaxKind.GreaterToken => KiriValue.FromBool(Compare(leftVal, rightVal, binary.Span) > 0),
            SyntaxKind.GreaterOrEqualToken => KiriValue.FromBool(Compare(leftVal, rightVal, binary.Span) >= 0),

            _ => throw new KiriRuntimeException($"Unsupported binary operator '{binary.Operator.Text}'.", binary.Span)
        };
    }

    private static KiriValue Add(KiriValue a, KiriValue b, TextSpan span)
    {
        if (a.Type == KiriValueType.Int && b.Type == KiriValueType.Int)
            return KiriValue.FromInt(a.AsInt() + b.AsInt());

        if (a.Type == KiriValueType.Float && b.Type == KiriValueType.Float)
            return KiriValue.FromFloat(a.AsFloat() + b.AsFloat());

        if (a.Type == KiriValueType.Int && b.Type == KiriValueType.Float)
            return KiriValue.FromFloat(a.AsInt() + b.AsFloat());

        if (a.Type == KiriValueType.Float && b.Type == KiriValueType.Int)
            return KiriValue.FromFloat(a.AsFloat() + b.AsInt());

        if (a.Type == KiriValueType.String && b.Type == KiriValueType.String)
            return KiriValue.FromString(a.AsString() + b.AsString());

        if (a.Type == KiriValueType.String)
            return KiriValue.FromString(a.AsString() + b.ToString());

        if (b.Type == KiriValueType.String)
            return KiriValue.FromString(a.ToString() + b.AsString());

        throw new KiriRuntimeException($"TypeError: Unsupported operand types for +: '{a.TypeName}' and '{b.TypeName}'.", span);
    }

    private static KiriValue Subtract(KiriValue a, KiriValue b, TextSpan span)
    {
        if (a.Type == KiriValueType.Int && b.Type == KiriValueType.Int)
            return KiriValue.FromInt(a.AsInt() - b.AsInt());

        if (a.Type == KiriValueType.Float && b.Type == KiriValueType.Float)
            return KiriValue.FromFloat(a.AsFloat() - b.AsFloat());

        if (a.Type == KiriValueType.Int && b.Type == KiriValueType.Float)
            return KiriValue.FromFloat(a.AsInt() - b.AsFloat());

        if (a.Type == KiriValueType.Float && b.Type == KiriValueType.Int)
            return KiriValue.FromFloat(a.AsFloat() - b.AsInt());

        throw new KiriRuntimeException($"TypeError: Unsupported operand types for -: '{a.TypeName}' and '{b.TypeName}'.", span);
    }

    private static KiriValue Multiply(KiriValue a, KiriValue b, TextSpan span)
    {
        if (a.Type == KiriValueType.Int && b.Type == KiriValueType.Int)
            return KiriValue.FromInt(a.AsInt() * b.AsInt());

        if (a.Type == KiriValueType.Float && b.Type == KiriValueType.Float)
            return KiriValue.FromFloat(a.AsFloat() * b.AsFloat());

        if (a.Type == KiriValueType.Int && b.Type == KiriValueType.Float)
            return KiriValue.FromFloat(a.AsInt() * b.AsFloat());

        if (a.Type == KiriValueType.Float && b.Type == KiriValueType.Int)
            return KiriValue.FromFloat(a.AsFloat() * b.AsInt());

        if (a.Type == KiriValueType.String && b.Type == KiriValueType.Int)
        {
            long times = Math.Max(0, b.AsInt());
            var sb = new StringBuilder();
            for (long i = 0; i < times; i++) sb.Append(a.AsString());
            return KiriValue.FromString(sb.ToString());
        }

        throw new KiriRuntimeException($"TypeError: Unsupported operand types for *: '{a.TypeName}' and '{b.TypeName}'.", span);
    }

    private static KiriValue Divide(KiriValue a, KiriValue b, TextSpan span)
    {
        double denom = b.Type == KiriValueType.Int ? b.AsInt() : (b.Type == KiriValueType.Float ? b.AsFloat() : double.NaN);
        if (denom == 0.0)
            throw new KiriRuntimeException("ZeroDivisionError: Division by zero.", span);

        double num = a.Type == KiriValueType.Int ? a.AsInt() : (a.Type == KiriValueType.Float ? a.AsFloat() : double.NaN);

        if (double.IsNaN(num) || double.IsNaN(denom))
            throw new KiriRuntimeException($"TypeError: Unsupported operand types for /: '{a.TypeName}' and '{b.TypeName}'.", span);

        return KiriValue.FromFloat(num / denom);
    }

    private static KiriValue Modulo(KiriValue a, KiriValue b, TextSpan span)
    {
        if (a.Type == KiriValueType.Int && b.Type == KiriValueType.Int)
        {
            long denom = b.AsInt();
            if (denom == 0) throw new KiriRuntimeException("ZeroDivisionError: Integer division or modulo by zero.", span);
            return KiriValue.FromInt(a.AsInt() % denom);
        }

        throw new KiriRuntimeException($"TypeError: Unsupported operand types for %: '{a.TypeName}' and '{b.TypeName}'.", span);
    }

    private static KiriValue Power(KiriValue a, KiriValue b, TextSpan span)
    {
        if (a.Type == KiriValueType.Int && b.Type == KiriValueType.Int && b.AsInt() >= 0)
        {
            long baseVal = a.AsInt();
            long expVal = b.AsInt();
            long res = 1;
            for (long i = 0; i < expVal; i++) res *= baseVal;
            return KiriValue.FromInt(res);
        }

        double num = a.Type == KiriValueType.Int ? a.AsInt() : (a.Type == KiriValueType.Float ? a.AsFloat() : double.NaN);
        double exp = b.Type == KiriValueType.Int ? b.AsInt() : (b.Type == KiriValueType.Float ? b.AsFloat() : double.NaN);
        if (double.IsNaN(num) || double.IsNaN(exp))
            throw new KiriRuntimeException($"TypeError: Unsupported operand types for **: '{a.TypeName}' and '{b.TypeName}'.", span);

        return KiriValue.FromFloat(Math.Pow(num, exp));
    }

    private static int Compare(KiriValue a, KiriValue b, TextSpan span)
    {
        if (a.Type == KiriValueType.Int && b.Type == KiriValueType.Int)
            return a.AsInt().CompareTo(b.AsInt());

        if (a.Type == KiriValueType.Float && b.Type == KiriValueType.Float)
            return a.AsFloat().CompareTo(b.AsFloat());

        if (a.Type == KiriValueType.Int && b.Type == KiriValueType.Float)
            return ((double)a.AsInt()).CompareTo(b.AsFloat());

        if (a.Type == KiriValueType.Float && b.Type == KiriValueType.Int)
            return a.AsFloat().CompareTo((double)b.AsInt());

        if (a.Type == KiriValueType.String && b.Type == KiriValueType.String)
            return string.CompareOrdinal(a.AsString(), b.AsString());

        throw new KiriRuntimeException($"TypeError: '<' not supported between instances of '{a.TypeName}' and '{b.TypeName}'.", span);
    }

    private KiriValue EvaluateCall(CallExpressionSyntax call, KiriEnvironment env)
    {
        var callee = EvaluateExpression(call.Callee, env);
        var argValues = new List<KiriValue>(call.Arguments.Count);
        foreach (var arg in call.Arguments)
        {
            argValues.Add(EvaluateExpression(arg, env));
        }

        if (callee.Type == KiriValueType.BuiltinFunction)
        {
            var builtin = callee.AsBuiltin();
            try
            {
                return builtin.Implementation(argValues, env);
            }
            catch (KiriRuntimeException kre)
            {
                throw new KiriRuntimeException(kre.Message, kre.Span ?? call.Span);
            }
        }

        if (callee.Type == KiriValueType.Function)
        {
            var fn = callee.AsFunction();
            if (argValues.Count > fn.Parameters.Count)
            {
                throw new KiriRuntimeException(
                    $"TypeError: {fn.Name}() takes at most {fn.Parameters.Count} arguments ({argValues.Count} given).",
                    call.Span);
            }

            var fnEnv = new KiriEnvironment(fn.Closure);

            for (int i = 0; i < fn.Parameters.Count; i++)
            {
                var param = fn.Parameters[i];
                if (i < argValues.Count)
                {
                    fnEnv.Define(param.Name, argValues[i]);
                }
                else if (param.DefaultValue != null)
                {
                    // Fresh evaluation per call! (Design Decision #1)
                    var defaultVal = EvaluateExpression(param.DefaultValue, fn.Closure);
                    fnEnv.Define(param.Name, defaultVal);
                }
                else
                {
                    throw new KiriRuntimeException(
                        $"TypeError: {fn.Name}() missing required positional argument: '{param.Name}'.",
                        call.Span);
                }
            }

            try
            {
                EvaluateBlock(fn.Body, fnEnv);
                return KiriValue.Null;
            }
            catch (ReturnSignalException ret)
            {
                return ret.Value;
            }
        }

        throw new KiriRuntimeException($"TypeError: '{callee.TypeName}' object is not callable.", call.Span);
    }
}
