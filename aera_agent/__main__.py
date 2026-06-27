"""Entry point: `python -m aera_agent [cli|gui]`."""

import sys


def main() -> None:
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "gui"
    if mode in ("cli", "terminal", "repl"):
        from .cli import main as cli_main
        cli_main()
    elif mode in ("gui", "ui", "desktop", ""):
        from .gui.app import main as gui_main
        gui_main()
    elif mode in ("-h", "--help", "help"):
        print(__doc__ or "Usage: python -m aera_agent [cli|gui]")
    else:
        print(f"Unknown mode: {mode!r}. Use 'cli' or 'gui'.")
        sys.exit(2)


if __name__ == "__main__":
    main()
