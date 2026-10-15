using Kiri.Core;
using Kiri.Core.Runtime;

namespace Kiri.Cli;

public static class Program
{
    private const string Version = "0.1.0 (Phase 1 Bootstrap)";

    public static int Main(string[] args)
    {
        if (args.Length == 0)
        {
            return RunRepl();
        }

        string command = args[0];

        switch (command)
        {
            case "--version" or "-v":
                Console.WriteLine($"Kiri {Version}");
                return 0;

            case "--help" or "-h":
                PrintHelp();
                return 0;

            case "repl":
                return RunRepl();

            case "run":
                if (args.Length < 2)
                {
                    Console.ForegroundColor = ConsoleColor.Red;
                    Console.Error.WriteLine("Error: 'kiri run' requires a target .kiri source file.");
                    Console.ResetColor();
                    return 1;
                }
                return RunFile(args[1]);

            default:
                if (command.EndsWith(".kiri") || File.Exists(command))
                {
                    return RunFile(command);
                }

                Console.ForegroundColor = ConsoleColor.Red;
                Console.Error.WriteLine($"Error: Unknown command or file '{command}'.");
                Console.ResetColor();
                PrintHelp();
                return 1;
        }
    }

    private static void PrintHelp()
    {
        Console.WriteLine($"""
        Kiri Programming Language - v{Version}
        "Python-level simplicity with systems-language-level performance."

        Usage:
            kiri <file.kiri>         Execute a Kiri source file
            kiri run <file.kiri>     Execute a Kiri source file
            kiri repl                Start the interactive REPL
            kiri --version           Display version information
            kiri --help              Display this help message
        """);
    }

    private static int RunFile(string path)
    {
        if (!File.Exists(path))
        {
            Console.ForegroundColor = ConsoleColor.Red;
            Console.Error.WriteLine($"Error: Source file '{path}' does not exist.");
            Console.ResetColor();
            return 1;
        }

        string source = File.ReadAllText(path);
        var engine = new KiriEngine();
        var result = engine.Execute(source, Path.GetFileName(path));

        if (!result.Success)
        {
            Console.ForegroundColor = ConsoleColor.Red;
            Console.Error.WriteLine(result.FormattedErrors);
            Console.ResetColor();
            return 1;
        }

        return 0;
    }

    private static int RunRepl()
    {
        Console.WriteLine($"Kiri {Version}");
        Console.WriteLine("Type ':quit' or ':exit' to exit, ':help' for commands.\n");

        var engine = new KiriEngine();

        while (true)
        {
            Console.ForegroundColor = ConsoleColor.Cyan;
            Console.Write(">>> ");
            Console.ResetColor();

            string? line = Console.ReadLine();
            if (line == null) break;

            string trimmed = line.Trim();
            if (trimmed == ":quit" || trimmed == ":exit")
            {
                break;
            }
            if (trimmed == ":help")
            {
                Console.WriteLine("REPL commands: :quit, :exit, :help, :clear");
                continue;
            }
            if (trimmed == ":clear")
            {
                Console.Clear();
                continue;
            }

            if (string.IsNullOrWhiteSpace(line))
            {
                continue;
            }

            // Check if line introduces a block (ends with ':')
            if (trimmed.EndsWith(':'))
            {
                var blockLines = new List<string> { line };
                while (true)
                {
                    Console.ForegroundColor = ConsoleColor.DarkCyan;
                    Console.Write("... ");
                    Console.ResetColor();

                    string? nextLine = Console.ReadLine();
                    if (string.IsNullOrWhiteSpace(nextLine))
                    {
                        break;
                    }
                    blockLines.Add(nextLine);
                }
                line = string.Join("\n", blockLines);
            }

            var result = engine.Execute(line, "<repl>");
            if (!result.Success)
            {
                Console.ForegroundColor = ConsoleColor.Red;
                Console.Error.WriteLine(result.FormattedErrors);
                Console.ResetColor();
            }
            else if (result.Value.Type != KiriValueType.Null)
            {
                Console.ForegroundColor = ConsoleColor.Green;
                Console.WriteLine(result.Value.ToRepr());
                Console.ResetColor();
            }
        }

        return 0;
    }
}
