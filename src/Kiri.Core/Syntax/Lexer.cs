using System.Globalization;
using System.Text;
using Kiri.Core.Diagnostics;

namespace Kiri.Core.Syntax;

public sealed class Lexer
{
    private readonly SourceText _source;
    private readonly DiagnosticBag _diagnostics;
    private readonly string _text;
    private int _position;

    // Indentation tracking
    private readonly Stack<int> _indentStack = new();
    private readonly Queue<SyntaxToken> _pendingTokens = new();
    private int _openBracketNesting = 0;
    private bool _atLineStart = true;
    private bool _hasEmittedTokensOnLine = false;

    public DiagnosticBag Diagnostics => _diagnostics;

    public Lexer(SourceText source, DiagnosticBag? diagnostics = null)
    {
        _source = source;
        _diagnostics = diagnostics ?? new DiagnosticBag();
        _text = source.Text;
        _indentStack.Push(0);
    }

    private char Current => Peek(0);
    private char Lookahead => Peek(1);

    private char Peek(int offset)
    {
        int index = _position + offset;
        return index >= _text.Length ? '\0' : _text[index];
    }

    public List<SyntaxToken> LexAll()
    {
        var tokens = new List<SyntaxToken>();
        SyntaxToken token;
        do
        {
            token = NextToken();
            tokens.Add(token);
        } while (token.Kind != SyntaxKind.EndOfFile);

        return tokens;
    }

