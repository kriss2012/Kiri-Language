namespace Kiri.Core.Runtime;

public sealed class KiriEnvironment
{
    private readonly Dictionary<string, KiriValue> _variables = new(StringComparer.Ordinal);
    public KiriEnvironment? Parent { get; }

    public KiriEnvironment(KiriEnvironment? parent = null)
    {
        Parent = parent;
    }

    public void Define(string name, KiriValue value)
    {
        _variables[name] = value;
    }

    public bool TryAssign(string name, KiriValue value)
    {
        if (_variables.ContainsKey(name))
        {
            _variables[name] = value;
            return true;
        }

        if (Parent != null)
        {
            return Parent.TryAssign(name, value);
        }

        return false;
    }

    public void SetOrAssign(string name, KiriValue value)
    {
        if (!TryAssign(name, value))
        {
            Define(name, value);
        }
    }

    public bool TryLookup(string name, out KiriValue value)
    {
        if (_variables.TryGetValue(name, out value))
        {
            return true;
        }

        if (Parent != null)
        {
            return Parent.TryLookup(name, out value);
        }

        value = KiriValue.Null;
        return false;
    }

    public IReadOnlyDictionary<string, KiriValue> GetLocalVariables() => _variables;
}
