"""
Spell and Mantra Extractor for Ultima Underworld

Extracts:
- All spells with their names, circles, rune combinations, and descriptions
- All mantras for shrines
- Verified spell metadata from uwadv documentation
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from ..parsers.strings_parser import StringsParser
from ..constants import RUNE_NAMES
from ..constants.spells import (
    SPELL_RUNES,
    SPELL_CIRCLES,
    SPELL_DESCRIPTIONS,
    SPELL_MANA_COSTS,
    SPELL_MIN_LEVELS,
    UNDOCUMENTED_SPELLS,
    NPC_ONLY_SPELLS,
    PLAYER_SPELLS,
    PROTECTION_SPELL_TIERS,
    LIGHT_SPELL_LEVELS,
    get_spell_info,
)


@dataclass
class Spell:
    """Information about a spell."""
    spell_id: int
    name: str
    circle: int = 0
    mana_cost: int = 0
    min_level: int = 0
    runes: List[str] = field(default_factory=list)
    description: str = ""
    undocumented: bool = False
    npc_only: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'spell_id': self.spell_id,
            'name': self.name,
            'circle': self.circle,
            'mana_cost': self.mana_cost,
            'min_level': self.min_level,
            'runes': self.runes,
            'rune_code': "".join(r[0] for r in self.runes) if self.runes else "",
            'description': self.description,
            'undocumented': self.undocumented,
            'npc_only': self.npc_only,
        }


@dataclass
class Mantra:
    """Information about a mantra."""
    mantra_id: int
    text: str
    skill: str = ""  # Associated skill if known
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'mantra_id': self.mantra_id,
            'text': self.text,
            'skill': self.skill
        }


class SpellExtractor:
    """
    Extracts all spell and mantra data from Ultima Underworld.
    
    Usage:
        extractor = SpellExtractor("path/to/DATA")
        extractor.extract()
        
        spells = extractor.get_all_spells()
        mantras = extractor.get_all_mantras()
    """
    
    def __init__(self, data_path: str | Path):
        self.data_path = Path(data_path)
        
        # Initialize parser
        self.strings = StringsParser(self.data_path / "STRINGS.PAK")
        
        # Extracted data
        self.spells: List[Spell] = []
        self.mantras: List[Mantra] = []
        
        self._extracted = False
    
    def extract(self) -> None:
        """Extract all spell and mantra data."""
        self.strings.parse()
        
        self._extract_spells()
        self._extract_mantras()
        
        self._extracted = True
    
    def _extract_spells(self) -> None:
        """Extract spell names from block 6 and enrich with metadata."""
        spell_names = self.strings.get_block(StringsParser.BLOCK_SPELL_NAMES) or []
        
        for spell_id, name in enumerate(spell_names):
            name = name.strip() if name else ""
            if not name:
                continue
            
            # Get verified metadata if available
            circle = SPELL_CIRCLES.get(name, 0)
            
            # If no verified circle, estimate from spell_id for internal spells
            if circle == 0 and spell_id < 64:
                circle = (spell_id // 8) + 1
            
            mana_cost = SPELL_MANA_COSTS.get(circle, 0)
            min_level = SPELL_MIN_LEVELS.get(circle, 0)
            runes = SPELL_RUNES.get(name, [])
            description = SPELL_DESCRIPTIONS.get(name, "")
            undocumented = name in UNDOCUMENTED_SPELLS
            npc_only = name in NPC_ONLY_SPELLS
            
            self.spells.append(Spell(
                spell_id=spell_id,
                name=name,
                circle=circle,
                mana_cost=mana_cost,
                min_level=min_level,
                runes=runes.copy() if runes else [],
                description=description,
                undocumented=undocumented,
                npc_only=npc_only,
            ))
    
    def _extract_mantras(self) -> None:
        """Extract mantras from block 2."""
        mantra_block = self.strings.get_block(StringsParser.BLOCK_CHARGEN_MANTRAS) or []
        
        # Mantras are typically later in this block
        # Known mantras and their associated skills
        known_mantras = {
            "om": "meditation",
            "mu": "attack",
            "ra": "defense",
            "summ": "swimming",
            "amo": "acrobat",
            "lore": "lore",
            "cav": "search",
            "dis": "stealth",
            "ora": "traps",
            "fahm": "repair",
            "kap": "charm",
            "hunn": "picklock",
            "anra": "casting",
            "monm": "mana",
            "lu": "eyesight",      # From scroll 34
            "un": "charm/barter",  # From scroll 35
            "sahf": "tracking",    # From scroll 68
            "ono": "swimming",     # From scroll 71
            "sol": "casting",      # From scroll 175 (mana regeneration)
        }
        
        for mantra_id, text in enumerate(mantra_block):
            text = text.strip().lower() if text else ""
            if text and len(text) >= 2 and len(text) <= 10:
                # Check if it looks like a mantra
                if text.isalpha():
                    skill = known_mantras.get(text, "")
                    self.mantras.append(Mantra(
                        mantra_id=mantra_id,
                        text=text,
                        skill=skill
                    ))
    
    def get_all_spells(self) -> List[Spell]:
        """Get all extracted spells."""
        if not self._extracted:
            self.extract()
        return self.spells
    
    def get_all_mantras(self) -> List[Mantra]:
        """Get all extracted mantras."""
        if not self._extracted:
            self.extract()
        return self.mantras
    
    def get_player_spells(self) -> List[Spell]:
        """Get only player-castable spells."""
        if not self._extracted:
            self.extract()
        return [s for s in self.spells if not s.npc_only and s.runes]
    
    def get_spells_by_circle(self, circle: int) -> List[Spell]:
        """Get spells of a specific circle."""
        if not self._extracted:
            self.extract()
        return [s for s in self.spells if s.circle == circle]
    
    def get_undocumented_spells(self) -> List[Spell]:
        """Get spells not in original manual."""
        if not self._extracted:
            self.extract()
        return [s for s in self.spells if s.undocumented]
    
    def get_npc_only_spells(self) -> List[Spell]:
        """Get spells only NPCs can cast."""
        if not self._extracted:
            self.extract()
        return [s for s in self.spells if s.npc_only]
    
    def get_rune_names(self) -> Dict[int, str]:
        """Get the rune names dictionary."""
        return RUNE_NAMES.copy()
    
    def get_spell_runes(self) -> Dict[str, List[str]]:
        """Get known spell rune combinations."""
        return SPELL_RUNES.copy()
    
    def get_spell_by_name(self, name: str) -> Optional[Spell]:
        """Get a spell by name."""
        if not self._extracted:
            self.extract()
        for spell in self.spells:
            if spell.name.lower() == name.lower():
                return spell
        return None
    
    def get_spell_by_runes(self, runes: List[str]) -> Optional[Spell]:
        """Get a spell by its rune combination."""
        if not self._extracted:
            self.extract()
        for spell_name, spell_runes in SPELL_RUNES.items():
            if spell_runes == runes:
                return self.get_spell_by_name(spell_name)
        return None
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of extracted data."""
        if not self._extracted:
            self.extract()
        
        spells_by_circle = {}
        for spell in self.spells:
            c = spell.circle
            spells_by_circle[c] = spells_by_circle.get(c, 0) + 1
        
        player_spells = [s for s in self.spells if not s.npc_only and s.runes]
        undocumented = [s for s in self.spells if s.undocumented]
        
        return {
            'total_spells': len(self.spells),
            'player_spells': len(player_spells),
            'npc_only_spells': len(self.spells) - len(player_spells),
            'undocumented_spells': len(undocumented),
            'total_mantras': len(self.mantras),
            'total_runes': len(RUNE_NAMES),
            'spells_by_circle': spells_by_circle,
            'known_spell_runes': len(SPELL_RUNES),
        }
    
    def get_spellbook(self) -> Dict[int, List[Dict]]:
        """Get spells organized as a spellbook by circle."""
        if not self._extracted:
            self.extract()
        
        spellbook = {}
        for circle in range(1, 9):
            circle_spells = self.get_spells_by_circle(circle)
            # Filter to player-castable spells with known runes
            player_castable = [s for s in circle_spells if s.runes and not s.npc_only]
            spellbook[circle] = [s.to_dict() for s in player_castable]
        
        return spellbook