    public SyntaxToken NextToken()
    {
        if (_pendingTokens.Count > 0)
        {
            return _pendingTokens.Dequeue();
        }

        while (_position < _text.Length)
        {
            if (_atLineStart)
            {
                // Measure leading indentation
                int indentStart = _position;
                int spaces = 0;
                while (_position < _text.Length && (_text[_position] == ' ' || _text[_position] == '\t'))
                {
                    spaces += (_text[_position] == '\t') ? 4 : 1;
                    _position++;
                }

                // Check for blank line or comment-only line
                if (_position < _text.Length && (_text[_position] == '\r' || _text[_position] == '\n'))
                {
                    ConsumePhysicalNewline();
                    continue;
                }

                if (_position < _text.Length && _text[_position] == '#')
                {
                    // Skip comment line
                    while (_position < _text.Length && _text[_position] != '\r' && _text[_position] != '\n')
                    {
                        _position++;
                    }
                    if (_position < _text.Length)
                    {
                        ConsumePhysicalNewline();
                    }
                    continue;
                }

                _atLineStart = false;

                // Only generate INDENT/DEDENT if we are not inside brackets/parentheses
                if (_openBracketNesting == 0)
                {
                    int currentIndent = _indentStack.Peek();
                    if (spaces > currentIndent)
                    {
                        _indentStack.Push(spaces);
                        _pendingTokens.Enqueue(new SyntaxToken(SyntaxKind.Indent, indentStart, new string(' ', spaces)));
                    }
                    else if (spaces < currentIndent)
                    {
                        while (_indentStack.Count > 1 && _indentStack.Peek() > spaces)
                        {
                            _indentStack.Pop();
                            _pendingTokens.Enqueue(new SyntaxToken(SyntaxKind.Dedent, indentStart, string.Empty));
                        }

                        if (_indentStack.Peek() != spaces)
                        {
                            _diagnostics.ReportError(
                                new TextSpan(indentStart, Math.Max(1, _position - indentStart)),
                                "IndentationError: Unindent does not match any outer indentation level.",
                                "Ensure line indentation matches the outer block's indentation level (e.g. 4 spaces).");
                        }
                    }

                    if (_pendingTokens.Count > 0)
                    {
                        return _pendingTokens.Dequeue();
                    }
                }
            }

            // Normal token scanning
            char c = Current;

            // Horizontal whitespace
            if (c == ' ' || c == '\t')
            {
                _position++;
                continue;
            }

            // Comments
            if (c == '#')
            {
                while (_position < _text.Length && _text[_position] != '\r' && _text[_position] != '\n')
                {
                    _position++;
                }
                continue;
            }

            // Explicit line continuation backslash '\'
            if (c == '\\' && (Lookahead == '\r' || Lookahead == '\n'))
            {
                _position++;
                ConsumePhysicalNewline();
                continue;
            }

            // Newline
            if (c == '\r' || c == '\n')
            {
                int newlinePos = _position;
                ConsumePhysicalNewline();
                _atLineStart = true;

                if (_openBracketNesting == 0 && _hasEmittedTokensOnLine)
                {
                    _hasEmittedTokensOnLine = false;
                    return new SyntaxToken(SyntaxKind.NewLine, newlinePos, "\n");
                }
                continue;
            }

            _hasEmittedTokensOnLine = true;

            // Numbers
            if (char.IsAsciiDigit(c))
            {
                return ScanNumber();
            }

            // Identifiers / Keywords
            if (char.IsLetter(c) || c == '_')
            {
                return ScanIdentifierOrKeyword();
            }

            // Strings
            if (c == '"' || c == '\'')
            {
                return ScanString();
            }

            // Two-character operators
            int start = _position;
            if (c == '=' && Lookahead == '=')
            {
                _position += 2;
                return new SyntaxToken(SyntaxKind.EqualEqualToken, start, "==");
            }
            if (c == '!' && Lookahead == '=')
            {
                _position += 2;
                return new SyntaxToken(SyntaxKind.BangEqualToken, start, "!=");
            }
            if (c == '<' && Lookahead == '=')
            {
                _position += 2;
                return new SyntaxToken(SyntaxKind.LessOrEqualToken, start, "<=");
            }
            if (c == '>' && Lookahead == '=')
            {
                _position += 2;
                return new SyntaxToken(SyntaxKind.GreaterOrEqualToken, start, ">=");
            }
            if (c == '-' && Lookahead == '>')
            {
                _position += 2;
                return new SyntaxToken(SyntaxKind.ArrowToken, start, "->");
            }
            if (c == '*' && Lookahead == '*')
            {
                _position += 2;
                return new SyntaxToken(SyntaxKind.DoubleStarToken, start, "**");
            }
            if (c == '&' && Lookahead == '&')
            {
                _position += 2;
                return new SyntaxToken(SyntaxKind.AmpersandAmpersandToken, start, "&&");
            }
            if (c == '|' && Lookahead == '|')
            {
                _position += 2;
                return new SyntaxToken(SyntaxKind.PipePipeToken, start, "||");
            }

            // Single-character operators & delimiters
            _position++;
            switch (c)
            {
                case '+': return new SyntaxToken(SyntaxKind.PlusToken, start, "+");
                case '-': return new SyntaxToken(SyntaxKind.MinusToken, start, "-");
                case '*': return new SyntaxToken(SyntaxKind.StarToken, start, "*");
                case '/': return new SyntaxToken(SyntaxKind.SlashToken, start, "/");
                case '%': return new SyntaxToken(SyntaxKind.PercentToken, start, "%");
                case '=': return new SyntaxToken(SyntaxKind.EqualToken, start, "=");
                case '<': return new SyntaxToken(SyntaxKind.LessToken, start, "<");
                case '>': return new SyntaxToken(SyntaxKind.GreaterToken, start, ">");
                case '!': return new SyntaxToken(SyntaxKind.BangToken, start, "!");
                case ':': return new SyntaxToken(SyntaxKind.ColonToken, start, ":");
                case ',': return new SyntaxToken(SyntaxKind.CommaToken, start, ",");
                case '.': return new SyntaxToken(SyntaxKind.DotToken, start, ".");

                case '(':
                    _openBracketNesting++;
                    return new SyntaxToken(SyntaxKind.OpenParenToken, start, "(");
                case ')':
                    if (_openBracketNesting > 0) _openBracketNesting--;
                    return new SyntaxToken(SyntaxKind.CloseParenToken, start, ")");
                case '[':
                    _openBracketNesting++;
                    return new SyntaxToken(SyntaxKind.OpenBracketToken, start, "[");
                case ']':
                    if (_openBracketNesting > 0) _openBracketNesting--;
                    return new SyntaxToken(SyntaxKind.CloseBracketToken, start, "]");
                case '{':
                    _openBracketNesting++;
                    return new SyntaxToken(SyntaxKind.OpenBraceToken, start, "{");
                case '}':
                    if (_openBracketNesting > 0) _openBracketNesting--;
                    return new SyntaxToken(SyntaxKind.CloseBraceToken, start, "}");

                default:
                    _diagnostics.ReportError(new TextSpan(start, 1), $"Unexpected character '{c}'.");
                    return new SyntaxToken(SyntaxKind.BadToken, start, c.ToString());
            }
        }

        // Emit trailing NEWLINE if needed
        if (_hasEmittedTokensOnLine)
        {
            _hasEmittedTokensOnLine = false;
            _pendingTokens.Enqueue(new SyntaxToken(SyntaxKind.NewLine, _position, "\n"));
        }

        // Emit remaining DEDENT tokens
        while (_indentStack.Count > 1)
        {
            _indentStack.Pop();
            _pendingTokens.Enqueue(new SyntaxToken(SyntaxKind.Dedent, _position, string.Empty));
        }

        if (_pendingTokens.Count > 0)
        {
            return _pendingTokens.Dequeue();
        }

        return new SyntaxToken(SyntaxKind.EndOfFile, _position, string.Empty);
    }

    private void ConsumePhysicalNewline()
    {
        if (Current == '\r' && Lookahead == '\n')
        {
            _position += 2;
        }
        else if (Current == '\n' || Current == '\r')
        {
            _position++;
        }
    }

