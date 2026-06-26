"""EDITH-X CLI — Typer-based command line interface."""
from __future__ import annotations

import asyncio
import subprocess
import sys

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

app = typer.Typer(
    name="edith",
    help="⚡ EDITH-X Enterprise AI Runtime CLI",
    add_completion=False,
)
console = Console()

API_BASE = "http://localhost:8000"


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Host to bind"),
    port: int = typer.Option(8000, help="Port to bind"),
    reload: bool = typer.Option(False, help="Enable hot reload"),
):
    """Start the EDITH-X REST API server."""
    console.print(Panel("⚡ Starting EDITH-X Runtime", style="bold cyan"))
    import uvicorn
    uvicorn.run(
        "edith_x.interfaces.rest.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


@app.command()
def demo():
    """Launch the EDITH-X Streamlit demo dashboard."""
    console.print(Panel("🎯 Launching EDITH-X Demo Dashboard", style="bold cyan"))
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        "edith_x/demo/ui.py",
        "--server.port", "8501",
        "--server.headless", "false",
    ])


@app.command()
def run(
    goal: str = typer.Argument(..., help="Goal or question to run"),
    api_key: str = typer.Option("demo-key", help="EDITH-X API key"),
):
    """Run a goal through the EDITH-X autonomous agent."""
    async def _run():
        with Progress(
            SpinnerColumn(),
            TextColumn("[cyan]Running EDITH-X pipeline..."),
            transient=True,
        ) as progress:
            progress.add_task("running")
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{API_BASE}/edith/v1/run",
                    json={"goal": goal, "autonomy": "autonomous"},
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                return resp.json()

    result = asyncio.run(_run())

    if "error" in result:
        console.print(f"[red]Error:[/red] {result['error']}")
        return

    # Display result
    console.print(Panel(
        result.get("response", "No response"),
        title="⚡ EDITH-X Response",
        style="bold green",
    ))

    # Metadata table
    table = Table(title="Pipeline Metadata", style="cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Value", style="green")

    layer = result.get("layer", "L3_cloud")
    layer_icons = {"L0_cache": "🟢 L0 Cache", "L1_local": "🔵 L1 Local", "L3_cloud": "🔴 L3 Cloud"}
    
    table.add_row("Layer", layer_icons.get(layer, layer))
    table.add_row("Model", result.get("model", "N/A"))
    table.add_row("Cache Hit", "✅ Yes" if result.get("cache_hit") else "❌ No")
    table.add_row("Cost", f"${result.get('cost_usd', 0):.5f}")
    table.add_row("Saved", f"${result.get('cost_saved_usd', 0):.5f}")
    table.add_row("Latency", f"{result.get('latency_ms', 0)}ms")
    table.add_row("Tokens In", str(result.get("tokens_input", 0)))
    table.add_row("Tokens Out", str(result.get("tokens_output", 0)))
    table.add_row("Intent", result.get("intent", "N/A"))

    console.print(table)


@app.command()
def metrics(
    window: str = typer.Option("24h", help="Time window"),
    api_key: str = typer.Option("demo-key", help="EDITH-X API key"),
):
    """View cost, token usage, and cache metrics."""
    async def _get():
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{API_BASE}/edith/v1/metrics?window={window}",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            return resp.json()

    data = asyncio.run(_get())

    table = Table(title=f"EDITH-X Metrics ({window})", style="cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Value", style="green")

    table.add_row("Total Requests", str(data.get("total_requests", 0)))
    table.add_row("Cache Hit Rate", f"{data.get('cache_hit_rate', 0):.1%}")
    table.add_row("Avg Cost/Request", f"${data.get('avg_cost_usd', 0):.5f}")
    table.add_row("Total Cost", f"${data.get('total_cost_usd', 0):.4f}")
    table.add_row("Total Saved", f"${data.get('total_saved_usd', 0):.4f}")
    table.add_row("Avg Latency", f"{data.get('avg_latency_ms', 0):.0f}ms")

    console.print(table)


@app.command()
def health():
    """Check runtime health."""
    async def _check():
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{API_BASE}/edith/v1/health")
            return resp.json()

    try:
        data = asyncio.run(_check())
        if data.get("status") == "healthy":
            console.print("[green]✅ EDITH-X Runtime is healthy[/green]")
            console.print(f"  Demo mode: {data.get('demo_mode')}")
            console.print(f"  Providers: {data.get('providers')}")
        else:
            console.print("[red]❌ Runtime unhealthy[/red]")
    except Exception as e:
        console.print(f"[red]❌ Cannot reach runtime: {e}[/red]")
        console.print("[yellow]Start with: edith serve[/yellow]")


if __name__ == "__main__":
    app()
