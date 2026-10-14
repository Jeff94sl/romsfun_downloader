#!/usr/bin/env python3
"""
RomsFun ROM Downloader & R36S Optimizer (Rich CLI)
La lógica vive en romsfun_core/; esta interfaz es la terminal.
"""

import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(SCRIPT_DIR, ".venv", "bin", "python3")
if os.path.exists(VENV_PYTHON) and sys.executable != VENV_PYTHON and "VIRTUAL_ENV" not in os.environ:
    os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)

import argparse

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
)
from rich.prompt import Prompt
from rich.text import Text

from romsfun_core import (
    extract_console_from_url,
    get_console_folder_name,
    list_console_roms,
    normalize_console_slug,
    process_download_batch,
    search_roms,
)
from romsfun_core.catalog import pages_for_limit

console = Console()


def print_banner():
    banner = Panel(
        Text.from_markup(
            "[bold cyan]🎮 ROMSFUN DOWNLOADER & R36S OPTIMIZER[/bold cyan]\n"
            "[bold white]Descarga Automática • Descompresión • Limpieza R36S/FAT32 • Idioma (ES 🇪🇸 > EN 🇬🇧)[/bold white]"
        ),
        title="[bold yellow]R36S Toolkit[/bold yellow]",
        border_style="magenta",
        expand=False,
    )
    console.print(banner)


def print_download_summary(summary_items, elapsed_time):
    table = Table(
        title="📊 Resumen Final de ROMs Optimizadas para R36S",
        header_style="bold magenta",
        border_style="cyan",
    )
    table.add_column("#", style="cyan", justify="right")
    table.add_column("Juego / Consola", style="bold white")
    table.add_column("Archivo ROM Sanitizado", style="bold yellow")
    table.add_column("Tamaño", style="bold cyan")
    table.add_column("Estado", style="bold green")

    success_count = 0
    failed_count = 0
    failed_items = []

    for idx, item in enumerate(summary_items, 1):
        status = item["status"]
        if status in ("success", "already_exists", "✓ Éxito", "⚡ Ya existía"):
            if status in ("already_exists", "⚡ Ya existía"):
                status_style = "[bold yellow]⚡ Ya existía[/bold yellow]"
            else:
                status_style = "[bold green]✓ Éxito[/bold green]"
            success_count += 1
        else:
            status_style = "[bold red]✗ Error[/bold red]"
            failed_count += 1
            failed_items.append(item)

        for rom in item["roms"]:
            if isinstance(rom, dict):
                rname, rsize = rom["name"], rom["size"]
            else:
                rname, rsize = rom
            table.add_row(
                str(idx),
                f"[{item['console']}] {item['title']}",
                rname,
                rsize,
                status_style,
            )

    console.print("\n")
    console.print(table)

    if failed_count > 0:
        failed_table = Table(
            title="⚠️ Juegos con Error o No Descargados",
            header_style="bold red",
            border_style="red",
        )
        failed_table.add_column("#", style="red", justify="right")
        failed_table.add_column("Consola", style="bold yellow")
        failed_table.add_column("Juego Fallido", style="bold white")
        failed_table.add_column("Detalle del Error", style="dim red")

        for fidx, fitem in enumerate(failed_items, 1):
            failed_table.add_row(
                str(fidx),
                fitem["console"],
                fitem["title"],
                fitem.get("error") or fitem.get("error_reason", "Falló la descarga"),
            )
        console.print("\n")
        console.print(failed_table)

    time_str = (
        f"{elapsed_time:.1f}s"
        if elapsed_time < 60
        else f"{int(elapsed_time // 60)}m {int(elapsed_time % 60)}s"
    )
    failed_markup = (
        f"   |   [bold white]Fallidos:[/bold white] [bold red]{failed_count}[/bold red]"
        if failed_count > 0
        else ""
    )
    border_color = "green" if failed_count == 0 else "yellow"

    summary_panel = Panel(
        Text.from_markup(
            f"[bold white]Total Procesados:[/bold white] [bold cyan]{len(summary_items)}[/bold cyan]   |   "
            f"[bold white]Exitosos / Listos:[/bold white] [bold green]{success_count}[/bold green]"
            f"{failed_markup}   |   "
            f"[bold white]Tiempo Total:[/bold white] [bold yellow]{time_str}[/bold yellow]"
        ),
        title="[bold yellow]✨ Resumen de Sesión[/bold yellow]",
        border_style=border_color,
    )
    console.print(summary_panel)


