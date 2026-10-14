import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
import zipfile
from typing import Callable, Optional

from .consoles import get_console_folder_name
from .http_client import HEADERS, get_html
from .sanitize import (
    clean_filename_for_r36s,
    format_size,
    normalize_title_for_matching,
    select_best_version,
)

ProgressCallback = Optional[Callable[[dict], None]]


def resolve_output_dir(base_output: str, console_name=None) -> str:
    if console_name:
        if os.path.basename(os.path.normpath(base_output)).upper() == console_name.upper():
            return base_output
        return os.path.join(base_output, console_name)
    return base_output


def find_direct_download_links(game_or_dl_url: str):
    html = get_html(game_or_dl_url)
    if not html:
        return []

    if "/roms/" in game_or_dl_url:
        dl_pages = set(re.findall(r'href="(https://romsfun\.com/download/[^"]+)"', html))
        if not dl_pages:
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
            direct_links = re.findall(r'id="download-link"[^>]*href="([^"]+)"', sub_html) + re.findall(
                r'href="([^"]+)"[^>]*id="download-link"', sub_html
            )
            for dlink in direct_links:
                filename = urllib.parse.unquote(dlink.split("/")[-1].split("?")[0])
                results.append((filename, dlink))
        except Exception:
            continue

    return results


def extract_archive(archive_path, output_dir, clean_tags=False):
    extracted_roms = []
    success = False

    try:
        if archive_path.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(archive_path, "r") as zip_ref:
                    zip_ref.extractall(output_dir)
                success = True
            except Exception:
                res = subprocess.run(
                    ["bsdtar", "-xf", archive_path, "-C", output_dir],
                    capture_output=True,
                    text=True,
                )
                if res.returncode == 0:
                    success = True
                else:
                    res7 = subprocess.run(
                        ["7z", "x", archive_path, f"-o{output_dir}", "-y"],
                        capture_output=True,
                        text=True,
                    )
                    if res7.returncode == 0:
                        success = True
        else:
            res = subprocess.run(
                ["bsdtar", "-xf", archive_path, "-C", output_dir],
                capture_output=True,
                text=True,
            )
            if res.returncode == 0:
                success = True
            else:
                res7 = subprocess.run(
                    ["7z", "x", archive_path, f"-o{output_dir}", "-y"],
                    capture_output=True,
                    text=True,
                )
                if res7.returncode == 0:
                    success = True

        if success:
            for fname in os.listdir(output_dir):
                fpath = os.path.join(output_dir, fname)
                if os.path.isfile(fpath) and not fname.endswith((".zip", ".7z", ".rar")):
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

    except Exception:
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


def is_game_already_downloaded(output_dir, filename, clean_tags=False):
    if not os.path.exists(output_dir):
        return False, "", ""

    norm_target = normalize_title_for_matching(filename)
    if not norm_target:
        return False, "", ""

    for fname in os.listdir(output_dir):
        fpath = os.path.join(output_dir, fname)
        if not os.path.isfile(fpath):
            continue
        norm_f = normalize_title_for_matching(fname)
        if norm_f == norm_target:
            return True, fname, format_size(os.path.getsize(fpath))

    if len(norm_target) > 4:
        for fname in os.listdir(output_dir):
            fpath = os.path.join(output_dir, fname)
            if not os.path.isfile(fpath):
                continue
            norm_f = normalize_title_for_matching(fname)
            if len(norm_f) > 4 and (norm_target in norm_f or norm_f in norm_target):
                return True, fname, format_size(os.path.getsize(fpath))

    return False, "", ""


