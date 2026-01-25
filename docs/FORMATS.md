# Ultima Underworld Binary File Formats

This document describes the binary file formats used by Ultima Underworld I: The Stygian Abyss (1992).

## Overview

The game stores data in several proprietary binary formats:

| File | Description |
|------|-------------|
| `STRINGS.PAK` | Huffman-compressed game text |
| `LEV.ARK` | Level data (tilemaps, objects) |
| `CNV.ARK` | Conversation scripts (bytecode VM) |
| `OBJECTS.DAT` | Object class properties |
| `COMOBJ.DAT` | Common object properties |

## STRINGS.PAK - Game Text

Huffman-compressed text strings organized into blocks.

### Header Structure

```
Offset  Size  Description
0x0000  2     Node count (N)
0x0002  N×4   Huffman tree nodes
        2     Block count (M)
        M×6   Block directory (block_num:2, offset:4)
```

### String Blocks

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

Object name format in Block 4: `article_name&plural` (e.g., `a_sword&swords`)

## LEV.ARK - Level Data

ARK container with 135 blocks (9 levels × 15 block types).

### ARK Container Format

```
Offset  Size    Description
0x0000  2       Block count (N)
0x0002  N×4     Block offsets
```

### Block Types

| Blocks | Content |
|--------|---------|
| 0-8 | Main level data (31752 bytes each) |
| 9-17 | Object animation overlay |
| 18-26 | Texture mapping |
| 27-35 | Automap data |
| 36-44 | Map notes |

### Level Data Block Layout (31752 bytes)

| Offset | Size | Content |
|--------|------|---------|
| 0x0000 | 16384 | Tilemap (64×64 tiles, 4 bytes each) |
| 0x4000 | 6912 | Mobile objects (256 × 27 bytes) |
| 0x5B00 | 6144 | Static objects (768 × 8 bytes) |
| 0x7300 | 508 | Mobile free list |
| 0x74FC | 1536 | Static free list |
| 0x7AFC | 260 | Unknown |
| 0x7C06 | 2 | Magic marker 'uw' (0x7775) |

### Tile Format (4 bytes)

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

### Object Format (8 bytes base, 27 for mobile)

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

## CNV.ARK - Conversations

ARK container with up to 256 conversation slots. Each conversation is bytecode for a virtual machine with 29+ opcodes.

### Conversation Header

| Offset | Size | Content |
|--------|------|---------|
| 0x0000 | 2 | Unknown (0x0828) |
| 0x0004 | 2 | Code size in words |
| 0x000A | 2 | String block number |
| 0x000C | 2 | Variable count |
| 0x000E | 2 | Import count |

### Key Opcodes

| Opcode | Name | Description |
|--------|------|-------------|
| 0x27 | SAY_OP | NPC speaks (string index on stack) |
| 0x16 | PUSHI | Push immediate value |
| CALLI 0 | babl_menu() | Player response selection |

## OBJECTS.DAT - Class Properties

Contains property tables for specific object classes.

| Offset | Count | Size | Content |
|--------|-------|------|---------|
| 0x0002 | 16 | 8 | Melee weapons (damage, skill, durability) |
| 0x0082 | 16 | 3 | Ranged weapons |
| 0x00B2 | 32 | 4 | Armor (protection, durability, slot) |
| 0x0132 | 64 | 48 | Creatures |
| 0x0D32 | 16 | 3 | Containers (capacity, accepts, slots) |
| 0x0D62 | 16 | 2 | Light sources (brightness, duration) |
| 0x0DA2 | 16 | 4 | Animations |

## COMOBJ.DAT - Common Properties

11 bytes per object (512 objects = 5632 bytes):

| Byte | Content |
|------|---------|
| 0 | bits 0-4: 3D height, bits 5-7: radius |
| 1 | bits 0-3: flags, bits 4-7: mass fraction |
| 2 | mass whole (×16 for 0.1 stones) |
| 3 | quality/type flags |
| 4 | value in gold |
| 5 | bit 4: can be picked up |
| 6-10 | various flags |

Mass formula: `mass = byte[2] * 16 + ((byte[1] >> 4) & 0x0F)` (in 0.1 stones)

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

## Enchantment Encoding

```
is_enchanted flag must be set
is_quantity determines if link field is quantity or enchantment link
If is_quantity=True and quantity >= 512: enchantment = quantity - 512

Weapons: 192-199 = accuracy, 200-207 = damage bonus
Armor: 192-199 = protection, 200-207 = toughness
0-63 maps to spell indices 256-319
```

## NPC Data (Mobile Objects)

Mobile objects have 19 extra bytes after the base 8:

| Offset | Content |
|--------|---------|
| 0 | HP |
| 3-4 | goal (bits 0-3), gtarg (bits 4-11) |
| 5-6 | level (bits 0-3), talkedto (bit 13), attitude (bits 14-15) |
| 14-15 | yhome (bits 4-9), xhome (bits 10-15) |
| 17 | hunger (bits 0-6) |
| 18 | npc_whoami (conversation slot) |

## Known Quirks

1. **Quality 63** in COMOBJ.DAT usually means "undefined" (placeholder)
2. **NPCs at tile (0,0)** are often templates, not actually placed
3. **Block 7 indices 0-16** are system strings, not NPC names
4. **Conversation slot 0** means no conversation (monster)
5. **Wands** store spell in linked object (item_id 0x120), not directly
6. **Container odd IDs** (0x81, 0x83, etc.) are "open" versions

## References

- [Underworld Adventures Project](http://uwadv.sourceforge.net/) - Original format documentation
- Level coordinate system: (0,0) is SW corner, Y increases north, X increases east
