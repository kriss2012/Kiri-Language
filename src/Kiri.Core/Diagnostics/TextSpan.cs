namespace Kiri.Core.Diagnostics;

public readonly record struct TextSpan(int Start, int Length)
{
    public int End => Start + Length;

    public static TextSpan FromBounds(int start, int end) => new(start, Math.Max(0, end - start));

    public override string ToString() => $"[{Start}..{End})";
}