def download_file(
    url,
    output_dir=".",
    unzip=True,
    clean_tags=False,
    on_progress: ProgressCallback = None,
    max_retries=3,
):
    os.makedirs(output_dir, exist_ok=True)
    raw_filename = url.split("/")[-1].split("?")[0]
    filename = urllib.parse.unquote(raw_filename)
    filepath = os.path.join(output_dir, filename)

    already_exists, found_name, found_size = is_game_already_downloaded(
        output_dir, filename, clean_tags=clean_tags
    )
    if already_exists:
        if on_progress:
            on_progress({"type": "file", "downloaded": 1, "total": 1, "filename": found_name})
        return {
            "status": "already_exists",
            "raw_name": filename,
            "roms": [{"name": found_name, "size": found_size}],
        }

    status = "success"
    rom_info = []

    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, headers={**HEADERS, "Referer": "https://romsfun.com/"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                total_size = int(resp.headers.get("content-length", 0))
                if on_progress:
                    on_progress(
                        {
                            "type": "file",
                            "downloaded": 0,
                            "total": total_size or None,
                            "filename": filename,
                        }
                    )

                chunk_size = 1024 * 64
                downloaded_bytes = 0
                with open(filepath, "wb") as f:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded_bytes += len(chunk)
                        if on_progress:
                            on_progress(
                                {
                                    "type": "file",
                                    "downloaded": downloaded_bytes,
                                    "total": total_size or None,
                                    "filename": filename,
                                }
                            )

                if total_size > 0 and downloaded_bytes < total_size:
                    raise OSError(f"Descarga incompleta ({downloaded_bytes}/{total_size} bytes)")
                break
        except Exception as e:
            if attempt < max_retries:
                time.sleep(2)
            else:
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except Exception:
                        pass
                return {
                    "status": "error",
                    "raw_name": filename,
                    "roms": [{"name": filename, "size": "0B"}],
                    "error": str(e),
                }

    if unzip and filepath.lower().endswith((".zip", ".7z", ".rar")):
        extracted = extract_archive(filepath, output_dir, clean_tags=clean_tags)
        rom_info = [{"name": n, "size": s} for n, s in extracted]
    else:
        clean_name = clean_filename_for_r36s(filename, clean_tags=clean_tags)
        clean_path = os.path.join(output_dir, clean_name)
        if filepath != clean_path:
            if os.path.exists(clean_path):
                os.remove(clean_path)
            os.rename(filepath, clean_path)
        fsize = format_size(os.path.getsize(clean_path)) if os.path.exists(clean_path) else "0B"
        rom_info = [{"name": clean_name, "size": fsize}]

    return {
        "status": status,
        "raw_name": filename,
        "roms": rom_info if rom_info else [{"name": filename, "size": "0B"}],
    }


def process_download_batch(
    items_to_download,
    base_output,
    unzip=True,
    single_version=True,
    clean_tags=False,
    on_progress: ProgressCallback = None,
    cancel_check: Optional[Callable[[], bool]] = None,
):
    total_games = len(items_to_download)
    summary_items = []
    pending_items = []
    start_time = time.time()

    def emit(event: dict):
        if on_progress:
            on_progress(event)

    emit({"type": "scan", "message": f"Analizando {total_games} juegos locales..."})

    for item in items_to_download:
        game_title = item["title"]
        console_name = item["console"]
        out_dir = resolve_output_dir(base_output, console_name)

        clean_expected = clean_filename_for_r36s(game_title, clean_tags=clean_tags)
        exists, found_name, found_size = is_game_already_downloaded(
            out_dir, clean_expected, clean_tags=clean_tags
        )
        if not exists:
            clean_no_tags = clean_filename_for_r36s(game_title, clean_tags=True)
            exists, found_name, found_size = is_game_already_downloaded(
                out_dir, clean_no_tags, clean_tags=True
            )

        if exists:
            summary_items.append(
                {
                    "title": game_title,
                    "console": console_name,
                    "status": "already_exists",
                    "roms": [{"name": found_name, "size": found_size}],
                }
            )
        else:
            pending_items.append(item)

    existing_count = len(summary_items)
    emit(
        {
            "type": "batch",
            "current": existing_count,
            "total": total_games,
            "message": f"{existing_count}/{total_games} ya listos",
        }
    )

    if not pending_items:
        elapsed = time.time() - start_time
        result = {"items": summary_items, "elapsed": elapsed}
        emit({"type": "done", **result})
        return result

    for current_idx, item in enumerate(pending_items, existing_count + 1):
        if cancel_check and cancel_check():
            emit({"type": "cancelled", "items": summary_items})
            break

        game_title = item["title"]
        console_name = item.get("console") or get_console_folder_name(item.get("console_slug", "ROM"))
        out_dir = resolve_output_dir(base_output, console_name)

        emit(
            {
                "type": "batch",
                "current": current_idx - 1,
                "total": total_games,
                "title": game_title,
                "console": console_name,
                "message": f"Procesando ({current_idx}/{total_games}): {game_title}",
            }
        )

        try:
            links = find_direct_download_links(item["url"])
            if single_version:
                links = select_best_version(links)

            if not links:
                summary_items.append(
                    {
                        "title": game_title,
                        "console": console_name,
                        "status": "error",
                        "roms": [{"name": game_title, "size": "0B"}],
                        "error": "No se encontraron enlaces de descarga",
                    }
                )
            else:
                for name, durl in links:
                    emit(
                        {
                            "type": "resolving",
                            "title": game_title,
                            "filename": name,
                            "message": f"Descargando: {name}",
                        }
                    )

                    def file_progress(ev):
                        emit({**ev, "title": game_title, "console": console_name})

                    res = download_file(
                        durl,
                        output_dir=out_dir,
                        unzip=unzip,
                        clean_tags=clean_tags,
                        on_progress=file_progress,
                    )
                    summary_items.append(
                        {
                            "title": game_title,
                            "console": console_name,
                            "status": res["status"],
                            "roms": res["roms"],
                            "error": res.get("error"),
                        }
                    )
        except Exception as e:
            summary_items.append(
                {
                    "title": game_title,
                    "console": console_name,
                    "status": "error",
                    "roms": [{"name": game_title, "size": "0B"}],
                    "error": str(e),
                }
            )

        emit(
            {
                "type": "batch",
                "current": current_idx,
                "total": total_games,
                "title": game_title,
                "console": console_name,
            }
        )

    elapsed = time.time() - start_time
    result = {"items": summary_items, "elapsed": elapsed}
    emit({"type": "done", **result})
    return result
