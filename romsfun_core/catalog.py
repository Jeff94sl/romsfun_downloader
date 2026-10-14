import math
import re
import urllib.parse

from .consoles import get_console_folder_name, normalize_console_slug
from .http_client import get_html


def search_roms(query: str):
    search_url = f"https://romsfun.com/?s={urllib.parse.quote(query)}"
    html = get_html(search_url)

    matches = re.findall(
        r'href="(https://romsfun\.com/roms/([^/]+)/([^/]+)\.html)"',
        html,
    )
    seen = set()
    results = []
    for full_url, console_slug, slug in matches:
        if full_url not in seen:
            seen.add(full_url)
            title = slug.replace("-", " ").title()
            console_name = get_console_folder_name(console_slug)
            results.append(
                {
                    "title": title,
                    "console": console_name,
                    "console_slug": console_slug,
                    "url": full_url,
                }
            )
    return results


def list_console_roms(console_slug: str, max_pages: int = 1, target_count=None):
    console_slug = normalize_console_slug(console_slug)
    console_name = get_console_folder_name(console_slug)
    results = []
    seen = set()

    for page in range(1, max_pages + 1):
        url = (
            f"https://romsfun.com/roms/{console_slug}/"
            if page == 1
            else f"https://romsfun.com/roms/{console_slug}/page/{page}/"
        )
        try:
            html = get_html(url)
            matches = re.findall(
                r'href="(https://romsfun\.com/roms/'
                + re.escape(console_slug)
                + r'/([^/]+)\.html)"',
                html,
            )
            if not matches:
                break
            for full_url, slug in matches:
                if full_url not in seen:
                    seen.add(full_url)
                    title = slug.replace("-", " ").title()
                    results.append(
                        {
                            "title": title,
                            "console": console_name,
                            "console_slug": console_slug,
                            "url": full_url,
                        }
                    )
                    if target_count and len(results) >= target_count:
                        break
            if target_count and len(results) >= target_count:
                break
        except Exception:
            break

    return results


def pages_for_limit(limit: int, per_page: int = 20) -> int:
    return max(1, math.ceil(limit / per_page))
