import re

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
    "gamecube": "gamecube",
    "dreamcast": "dreamcast",
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

# Lista ordenada para la UI de escritorio
CONSOLE_OPTIONS = [
    {"alias": "gba", "slug": "game-boy-advance", "label": "Game Boy Advance", "folder": "GBA"},
    {"alias": "gb", "slug": "game-boy", "label": "Game Boy", "folder": "GB"},
    {"alias": "gbc", "slug": "game-boy-color", "label": "Game Boy Color", "folder": "GBC"},
    {"alias": "nds", "slug": "nintendo-ds", "label": "Nintendo DS", "folder": "NDS"},
    {"alias": "3ds", "slug": "nintendo-3ds", "label": "Nintendo 3DS", "folder": "3DS"},
    {"alias": "n64", "slug": "nintendo-64", "label": "Nintendo 64", "folder": "N64"},
    {"alias": "snes", "slug": "super-nintendo", "label": "Super Nintendo", "folder": "SNES"},
    {"alias": "nes", "slug": "nes", "label": "NES", "folder": "NES"},
    {"alias": "ps1", "slug": "playstation", "label": "PlayStation 1", "folder": "PS1"},
    {"alias": "ps2", "slug": "playstation-2", "label": "PlayStation 2", "folder": "PS2"},
    {"alias": "psp", "slug": "playstation-portable", "label": "PlayStation Portable", "folder": "PSP"},
    {"alias": "genesis", "slug": "sega-genesis", "label": "Sega Genesis", "folder": "SegaGenesis"},
    {"alias": "gamecube", "slug": "gamecube", "label": "Nintendo GameCube", "folder": "GameCube"},
    {"alias": "wii", "slug": "nintendo-wii", "label": "Nintendo Wii", "folder": "Wii"},
    {"alias": "wiiu", "slug": "wii-u", "label": "Nintendo Wii U", "folder": "WiiU"},
    {"alias": "psvita", "slug": "ps-vita", "label": "PS Vita", "folder": "PSVita"},
    {"alias": "dreamcast", "slug": "dreamcast", "label": "Dreamcast", "folder": "Dreamcast"},
]


def normalize_console_slug(console_str: str) -> str:
    cleaned = console_str.lower().strip()
    if cleaned in CONSOLE_ALIASES:
        return CONSOLE_ALIASES[cleaned]
    return cleaned.replace(" ", "-")


def get_console_folder_name(console_slug: str) -> str:
    slug = normalize_console_slug(console_slug)
    return CONSOLE_DISPLAY_NAMES.get(slug, slug.upper())


def extract_console_from_url(url: str):
    match = re.search(r"/roms/([^/]+)/", url)
    if match:
        return get_console_folder_name(match.group(1))
    return None
