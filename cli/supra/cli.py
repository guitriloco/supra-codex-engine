"""Supra-Codex CLI — sovereign, local-first orchestration from the terminal.

Commands:
    supra status                     engine health check
    supra scrape <url>               scrape a URL
    supra pipeline run <url>         run the full scrape + AI pipeline
    supra nodes list                 list active nodes
    supra marketplace search <q>     search Nectar Marketplace modules
    supra marketplace install <id>   install a marketplace module
    supra marketplace uninstall <id> uninstall a module
    supra config                     show current configuration
"""

from __future__ import annotations

import json
from typing import Optional

import typer

from . import __version__
from .client import SupraApiError, SupraClient
from .config import ensure_config
from . import ui

app = typer.Typer(
    name="supra",
    help="Supra-Codex — sovereign, local-first AI orchestration CLI.",
    no_args_is_help=True,
    add_completion=False,
)
config_cmd = typer.Typer(help="Manage CLI configuration.")
app.add_typer(config_cmd, name="config")

# ---------------------------------------------------------------------------
# Wiring
# ---------------------------------------------------------------------------


def _client() -> SupraClient:
    cfg = ensure_config()
    return SupraClient.from_config(cfg)


def _version_callback(value: bool) -> None:
    if value:
        ui.console.print(f"supra-codex {__version__}")
        raise typer.Exit()


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", "-V", help="Show version and exit.",
        callback=_version_callback, is_eager=True,
    ),
) -> None:
    """Supra-Codex CLI."""
    pass


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


@app.command("status")
def status() -> None:
    """Engine health check."""
    client = _client()
    try:
        health = client.health()
    except SupraApiError as exc:
        ui.error(str(exc))
        raise typer.Exit(code=1)

    engine_state = health.get("engine", "unknown")
    xerebro = health.get("xerebro", False)
    ui.console.print(f"[bold]Supra-Codex Engine[/]  [dim]v{health.get('version', '?')}[/]")
    ui.console.print(f"  Engine:    {ui.status_text(engine_state)}")
    ui.console.print(
        f"  Xerebro AI: {ui.status_text('online' if xerebro else 'offline')}"
        f"[dim] (Ollama)[/]"
    )
    ui.console.print(f"  API:       [cyan]{client.base_url}[/]")

    try:
        st = client.status()
        stats = st.get("stats", {}) or {}
        ui.console.print(f"  Running:   {ui.status_text('running' if st.get('running') else 'stopped')}")
        if stats:
            keys = [k for k in ("tasks_submitted", "tasks_completed", "active_tasks",
                                "total_tasks", "throughput", "uptime_s") if k in stats]
            for k in keys:
                ui.console.print(f"  {k.replace('_', ' ').title():<11}: {stats[k]}")
    except SupraApiError as exc:
        ui.error(str(exc))


# ---------------------------------------------------------------------------
# scrape
# ---------------------------------------------------------------------------


@app.command("scrape")
def scrape(url: str = typer.Argument(..., help="URL to scrape.")) -> None:
    """Scrape a URL through the engine."""
    client = _client()
    try:
        with ui.console.status(f"[bold cyan]Scraping {url}…[/]"):
            result = client.run_pipeline(url)
    except SupraApiError as exc:
        ui.error(str(exc))
        raise typer.Exit(code=1)

    content = result.get("scraped_content") or {}
    ui.success(f"Scraped {result.get('url', url)}")
    ui.print_steps([s for s in result.get("steps", []) if s.get("step") != "xerebro_analysis"])
    title = content.get("title") or "Untitled"
    body = (content.get("body_text") or "")[:500]
    ui.console.print(f"[bold]Title:[/] {title}")
    if body:
        ui.console.print(ui.Text(body, style="dim"))


# ---------------------------------------------------------------------------
# pipeline
# ---------------------------------------------------------------------------

pipeline_app = typer.Typer(help="Pipeline operations (scrape + AI).")
app.add_typer(pipeline_app, name="pipeline")


@pipeline_app.command("run")
def pipeline_run(
    url: str = typer.Argument(..., help="URL to run the full pipeline on."),
    prompt: Optional[str] = typer.Option(None, "--prompt", "-p", help="Custom Xerebro prompt."),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Override Ollama model."),
    json_output: bool = typer.Option(False, "--json", help="Emit raw JSON result."),
) -> None:
    """Run the full pipeline: scrape + Xerebro AI enrichment."""
    client = _client()
    try:
        with ui.console.status(f"[bold cyan]Running pipeline on {url}…[/]"):
            result = client.run_pipeline(url, prompt=prompt, model=model)
    except SupraApiError as exc:
        ui.error(str(exc))
        raise typer.Exit(code=1)

    if json_output:
        ui.console.print(json.dumps(result, indent=2, default=str))
        return

    ui.console.print(ui.Panel(
        f"[bold]{result.get('url')}[/]",
        title=f"Pipeline {result.get('pipeline_id', '')[:8]}",
        border_style="cyan",
    ))
    ui.print_steps(result.get("steps", []))
    ui.console.print(
        f"[bold]Total:[/] {result.get('total_duration_ms', 0):.0f} ms   "
        f"[bold]Status:[/] {ui.status_text(result.get('status', '?'))}"
    )
    xerebro = result.get("xerebro_analysis")
    if xerebro:
        ui.console.print(f"[bold cyan]Xerebro AI:[/]")
        ui.console.print(ui.Text(json.dumps(xerebro, indent=2, default=str), style="dim"))