def main():
    """Test the spell extractor."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python spell_extractor.py <path_to_DATA_folder>")
        sys.exit(1)
    
    extractor = SpellExtractor(sys.argv[1])
    extractor.extract()
    
    summary = extractor.get_summary()
    
    print("Spell & Mantra Summary:")
    print("=" * 60)
    print(f"Total spells in game: {summary['total_spells']}")
    print(f"Player-castable spells: {summary['player_spells']}")
    print(f"NPC-only spells: {summary['npc_only_spells']}")
    print(f"Undocumented spells: {summary['undocumented_spells']}")
    print(f"Total mantras: {summary['total_mantras']}")
    print(f"Total runes: {summary['total_runes']}")
    
    print("\nPlayer Spells by Circle:")
    print("-" * 60)
    for circle in range(1, 9):
        spells = extractor.get_spells_by_circle(circle)
        player_spells = [s for s in spells if s.runes and not s.npc_only]
        if player_spells:
            mana = SPELL_MANA_COSTS.get(circle, 0)
            min_lvl = SPELL_MIN_LEVELS.get(circle, 0)
            print(f"\n  Circle {circle} (Mana: {mana}, Min Level: {min_lvl}):")
            for spell in player_spells:
                rune_code = "".join(r[0] for r in spell.runes)
                undoc = " *" if spell.undocumented else ""
                print(f"    {spell.name}{undoc}")
                print(f"      Runes: {' '.join(spell.runes)} ({rune_code})")
                if spell.description:
                    print(f"      Effect: {spell.description}")
    
    print("\n\nUndocumented Spells (not in original manual):")
    print("-" * 60)
    for spell in extractor.get_undocumented_spells():
        if spell.runes:
            rune_code = "".join(r[0] for r in spell.runes)
            print(f"  {spell.name} ({rune_code}) - Circle {spell.circle}")
    
    print("\nRunes:")
    for rune_id, name in sorted(RUNE_NAMES.items()):
        print(f"  {rune_id:2d}: {name}")
    
    print("\nMantras (with known skills):")
    for mantra in extractor.mantras:
        if mantra.skill:
            print(f"  '{mantra.text}' -> {mantra.skill}")


if __name__ == '__main__':
    main()
