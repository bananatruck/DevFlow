"""CLI entrypoint (Typer + Rich).

Goal:
- Provide the main developer UX: `devflow run "<feature request>"`
- Stream progress (plan -> execute -> summary) and show diffs/artifacts
"""

from __future__ import annotations

import typer

app = typer.Typer(help="DevFlow Agent CLI (stub).")


@app.command()
def run(feature_request: str, repo_url: str = typer.Option(..., "--repo")):
    """Run DevFlow on a repo."""
    # TODO: Call API or run locally
    typer.echo("Stub: would enqueue a run and stream results.")


if __name__ == "__main__":
    app()
