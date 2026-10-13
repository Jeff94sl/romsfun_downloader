#!/usr/bin/env python3
"""
RomsFun ROM Downloader & R36S Optimizer (Rich UI Edition)
- Automatic downloader for romsfun.com
- Auto-executes inside local virtual environment (.venv)
- Organizes ROMs into subfolders per console (e.g. downloads/GBA, downloads/NDS)
- Language deduplication: Downloads only ONE best version per game (Spanish 🇪🇸 > English 🇬🇧/🇺🇸 > Others)
- Dual Progress Bar (Overall Batch Progress + Individual File Speed/ETA)
- Automatically uncompresses (.zip, .7z, .rar) and deletes compressed archive
- Sanitizes filenames for R36S / ArkOS / EmulationStation (removes invalid FAT32 chars, accents, colons, quotes, etc.)
- Rich terminal interface with final summary report table
"""

import sys
import os

# Auto-re-execute inside .venv if available and not already active
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(SCRIPT_DIR, ".venv", "bin", "python3")
if os.path.exists(VENV_PYTHON) and sys.executable != VENV_PYTHON and "VIRTUAL_ENV" not in os.environ:
    os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)

import re
import math
import time
import zipfile
import subprocess
import unicodedata
import urllib.request
import urllib.parse
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
    TimeRemainingColumn
)
from rich.prompt import Prompt
from rich.text import Text

console = Console()

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
HEADERS = {"User-Agent": USER_AGENT}

CONSOLE_ALIASES = {
    "gba": "game-boy-advance",
    "gameboy-advance": "game-boy-advance",
    "gameboy advance": "game-boy-advance",
    "gb": "game-boy",
    "gameboy": "game-boy",
    "gbc": "game-boy-color",
    "gameboy color": "game-boy-color",
    "gameboy-color": "game-boy-color",
    "nds": "nintendo-ds",
    "ds": "nintendo-ds",
    "3ds": "nintendo-3ds",
    "n64": "nintendo-64",
    "snes": "super-nintendo",
    "nes": "nes",
    "psp": "playstation-portable",
    "ps1": "playstation",
    "ps2": "playstation-2",
    "ps3": "ps3",
    "psvita": "ps-vita",
    "vita": "ps-vita",
    "wii": "nintendo-wii",
    "wiiu": "wii-u",
    "genesis": "sega-genesis",
    "sega": "sega-genesis",
}

CONSOLE_DISPLAY_NAMES = {
    "game-boy-advance": "GBA",
    "game-boy": "GB",
    "game-boy-color": "GBC",
    "nintendo-ds": "NDS",
    "nintendo-3ds": "3DS",
    "nintendo-64": "N64",
    "super-nintendo": "SNES",
    "nes": "NES",
    "playstation-portable": "PSP",
    "playstation": "PS1",
    "playstation-2": "PS2",
    "ps3": "PS3",
    "ps-vita": "PSVita",
    "nintendo-wii": "Wii",
    "wii-u": "WiiU",
    "sega-genesis": "SegaGenesis",
    "gamecube": "GameCube",
    "dreamcast": "Dreamcast",
    "xbox": "Xbox",
    "xbox-360": "Xbox360",
}

def print_banner():
    banner = Panel(
        Text.from_markup(
            "[bold cyan]🎮 ROMSFUN DOWNLOADER & R36S OPTIMIZER[/bold cyan]\n"
            "[bold white]Descarga Automática • Descompresión • Limpieza R36S/FAT32 • Idioma (ES 🇪🇸 > EN 🇬🇧)[/bold white]"
        ),
        title="[bold yellow]R36S Toolkit[/bold yellow]",
        border_style="magenta",
        expand=False
    )
    console.print(banner)

def normalize_console_slug(console_str):
    cleaned = console_str.lower().strip()
    if cleaned in CONSOLE_ALIASES:
        return CONSOLE_ALIASES[cleaned]
    return cleaned.replace(" ", "-")

def get_console_folder_name(console_slug):
    slug = normalize_console_slug(console_slug)
    return CONSOLE_DISPLAY_NAMES.get(slug, slug.upper())

