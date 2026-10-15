using System.Collections.Immutable;

namespace Kiri.Core.Diagnostics;

public sealed class SourceText
{
    private readonly string _text;
    private readonly ImmutableArray<int> _lineStarts;

    public string FileName { get; }
    public string Text => _text;
    public int Length => _text.Length;

    public SourceText(string text, string fileName = "<stdin>")
    {
        _text = text ?? string.Empty;
        FileName = fileName;
        _lineStarts = BuildLineStarts(_text);
    }

    public static SourceText From(string text, string fileName = "<stdin>") => new(text, fileName);

    public int LineCount => _lineStarts.Length;

    public int GetLineIndex(int position)
    {
        if (position < 0) return 0;
        if (position >= _text.Length && _text.Length > 0) position = _text.Length - 1;

        int lower = 0;
        int upper = _lineStarts.Length - 1;

        while (lower <= upper)
        {
            int mid = lower + (upper - lower) / 2;
            int start = _lineStarts[mid];

            if (position < start)
            {
                upper = mid - 1;
            }
            else
            {
                int nextStart = (mid + 1 < _lineStarts.Length) ? _lineStarts[mid + 1] : _text.Length + 1;
                if (position < nextStart)
                    return mid;
                lower = mid + 1;
            }
        }

        return Math.Max(0, lower - 1);
    }

    public (int Line, int Column) GetLineAndColumn(int position)
    {
        int lineIndex = GetLineIndex(position);
        int lineStart = _lineStarts[lineIndex];
        int column = Math.Max(1, position - lineStart + 1);
        return (lineIndex + 1, column);
    }

    public string GetLineText(int lineIndex)
    {
        if (lineIndex < 0 || lineIndex >= _lineStarts.Length)
            return string.Empty;

        int start = _lineStarts[lineIndex];
        int end = (lineIndex + 1 < _lineStarts.Length) ? _lineStarts[lineIndex + 1] : _text.Length;

        // Strip trailing \r or \n
        while (end > start && (_text[end - 1] == '\r' || _text[end - 1] == '\n'))
        {
            end--;
        }

        return _text[start..end];
    }

    private static ImmutableArray<int> BuildLineStarts(string text)
    {
        var list = ImmutableArray.CreateBuilder<int>();
        list.Add(0);

        for (int i = 0; i < text.Length; i++)
        {
            char c = text[i];
            if (c == '\r')
            {
                if (i + 1 < text.Length && text[i + 1] == '\n')
                {
                    i++;
                }
                list.Add(i + 1);
            }
            else if (c == '\n')
            {
                list.Add(i + 1);
            }
        }

        return list.ToImmutable();
    }
}
