"""Regression guard: heavy modules must stay out of the startup import graph.

`mytruv --help` ships as a Nuitka onefile binary; every transitive top-level
import on the help path turns into hundreds of milliseconds of dyld + AMFI
work on macOS, which is why v1.0.0 took ~9 s to print help. The fix defers
rich/httpx/oauth machinery until a command actually needs them.

This test fails loudly if a future change adds an eager import that re-pulls
any of those heavy dependencies into the startup path.
"""

import subprocess
import sys
import textwrap

HEAVY_MODULES = ("rich", "httpx", "http.server", "webbrowser")


def test_help_path_does_not_load_heavy_modules() -> None:
    """Importing mytruv_cli.main must not pull rich, httpx, http.server, or webbrowser.

    Run in a fresh subprocess so prior test imports in this process don't pollute sys.modules.
    """
    script = textwrap.dedent(f"""
        import sys
        import mytruv_cli.main  # noqa: F401

        heavy = {HEAVY_MODULES!r}
        loaded = [
            m for m in heavy
            if m in sys.modules or any(name.startswith(m + ".") for name in sys.modules)
        ]
        if loaded:
            print(",".join(loaded))
            sys.exit(1)
    """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Heavy modules leaked into startup imports: {result.stdout.strip()}\n"
        "If you intentionally added a top-level import, move it inside the function "
        "that uses it (see commands/auth.py and client/api.py for the pattern)."
    )