def extract_console_from_url(url):
    match = re.search(r'/roms/([^/]+)/', url)
    if match:
        return get_console_folder_name(match.group(1))
    return None

def score_version_for_language(filename):
    fn = filename.lower()
    score = 0
    
    is_spanish = bool(
        re.search(r'\b(spain|spanish|espanol|edicion)\b', fn) or
        re.search(r'[\(\s,](es|sp)[\),\s]', fn) or
        'espanol' in fn or 'edicion' in fn
    )
    
    is_english = bool(
        re.search(r'\b(usa|europe|world|us|eu|en|english|uk)\b', fn) or
        re.search(r'[\(\s,](en)[\),\s]', fn)
    )
    
    if is_spanish:
        score += 1000
    elif is_english:
        score += 500
    else:
        score += 100

    rev_match = re.search(r'rev\s*(\d+)', fn)
    if rev_match:
        score += int(rev_match.group(1)) * 10
        
    if '(wii u virtual console)' in fn or '(wii virtual console)' in fn:
        score += 5

    if any(x in fn for x in ['beta', 'demo', 'proto', 'sample']):
        score -= 200

    return score

def select_best_version(links):
    if not links:
        return []
    if len(links) == 1:
        return links
    
    best_link = max(links, key=lambda x: score_version_for_language(x[0]))
    return [best_link]

def clean_filename_for_r36s(filename, clean_tags=False):
    r"""
    Sanitizes filename to be 100% compatible with R36S / ArkOS / EmulationStation / FAT32:
    - Converts unicode accents (é, ñ, ó, etc.) to ASCII
    - Removes characters illegal or problematic on R36S / FAT32: : ? * " < > | / \ # % { } @ ! ~ $ & '
    - Optional clean_tags removes region tags in parenthesis/brackets
    """
    name, ext = os.path.splitext(filename)
    
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('utf-8')
    name = re.sub(r'[:?\*\"<>|/\\#%{}@!~\$&\']', '', name)
    
    if clean_tags:
        name = re.sub(r'\([^)]*\)', '', name)
        name = re.sub(r'\[[^\]]*\]', '', name)
    
    name = re.sub(r'\s+', ' ', name).strip()
    name = re.sub(r'-+', '-', name).strip(' -')
    
    if not name:
        name = "ROM_Game"
        
    return f"{name}{ext.lower()}"

def format_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

def get_html(url, retries=3):
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            if attempt == retries:
                console.print(f"[bold yellow]⚠️ Connection error for {url}: {e}[/bold yellow]")
                return ""
            time.sleep(1.5)
    return ""

def find_direct_download_links(game_or_dl_url):
    html = get_html(game_or_dl_url)
    if not html:
        return []
    
    if "/roms/" in game_or_dl_url:
        dl_pages = set(re.findall(r'href="(https://romsfun\.com/download/[^"]+)"', html))
        if not dl_pages:
            console.print(f"[bold red]✗ No download button found on game page:[/bold red] {game_or_dl_url}")
            return []
        dl_url = list(dl_pages)[0]
    else:
        dl_url = game_or_dl_url

    dl_html = get_html(dl_url)
    if not dl_html:
        return []
        
    sub_pages = set(re.findall(r'href="(https://romsfun\.com/download/[^"]+/\d+)"', dl_html))
    if not sub_pages:
        sub_pages = {dl_url}

    results = []
    for sub in sorted(sub_pages):
        try:
            sub_html = get_html(sub)
            if not sub_html:
                continue
            direct_links = (
                re.findall(r'id="download-link"[^>]*href="([^"]+)"', sub_html) +
                re.findall(r'href="([^"]+)"[^>]*id="download-link"', sub_html)
            )
            for dlink in direct_links:
                filename = urllib.parse.unquote(dlink.split("/")[-1].split("?")[0])
                results.append((filename, dlink))
        except Exception as e:
            console.print(f"[bold yellow]! Error reading subpage {sub}:[/bold yellow] {e}")
            
    return results

