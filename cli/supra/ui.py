"""Rich rendering helpers for the Supra-Codex CLI.

Tiny wrappers so command handlers read clearly and output stays consistent:
colored status text, tables for nodes and marketplace listings, a progress
spinner for long-running operations, and rich error printing.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console(width=120)

ACCENT = "cyan"
OK = "green"
WARN = "yellow"
ERR = "red"


def status_text(status: str) -> Text:
    """Render a pipeline/node status with an appropriate color."""
    mapping = {
        "online": "green",
        "running": "green",
        "completed": "green",
        "success": "green",
        "idle": "cyan",
        "queued": "cyan",
        "paused": "yellow",
        "pending": "yellow",
        "offline": "red",
        "failed": "red",
        "skipped": "yellow",
        "error": "red",
    }
    return Text(status, style=mapping.get(str(status).lower(), ACCENT))


def error(message: str, status_code: Optional[int] = None) -> None:
    suffix = f" (HTTP {status_code})" if status_code is not None else ""
    console.print(Text(f"✗ {message}{suffix}", style=ERR))


def success(message: str) -> None:
    console.print(Text(f"✓ {message}", style=OK))


def _confirm(msg: str) -> bool:
    answer = console.input(f"{msg} [y/N]: ").strip().lower()
    return answer in ("y", "yes")


def build_nodes_table(nodes: Iterable[Dict[str, Any]]) -> Table:
    table = Table(title="Active Nodes", title_style=f"bold {ACCENT}")
    table.add_column("Hostname", style="bold")
    table.add_column("ID", style="dim")
    table.add_column("Region")
    table.add_column("Capabilities")
    table.add_column("CPU %", justify="right")
    table.add_column("RAM (MB)", justify="right")
    table.add_column("Tasks", justify="right")
    table.add_column("Status")
    for n in nodes:
        caps = ", ".join(n.get("capabilities", [])) or "—"
        table.add_row(
            n.get("hostname", n.get("id", "?")),
            (n.get("id") or "")[:8],
            n.get("region", "unknown"),
            caps,
            f"{float(n.get('cpu', 0)):.1f}",
            f"{float(n.get('ram', 0)):.0f}",
            str(n.get("task_count", 0)),
            status_text(n.get("status", "offline")),
        )
    return table


def build_marketplace_table(modules: Iterable[Dict[str, Any]]) -> Table:
    table = Table(title="Nectar Marketplace", title_style=f"bold {ACCENT}")
    table.add_column("ID", style="bold")
    table.add_column("Name")
    table.add_column("Category")
    table.add_column("Author", style="dim")
    table.add_column("Rating", justify="right")
    table.add_column("Downloads", justify="right")
    table.add_column("Price")
    table.add_column("Status")
    for m in modules:
        price = m.get("price_label", f"{m.get('price', '—')} pts")
        installed = m.get("installed", False)
        table.add_row(
            m.get("id", "?"),
            m.get("name", "?"),
            m.get("category", "—"),
            m.get("author", "—"),
            f"{float(m.get('rating', 0)):.1f}",
            str(m.get("downloads", 0)),
            price,
            status_text("installed" if installed else "available"),
        )
    return table


def print_module_detail(m: Dict[str, Any]) -> None:
    lines = [
        f"[bold]{m.get('name')}[/]  [dim]{m.get('version')}[/]",
        "",
        m.get("description", ""),
        "",
        f"[bold]Author:[/] {m.get('author')}   [bold]Category:[/] {m.get('category')}",
        f"[bold]Rating:[/] {float(m.get('rating', 0)):.1f}   "
        f"[bold]Downloads:[/] {m.get('downloads', 0)}   "
        f"[bold]Price:[/] {m.get('price_label', m.get('price','—'))}",
        "",
    ]
    if m.get("features"):
        lines.append("[bold]Features:[/]")
        lines += [f"  • {f}" for f in m["features"]]
    if m.get("requirements"):
        lines.append("[bold]Requirements:[/]")
        lines += [f"  • {r}" for r in m["requirements"]]
    console.print(Panel("\n".join(lines), title=m.get("id", "module"), border_style=ACCENT))


def print_steps(steps: List[Dict[str, Any]]) -> None:
    if not steps:
        return
    for s in steps:
        color = {
            "success": "green", "completed": "green", "running": "cyan",
            "failed": "red", "skipped": "yellow",
        }.get(s.get("status", ""), "white")
        label = Text(f"  • {s.get('step', '?')}", style=color)
        console.print(label)
        summary = s.get("result_summary")
        if summary:
            console.print(Text(f"      {summary}", style="dim"))
