"""Import every module of src/ and app/ to catch broken imports (ticket #41).

Run from anywhere: python scripts/check_imports.py
Exit code 0 if every module imports, 1 otherwise. It is the import check that
the CI workflow runs on every pull request.
"""
import importlib
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# The training modules are plain scripts that import each other by bare name.
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

# A Streamlit script runs its UI code on import, so it is not an importable module.
SKIP = {"app.main"}


def module_names() -> list[str]:
    names = [path.stem for path in sorted((ROOT / "src").glob("*.py"))]
    for path in sorted((ROOT / "app").glob("*.py")):
        name = f"app.{path.stem}"
        if name not in SKIP:
            names.append(name)
    return names


def main() -> int:
    failures = []
    names = module_names()
    for name in names:
        try:
            importlib.import_module(name)
            print(f"ok    {name}")
        except Exception:
            failures.append(name)
            print(f"FAIL  {name}")
            traceback.print_exc()
    if failures:
        print(f"\n{len(failures)} module(s) failed to import: {', '.join(failures)}")
        return 1
    print(f"\nAll {len(names)} modules import correctly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