def cli_process_batch(items, base_output, unzip, single_version, clean_tags):
    total_games = len(items)
    console.print(f"[bold cyan]🔍 Analizando archivos locales ({total_games} juegos)...[/bold cyan]")

    file_task = None
    progress = Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(bar_width=30),
        TaskProgressColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
    )

    t_total = None
    started = False

    def on_progress(event):
        nonlocal file_task, t_total, started
        etype = event.get("type")

        if etype == "batch" and not started:
            existing = event.get("current", 0)
            if existing > 0:
                console.print(
                    f"[bold green]⚡ Detectados {existing}/{total_games} juegos previamente listos en disco.[/bold green]"
                )
            if existing >= total_games:
                return
            progress.start()
            started = True
            t_total = progress.add_task(
                f"[bold yellow]🎮 Progreso Lote ({existing}/{total_games})[/bold yellow]",
                total=total_games,
                completed=existing,
            )

        if not started and etype in ("resolving", "file"):
            progress.start()
            started = True
            t_total = progress.add_task(
                f"[bold yellow]🎮 Progreso Lote (0/{total_games})[/bold yellow]",
                total=total_games,
                completed=0,
            )

        if etype == "batch" and started and t_total is not None:
            current = event.get("current", 0)
            title = (event.get("title") or "")[:20]
            progress.update(
                t_total,
                completed=current,
                description=f"[bold yellow]🎮 Procesando ({current}/{total_games}): {title}[/bold yellow]",
            )

        if etype == "resolving" and started:
            if file_task is not None:
                progress.remove_task(file_task)
            name = (event.get("filename") or event.get("title") or "")[:22]
            file_task = progress.add_task(f"[cyan]📥 Resolviendo {name}...[/cyan]", total=None)

        if etype == "file" and started:
            if file_task is None:
                name = (event.get("filename") or "")[:22]
                file_task = progress.add_task(f"[cyan]📥 Descargando: {name}...[/cyan]", total=None)
            total = event.get("total")
            downloaded = event.get("downloaded", 0)
            name = (event.get("filename") or "")[:22]
            kwargs = {"description": f"[cyan]📥 Descargando: {name}...[/cyan]"}
            if total:
                kwargs["total"] = total
                kwargs["completed"] = downloaded
            else:
                kwargs["completed"] = downloaded
            progress.update(file_task, **kwargs)

        if etype == "batch" and file_task is not None and event.get("current"):
            progress.remove_task(file_task)
            file_task = None

    try:
        result = process_download_batch(
            items,
            base_output=base_output,
            unzip=unzip,
            single_version=single_version,
            clean_tags=clean_tags,
            on_progress=on_progress,
        )
    finally:
        if started:
            progress.stop()

    if result["items"] and all(
        i["status"] in ("already_exists", "success") for i in result["items"]
    ) and not any(e.get("type") == "file" for e in []):
        if all(i["status"] == "already_exists" for i in result["items"]):
            console.print(
                "[bold green]✓ Todos los juegos del lote ya están descargados y optimizados.[/bold green]"
            )

    print_download_summary(result["items"], result["elapsed"])


