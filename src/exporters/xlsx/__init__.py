"""
Excel (XLSX) Exporter for Ultima Underworld extracted data.

This module provides the XlsxExporter class for exporting game data
to multi-sheet Excel workbooks.

The exporter is split into multiple modules for better organization:
- base_exporter: Core XlsxExporterBase class with styles and helpers
- item_sheets: Item, weapon, armor, container, food, light source exports
- npc_sheets: NPC and NPC names exports
- spell_sheets: Spell, rune, and mantra exports
- conversation_sheets: Conversation exports
- placed_objects_sheet: Placed objects and unused items exports
"""

try:
    from openpyxl import Workbook
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

from .base_exporter import XlsxExporterBase
from .item_sheets import ItemSheetsMixin
from .npc_sheets import NPCSheetsMixin
from .spell_sheets import SpellSheetsMixin
from .conversation_sheets import ConversationSheetsMixin
from .placed_objects_sheet import PlacedObjectsSheetsMixin


class XlsxExporter(
    ItemSheetsMixin,
    NPCSheetsMixin,
    SpellSheetsMixin,
    ConversationSheetsMixin,
    PlacedObjectsSheetsMixin,
    XlsxExporterBase
):
    """
    Exports game data to Excel xlsx format.
    
    Combines all sheet export capabilities from mixin classes.
    
    Usage:
        exporter = XlsxExporter("Output")
        exporter.export_items(item_types, placed_items)
        exporter.export_npcs(npcs, npc_names, strings_parser)
        exporter.save()
    """
    pass


__all__ = ['XlsxExporter', 'OPENPYXL_AVAILABLE']
