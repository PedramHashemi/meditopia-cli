"""
medi — Meditopia CLI

Usage examples:
  medi login --token mtc_xxxx
  medi whoami
  medi add dataset ./my-data --to pedram/projects/radiology/chest-xray --privacy public --modality imaging
  medi add model   ./my-model --to pedram/projects/radiology/chexnet    --privacy public --task radiology --framework pytorch
"""

from __future__ import annotations

import sys
from typing import List, Optional

import typer
from rich import print as rprint
from rich.table import Table
from rich import box

from . import config, client
from .uploader import collect_files

app = typer.Typer(
    name="medi",
    help="Meditopia CLI — push models and datasets from your terminal.",
    add_completion=False,
)
add_app = typer.Typer(help="Add a model or dataset to Meditopia.")
app.add_typer(add_app, name="add")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_to(to: str) -> tuple[str, str, str]:
    """
    Split 'owner/collection/path/name' into (owner, collection_path, slug).
    The last segment is the slug; everything between owner and slug is collection_path.
    e.g. 'pedram/projects/radiology/chest-xray'  →  ('pedram', 'projects/radiology', 'chest-xray')
         'pedram/chest-xray'                      →  ('pedram', '', 'chest-xray')
    """
    parts = to.strip("/").split("/")
    if len(parts) < 2:
        rprint(f"[red]--to must be at least owner/name, got: {to!r}[/red]")
        raise typer.Exit(1)
    owner           = parts[0]
    slug            = parts[-1]
    collection_path = "/".join(parts[1:-1])
    return owner, collection_path, slug


def _abort_if_error(r: dict) -> None:
    if "detail" in r or "error" in r:
        rprint(f"[red]API error:[/red] {r.get('detail') or r.get('error')}")
        raise typer.Exit(1)


# ── login ─────────────────────────────────────────────────────────────────────

@app.command()
def login(
    token:   str = typer.Option(..., help="Your Meditopia API token (starts with mtc_)"),
    api_url: str = typer.Option(config.DEFAULT_API_URL, help="API base URL"),
):
    """Save your API token and verify it against the server."""
    config.set_credentials(token, api_url)
    try:
        me = client.whoami()
    except Exception as exc:
        rprint(f"[red]Login failed:[/red] {exc}")
        config.clear()
        raise typer.Exit(1)
    rprint(f"[green]✓[/green] Logged in as [bold]{me['username']}[/bold] ({me.get('plan', 'free')} plan)")


# ── whoami ────────────────────────────────────────────────────────────────────

@app.command()
def whoami():
    """Show the currently authenticated user."""
    try:
        me = client.whoami()
    except RuntimeError as exc:
        rprint(f"[yellow]{exc}[/yellow]")
        raise typer.Exit(1)
    rprint(f"[bold]{me['username']}[/bold]  ·  {me.get('email', '')}  ·  {me.get('plan', 'free')} plan")


# ── add dataset ───────────────────────────────────────────────────────────────

@add_app.command("dataset")
def add_dataset(
    local_path: str = typer.Argument(..., help="Local file or directory to upload"),
    to:         str = typer.Option(..., help="Destination path: owner[/collection/...]/ name"),
    privacy:    str = typer.Option("public",  help="public | private | restricted"),
    modality:   str = typer.Option(...,       help="imaging | ehr | genomics | clinical-notes | waveform | multimodal | other"),
    description:str = typer.Option("",        help="Short description of the dataset"),
    license:    str = typer.Option("unknown", help="License identifier, e.g. mit, apache-2.0, cc-by-4.0"),
    institution:str = typer.Option("",        help="Publishing institution"),
    dua:        bool= typer.Option(False,     help="Require a Data Use Agreement"),
    compliance: Optional[List[str]] = typer.Option(None, help="Compliance badges: hipaa, gdpr, fda-track, ce-mark, fhir"),
    tags:       Optional[List[str]] = typer.Option(None, help="Free-form tags"),
    num_patients: Optional[int] = typer.Option(None, help="Number of patients in the dataset"),
    num_records:  Optional[int] = typer.Option(None, help="Number of records"),
):
    """Upload a local dataset (files + metadata) to Meditopia."""
    owner, collection_path, slug = _parse_to(to)

    rprint(f"[bold]Creating dataset[/bold] [cyan]{owner}/{collection_path}/{slug}[/cyan] …")

    payload = {
        "name":            slug,
        "description":     description,
        "modality":        modality,
        "visibility":      privacy,
        "license":         license,
        "institution":     institution,
        "requires_dua":    dua,
        "compliance":      compliance or [],
        "tags":            tags or [],
        "collection_path": collection_path,
        "num_patients":    num_patients,
        "num_records":     num_records,
    }

    try:
        ds = client.create_dataset(payload)
    except Exception as exc:
        rprint(f"[red]Failed to create dataset:[/red] {exc}")
        raise typer.Exit(1)

    _abort_if_error(ds)
    rprint(f"[green]✓[/green] Dataset created: [bold]{ds['full_path']}[/bold]")

    # Upload files
    rprint(f"Collecting files from [cyan]{local_path}[/cyan] …")
    try:
        file_tuples = collect_files(local_path)
    except FileNotFoundError:
        rprint(f"[red]Path not found:[/red] {local_path}")
        raise typer.Exit(1)

    if not file_tuples:
        rprint("[yellow]No files found — dataset created with no files.[/yellow]")
        return

    rprint(f"Uploading [bold]{len(file_tuples)}[/bold] file(s) …")
    try:
        result = client.upload_dataset_files(owner, ds["slug"], file_tuples)
    except Exception as exc:
        rprint(f"[red]Upload failed:[/red] {exc}")
        raise typer.Exit(1)

    _print_upload_summary(result)
    rprint(f"\n[green]✓ Done.[/green] View at: {config.get_api_url().replace('/api/v1', '')}/datasets/{ds['full_path']}")


