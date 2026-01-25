# Ultima Underworld Data Extraction Toolkit

A Python toolkit for extracting and analyzing game data from **Ultima Underworld I: The Stygian Abyss** (1992).

**Live Demo:** [https://sircabby.github.io/UltimaUnderworldReader/](https://sircabby.github.io/UltimaUnderworldReader/)

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Place game files in Input/UW1/DATA/ (see below)

# 3. Extract all game data
make extract
```

## Features

- **Complete Data Extraction**: 512 item types, 872+ NPCs, 64 spells, 60+ conversations
- **Binary Format Parsing**: Decodes Huffman-compressed strings, ARK containers, level data
- **Multiple Export Formats**: JSON for programmatic use, XLSX for spreadsheet analysis
- **Interactive Web Viewer**: Browse levels, objects, and NPCs visually
- **Conversation Decompiler**: Parses the bytecode VM used for NPC dialogues

## Installation

### Requirements

- **Python 3.8+**
- **openpyxl** (optional, for Excel export)
- **Pillow** (optional, for image extraction)

```bash
pip install -r requirements.txt
```

### Game Files

Place the following files in `Input/UW1/DATA/`:

| File | Description |
|------|-------------|
| `STRINGS.PAK` | Game text strings |
| `LEV.ARK` | Level data |
| `CNV.ARK` | Conversation scripts |
| `OBJECTS.DAT` | Object properties |
| `COMOBJ.DAT` | Common object properties |

**Optional files** for web viewer:
- `OBJECTS.GR` or `TMOBJ.GR` - Object sprites
- `TERRAIN.DAT` - Terrain classification

See [`Input/README.md`](Input/README.md) for how to obtain game files from GOG, Steam, or original media.

## Usage

### Command Line

```bash
# Extract to JSON
python main.py Input/UW1/DATA Output

# Extract to JSON and Excel
python main.py Input/UW1/DATA Output --xlsx
```

### Using Makefile

```bash
make extract    # Extract data to JSON/XLSX
make web        # Generate web viewer (maps, images, data)
make serve      # Start local web server
make clean      # Remove generated files
```

### Web Viewer

**Option 1: GitHub Pages** (no setup required)

Visit [https://sircabby.github.io/UltimaUnderworldReader/](https://sircabby.github.io/UltimaUnderworldReader/)

**Option 2: Local**

```bash
make web        # Generate all data
make serve      # Start server at http://localhost:8000
```

## Output Files

### JSON Files (in `Output/`)

| File | Content |
|------|---------|
| `strings.json` | All game text by block |
| `items.json` | 512 item type definitions |
| `placed_objects.json` | All objects in levels |
| `npcs.json` | NPCs with stats and positions |
| `spells.json` | Spells, runes, mantras |
| `conversations.json` | Decompiled conversations |
| `map_data.json` | Level statistics |

### Excel Workbook

`ultima_underworld_data.xlsx` contains multiple sheets:
- Items, Weapons, Armor, Containers
- NPCs, NPC Names
- Spells, Runes, Mantras
- Conversations, Placed Objects

---

## For Developers

### Project Structure

```
├── main.py                 # Main entry point
├── src/
│   ├── parsers/            # Binary file parsers
│   │   ├── strings_parser.py   # STRINGS.PAK
│   │   ├── level_parser.py     # LEV.ARK
│   │   ├── objects_parser.py   # OBJECTS.DAT
│   │   └── conversation_parser.py
│   ├── extractors/         # High-level extractors
│   │   ├── item_extractor.py
│   │   ├── npc_extractor.py
│   │   └── spell_extractor.py
│   ├── models/             # Data models
│   ├── exporters/          # JSON and XLSX export
│   ├── resolvers/          # Enchantment, lock, spell resolution
│   ├── constants/          # Game constants
│   ├── tools/              # Debug utilities
│   └── utils.py            # Shared utilities
├── web/                    # Web viewer
└── docs/                   # Technical documentation
```

### Architecture

**Parsers** (stateless after `.parse()`):
```python
parser = StringsParser("STRINGS.PAK")
parser.parse()
data = parser.get_block(4)  # Object names
```

**Extractors** (high-level, use dependency injection):
```python
extractor = ItemExtractor("path/to/DATA")
extractor.extract()
items = extractor.get_all_item_types()
```

### Adding New Features

**New Extractor:**
1. Create `src/extractors/new_extractor.py`
2. Use relative imports from `..parsers`, `..constants`
3. Export from `src/extractors/__init__.py`
4. Add export methods to JsonExporter/XlsxExporter

**New Constants:**
1. Add to appropriate file in `src/constants/`
2. Export from `src/constants/__init__.py`

### Testing Changes

```bash
# Regenerate all outputs
python main.py Input/UW1/DATA Output --xlsx

# Regenerate web viewer
make web
```

### Binary Format Documentation

See [`docs/FORMATS.md`](docs/FORMATS.md) for detailed binary file format specifications.

---

## Credits

- Format documentation: [Underworld Adventures](http://uwadv.sourceforge.net/) project
- Original game: Blue Sky Productions / Looking Glass Technologies

## License

MIT License - See LICENSE file