# ---------------------------------------------------------------------------
# nodes
# ---------------------------------------------------------------------------

nodes_app = typer.Typer(help="Manage and inspect distributed nodes.")
app.add_typer(nodes_app, name="nodes")


@nodes_app.command("list")
def nodes_list() -> None:
    """List active compute nodes."""
    client = _client()
    try:
        data = client.list_nodes()
    except SupraApiError as exc:
        ui.error(str(exc))
        raise typer.Exit(code=1)

    nodes = data.get("nodes", [])
    if not nodes:
        ui.console.print("[yellow]No nodes registered yet.[/]")
        ui.console.print("[dim]Register a node or run the node simulator to see it here.[/]")
        return
    ui.console.print(ui.build_nodes_table(nodes))
    ui.console.print(
        f"[dim]{data.get('count', len(nodes))} total · "
        f"{data.get('online', len(nodes))} online[/]"
    )


# ---------------------------------------------------------------------------
# marketplace
# ---------------------------------------------------------------------------

market_app = typer.Typer(help="Nectar Marketplace — pre-built automation modules.")
app.add_typer(market_app, name="marketplace")


@market_app.command("search")
def market_search(
    query: str = typer.Argument(..., help="Search term (name, description, category, author)."),
    installed_only: bool = typer.Option(False, "--installed", help="Only show installed modules."),
) -> None:
    """Search the Nectar Marketplace."""
    client = _client()
    try:
        results = client.search_marketplace(query)
        if installed_only:
            results = [m for m in results if m.get("installed")]
    except SupraApiError as exc:
        ui.error(str(exc))
        raise typer.Exit(code=1)

    if not results:
        ui.console.print(f"[yellow]No modules matched '{query}'.[/]")
        return
    ui.console.print(ui.build_marketplace_table(results))
    ui.console.print(f"[dim]{len(results)} result(s)[/]")


@market_app.command("list")
def market_list(
    installed_only: bool = typer.Option(False, "--installed", help="Only show installed modules."),
) -> None:
    """List all marketplace modules (optionally only installed)."""
    client = _client()
    try:
        if installed_only:
            modules = client.list_installed_modules()
        else:
            modules = client.list_marketplace_modules()
    except SupraApiError as exc:
        ui.error(str(exc))
        raise typer.Exit(code=1)
    if not modules:
        ui.console.print("[yellow]No modules found.[/]")
        return
    ui.console.print(ui.build_marketplace_table(modules))
    ui.console.print(f"[dim]{len(modules)} module(s)[/]")


@market_app.command("install")
def market_install(
    module_id: str = typer.Argument(..., help="Module ID to install."),
) -> None:
    """Install a module from the marketplace."""
    client = _client()
    try:
        result = client.install_module(module_id)
    except SupraApiError as exc:
        ui.error(str(exc))
        raise typer.Exit(code=1)
    ui.success(result.get("message", f"Module {module_id} installed."))


@market_app.command("uninstall")
def market_uninstall(
    module_id: str = typer.Argument(..., help="Module ID to uninstall."),
) -> None:
    """Uninstall a module."""
    client = _client()
    try:
        result = client.uninstall_module(module_id)
    except SupraApiError as exc:
        ui.error(str(exc))
        raise typer.Exit(code=1)
    ui.success(result.get("message", f"Module {module_id} uninstalled."))


@market_app.command("info")
def market_info(
    module_id: str = typer.Argument(..., help="Module ID to inspect."),
) -> None:
    """Show detailed info about a module."""
    client = _client()
    try:
        mod = client.get_module(module_id)
    except SupraApiError as exc:
        ui.error(str(exc))
        raise typer.Exit(code=1)
    ui.print_module_detail(mod)


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------


@config_cmd.command("show")
def config_show() -> None:
    """Show the current CLI configuration."""
    cfg = ensure_config()
    for key in ("api_base_url", "timeout_seconds"):
        ui.console.print(f"  [cyan]{key}[/] = {cfg.get(key)}")


@config_cmd.command("set")
def config_set(
    key: str = typer.Argument(..., help="Config key. e.g. api_base_url"),
    value: str = typer.Argument(..., help="Value to set."),
) -> None:
    """Set a configuration value (e.g. api_base_url)."""
    cfg = ensure_config()
    keys = ("api_base_url", "timeout_seconds")
    if key not in keys:
        ui.error(f"Unknown key '{key}'. Valid keys: {', '.join(keys)}")
        raise typer.Exit(code=1)
    if key == "timeout_seconds":
        try:
            float(value)
        except ValueError:
            ui.error("timeout_seconds must be a number")
            raise typer.Exit(code=1)
    cfg.set(key, value)
    ui.success(f"{key} = {value}")


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------


def main_entry() -> None:
    app()


if __name__ == "__main__":
    app()