def extract_archive(archive_path, output_dir, clean_r36s=True, clean_tags=False):
    """
    Extracts zip / 7z archive, cleans ROM filenames for R36S, and deletes original archive.
    If encrypted or extraction fails, retains the archive safely.
    Returns list of (clean_rom_name, file_size_str).
    """
    extracted_roms = []
    success = False

    try:
        if archive_path.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(output_dir)
                success = True
            except (zipfile.BadZipFile, RuntimeError, Exception):
                # Fallback to bsdtar / 7z if encrypted or non-standard zip
                res = subprocess.run(["bsdtar", "-xf", archive_path, "-C", output_dir], capture_output=True, text=True)
                if res.returncode == 0:
                    success = True
                else:
                    res7 = subprocess.run(["7z", "x", archive_path, f"-o{output_dir}", "-y"], capture_output=True, text=True)
                    if res7.returncode == 0:
                        success = True
                    else:
                        console.print(f"[bold yellow]⚠️ Archivo protegido o cifrado ({os.path.basename(archive_path)}). Se conserva el .zip original.[/bold yellow]")
        else:
            res = subprocess.run(["bsdtar", "-xf", archive_path, "-C", output_dir], capture_output=True, text=True)
            if res.returncode == 0:
                success = True
            else:
                res7 = subprocess.run(["7z", "x", archive_path, f"-o{output_dir}", "-y"], capture_output=True, text=True)
                if res7.returncode == 0:
                    success = True
                else:
                    console.print(f"[bold yellow]⚠️ No se pudo extraer ({os.path.basename(archive_path)}). Se conserva el archivo original.[/bold yellow]")

        if success:
            for fname in os.listdir(output_dir):
                fpath = os.path.join(output_dir, fname)
                if os.path.isfile(fpath) and not fname.endswith(('.zip', '.7z', '.rar')):
                    clean_name = clean_filename_for_r36s(fname, clean_tags=clean_tags)
                    clean_path = os.path.join(output_dir, clean_name)
                    
                    if fpath != clean_path:
                        if os.path.exists(clean_path):
                            os.remove(clean_path)
                        os.rename(fpath, clean_path)
                    
                    fsize = format_size(os.path.getsize(clean_path))
                    extracted_roms.append((clean_name, fsize))

            if os.path.exists(archive_path):
                os.remove(archive_path)
        else:
            clean_arc_name = clean_filename_for_r36s(os.path.basename(archive_path), clean_tags=clean_tags)
            clean_arc_path = os.path.join(output_dir, clean_arc_name)
            if archive_path != clean_arc_path:
                if os.path.exists(clean_arc_path):
                    os.remove(clean_arc_path)
                os.rename(archive_path, clean_arc_path)
            fsize = format_size(os.path.getsize(clean_arc_path)) if os.path.exists(clean_arc_path) else "0B"
            extracted_roms.append((clean_arc_name, fsize))

    except Exception as e:
        console.print(f"[bold yellow]⚠️ Error durante la descompresión ({os.path.basename(archive_path)}): {e}[/bold yellow]")
        if os.path.exists(archive_path):
            clean_arc_name = clean_filename_for_r36s(os.path.basename(archive_path), clean_tags=clean_tags)
            clean_arc_path = os.path.join(output_dir, clean_arc_name)
            if archive_path != clean_arc_path:
                if os.path.exists(clean_arc_path):
                    os.remove(clean_arc_path)
                os.rename(archive_path, clean_arc_path)
            fsize = format_size(os.path.getsize(clean_arc_path)) if os.path.exists(clean_arc_path) else "0B"
            extracted_roms.append((clean_arc_name, fsize))

    return extracted_roms

def normalize_title_for_matching(title):
    """
    Normalizes a game title or filename for smart matching across consoles:
    - Removes extension
    - Removes all tags in () and []
    - Removes accents and non-alphanumeric characters (hyphens, dots, colons, spaces)
    - Converts to lowercase
    Example:
      'Gran Turismo 3 - A-Spec (Europe, Australia) (v1.00).iso' -> 'granturismo3aspec'
      'Gran Turismo 3 A Spec' -> 'granturismo3aspec'
    """
    name, _ = os.path.splitext(title)
    name = re.sub(r'\([^)]*\)', '', name)
    name = re.sub(r'\[[^\]]*\]', '', name)
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('utf-8')
    name = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
    return name

