# 🎮 RomsFun Downloader & R36S Optimizer

Una herramienta para buscar, listar y descargar ROMs desde **RomsFun**, optimizada para consolas portátiles retro como la **R36S** (ArkOS / EmulationStation / AmberELEC).

Incluye **CLI en Python** y una **app de escritorio nativa** (PySide6 / Qt) con tema azul celeste.

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![Desktop](https://img.shields.io/badge/Desktop-PySide6-skyblue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![R36S Ready](https://img.shields.io/badge/R36S-Ready-magenta.svg)
![Rich UI](https://img.shields.io/badge/UI-Rich%20Terminal-cyan.svg)

---

## ✨ Características Principales

* 📂 **Organización Automática por Consola:** Crea automáticamente carpetas ordenadas por consola (`downloads/GBA/`, `downloads/NDS/`, `downloads/PS2/`, `downloads/N64/`, etc.).
* 🌐 **Filtrado Inteligente de Idioma (Deduplicación):**
  * **Prioridad 1:** Versión en **Español** 🇪🇸 (`Spain`, `Spanish`, `Espanol`, `Edicion`, `Es`).
  * **Prioridad 2:** Versión en **Inglés** 🇬🇧/🇺🇸 (`USA`, `Europe`, `En`, `World`).
  * Descarga **únicamente 1 versión óptima por juego**, evitando descargar versiones redundantes en otros idiomas o revisiones duplicadas.
* 📦 **Descompresión e Higienización de Nombres para R36S:**
  * Extrae automáticamente archivos `.zip`, `.7z` y `.rar`.
  * Sanitiza los nombres de los archivos eliminando caracteres incompatibles con **FAT32** y **EmulationStation** (`: ? * " < > | / \ # % { } @ ! ~ $ & '`).
  * Convierte tildes y caracteres especiales Unicode a ASCII plano.
  * Elimina automáticamente los archivos comprimidos originales tras la extracción.
* 📄 **Paginación Multipágina:** Navega automáticamente entre las páginas de RomsFun para cumplir con cualquier número de juegos solicitado en `--limit` (ej. `--limit 100`).
* 🎨 **Interfaz de Terminal Avanzada (Rich UI):** Tablas elegantes, alertas a color y barra de progreso interactiva con velocidad de descarga (MB/s) y tiempo restante.
* 🖥️ **App de escritorio (PySide6):** misma UX azul celeste con búsqueda, lotes por consola (+ filtro por nombre), URL directa, progreso en vivo y ajustes R36S.
* 🐍 **Entorno Virtual Automatizado:** Detecta y ejecuta el entorno virtual `.venv` automáticamente sin necesidad de activación manual previa.

---

## 🚀 Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/romsfun-downloader.git
cd romsfun-downloader
```

### 2. Crear el entorno virtual e instalar dependencias
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. App de escritorio
```bash
./start-desktop.sh
# o
python3 romsfun_gui.py
```

---

## 🖥️ App de escritorio

Funciones:
* Buscar por palabra clave y seleccionar juegos
* Por consola: listar lote o buscar por nombre dentro de la consola
* Descargar desde URL directa de RomsFun
* Progreso del lote + archivo actual
* Ajustes: carpeta de salida, unzip, mejor versión ES>EN, limpieza de tags

Arquitectura:
* `romsfun_core/` — lógica de negocio Python
* `gui/` — interfaz PySide6 (diseño azul celeste)
* `romsfun_gui.py` — punto de entrada de la app
* `romsfun_downloader.py` — CLI Rich
* `api_server.py` — API local opcional (JSON + SSE)

---

## 🛠️ Modos de Uso (CLI)

### 🔍 1. Buscar un juego por palabra clave
```bash
python3 romsfun_downloader.py --search "mario kart"
```

### 🕹️ 2. Descargar juegos por lote por consola (ej. GBA, NDS, PS2, N64)
```bash
python3 romsfun_downloader.py --console gba --limit 10 --yes
```

### 🔗 3. Descargar un juego mediante su URL directa
```bash
python3 romsfun_downloader.py --url "https://romsfun.com/roms/nintendo-ds/pokemon-conquest-ultimate.html"
```

---

## 🕹️ Aliases de Consolas Soportadas

| Consola | Alias Válidos |
|---|---|
| **Game Boy Advance** | `gba`, `gameboy-advance`, `gameboy advance` |
| **Nintendo DS** | `nds`, `ds` |
| **Nintendo 3DS** | `3ds` |
| **Nintendo 64** | `n64` |
| **Super Nintendo** | `snes` |
| **NES** | `nes` |
| **PlayStation 1** | `ps1`, `playstation` |
| **PlayStation 2** | `ps2`, `playstation-2` |
| **PlayStation Portable** | `psp`, `playstation-portable` |
| **Sega Genesis** | `sega`, `genesis`, `sega-genesis` |
| **Nintendo GameCube** | `gamecube` |
| **Nintendo Wii** | `wii` |

---

## ⚙️ Referencia de Banderas y Opciones

```text
-s, --search SEARCH   Buscar juegos por palabra clave.
-c, --console CONSOLE Nombre o alias de la consola.
-u, --url URL         URL directa de la página del juego en RomsFun.
-l, --limit LIMIT     Cantidad máxima de juegos a descargar (por defecto: 5).
-o, --output OUTPUT   Directorio base de descargas (por defecto: ./downloads).
-y, --yes             Confirmar descargas automáticamente (modo no interactivo).
--all-versions        Descargar todas las versiones de idioma en lugar de la mejor.
--clean-tags          Remover etiquetas de región en () y [] de los nombres.
--no-unzip            No extraer automáticamente los archivos comprimidos.
```

---

## 📝 Licencia

Este proyecto está bajo la Licencia MIT.
