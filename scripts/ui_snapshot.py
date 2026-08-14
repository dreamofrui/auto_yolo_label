"""Capture PNG snapshots of every AutoLabeler GUI surface at multiple desktop sizes.

Usage:
    python scripts/ui_snapshot.py [--out DIR] [--size WxH [--size WxH ...]]

Captures the login view and each workbench surface offscreen at one or more
window sizes. Writes one PNG per surface per size into
``out_dir / <width>x<height> / <NN>-<name>.png``.

The default output directory (``.ui-snapshots/``) is git-ignored. PNGs are
not preserved as source assets.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from PySide6.QtWidgets import QApplication  # noqa: E402

from gui.workbench import MODULES, AutoLabelerWindow  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _flush(app: QApplication, count: int = 3) -> None:
    """Let Qt finish layout and deferred work before grabbing pixels."""
    for _ in range(count):
        app.processEvents()


def _grab(window: AutoLabelerWindow, app: QApplication, path: Path) -> None:
    """Write one snapshot of the window's current state."""
    _flush(app)
    window.grab().save(str(path))
    print(f"  wrote {path.name}")


def _capture_surface(
    window: AutoLabelerWindow,
    app: QApplication,
    dest: Path,
    index: int,
    name: str,
    show_fn,
) -> None:
    """Call *show_fn*, flush, grab, and save to *dest*."""
    show_fn()
    path = dest / f"{index:02d}-{name}.png"
    _grab(window, app, path)


# ---------------------------------------------------------------------------
# Main capture
# ---------------------------------------------------------------------------

def capture(out_dir: Path, width: int, height: int) -> None:
    """Capture one PNG per GUI surface into ``out_dir / <W>x<H>/``."""
    size_dir = out_dir / f"{width}x{height}"
    size_dir.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication(sys.argv[:1])

    window = AutoLabelerWindow()
    window.resize(width, height)
    window.show()

    # --- Login ------------------------------------------------------------
    _capture_surface(window, app, size_dir, 1, "login", lambda: None)

    # --- Workbench (home) -------------------------------------------------
    window.enter_workbench()
    view = window.workbench_view
    _capture_surface(window, app, size_dir, 2, "home", lambda: None)

    # --- Module pages -----------------------------------------------------
    module_start = 3
    for offset, module in enumerate(MODULES):
        _capture_surface(
            window, app, size_dir,
            module_start + offset,
            module.key,
            lambda key=module.key: view.show_module(key),
        )

    # --- Task center, manual, settings ------------------------------------
    tail_start = module_start + len(MODULES)
    extra_surfaces = [
        ("task-center", view.show_task_center),
        ("manual", view.show_manual),
        ("settings", view.show_settings),
    ]
    for offset, (name, show_fn) in enumerate(extra_surfaces):
        _capture_surface(
            window, app, size_dir,
            tail_start + offset,
            name,
            show_fn,
        )

    window.close()
    print(f"  [{width}x{height}] {len(MODULES) + 2 + len(extra_surfaces)} surfaces captured")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_size(raw: str) -> tuple[int, int]:
    """Parse a ``WxH`` string into ``(width, height)``."""
    w_str, _, h_str = raw.partition("x")
    return int(w_str), int(h_str)


def main() -> int:
    """Parse arguments and capture snapshots at each configured size."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=_REPO_ROOT / ".ui-snapshots",
        help="output directory for PNG snapshots (default: .ui-snapshots/)",
    )
    parser.add_argument(
        "--size",
        action="append",
        dest="sizes",
        help="window size as WxH (can be repeated; default: 1440x900 1280x720)",
    )
    args = parser.parse_args()

    # Parse sizes -----------------------------------------------------------
    if args.sizes:
        sizes = [_parse_size(s) for s in args.sizes]
    else:
        sizes = [(1440, 900), (1280, 720)]

    for width, height in sizes:
        capture(args.out, width, height)

    print(f"\nDone. Snapshots written to {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
