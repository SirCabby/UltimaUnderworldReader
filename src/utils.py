"""
Shared utility functions for Ultima Underworld data extraction.

These functions are used across multiple extractors and exporters.
"""

from typing import Tuple


def parse_item_name(raw_name: str) -> Tuple[str, str, str]:
    """
    Parse item name format from STRINGS.PAK block 4.
    
    Format: 'article_name&plural'
    Examples:
        'a_sword&swords' -> ('sword', 'a', 'swords')
        'an_apple&apples' -> ('apple', 'an', 'apples')
        'some_gold&gold' -> ('gold', 'some', 'gold')
    
    Args:
        raw_name: Raw string from STRINGS.PAK block 4
        
    Returns:
        Tuple of (name, article, plural)
    """
    article = "a"
    name = raw_name
    plural = ""
    
    if '_' in raw_name:
        parts = raw_name.split('_', 1)
        article = parts[0]
        name = parts[1]
    
    if '&' in name:
        parts = name.split('&', 1)
        name = parts[0]
        plural = parts[1]
    
    return name, article, plural


def extract_name_only(raw_name: str) -> str:
    """
    Extract just the name portion from a raw object name string.
    
    Args:
        raw_name: Raw string from STRINGS.PAK block 4
        
    Returns:
        The name without article or plural suffix
    """
    name, _, _ = parse_item_name(raw_name)
    return name


def format_hex_id(value: int, width: int = 3) -> str:
    """
    Format an integer as a hex string with leading zeros.
    
    Args:
        value: Integer value to format
        width: Number of hex digits (default 3 for object IDs)
        
    Returns:
        Hex string like '0x00F' or '0x1A0'
    """
    return f"0x{value:0{width}X}"


def clamp(value: int, min_val: int, max_val: int) -> int:
    """
    Clamp a value to a range.
    
    Args:
        value: Value to clamp
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        Value clamped to [min_val, max_val]
    """
    return max(min_val, min(max_val, value))


def quality_to_offset(quality: int) -> int:
    """
    Convert quality value (0-63) to description offset (0-5).
    
    Quality descriptions in STRINGS.PAK block 5 are organized in groups of 6.
    This converts the raw quality value to an offset within a description group.
    
    Mapping:
        0-9   -> 0
        10-19 -> 1
        20-29 -> 2
        30-39 -> 3
        40-49 -> 4
        50-63 -> 5
    
    Args:
        quality: Quality value from object data (0-63)
        
    Returns:
        Offset into description group (0-5)
    """
    return min(5, quality // 10)