# ── add model ─────────────────────────────────────────────────────────────────

@add_app.command("model")
def add_model(
    local_path:  str = typer.Argument(..., help="Local file or directory to upload"),
    to:          str = typer.Option(...,        help="Destination path: owner[/collection/...]/name"),
    privacy:     str = typer.Option("public",   help="public | private | restricted"),
    task:        str = typer.Option(...,        help="diagnosis | radiology | pathology | genomics | clinical-nlp | drug-discovery | risk-scoring | cardiology | neurology | dermatology | ophthalmology | other"),
    framework:   str = typer.Option(...,        help="pytorch | tensorflow | jax | onnx | scikit-learn | other"),
    modality:    str = typer.Option("",         help="Imaging modality if applicable: CT | MRI | X-ray | PET | Ultrasound | other"),
    description: str = typer.Option("",         help="Short description of the model"),
    license:     str = typer.Option("unknown",  help="License identifier"),
    institution: str = typer.Option("",         help="Publishing institution"),
    compliance:  Optional[List[str]] = typer.Option(None, help="Compliance badges"),
    tags:        Optional[List[str]] = typer.Option(None, help="Free-form tags"),
    auc:         Optional[float]     = typer.Option(None, help="Primary AUC metric (0–1)"),
):
    """Upload a local model (weights + metadata) to Meditopia."""
    owner, collection_path, slug = _parse_to(to)

    rprint(f"[bold]Creating model[/bold] [cyan]{owner}/{collection_path}/{slug}[/cyan] …")

    payload = {
        "name":            slug,
        "description":     description,
        "task":            task,
        "framework":       framework,
        "modality":        modality,
        "visibility":      privacy,
        "license":         license,
        "institution":     institution,
        "compliance":      compliance or [],
        "tags":            tags or [],
        "collection_path": collection_path,
        "auc":             auc,
    }

    try:
        model = client.create_model(payload)
    except Exception as exc:
        rprint(f"[red]Failed to create model:[/red] {exc}")
        raise typer.Exit(1)

    _abort_if_error(model)
    rprint(f"[green]✓[/green] Model created: [bold]{model['full_path']}[/bold]")

    rprint(f"Collecting files from [cyan]{local_path}[/cyan] …")
    try:
        file_tuples = collect_files(local_path)
    except FileNotFoundError:
        rprint(f"[red]Path not found:[/red] {local_path}")
        raise typer.Exit(1)

    if not file_tuples:
        rprint("[yellow]No files found — model created with no files.[/yellow]")
        return

    rprint(f"Uploading [bold]{len(file_tuples)}[/bold] file(s) …")
    try:
        result = client.upload_model_files(owner, model["slug"], file_tuples)
    except Exception as exc:
        rprint(f"[red]Upload failed:[/red] {exc}")
        raise typer.Exit(1)

    _print_upload_summary(result)
    rprint(f"\n[green]✓ Done.[/green] View at: {config.get_api_url().replace('/api/v1', '')}/models/{model['full_path']}")


# ── helpers ───────────────────────────────────────────────────────────────────

def _print_upload_summary(result: dict) -> None:
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("File")
    table.add_column("Status", style="green")
    for f in result.get("files", []):
        table.add_row(f, "✓ uploaded")
    rprint(table)
    mb = result.get("bytes", 0) / 1_048_576
    rprint(f"Total: [bold]{result.get('uploaded', 0)}[/bold] files · [bold]{mb:.2f} MB[/bold]")


if __name__ == "__main__":
    app()
