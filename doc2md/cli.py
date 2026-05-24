import sys
import io
import typer
from pathlib import Path
from typing import Optional
from doc2md.processors import get_processor
from doc2md.config import config
from datetime import datetime

app = typer.Typer(help="doc2md - Document to Markdown converter")

def generate_project_id() -> str:
    return datetime.now().strftime("%Y-%m-%d-%H%M")

@app.command()
def convert(
    file: str = typer.Argument(..., help="Path to the document file"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output directory"),
    ocr_mode: str = typer.Option("full", "--ocr-mode", help="OCR mode: full, caption, none")
):
    """Convert a document to Markdown."""
    file_path = Path(file)

    if not file_path.exists():
        typer.echo(f"Error: File not found: {file}", err=True)
        raise typer.Exit(1)

    project_id = generate_project_id()
    output_dir = Path(output) if output else Path(config.PROJECTS_DIR) / project_id
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        processor_class = get_processor(str(file_path))
        processor = processor_class(project_id=project_id, ocr_mode=ocr_mode)
        result = processor.process(str(file_path))

        typer.echo(f"[OK] Converted: {result.filename}")
        typer.echo(f"[OK] Project: {result.project_id}")
        typer.echo(f"[OK] Assets: {len(result.assets)}")

        if result.assets:
            typer.echo("\nAssets extracted:")
            for asset in result.assets:
                typer.echo(f"  - {asset}")

    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

@app.command()
def batch(
    files: list[str] = typer.Argument(..., help="Paths to document files"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output directory"),
    ocr_mode: str = typer.Option("full", "--ocr-mode", help="OCR mode: full, caption, none")
):
    """Convert multiple documents to Markdown."""
    project_id = generate_project_id()
    output_dir = Path(output) if output else Path(config.PROJECTS_DIR) / project_id
    output_dir.mkdir(parents=True, exist_ok=True)

    typer.echo(f"Project: {project_id}")

    success = 0
    failed = 0

    for file in files:
        file_path = Path(file)
        if not file_path.exists():
            typer.echo(f"[SKIP] Not found: {file}", err=True)
            failed += 1
            continue

        try:
            processor_class = get_processor(str(file_path))
            processor = processor_class(project_id=project_id, ocr_mode=ocr_mode)
            result = processor.process(str(file_path))
            typer.echo(f"[OK] {result.filename}")
            success += 1
        except ValueError as e:
            typer.echo(f"[FAIL] {file}: {e}", err=True)
            failed += 1

    typer.echo(f"\nDone. {success} succeeded, {failed} failed.")

@app.command()
def list_projects():
    """List all conversion projects."""
    projects_dir = Path(config.PROJECTS_DIR)
    if not projects_dir.exists():
        typer.echo("No projects found.")
        return

    projects = sorted([d.name for d in projects_dir.iterdir() if d.is_dir()], reverse=True)

    if not projects:
        typer.echo("No projects found.")
        return

    typer.echo("Projects:\n")
    for p in projects:
        typer.echo(f"  - {p}")

@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind"),
    port: int = typer.Option(8000, "--port", help="Port to bind")
):
    """Start the web server."""
    import uvicorn
    from doc2md.api import app

    # Fix Windows GBK encoding issue for emoji/non-ASCII output
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    typer.echo(f"Starting server at http://{host}:{port}")
    typer.echo(f"API docs at http://{host}:{port}/docs")
    typer.echo(f"Browser at http://{host}:{port}/browser")

    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    app()
