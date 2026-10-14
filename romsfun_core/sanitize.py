import math
import os
import re
import unicodedata


def score_version_for_language(filename: str) -> int:
    fn = filename.lower()
    score = 0

    is_spanish = bool(
        re.search(r"\b(spain|spanish|espanol|edicion)\b", fn)
        or re.search(r"[\(\s,](es|sp)[\),\s]", fn)
        or "espanol" in fn
        or "edicion" in fn
    )

    is_english = bool(
        re.search(r"\b(usa|europe|world|us|eu|en|english|uk)\b", fn)
        or re.search(r"[\(\s,](en)[\),\s]", fn)
    )

    if is_spanish:
        score += 1000
    elif is_english:
        score += 500
    else:
        score += 100

    rev_match = re.search(r"rev\s*(\d+)", fn)
    if rev_match:
        score += int(rev_match.group(1)) * 10

    if "(wii u virtual console)" in fn or "(wii virtual console)" in fn:
        score += 5

    if any(x in fn for x in ["beta", "demo", "proto", "sample"]):
        score -= 200

    return score


def select_best_version(links):
    if not links:
        return []
    if len(links) == 1:
        return links
    best_link = max(links, key=lambda x: score_version_for_language(x[0]))
    return [best_link]


def clean_filename_for_r36s(filename: str, clean_tags: bool = False) -> str:
    name, ext = os.path.splitext(filename)
    name = unicodedata.normalize("NFKD", name).encode("ASCII", "ignore").decode("utf-8")
    name = re.sub(r'[:?\*\"<>|/\\#%{}@!~\$&\']', "", name)

    if clean_tags:
        name = re.sub(r"\([^)]*\)", "", name)
        name = re.sub(r"\[[^\]]*\]", "", name)

    name = re.sub(r"\s+", " ", name).strip()
    name = re.sub(r"-+", "-", name).strip(" -")

    if not name:
        name = "ROM_Game"

    return f"{name}{ext.lower()}"


def format_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"


def normalize_title_for_matching(title: str) -> str:
    name, _ = os.path.splitext(title)
    name = re.sub(r"\([^)]*\)", "", name)
    name = re.sub(r"\[[^\]]*\]", "", name)
    name = unicodedata.normalize("NFKD", name).encode("ASCII", "ignore").decode("utf-8")
    name = re.sub(r"[^a-zA-Z0-9]", "", name).lower()
    return name