def is_game_already_downloaded(output_dir, filename, clean_tags=False):
    """
    Validates if the game, its archive, or its extracted ROM file already exists in output_dir.
    Uses smart normalized matching so hyphens, tags, extensions (.iso, .bin, .zip) don't break detection.
    Returns (already_exists: bool, existing_filename: str, file_size_str: str)
    """
    if not os.path.exists(output_dir):
        return False, "", ""

    norm_target = normalize_title_for_matching(filename)
    if not norm_target:
        return False, "", ""

    # Pass 1: Exact normalized title match
    for fname in os.listdir(output_dir):
        fpath = os.path.join(output_dir, fname)
        if not os.path.isfile(fpath):
            continue
        norm_f = normalize_title_for_matching(fname)
        if norm_f == norm_target:
            return True, fname, format_size(os.path.getsize(fpath))

    # Pass 2: Substring match if target length > 4
    if len(norm_target) > 4:
        for fname in os.listdir(output_dir):
            fpath = os.path.join(output_dir, fname)
            if not os.path.isfile(fpath):
                continue
            norm_f = normalize_title_for_matching(fname)
            if len(norm_f) > 4 and (norm_target in norm_f or norm_f in norm_target):
                return True, fname, format_size(os.path.getsize(fpath))

    return False, "", ""

