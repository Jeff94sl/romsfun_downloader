"""Núcleo reutilizable de RomsFun Downloader (CLI + API de escritorio)."""

from .consoles import (
    CONSOLE_ALIASES,
    CONSOLE_DISPLAY_NAMES,
    CONSOLE_OPTIONS,
    get_console_folder_name,
    normalize_console_slug,
    extract_console_from_url,
)
from .catalog import search_roms, list_console_roms
from .download import (
    find_direct_download_links,
    download_file,
    process_download_batch,
    resolve_output_dir,
)
from .sanitize import (
    clean_filename_for_r36s,
    select_best_version,
    score_version_for_language,
    format_size,
)

__all__ = [
    "CONSOLE_ALIASES",
    "CONSOLE_DISPLAY_NAMES",
    "CONSOLE_OPTIONS",
    "get_console_folder_name",
    "normalize_console_slug",
    "extract_console_from_url",
    "search_roms",
    "list_console_roms",
    "find_direct_download_links",
    "download_file",
    "process_download_batch",
    "resolve_output_dir",
    "clean_filename_for_r36s",
    "select_best_version",
    "score_version_for_language",
    "format_size",
]