def main():
    print_banner()

    parser = argparse.ArgumentParser(description="Downloader and R36S Optimizer script for RomsFun")
    parser.add_argument("-s", "--search", help="Search for games by keyword")
    parser.add_argument("-u", "--url", help="Direct URL of game page or download page on romsfun.com")
    parser.add_argument("-c", "--console", help="Console name or alias (e.g. gba, nds, n64, psp, ps2, snes)")
    parser.add_argument("-l", "--limit", type=int, default=5, help="Limit number of ROMs to list/download")
    parser.add_argument("-o", "--output", default="./downloads", help="Base output directory")
    parser.add_argument("-y", "--yes", action="store_true", help="Automatically confirm download")
    parser.add_argument("--all-versions", action="store_true", help="Download all language versions")
    parser.add_argument("--no-unzip", action="store_true", help="Do not extract downloaded archives")
    parser.add_argument("--clean-tags", action="store_true", help="Remove region/version tags from ROM names")

    args = parser.parse_args()
    unzip = not args.no_unzip
    single_version = not args.all_versions

    if args.url:
        console_name = extract_console_from_url(args.url) or "ROM"
        game_title = args.url.split("/")[-1].replace(".html", "").replace("-", " ").title()
        item = {"title": game_title, "console": console_name, "url": args.url}
        cli_process_batch([item], args.output, unzip, single_version, args.clean_tags)

    elif args.search:
        console.print(f"[bold magenta]🔍 Buscando '[yellow]{args.search}[/yellow]' en RomsFun...[/bold magenta]")
        results = search_roms(args.search)
        if not results:
            console.print("[bold red]✗ No se encontraron juegos para la búsqueda.[/bold red]")
            return

        table = Table(title=f"Coincidencias para '{args.search}'", header_style="bold magenta", border_style="dim")
        table.add_column("#", style="cyan", justify="right")
        table.add_column("Consola", style="bold green")
        table.add_column("Título del Juego", style="bold white")
        table.add_column("Enlace URL", style="dim")

        for idx, item in enumerate(results[:15], 1):
            table.add_row(str(idx), item["console"], item["title"], item["url"])

        console.print(table)

        if args.yes:
            choice = "1"
        else:
            try:
                choice = Prompt.ask(
                    "\n[bold yellow]Ingresa el número del juego a descargar (o Enter para salir)[/bold yellow]",
                    default="",
                )
            except (EOFError, KeyboardInterrupt):
                choice = ""

        if choice.isdigit():
            sel_idx = int(choice) - 1
            if 0 <= sel_idx < len(results):
                cli_process_batch([results[sel_idx]], args.output, unzip, single_version, args.clean_tags)

    elif args.console:
        slug = normalize_console_slug(args.console)
        console_name = get_console_folder_name(slug)
        console.print(
            f"[bold magenta]🕹️ Obteniendo lista de juegos para '[yellow]{args.console}[/yellow]' "
            f"([bold green]{console_name}[/bold green])...[/bold magenta]"
        )
        results = list_console_roms(slug, max_pages=pages_for_limit(args.limit), target_count=args.limit)
        if not results:
            console.print(f"[bold red]✗ No se encontraron juegos para '{args.console}'.[/bold red]")
            return

        limit = min(args.limit, len(results))
        items_to_download = results[:limit]

        table = Table(title=f"Juegos de {console_name} (Top {limit})", header_style="bold magenta", border_style="dim")
        table.add_column("#", style="cyan", justify="right")
        table.add_column("Consola", style="bold green")
        table.add_column("Título del Juego", style="bold white")

        for idx, item in enumerate(items_to_download, 1):
            table.add_row(str(idx), item["console"], item["title"])

        console.print(table)

        if args.yes:
            confirm = "y"
        else:
            try:
                confirm = Prompt.ask(
                    f"\n[bold yellow]¿Descargar y optimizar los {limit} juegos para R36S en '{console_name}'?[/bold yellow]",
                    choices=["y", "n"],
                    default="y",
                )
            except (EOFError, KeyboardInterrupt):
                confirm = "y"

        if confirm.lower() == "y":
            cli_process_batch(items_to_download, args.output, unzip, single_version, args.clean_tags)

    else:
        parser.print_help()


def flush_stdin():
    try:
        import termios

        termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    finally:
        flush_stdin()