def download_file(url, output_dir=".", unzip=True, clean_r36s=True, clean_tags=False, progress=None, file_task=None, max_retries=3):
    """
    Downloads a file given its direct URL with retries, extraction, and R36S filename cleaning.
    """
    os.makedirs(output_dir, exist_ok=True)
    raw_filename = url.split("/")[-1].split("?")[0]
    filename = urllib.parse.unquote(raw_filename)
    filepath = os.path.join(output_dir, filename)

    # Check if game or extracted ROM already exists on disk
    already_exists, found_name, found_size = is_game_already_downloaded(output_dir, filename, clean_tags=clean_tags)
    if already_exists:
        if file_task and progress:
            progress.update(file_task, completed=100, total=100)
        return {
            "status": "⚡ Ya existía",
            "raw_name": filename,
            "roms": [(found_name, found_size)]
        }

    status = "✓ Éxito"
    rom_info = []

    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, headers={**HEADERS, "Referer": "https://romsfun.com/"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                total_size = int(resp.headers.get("content-length", 0))
                
                if file_task and progress:
                    progress.update(file_task, total=total_size if total_size > 0 else None)

                chunk_size = 1024 * 64
                downloaded_bytes = 0
                with open(filepath, "wb") as f:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded_bytes += len(chunk)
                        if file_task and progress:
                            progress.update(file_task, advance=len(chunk))
                
                if total_size > 0 and downloaded_bytes < total_size:
                    raise OSError(f"Descarga incompleta ({downloaded_bytes}/{total_size} bytes)")
                break
        except Exception as e:
            if attempt < max_retries:
                if progress and file_task:
                    progress.update(file_task, completed=0)
                time.sleep(2)
            else:
                console.print(f"[bold red]✗ Error de descarga ({filename}): {e}[/bold red]")
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except Exception:
                        pass
                return {
                    "status": "✗ Error",
                    "raw_name": filename,
                    "roms": [(filename, "0B")]
                }

    if unzip and filepath.lower().endswith(('.zip', '.7z', '.rar')):
        rom_info = extract_archive(filepath, output_dir, clean_r36s=clean_r36s, clean_tags=clean_tags)
    elif clean_r36s:
        clean_name = clean_filename_for_r36s(filename, clean_tags=clean_tags)
        clean_path = os.path.join(output_dir, clean_name)
        if filepath != clean_path:
            if os.path.exists(clean_path):
                os.remove(clean_path)
            os.rename(filepath, clean_path)
        fsize = format_size(os.path.getsize(clean_path)) if os.path.exists(clean_path) else "0B"
        rom_info = [(clean_name, fsize)]
    else:
        fsize = format_size(os.path.getsize(filepath)) if os.path.exists(filepath) else "0B"
        rom_info = [(filename, fsize)]

    return {
        "status": status,
        "raw_name": filename,
        "roms": rom_info if rom_info else [(filename, format_size(os.path.getsize(filepath)) if os.path.exists(filepath) else "0B")]
    }

def print_download_summary(summary_items, elapsed_time):
    table = Table(title="📊 Resumen Final de ROMs Optimizadas para R36S", header_style="bold magenta", border_style="cyan")
    table.add_column("#", style="cyan", justify="right")
    table.add_column("Juego / Consola", style="bold white")
    table.add_column("Archivo ROM Sanitizado", style="bold yellow")
    table.add_column("Tamaño", style="bold cyan")
    table.add_column("Estado", style="bold green")

    success_count = 0
    failed_count = 0
    failed_items = []

    for idx, item in enumerate(summary_items, 1):
        if "Éxito" in item['status'] or "existía" in item['status']:
            status_style = "[bold green]✓ Éxito[/bold green]" if "Éxito" in item['status'] else "[bold yellow]⚡ Ya existía[/bold yellow]"
            success_count += 1
        else:
            status_style = "[bold red]✗ Error[/bold red]"
            failed_count += 1
            failed_items.append(item)
            
        for rname, rsize in item['roms']:
            table.add_row(
                str(idx),
                f"[{item['console']}] {item['title']}",
                rname,
                rsize,
                status_style
            )

    console.print("\n")
    console.print(table)

    if failed_count > 0:
        failed_table = Table(title="⚠️ Juegos con Error o No Descargados", header_style="bold red", border_style="red")
        failed_table.add_column("#", style="red", justify="right")
        failed_table.add_column("Consola", style="bold yellow")
        failed_table.add_column("Juego Fallido", style="bold white")
        failed_table.add_column("Detalle del Error", style="dim red")
        
        for fidx, fitem in enumerate(failed_items, 1):
            failed_table.add_row(
                str(fidx),
                fitem['console'],
                fitem['title'],
                fitem.get('error_reason', 'Falló la descarga o enlace no disponible')
            )
        console.print("\n")
        console.print(failed_table)
    
    time_str = f"{elapsed_time:.1f}s" if elapsed_time < 60 else f"{int(elapsed_time//60)}m {int(elapsed_time%60)}s"
    failed_markup = f"   |   [bold white]Fallidos:[/bold white] [bold red]{failed_count}[/bold red]" if failed_count > 0 else ""
    border_color = "green" if failed_count == 0 else "yellow"

    summary_panel = Panel(
        Text.from_markup(
            f"[bold white]Total Procesados:[/bold white] [bold cyan]{len(summary_items)}[/bold cyan]   |   "
            f"[bold white]Exitosos / Listos:[/bold white] [bold green]{success_count}[/bold green]"
            f"{failed_markup}   |   "
            f"[bold white]Tiempo Total:[/bold white] [bold yellow]{time_str}[/bold yellow]"
        ),
        title="[bold yellow]✨ Resumen de Sesión[/bold yellow]",
        border_style=border_color
    )
    console.print(summary_panel)

def search_roms(query):
    search_url = f"https://romsfun.com/?s={urllib.parse.quote(query)}"
    html = get_html(search_url)
    
    matches = re.findall(r'href="(https://romsfun\.com/roms/([^/]+)/([^/]+)\.html)"', html)
    seen = set()
    results = []
    for full_url, console_slug, slug in matches:
        if full_url not in seen:
            seen.add(full_url)
            title = slug.replace("-", " ").title()
            console_name = get_console_folder_name(console_slug)
            results.append({
                "title": title,
                "console": console_name,
                "console_slug": console_slug,
                "url": full_url
            })
    return results

def list_console_roms(console_slug, max_pages=1, target_count=None):
    console_slug = normalize_console_slug(console_slug)
    console_name = get_console_folder_name(console_slug)
    results = []
    seen = set()
    
    for page in range(1, max_pages + 1):
        url = f"https://romsfun.com/roms/{console_slug}/" if page == 1 else f"https://romsfun.com/roms/{console_slug}/page/{page}/"
        try:
            html = get_html(url)
            matches = re.findall(r'href="(https://romsfun\.com/roms/' + re.escape(console_slug) + r'/([^/]+)\.html)"', html)
            if not matches:
                break
            for full_url, slug in matches:
                if full_url not in seen:
                    seen.add(full_url)
                    title = slug.replace("-", " ").title()
                    results.append({
                        "title": title,
                        "console": console_name,
                        "console_slug": console_slug,
                        "url": full_url
                    })
                    if target_count and len(results) >= target_count:
                        break
            if target_count and len(results) >= target_count:
                break
        except Exception as e:
            if page > 1 and "404" in str(e):
                break
            console.print(f"[bold red]! Error fetching console page {page} for '{console_slug}':[/bold red] {e}")
            break
            
    return results

def resolve_output_dir(base_output, console_name=None):
    if console_name:
        if os.path.basename(os.path.normpath(base_output)).upper() == console_name.upper():
            return base_output
        return os.path.join(base_output, console_name)
    return base_output

def process_download_batch(items_to_download, base_output, unzip, single_version, clean_tags):
    """
    Handles batch downloading with dual progress bars (overall total progress + individual file progress).
    Pre-scans items to immediately set initial progress if games already exist on disk.
    """
    total_games = len(items_to_download)
    summary_items = []
    pending_items = []
    start_time = time.time()

    # Pre-scan for existing games before starting download UI
    console.print(f"[bold cyan]🔍 Analizando archivos locales ({total_games} juegos)...[/bold cyan]")
    for item in items_to_download:
        game_title = item['title']
        console_name = item['console']
        out_dir = resolve_output_dir(base_output, console_name)

        clean_expected = clean_filename_for_r36s(game_title, clean_tags=clean_tags)
        exists, found_name, found_size = is_game_already_downloaded(out_dir, clean_expected, clean_tags=clean_tags)
        if not exists:
            clean_no_tags = clean_filename_for_r36s(game_title, clean_tags=True)
            exists, found_name, found_size = is_game_already_downloaded(out_dir, clean_no_tags, clean_tags=True)

        if exists:
            summary_items.append({
                "title": game_title,
                "console": console_name,
                "status": "⚡ Ya existía",
                "roms": [(found_name, found_size)]
            })
        else:
            pending_items.append(item)

    existing_count = len(summary_items)
    if existing_count > 0:
        console.print(f"[bold green]⚡ Detectados {existing_count}/{total_games} juegos previamente listos en disco.[/bold green]")

    if not pending_items:
        console.print("[bold green]✓ Todos los juegos del lote ya están descargados y optimizados.[/bold green]")
        elapsed = time.time() - start_time
        print_download_summary(summary_items, elapsed)
        return

    progress = Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(bar_width=30),
        TaskProgressColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console
    )

    with progress:
        t_total = progress.add_task(
            f"[bold yellow]🎮 Progreso Lote ({existing_count}/{total_games})[/bold yellow]",
            total=total_games,
            completed=existing_count
        )

        for current_idx, item in enumerate(pending_items, existing_count + 1):
            game_title = item['title']
            console_name = item['console']
            out_dir = resolve_output_dir(base_output, console_name)

            progress.update(t_total, description=f"[bold yellow]🎮 Procesando ({current_idx}/{total_games}): {game_title[:20]}[/bold yellow]")
            t_file = progress.add_task(f"[cyan]📥 Resolviendo {game_title[:20]}...[/cyan]", total=None)

            try:
                links = find_direct_download_links(item['url'])
                if single_version:
                    links = select_best_version(links)

                if not links:
                    summary_items.append({
                        "title": game_title,
                        "console": console_name,
                        "status": "✗ Error",
                        "roms": [(game_title, "0B")]
                    })
                else:
                    for name, durl in links:
                        progress.update(t_file, description=f"[cyan]📥 Descargando: {name[:22]}...[/cyan]")
                        res = download_file(
                            durl,
                            output_dir=out_dir,
                            unzip=unzip,
                            clean_tags=clean_tags,
                            progress=progress,
                            file_task=t_file
                        )
                        summary_items.append({
                            "title": game_title,
                            "console": console_name,
                            "status": res['status'],
                            "roms": res['roms']
                        })

            except Exception as e:
                console.print(f"[bold red]✗ Error al procesar {game_title}:[/bold red] {e}")
                summary_items.append({
                    "title": game_title,
                    "console": console_name,
                    "status": "✗ Error",
                    "roms": [(game_title, "0B")]
                })
            finally:
                progress.remove_task(t_file)
                progress.update(t_total, advance=1, description=f"[bold yellow]🎮 Progreso Lote ({current_idx}/{total_games})[/bold yellow]")

    elapsed = time.time() - start_time
    print_download_summary(summary_items, elapsed)

