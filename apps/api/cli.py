import os
import click
import uvicorn


@click.group()
def cli():
    """Plotter Studio CLI group."""
    pass


@cli.command()
@click.option("--host", default=lambda: os.getenv("PLOTTERSTUDIO_HOST", "0.0.0.0"), help="Host to bind to")
@click.option("--port", type=int, default=lambda: int(os.getenv("PLOTTERSTUDIO_PORT", "2222")), help="Port to listen on")
@click.option("--reload", is_flag=True, default=False, help="Enable uvicorn reload")
def run(host: str, port: int, reload: bool):
    """Start the Plotter Studio API using uvicorn."""
    # Import path is expected to be the package-style app: apps.api.main:app
    app_target = "apps.api.main:app"
    uvicorn.run(app_target, host=host, port=port, reload=reload, log_level="info")


if __name__ == "__main__":
    cli()