    private SyntaxToken ScanNumber()
    {
        int start = _position;
        bool isHex = false;
        bool isBinary = false;
        bool isOctal = false;

        if (Current == '0' && (_position + 1 < _text.Length))
        {
            char next = char.ToLowerInvariant(Lookahead);
            if (next == 'x') { isHex = true; _position += 2; }
            else if (next == 'b') { isBinary = true; _position += 2; }
            else if (next == 'o') { isOctal = true; _position += 2; }
        }

        if (isHex)
        {
            while (_position < _text.Length && (char.IsAsciiHexDigit(Current) || Current == '_'))
                _position++;

            string raw = _text[start.._position].Replace("_", string.Empty);
            long hexVal = Convert.ToInt64(raw[2..], 16);
            return new SyntaxToken(SyntaxKind.IntegerLiteral, start, _text[start.._position], hexVal);
        }

        if (isBinary)
        {
            while (_position < _text.Length && (Current == '0' || Current == '1' || Current == '_'))
                _position++;

            string raw = _text[start.._position].Replace("_", string.Empty);
            long binVal = Convert.ToInt64(raw[2..], 2);
            return new SyntaxToken(SyntaxKind.IntegerLiteral, start, _text[start.._position], binVal);
        }

        if (isOctal)
        {
            while (_position < _text.Length && ((Current >= '0' && Current <= '7') || Current == '_'))
                _position++;

            string raw = _text[start.._position].Replace("_", string.Empty);
            long octVal = Convert.ToInt64(raw[2..], 8);
            return new SyntaxToken(SyntaxKind.IntegerLiteral, start, _text[start.._position], octVal);
        }

        // Standard decimal or float
        bool hasDot = false;
        bool hasExp = false;

        while (_position < _text.Length)
        {
            char ch = Current;
            if (char.IsAsciiDigit(ch) || ch == '_')
            {
                _position++;
            }
            else if (ch == '.' && !hasDot && !hasExp && char.IsAsciiDigit(Lookahead))
            {
                hasDot = true;
                _position++;
            }
            else if ((ch == 'e' || ch == 'E') && !hasExp)
            {
                hasExp = true;
                _position++;
                if (Current == '+' || Current == '-')
                    _position++;
            }
            else
            {
                break;
            }
        }

        string text = _text[start.._position];
        string clean = text.Replace("_", string.Empty);

        if (hasDot || hasExp)
        {
            if (double.TryParse(clean, NumberStyles.Float, CultureInfo.InvariantCulture, out double fVal))
            {
                return new SyntaxToken(SyntaxKind.FloatLiteral, start, text, fVal);
            }
            _diagnostics.ReportError(new TextSpan(start, text.Length), $"Invalid floating point literal '{text}'.");
            return new SyntaxToken(SyntaxKind.FloatLiteral, start, text, 0.0);
        }
        else
        {
            if (long.TryParse(clean, NumberStyles.Integer, CultureInfo.InvariantCulture, out long iVal))
            {
                return new SyntaxToken(SyntaxKind.IntegerLiteral, start, text, iVal);
            }
            _diagnostics.ReportError(new TextSpan(start, text.Length), $"Integer literal '{text}' overflows 64-bit integer.");
            return new SyntaxToken(SyntaxKind.IntegerLiteral, start, text, 0L);
        }
    }

    private SyntaxToken ScanIdentifierOrKeyword()
    {
        int start = _position;
        while (_position < _text.Length && (char.IsLetterOrDigit(Current) || Current == '_'))
        {
            _position++;
        }

        string text = _text[start.._position];
        SyntaxKind kind = SyntaxFacts.GetKeywordKind(text);

        object? val = kind switch
        {
            SyntaxKind.TrueKeyword => true,
            SyntaxKind.FalseKeyword => false,
            _ => null
        };

        if (kind == SyntaxKind.TrueKeyword || kind == SyntaxKind.FalseKeyword)
        {
            return new SyntaxToken(SyntaxKind.BooleanLiteral, start, text, val);
        }
        if (kind == SyntaxKind.NullKeyword)
        {
            return new SyntaxToken(SyntaxKind.NullLiteral, start, text, null);
        }

        return new SyntaxToken(kind, start, text, val);
    }

    private SyntaxToken ScanString()
    {
        char quote = Current;
        int start = _position;
        _position++; // Skip opening quote

        var sb = new StringBuilder();
        bool closed = false;

        while (_position < _text.Length)
        {
            char c = Current;
            if (c == quote)
            {
                _position++;
                closed = true;
                break;
            }
            if (c == '\\')
            {
                _position++;
                if (_position >= _text.Length) break;
                char esc = Current;
                _position++;
                switch (esc)
                {
                    case 'n': sb.Append('\n'); break;
                    case 'r': sb.Append('\r'); break;
                    case 't': sb.Append('\t'); break;
                    case '\\': sb.Append('\\'); break;
                    case '"': sb.Append('"'); break;
                    case '\'': sb.Append('\''); break;
                    case '0': sb.Append('\0'); break;
                    default:
                        sb.Append(esc);
                        break;
                }
            }
            else if (c == '\r' || c == '\n')
            {
                _diagnostics.ReportError(new TextSpan(start, _position - start), "Unterminated string literal.");
                break;
            }
            else
            {
                sb.Append(c);
                _position++;
            }
        }

        if (!closed)
        {
            _diagnostics.ReportError(new TextSpan(start, _position - start), "Unclosed string literal.", "Add closing quotation mark.");
        }

        return new SyntaxToken(SyntaxKind.StringLiteral, start, _text[start.._position], sb.ToString());
    }
}
