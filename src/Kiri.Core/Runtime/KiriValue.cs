using System.Globalization;

namespace Kiri.Core.Runtime;

public enum KiriValueType : byte
{
    Null,
    Bool,
    Int,
    Float,
    String,
    Function,
    BuiltinFunction
}

public readonly struct KiriValue : IEquatable<KiriValue>
{
    public KiriValueType Type { get; }
    public long IntBits { get; }
    public object? ObjectValue { get; }

    public static readonly KiriValue Null = new(KiriValueType.Null, 0, null);
    public static readonly KiriValue True = new(KiriValueType.Bool, 1, null);
    public static readonly KiriValue False = new(KiriValueType.Bool, 0, null);

    private KiriValue(KiriValueType type, long intBits, object? objectValue)
    {
        Type = type;
        IntBits = intBits;
        ObjectValue = objectValue;
    }

    public static KiriValue FromBool(bool value) => value ? True : False;
    public static KiriValue FromInt(long value) => new(KiriValueType.Int, value, null);
    public static KiriValue FromFloat(double value) => new(KiriValueType.Float, BitConverter.DoubleToInt64Bits(value), null);
    public static KiriValue FromString(string value) => new(KiriValueType.String, 0, value);
    public static KiriValue FromFunction(KiriFunction fn) => new(KiriValueType.Function, 0, fn);
    public static KiriValue FromBuiltin(KiriBuiltinFunction fn) => new(KiriValueType.BuiltinFunction, 0, fn);

    public bool AsBool() => IntBits != 0;
    public long AsInt() => IntBits;
    public double AsFloat() => BitConverter.Int64BitsToDouble(IntBits);
    public string AsString() => (string)(ObjectValue ?? string.Empty);
    public KiriFunction AsFunction() => (KiriFunction)ObjectValue!;
    public KiriBuiltinFunction AsBuiltin() => (KiriBuiltinFunction)ObjectValue!;

    public bool IsTruthy => Type switch
    {
        KiriValueType.Null => false,
        KiriValueType.Bool => AsBool(),
        KiriValueType.Int => AsInt() != 0,
        KiriValueType.Float => AsFloat() != 0.0,
        KiriValueType.String => !string.IsNullOrEmpty(AsString()),
        _ => true
    };

    public string TypeName => Type switch
    {
        KiriValueType.Null => "Null",
        KiriValueType.Bool => "Bool",
        KiriValueType.Int => "Int",
        KiriValueType.Float => "Float",
        KiriValueType.String => "String",
        KiriValueType.Function => "Function",
        KiriValueType.BuiltinFunction => "BuiltinFunction",
        _ => "Unknown"
    };

    public override string ToString() => Type switch
    {
        KiriValueType.Null => "null",
        KiriValueType.Bool => AsBool() ? "true" : "false",
        KiriValueType.Int => AsInt().ToString(CultureInfo.InvariantCulture),
        KiriValueType.Float => AsFloat().ToString(CultureInfo.InvariantCulture),
        KiriValueType.String => AsString(),
        KiriValueType.Function => $"<function {AsFunction().Name}>",
        KiriValueType.BuiltinFunction => $"<builtin {AsBuiltin().Name}>",
        _ => "unknown"
    };

    public string ToRepr() => Type switch
    {
        KiriValueType.String => $"\"{AsString().Replace("\"", "\\\"")}\"",
        _ => ToString()
    };

    public bool Equals(KiriValue other)
    {
        if (Type != other.Type)
        {
            if (Type == KiriValueType.Int && other.Type == KiriValueType.Float)
                return AsInt() == other.AsFloat();
            if (Type == KiriValueType.Float && other.Type == KiriValueType.Int)
                return AsFloat() == other.AsInt();
            return false;
        }

        return Type switch
        {
            KiriValueType.Null => true,
            KiriValueType.Bool => AsBool() == other.AsBool(),
            KiriValueType.Int => AsInt() == other.AsInt(),
            KiriValueType.Float => AsFloat() == other.AsFloat(),
            KiriValueType.String => string.Equals(AsString(), other.AsString(), StringComparison.Ordinal),
            KiriValueType.Function => ReferenceEquals(ObjectValue, other.ObjectValue),
            KiriValueType.BuiltinFunction => ReferenceEquals(ObjectValue, other.ObjectValue),
            _ => false
        };
    }

    public override bool Equals(object? obj) => obj is KiriValue other && Equals(other);

    public override int GetHashCode() => Type switch
    {
        KiriValueType.Null => 0,
        KiriValueType.Bool => AsBool().GetHashCode(),
        KiriValueType.Int => AsInt().GetHashCode(),
        KiriValueType.Float => AsFloat().GetHashCode(),
        KiriValueType.String => AsString().GetHashCode(StringComparison.Ordinal),
        _ => ObjectValue?.GetHashCode() ?? 0
    };

    public static bool operator ==(KiriValue left, KiriValue right) => left.Equals(right);
    public static bool operator !=(KiriValue left, KiriValue right) => !left.Equals(right);
}
