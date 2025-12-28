# Input Folder - Game Data Files

This folder should contain the original game data files from **Ultima Underworld: The Stygian Abyss** (1992).

## Required Structure

```
Input/
└── UW1/
    └── DATA/
        ├── COMOBJ.DAT      # Common object properties
        ├── CNV.ARK         # Conversation scripts
        ├── LEV.ARK         # Level data (tilemaps, objects)
        ├── OBJECTS.DAT     # Object class properties
        └── STRINGS.PAK     # Game text strings (Huffman compressed)
```

## Where to Get the Game Files

You need a legal copy of Ultima Underworld I. The game is available from:

- **GOG.com**: [Ultima Underworld 1+2](https://www.gog.com/game/ultima_underworld_1_2)
- **Steam**: Search for "Ultima Underworld"
- **Original CD-ROM**: If you have the original media

### Extracting from GOG/Steam

After purchasing and downloading:

1. **GOG**: Install the game, then find the DATA folder in the installation directory
2. **Steam**: Right-click the game → Properties → Local Files → Browse Local Files

Copy the entire `DATA` folder to `Input/UW1/DATA/`.

## Verification

After placing the files, you should have at minimum these files:
- `Input/UW1/DATA/STRINGS.PAK` (~47 KB)
- `Input/UW1/DATA/LEV.ARK` (~300 KB)
- `Input/UW1/DATA/CNV.ARK` (~166 KB)
- `Input/UW1/DATA/OBJECTS.DAT` (~1 KB)
- `Input/UW1/DATA/COMOBJ.DAT` (~6 KB)

## Running the Extraction

Once you have the game files in place:

```bash
# Extract all data to JSON and Excel
make xlsx

# Or just JSON
make extract

# Generate web map viewer
make web
make start
```

## Legal Notice

The game data files are copyrighted material owned by Electronic Arts / Origin Systems. This toolkit only extracts and displays data from legally obtained copies of the game. Do not distribute the game files.

## Troubleshooting

**"File not found" errors**: Make sure the folder structure exactly matches `Input/UW1/DATA/` with the files directly inside (not in a subdirectory).

**Case sensitivity**: On Linux/Mac, file names are case-sensitive. The original DOS files are uppercase (e.g., `STRINGS.PAK`), but most extraction tools will work with any case.

