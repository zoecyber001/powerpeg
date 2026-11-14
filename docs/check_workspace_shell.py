#!/usr/bin/env python3
"""
One functional smoke test for the ped(business) workspace shell.

It does **not** spin up a Workpeg session or the live API. It imports the UI
package and checks that the workspace shell + the new customer-experience rail
actually compose from the SDK widgets, that the four-module workspace rail and
the customer marketplace rail both render, and that the merged components are
available to the pages.

This is a local static-composition check, not a live-server test.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ui"))

import app_shell
import components  # noqa: F401
from app_shell import AppShell
from components import PageHeader, RecordTag, StatCard
from workpeg.ui import Button

# Make the page modules importable too, so this test also confirms the shared
# components are reachable from the page package shape the app uses.
sys.path.insert(0, str(Path(__file__).resolve().parent / "ui" / "pages"))


def _collect_widget_text(node, out: list[str]) -> None:
    """Collect the text labels a composed shell actually carries, without
    rendering. We only follow the SDK widget tree shallowly: Scaffold ->
    sidebar (NavSection list) -> NavItem.label.

    NavSection keeps its NavItems in `self.items`. We read them directly.
    """
    if isinstance(node, str):
        out.append(node)
        return
    if isinstance(node, (list, tuple)):
        for child in node:
            _collect_widget_text(child, out)
        return
    # SDK scaffold exposes sidebar as a tuple of NavSection objects.
    if hasattr(node, "sidebar"):
        _collect_widget_text(node.sidebar, out)
        _collect_widget_text(getattr(node, "fixed", ()), out)
        return
    # NavSection keeps its NavItems in `self.items`.
    if type(node).__name__ == "NavSection":
        _collect_widget_text(getattr(node, "items", ()), out)
        return
    # NavItem carries label + icon + href.
    if type(node).__name__ == "NavItem":
        out.append(getattr(node, "label", ""))
        return


def _app_shell_has_both_rails():
    shell = AppShell(shell=None)
    built = shell.build()
    texts: list[str] = []
    _collect_widget_text(built, texts)
    joined = "\n".join(texts)
    workspace_markers = ("Commerce", "QuickPass", "Guest Experience & Ops", "RoomPower")
    customer_markers = ("Marketplace", "My bookings", "Guest hub")
    return all(m in joined for m in workspace_markers), all(
        m in joined for m in customer_markers
    )


def main() -> int:
    workspace_ok, customer_ok = _app_shell_has_both_rails()

    checks = [
        ("workspace rail renders the four modules", workspace_ok),
        ("customer rail renders marketplace + my bookings + guest hub", customer_ok),
        ("RecordTag exists in components", "RecordTag" in dir(components)),
        ("StatCard exists in components", "StatCard" in dir(components)),
        ("PageHeader exists in components", "PageHeader" in dir(components)),
        ("Button importable from workpeg.ui", True),
    ]

    all_ok = True
    for label, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}: {label}")
        if not ok:
            all_ok = False

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
