"""
Spell-related sheet exports for Excel exporter.
"""

from typing import Dict, List

from ...constants import (
    COMPLETE_MANTRAS,
    NPC_ONLY_SPELLS,
    PLAYER_SPELLS,
    RUNE_MEANINGS,
)


class SpellSheetsMixin:
    """Mixin providing spell-related sheet exports."""
    
    def export_spells(self, spells: List, spell_runes: Dict) -> None:
        """Export spells with descriptions and caster info."""
        from ...constants import SPELL_DESCRIPTIONS
        
        headers = ["ID", "Name", "Circle", "Rune Combination", "Description", "Caster"]
        ws = self._create_sheet("Spells", headers)
        
        row = 2
        for spell in spells:
            runes = spell_runes.get(spell.name, [])
            rune_str = " ".join(runes) if runes else ""
            
            description = SPELL_DESCRIPTIONS.get(spell.name, "")
            
            # Only show circle for player spells with rune combinations
            circle_str = spell.circle if rune_str else ""
            
            if spell.name in NPC_ONLY_SPELLS:
                caster = "NPC Only"
            elif spell.name in PLAYER_SPELLS or rune_str:
                caster = "Player"
            else:
                caster = ""
            
            values = [spell.spell_id, spell.name, circle_str, rune_str, description, caster]
            self._add_row(ws, row, values, row % 2 == 0)
            row += 1
        self._auto_column_width(ws)
    
    def export_runes(self, runes: Dict) -> None:
        """Export runes."""
        headers = ["ID", "Rune Name", "Meaning"]
        ws = self._create_sheet("Runes", headers)
        
        row = 2
        for rune_id in sorted(runes.keys()):
            name = runes[rune_id]
            meaning = RUNE_MEANINGS.get(name, "")
            self._add_row(ws, row, [rune_id, name, meaning], row % 2 == 0)
            row += 1
        self._auto_column_width(ws)
    
    def export_mantras(self) -> None:
        """Export complete mantra list with point increases."""
        headers = ["Mantra", "Skill(s) Affected", "Effect/Notes", "Point Increase"]
        ws = self._create_sheet("Mantras", headers)
        
        row = 2
        for mantra, skills, notes, points in COMPLETE_MANTRAS:
            self._add_row(ws, row, [mantra, skills, notes, points], row % 2 == 0)
            row += 1
        self._auto_column_width(ws)