def main():
    print_banner()

    parser = argparse.ArgumentParser(description="Downloader and R36S Optimizer script for RomsFun")
    parser.add_argument("-s", "--search", help="Search for games by keyword")
    parser.add_argument("-u", "--url", help="Direct URL of game page or download page on romsfun.com")
    parser.add_argument("-c", "--console", help="Console name or alias (e.g. gba, nds, n64, psp, ps2, snes)")
    parser.add_argument("-l", "--limit", type=int, default=5, help="Limit number of ROMs to list/download when scraping console")
    parser.add_argument("-o", "--output", default="./downloads", help="Base output directory for downloaded files (default: ./downloads)")
    parser.add_argument("-y", "--yes", action="store_true", help="Automatically confirm download without asking")
    parser.add_argument("--all-versions", action="store_true", help="Download all language versions instead of picking the single best version")
    parser.add_argument("--no-unzip", action="store_true", help="Do not extract downloaded archives")
    parser.add_argument("--clean-tags", action="store_true", help="Remove region/version tags in () and [] from ROM names")
    
    args = parser.parse_args()
    unzip = not args.no_unzip
    single_version = not args.all_versions

    if args.url:
        console_name = extract_console_from_url(args.url) or "ROM"
        game_title = args.url.split("/")[-1].replace(".html", "").replace("-", " ").title()
        item = {"title": game_title, "console": console_name, "url": args.url}
        process_download_batch([item], args.output, unzip, single_version, args.clean_tags)

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
            table.add_row(str(idx), item['console'], item['title'], item['url'])

        console.print(table)
            
        if args.yes:
            choice = "1"
        else:
            try:
                choice = Prompt.ask("\n[bold yellow]Ingresa el número del juego a descargar (o Enter para salir)[/bold yellow]", default="")
            except (EOFError, KeyboardInterrupt):
                choice = ""

        if choice.isdigit():
            sel_idx = int(choice) - 1
            if 0 <= sel_idx < len(results):
                selected = results[sel_idx]
                process_download_batch([selected], args.output, unzip, single_version, args.clean_tags)

    elif args.console:
        slug = normalize_console_slug(args.console)
        console_name = get_console_folder_name(slug)
        console.print(f"[bold magenta]🕹️ Obteniendo lista de juegos para '[yellow]{args.console}[/yellow]' ([bold green]{console_name}[/bold green])...[/bold magenta]")
        pages_to_fetch = math.ceil(args.limit / 20)
        results = list_console_roms(slug, max_pages=pages_to_fetch, target_count=args.limit)
        if not results:
            console.print(f"[bold red]✗ No se encontraron juegos para '{args.console}'. Revisa el nombre o alias.[/bold red]")
            return
        
        limit = min(args.limit, len(results))
        items_to_download = results[:limit]

        table = Table(title=f"Juegos de {console_name} (Top {limit})", header_style="bold magenta", border_style="dim")
        table.add_column("#", style="cyan", justify="right")
        table.add_column("Consola", style="bold green")
        table.add_column("Título del Juego", style="bold white")

        for idx, item in enumerate(items_to_download, 1):
            table.add_row(str(idx), item['console'], item['title'])

        console.print(table)
            
        if args.yes:
            confirm = "y"
        else:
            try:
                confirm = Prompt.ask(f"\n[bold yellow]¿Descargar y optimizar los {limit} juegos para R36S en '{console_name}'?[/bold yellow]", choices=["y", "n"], default="y")
            except (EOFError, KeyboardInterrupt):
                confirm = "y"
                
        if confirm.lower() == 'y':
            process_download_batch(items_to_download, args.output, unzip, single_version, args.clean_tags)

    else:
        parser.print_help()

def flush_stdin():
    """Flushes any leftover unread keystrokes in terminal input buffer (e.g. zsh/bash)."""
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

