# Ultima Underworld Difficulty System Investigation

## Summary

This document summarizes the investigation into how difficulty settings (Standard vs Easy) affect item locations in Ultima Underworld I: The Stygian Abyss.

## Findings

### LEV.ARK Structure Analysis

**File**: `Input/UW1/DATA/LEV.ARK`  
**Size**: 290,864 bytes  
**Block Structure**: Exactly 135 blocks (as expected)

- **Blocks 0-8**: Level data (9 levels, 31,752 bytes each)
- **Blocks 9-17**: Animation overlay data (9 levels, 384 bytes each)
- **Blocks 18-26**: Texture mapping (9 levels, 122 bytes each)
- **Blocks 27-35**: Automap data (empty in this file)
- **Blocks 36-44**: Map notes (empty in this file)
- **Blocks 45+**: Unused (empty)

**Key Finding**: LEV.ARK contains exactly 135 blocks with no additional difficulty-specific blocks. All level data blocks are consistently 31,752 bytes.

### Which Difficulty Is Currently Exported?

**Conclusion**: The current export represents **ONE** difficulty setting, but we cannot determine which one (Standard or Easy) from the static data files alone.

### How Difficulty Affects Item Locations

**Hypothesis**: Difficulty differences are likely **applied at runtime** by the game engine, rather than being stored as separate data in LEV.ARK.

**Evidence**:
1. LEV.ARK contains exactly the expected 135 blocks - no additional blocks for different difficulties
2. All level data blocks have consistent structure and sizes
3. No difficulty flags or indicators found in level data structure
4. The unknown data region (0x7AFC-0x7BFF, 260 bytes) differs between levels but appears to contain level-specific data (some code/data patterns), not difficulty metadata

### Unknown Data Region Analysis

The "unknown" region at offset 0x7AFC-0x7BFF (260 bytes) in each level data block:
- **Levels 0-4, 6-7**: Contains non-zero data with patterns resembling code/data
- **Level 5**: Mostly zeros (204 of 260 bytes are 0x00)
- Patterns suggest this region may contain embedded code or level-specific configuration data
- **Not difficulty-related**: The differences between levels don't correlate with difficulty settings

### String Data

Difficulty strings are found in STRINGS.PAK, Block 2 (Character Generation):
- Index 544: "Standard"
- Index 545: "Easy"
- Index 537: "Choose difficulty:"

These strings are used for the character creation UI but don't indicate which difficulty data is stored in LEV.ARK.

### Object Placement

All levels contain:
- 1024 total object slots (256 mobile + 768 static)
- Many objects at tile (0,0) are templates (not actually placed)
- Objects have flag bits, but no difficulty-specific flags were identified

## Implications for Export

1. **Single Difficulty Export**: Our current export represents one difficulty setting, but we cannot determine which one from the data files
2. **Runtime Application**: If difficulty affects item locations, the game engine likely:
   - Reads the base level data from LEV.ARK
   - Applies difficulty-specific modifications at runtime
   - These modifications could involve:
     - Filtering out certain items
     - Moving items to different locations
     - Changing item properties
     - Spawning additional items

3. **No Separate Data Files**: There are no separate LEV.ARK files for different difficulties (at least not in the standard game distribution)

## Recommendations

1. **Document Current State**: Note in README that exports represent one difficulty setting (unspecified)
2. **User Verification**: Users can verify which difficulty their game files represent by comparing exported item locations with in-game observations
3. **Future Enhancement**: If both difficulty versions can be obtained, compare item locations to identify differences
4. **Game Engine Analysis**: A reverse engineering of the game executable could reveal how difficulty modifies level data at runtime

## Analysis Tools Created

- `analyze_lev_ark.py`: Analyzes LEV.ARK structure, block counts, sizes, and patterns
- `inspect_level_data.py`: Byte-level inspection of level data blocks, unknown regions, and object placement patterns

## References

- LEV.ARK file structure: See `src/parsers/ark_parser.py` and `src/parsers/level_parser.py`
- Level data format: See `README.md` and `.cursorrules`
- Analysis output: Run `python analyze_lev_ark.py` and `python inspect_level_data.py`
