#!/usr/bin/env python3
"""
Release helper for AERA Agent.

Usage:
    python build_tools/release.py 0.1.0          # tag a new release
    python build_tools/release.py 0.1.0 --dry    # show what would change

What it does:
  1. Updates the version string in 4 files (pyproject.toml,
     aera_agent/__init__.py, aera.spec, build.py).
  2. Inserts a "[X.Y.Z] — YYYY-MM-DD" header at the top of CHANGELOG.md
     (or warns if it's already there).
  3. Runs `python -m py_compile` on every .py in aera_agent/ as a sanity check.
  4. Prints the git commands you should run to commit + tag the release.
"""

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# File → list of (regex, replacement-template-with-{ver})
VERSION_FILES = {
    ROOT / "pyproject.toml":               [(r'^version\s*=\s*".*"', 'version     = "{ver}"')],
    ROOT / "aera_agent" / "__init__.py":   [(r'^__version__\s*=\s*".*"', '__version__ = "{ver}"')],
    ROOT / "build_tools" / "aera.spec":    [(r'"CFBundleShortVersionString":\s*".*"',
                                              '"CFBundleShortVersionString": "{ver}"')],
    ROOT / "build_tools" / "build.py":     [(r'^AppVersion=.*', 'AppVersion={ver}')],
}


def bump_versions(ver: str, dry: bool) -> None:
    print(f"\n── Updating version → {ver} in:")
    for path, patterns in VERSION_FILES.items():
        if not path.exists():
            print(f"  ⚠  missing {path}"); continue
        src = path.read_text(encoding="utf-8")
        new = src
        for pat, tmpl in patterns:
            new = re.sub(pat, tmpl.format(ver=ver), new, count=1, flags=re.M)
        if new == src:
            print(f"  ·   {path.relative_to(ROOT)}  (no change)")
        else:
            print(f"  ✓   {path.relative_to(ROOT)}")
            if not dry:
                path.write_text(new, encoding="utf-8")


def bump_changelog(ver: str, dry: bool) -> None:
    path = ROOT / "CHANGELOG.md"
    if not path.exists():
        print(f"\n⚠  No CHANGELOG.md — skipping"); return
    src = path.read_text(encoding="utf-8")
    if f"[{ver}]" in src:
        print(f"\n── CHANGELOG already has [{ver}] — leaving alone")
        return
    today = dt.date.today().isoformat()
    header = f"\n## [{ver}] — {today}\n\n_(describe changes)_\n\n---\n"
    new = re.sub(r"(?m)^(## .)", header + r"\n\1", src, count=1)
    print(f"\n── Inserting CHANGELOG entry for {ver} ({today})")
    if not dry:
        path.write_text(new, encoding="utf-8")


def run_compile_check() -> bool:
    print("\n── Compile-checking all .py files…")
    files = list((ROOT / "aera_agent").rglob("*.py"))
    try:
        subprocess.run([sys.executable, "-m", "py_compile", *map(str, files)],
                       check=True)
        print(f"  ✓ {len(files)} files compile clean")
        return True
    except subprocess.CalledProcessError:
        print("  ✗ COMPILE FAILED — fix errors before tagging.")
        return False


def print_git_commands(ver: str) -> None:
    print(f"""
────────────────────────────────────────────────────────
✓ Local files updated. To publish:

    git add -A
    git commit -m "Release v{ver}"
    git tag v{ver}
    git push && git push --tags

The Release workflow (.github/workflows/release.yml) will then:
  1. Build AERA on Windows, macOS, and Linux runners
  2. Attach the bundles + installers to a GitHub Release
  3. Use CHANGELOG.md as the release notes
────────────────────────────────────────────────────────
""")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("version", help="Semantic version, e.g. 0.1.0")
    parser.add_argument("--dry", action="store_true",
                        help="Show what would change, but don't write")
    args = parser.parse_args()

    if not re.match(r"^\d+\.\d+\.\d+(-[a-z0-9.]+)?$", args.version):
        sys.exit(f"Bad version string: {args.version!r}  (use semver, e.g. 0.1.0)")

    print(f"== Preparing AERA Agent v{args.version} ==")
    bump_versions(args.version, args.dry)
    bump_changelog(args.version, args.dry)

    if not args.dry and not run_compile_check():
        sys.exit(1)

    if args.dry:
        print("\n(dry run — no files modified)")
    else:
        print_git_commands(args.version)


if __name__ == "__main__":
    main()
