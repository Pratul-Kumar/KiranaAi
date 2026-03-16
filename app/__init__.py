from pathlib import Path

_backend_app = Path(__file__).resolve().parent.parent / "backend" / "app"
__path__ = [str(_backend_app)]
