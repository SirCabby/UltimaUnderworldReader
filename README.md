# Ultima Underworld Data Extraction Toolkit

A Python toolkit for extracting and analyzing game data from **Ultima Underworld I: The Stygian Abyss** (1992).

This project parses the original DOS game files and extracts comprehensive game data including items, NPCs, spells, conversations, level maps, and more.

## Features

- **Complete Data Extraction**: Extracts 512 item types, 872+ NPCs, 64 spells, 60+ conversations
- **Binary Format Parsing**: Fully decodes Huffman-compressed strings, ARK containers, level data
- **Multiple Export Formats**: JSON for programmatic use, XLSX for spreadsheet analysis
- **Conversation Decompiler**: Parses the bytecode VM used for NPC dialogues

## Requirements

- **Python 3.8+**
- **openpyxl** (optional, for Excel export)
- **Pillow** (optional, for image extraction)

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Prepare input files:**
   - Place your Ultima Underworld game data files in the `Input` folder
   - Follow the detailed instructions available at [`Input/README.md`](Input/README.md)
   - See [Required Input Files](#required-input-files) below for the complete list

## Quick Start

**Prerequisites:** Ensure you have the required game data files in `Input/UW1/DATA/` (see [Required Input Files](#required-input-files)).

### Basic Extraction

**Using Makefile (recommended):**
```bash
# Extract to JSON and XLSX
make extract
```

### Web Map Viewer

The web viewer provides an interactive map interface with the following options:

#### Option 1: View on GitHub Pages (No Setup Required)

The web viewer is hosted on GitHub Pages and can be accessed directly:

**https://\<username\>.github.io/UltimaUnderworldReader/**

This includes all features including save game comparison (parsed client-side in your browser).

#### Option 2: Run Locally

For local development, or if you prefer a local solution:

```bash
# Generate all web viewer data (extracts data, generates maps, extracts images)
make web

# Start a simple static server (simulates GitHub Pages)
make serve

# Open in browser automatically
make open
```

**Note:** Local generation requires:
- Game data files (see [Required Input Files](#required-input-files))
- Optional: `OBJECTS.GR` or `TMOBJ.GR` for object images
- Optional: `TERRAIN.DAT` for accurate map generation

See [Generated Files](#generated-files) for details on what gets created.

## Required Input Files

The following files are **required** and must be placed in `Input/UW1/DATA/`:

| File | Size (approx) | Description |
|------|---------------|-------------|
| `STRINGS.PAK` | ~47 KB | Game text strings (Huffman compressed) |
| `LEV.ARK` | ~300 KB | Level data (tilemaps, objects) |
| `CNV.ARK` | ~166 KB | Conversation scripts |
| `OBJECTS.DAT` | ~1 KB | Object class properties |
| `COMOBJ.DAT` | ~6 KB | Common object properties |

**Optional files** (for web viewer features):

| File | Purpose |
|------|---------|
| `OBJECTS.GR` or `TMOBJ.GR` | Object sprite images (for web viewer) |
| `TERRAIN.DAT` | Terrain classification (for accurate map generation) |

**Where to get the files:**
- See [`Input/README.md`](Input/README.md) for detailed instructions on obtaining game files from GOG, Steam, or original media
- The game data files are copyrighted material and must be obtained legally

## Generated Files

After cloning the repository, several directories are excluded by `.gitignore` and need to be regenerated:

### Output Directory (`Output/`)

Contains all extracted game data in JSON format (and optionally XLSX):

- `strings.json` - All game text organized by block
- `items.json` - 512 item type definitions
- `placed_objects.json` - All objects placed in levels
- `npcs.json` - All NPCs with stats and positions
- `spells.json` - Spells, runes, mantras
- `conversations.json` - Decompiled conversation data
- `map_data.json` - Level statistics
- `web_map_data.json` - Web viewer data format
- `ultima_underworld_data.xlsx` - Multi-sheet Excel workbook (if `--xlsx` used)

**Regenerate with:**
```bash
make extract
```

### Web Viewer Files

**`web/data/`** - Web viewer data:
- `web_map_data.json` - Formatted data for the interactive map viewer

**`web/maps/`** - Map images:
- `level1.png` through `level9.png` - Visual map representations

**`web/images/extracted/objects/`** - Object sprite images:
- `object_*.png` - Extracted object sprites (if `OBJECTS.GR`/`TMOBJ.GR` available)

**`web/images/static/`** - Static assets (committed to repository):
- `stairs/stairs_up.png`, `stairs/stairs_down.png` - Stair images

**Regenerate with:**
```bash
# Generate everything for web viewer
make web
```

**Clean all generated files:**
```bash
make clean
```

## Project Structure

```
├── main.py                 # Main entry point
├── src/
│   ├── parsers/            # Low-level binary file parsers
│   │   ├── ark_parser.py       # ARK container format (LEV.ARK, CNV.ARK)
│   │   ├── strings_parser.py   # STRINGS.PAK Huffman decompression
│   │   ├── level_parser.py     # Level tilemap and object data
│   │   ├── objects_parser.py   # OBJECTS.DAT, COMOBJ.DAT properties
│   │   └── conversation_parser.py  # CNV.ARK bytecode decompiler
│   ├── extractors/         # High-level data extractors
│   │   ├── item_extractor.py   # All item types and placed objects
│   │   ├── npc_extractor.py    # NPCs with stats and conversations
│   │   ├── spell_extractor.py  # Spells, mantras, runes
│   │   └── secret_finder.py    # Triggers, traps, secrets
│   ├── models/             # Data models
│   │   ├── game_object.py      # GameObjectInfo, ItemInfo
│   │   └── npc.py              # NPCInfo
│   ├── constants/          # Game data constants
│   │   ├── runes.py            # Rune names and meanings
│   │   ├── spells.py           # Spell rune combinations
│   │   ├── npcs.py             # NPC types, goals, attitudes
│   │   ├── objects.py          # Object categories
│   │   └── mantras.py          # Shrine mantras
│   ├── exporters/          # Export formats
│   │   ├── json_exporter.py
│   │   └── xlsx_exporter.py
│   ├── tools/              # Debug and analysis utilities
│   │   ├── analyze_lev_ark.py  # LEV.ARK structure analyzer
│   │   ├── check_item.py       # Check specific item raw data
│   │   └── inspect_level_data.py  # Level data byte-level inspector
│   └── utils.py            # Shared utilities
├── Input/UW1/DATA/         # Game data files (not included)
├── Output/                 # Extracted data (JSON, XLSX)
└── web/                    # Web map viewer
    ├── data/               # Web viewer data (generated)
    ├── maps/               # Map images (generated)
    ├── images/             # Object sprites (extracted/) and static assets (static/)
    ├── generate_maps.py    # Map image generator
    ├── generate_images.py  # Object image extractor
    ├── index.html          # Web viewer interface
    └── server.py           # Simple HTTP server
```

## Binary File Formats

### STRINGS.PAK - Game Text

Huffman-compressed text strings organized into blocks:

| Block | Content |
|-------|---------|
| 1 | UI strings |
| 2 | Character creation, mantras |
| 3 | Book/scroll text |
| 4 | Object names (512 entries) |
| 5 | Object "look" descriptions |
| 6 | Spell names |
| 7 | NPC names (by conversation slot) |
| 8 | Wall/sign text |
| 9 | Trap messages |
| 0x0C00+ | Conversation dialogue |

Object name format: `article_name&plural` (e.g., `a_sword&swords`)

### LEV.ARK - Level Data

ARK container with 135 blocks (9 levels × 15 block types):

- **Blocks 0-8**: Level tilemap + master object list (31752 bytes each)
- **Blocks 9-17**: Object animation overlay
- **Blocks 18-26**: Texture mapping
- **Blocks 27-35**: Automap data
- **Blocks 36-44**: Map notes

#### Level Data Block Layout (31752 bytes)

| Offset | Size | Content |
|--------|------|---------|
| 0x0000 | 16384 | Tilemap (64×64 tiles, 4 bytes each) |
| 0x4000 | 6912 | Mobile objects (256 × 27 bytes) |
| 0x5B00 | 6144 | Static objects (768 × 8 bytes) |
| 0x7300 | 508 | Mobile free list |
| 0x74FC | 1536 | Static free list |
| 0x7AFC | 260 | Unknown |
| 0x7C06 | 2 | Magic marker 'uw' (0x7775) |

#### Tile Format (4 bytes)

```
Word 0:
  bits 0-3:   Tile type (0=solid, 1=open, 2-5=diagonal, 6-9=slope)
  bits 4-7:   Floor height (0-15)
  bits 10-13: Floor texture
  bit 14:     No-magic zone
  bit 15:     Door present

Word 1:
  bits 0-5:   Wall texture
  bits 6-15:  First object index in tile
```

#### Object Format (8 bytes base, 27 for mobile)

```
Word 0 (item_id/flags):
  bits 0-8:   Object ID (0-511)
  bit 12:     Enchanted
  bit 14:     Invisible
  bit 15:     is_quantity flag

Word 1 (position):
  bits 0-6:   Z position
  bits 7-9:   Heading (0-7, ×45°)
  bits 10-12: Y within tile (0-7)
  bits 13-15: X within tile (0-7)

Word 2 (quality/chain):
  bits 0-5:   Quality
  bits 6-15:  Next object index

Word 3 (link/special):
  bits 0-5:   Owner
  bits 6-15:  Quantity OR special link
```

Mobile objects (NPCs) have 19 additional bytes containing HP, goals, attitude, home position, conversation slot, etc.

### CNV.ARK - Conversations

ARK container with up to 256 conversation slots. Each conversation is bytecode for a virtual machine with 29+ opcodes.

#### Conversation Header

| Offset | Size | Content |
|--------|------|---------|
| 0x0000 | 2 | Unknown (0x0828) |
| 0x0004 | 2 | Code size in words |
| 0x000A | 2 | String block number |
| 0x000C | 2 | Variable count |
| 0x000E | 2 | Import count |

Key opcodes:
- `SAY_OP (0x27)`: NPC speaks (string index on stack)
- `CALLI 0`: `babl_menu()` - player response selection
- `PUSHI`: Push immediate value (string indices, etc.)

### OBJECTS.DAT - Class Properties

Contains property tables for specific object classes:

| Offset | Count | Size | Content |
|--------|-------|------|---------|
| 0x0002 | 16 | 8 | Melee weapons (damage, skill, durability) |
| 0x0082 | 16 | 3 | Ranged weapons |
| 0x00B2 | 32 | 4 | Armor (protection, durability, slot) |
| 0x0132 | 64 | 48 | Creatures |
| 0x0D32 | 16 | 3 | Containers (capacity, accepts, slots) |
| 0x0D62 | 16 | 2 | Light sources (brightness, duration) |
| 0x0DA2 | 16 | 4 | Animations |

### COMOBJ.DAT - Common Properties

11 bytes per object (512 objects = 5632 bytes):
- Mass in 0.1 stones
- Value in 0.1 gold
- Various flags (can be picked up, enchantable, etc.)

## Object ID Ranges

| Range | Category |
|-------|----------|
| 0x000-0x00F | Melee weapons |
| 0x010-0x01F | Ranged weapons |
| 0x020-0x03F | Armor |
| 0x040-0x07F | NPCs/Creatures |
| 0x080-0x08F | Containers |
| 0x090-0x09F | Light sources & wands |
| 0x0A0-0x0AF | Treasure |
| 0x0B0-0x0BF | Food & potions |
| 0x0C0-0x0DF | Scenery |
| 0x0E0-0x0FF | Runes |
| 0x100-0x10F | Keys |
| 0x110-0x12F | Quest items & misc |
| 0x130-0x13F | Books & scrolls |
| 0x140-0x14F | Doors |
| 0x150-0x17F | Furniture & switches |
| 0x180-0x19F | Traps |
| 0x1A0-0x1BF | Triggers |
| 0x1C0-0x1FF | System objects |

## Credits

- Format documentation based on the [Underworld Adventures](http://uwadv.sourceforge.net/) project
- Original game by Blue Sky Productions / Looking Glass Technologies

## License

MIT License - See LICENSE file

