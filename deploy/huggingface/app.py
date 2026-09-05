"""Entry point for Hugging Face Spaces.

Spaces looks for `app.py` at the repository root and will not be talked out of
it. The real application is `demo/app.py`, which is where it belongs and where
`tests/test_demo_app.py` drives it, so this file exists only to point Spaces at
it without moving anything.

Copy this to the root of the Space, not into this repository — see the README
next to it.
"""

from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

runpy.run_path(str(ROOT / "demo" / "app.py"), run_name="__main__")
