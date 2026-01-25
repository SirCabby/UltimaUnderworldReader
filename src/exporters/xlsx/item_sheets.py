"""
Item-related sheet exports for Excel exporter.

Includes: Items, Weapons, Armor, Containers, Food, Light Sources
"""

from typing import Dict, List

from ...constants import (
    CARRYABLE_CATEGORIES,
    CARRYABLE_CONTAINERS,
)
from ...utils import parse_item_name


class ItemSheetsMixin:
    """Mixin providing item-related sheet exports."""
    
    def export_items(self, item_types: Dict, placed_items: List) -> None:
        """Export all item types."""
        headers = [
            "ID", "ID (Hex)", "Name", "Category",
            "Weight", "Value", 
            "Property 1", "Property 2", "Property 3", "Property 4"
        ]
        ws = self._create_sheet("Items", headers)
        
        row = 2
        for item_id in sorted(item_types.keys()):
            item = item_types[item_id]
            props = item.properties
            prop_strs = [f"{k}: {v}" for k, v in list(props.items())[:4]]
            prop_strs.extend([""] * (4 - len(prop_strs)))
            
            # Determine if item can be carried based on category
            is_carryable = item.category in CARRYABLE_CATEGORIES
            
            # Weight in stones (mass is stored in 0.1 stone units)
            if is_carryable and item.mass > 0:
                weight_str = f"{item.mass / 10:.1f}"
            else:
                weight_str = ""
            
            # Value in gold
            value_str = str(item.value) if item.value > 0 else ""
            
            values = [
                item.item_id, f"0x{item.item_id:03X}", item.name, item.category,
                weight_str, value_str,
                prop_strs[0], prop_strs[1], prop_strs[2], prop_strs[3]
            ]
            self._add_row(ws, row, values, row % 2 == 0)
            row += 1
        self._auto_column_width(ws)
    
    def export_weapons(self, item_types: Dict, objects_parser) -> None:
        """Export weapons."""
        headers = ["ID", "Name", "Type", "Slash", "Bash", "Stab", "Skill", "Durability", "Weight", "Value"]
        ws = self._create_sheet("Weapons", headers)
        
        row = 2
        # Melee weapons (0x00-0x0F)
        for item_id in range(0x10):
            item = item_types.get(item_id)
            weapon = objects_parser.get_melee_weapon(item_id)
            if item and weapon:
                skill = weapon.skill_type.name if hasattr(weapon.skill_type, 'name') else str(weapon.skill_type)
                weight_str = f"{item.mass / 10:.1f}" if item.mass > 0 else ""
                values = [item_id, item.name, "Melee", weapon.slash_damage, weapon.bash_damage,
                         weapon.stab_damage, skill, weapon.durability, weight_str, item.value]
                self._add_row(ws, row, values, row % 2 == 0)
                row += 1
        
        # Ranged weapons (0x10-0x1F)
        for item_id in range(0x10, 0x20):
            item = item_types.get(item_id)
            weapon = objects_parser.get_ranged_weapon(item_id)
            if item and weapon:
                weight_str = f"{item.mass / 10:.1f}" if item.mass > 0 else ""
                values = [item_id, item.name, "Ranged", "-", "-", "-", "Missile",
                         weapon.durability, weight_str, item.value]
                self._add_row(ws, row, values, row % 2 == 0)
                row += 1
        self._auto_column_width(ws)
    
    def export_armor(self, item_types: Dict, objects_parser) -> None:
        """Export armor."""
        headers = ["ID", "Name", "Category", "Protection", "Durability", "Weight", "Value"]
        ws = self._create_sheet("Armor", headers)
        
        row = 2
        for item_id in range(0x20, 0x40):
            item = item_types.get(item_id)
            armor = objects_parser.get_armour(item_id)
            if item and armor:
                cat = armor.category.name if hasattr(armor.category, 'name') else str(armor.category)
                weight_str = f"{item.mass / 10:.1f}" if item.mass > 0 else ""
                values = [item_id, item.name, cat, armor.protection, armor.durability, weight_str, item.value]
                self._add_row(ws, row, values, row % 2 == 0)
                row += 1
        self._auto_column_width(ws)
    
    def export_containers(self, item_types: Dict, objects_parser, common_parser=None) -> None:
        """Export carryable containers only."""
        headers = ["ID", "Name", "Weight", "Capacity (stones)", "Accepts"]
        ws = self._create_sheet("Containers", headers)
        
        row = 2
        for item_id in sorted(CARRYABLE_CONTAINERS.keys()):
            item = item_types.get(item_id)
            container = objects_parser.get_container(item_id)
            if item and container:
                weight_str = f"{item.mass / 10:.1f}" if item.mass > 0 else ""
                values = [
                    item_id, item.name, weight_str, container.capacity_stones,
                    container.accepted_type_name
                ]
                self._add_row(ws, row, values, row % 2 == 0)
                row += 1
        self._auto_column_width(ws)
    
    def export_food(self, item_types: Dict, strings_parser=None) -> None:
        """Export food items with nutrition values."""
        from ...constants import FOOD_NUTRITION, FOOD_NOTES, FOOD_ID_MIN, FOOD_ID_MAX
        
        headers = ["ID", "Name", "Nutrition", "Weight", "Nutrition/Weight", "Notes"]
        ws = self._create_sheet("Food", headers)
        
        obj_names = []
        if strings_parser:
            obj_names = strings_parser.get_block(4) or []
        
        row = 2
        for item_id in range(FOOD_ID_MIN, FOOD_ID_MAX + 1):
            item = item_types.get(item_id)
            nutrition = FOOD_NUTRITION.get(item_id, 0)
            notes = FOOD_NOTES.get(item_id, "")
            
            name = ""
            if item:
                name = item.name
            elif item_id < len(obj_names) and obj_names[item_id]:
                name, _, _ = parse_item_name(obj_names[item_id])
            
            weight = 0.0
            weight_str = ""
            if item and item.mass > 0:
                weight = item.mass / 10.0
                weight_str = f"{weight:.1f}"
            
            efficiency_str = ""
            if weight > 0:
                efficiency = nutrition / weight
                efficiency_str = f"{efficiency:.1f}"
            
            values = [item_id, name, nutrition, weight_str, efficiency_str, notes]
            self._add_row(ws, row, values, row % 2 == 0)
            row += 1
        self._auto_column_width(ws)
    
    def export_light_sources(self, item_types: Dict, objects_parser, strings_parser=None) -> None:
        """Export light sources and light-granting spells."""
        from ...constants import SPELL_CIRCLES, LIGHT_SPELL_LEVELS
        
        headers = ["Type", "Name", "Light Level", "Duration", "Notes"]
        ws = self._create_sheet("Light Sources", headers)
        
        obj_names = []
        if strings_parser:
            obj_names = strings_parser.get_block(4) or []
        
        row = 2
        
        DURATION_SECONDS = {1: 300, 2: 600, 3: 900, 4: 1200}
        ITEM_LIGHT_LEVELS = {0x94: 5, 0x95: 4, 0x96: 2, 0x97: 3}
        
        # Lit light sources only
        for obj_id in (0x94, 0x95, 0x96, 0x97):
            light = objects_parser.get_light_source(obj_id)
            if light:
                name = ""
                if obj_id < len(obj_names) and obj_names[obj_id]:
                    name, _, _ = parse_item_name(obj_names[obj_id])
                if not name:
                    name = f"Light Source 0x{obj_id:02X}"
                
                light_level = ITEM_LIGHT_LEVELS.get(obj_id, 3)
                
                if obj_id == 0x97:  # Taper
                    duration_str = "Eternal"
                    notes = "Magical item from Shrine of Spirituality"
                else:
                    seconds = DURATION_SECONDS.get(light.duration, light.duration * 300)
                    minutes = seconds // 60
                    duration_str = f"~{minutes} min"
                    
                    if "lantern" in name.lower():
                        notes = "Brightest portable light, reusable"
                    elif "torch" in name.lower():
                        notes = "Standard portable light"
                    elif "candle" in name.lower():
                        notes = "Dim light, burns quickly"
                    else:
                        notes = ""
                
                values = ["Item", name, light_level, duration_str, notes]
                self._add_row(ws, row, values, row % 2 == 0)
                row += 1
        
        # Separator
        self._add_row(ws, row, ["", "", "", "", ""], False)
        row += 1
        
        # Light spells
        light_spells = [
            ("Light", 1, "~3 min", "IN LOR - Basic illumination"),
            ("Night Vision", 3, "~6 min", "QUAS LOR - See in darkness"),
            ("Daylight", 6, "~10 min", "VAS IN LOR - Bright area light"),
        ]
        
        for spell_name, circle, duration, notes in light_spells:
            light_level = LIGHT_SPELL_LEVELS.get(spell_name, circle)
            type_str = f"Spell (Circle {circle})"
            values = [type_str, spell_name, light_level, duration, notes]
            self._add_row(ws, row, values, row % 2 == 0)
            row += 1
        
        self._auto_column_width(ws)
