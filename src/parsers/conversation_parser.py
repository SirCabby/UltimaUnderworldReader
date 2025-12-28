"""
Conversation Decompiler for Ultima Underworld CNV.ARK

The conversation system uses a bytecode VM with 29+ opcodes.
This parser decompiles the bytecode into readable pseudo-code
and extracts all dialogue text.

Conversation header:
  0x0000: Int16 - Unknown (always 0x0828)
  0x0002: Int16 - Unknown (always 0x0000)
  0x0004: Int16 - Code size in 16-bit words
  0x0006: Int16 - Unknown
  0x0008: Int16 - Unknown
  0x000A: Int16 - String block number for conversation text
  0x000C: Int16 - Number of memory slots for variables
  0x000E: Int16 - Number of imported functions/globals

Import record format:
  Int16 - Length of function name
  N chars - Function name
  Int16 - ID (function) or memory address (variable)
  Int16 - Unknown (always 1)
  Int16 - Import type (0x010F=variable, 0x0111=function)
  Int16 - Return type (0x0000=void, 0x0129=int, 0x012B=string)
"""

import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from enum import IntEnum

try:
    from .ark_parser import CnvArkParser
except ImportError:
    from ark_parser import CnvArkParser


class Opcode(IntEnum):
    """Conversation VM opcodes."""
    NOP = 0x00
    OPADD = 0x01
    OPMUL = 0x02
    OPSUB = 0x03
    OPDIV = 0x04
    OPMOD = 0x05
    OPOR = 0x06
    OPAND = 0x07
    OPNOT = 0x08
    TSTGT = 0x09      # Greater than
    TSTGE = 0x0A      # Greater or equal
    TSTLT = 0x0B      # Less than
    TSTLE = 0x0C      # Less or equal
    TSTEQ = 0x0D      # Equal
    TSTNE = 0x0E      # Not equal
    JMP = 0x0F        # Jump absolute
    BEQ = 0x10        # Branch if equal (zero)
    BNE = 0x11        # Branch if not equal (non-zero)
    BRA = 0x12        # Branch always (relative)
    CALL = 0x13       # Call subroutine
    CALLI = 0x14      # Call intrinsic/imported function
    RET = 0x15        # Return from subroutine
    PUSHI = 0x16      # Push immediate value
    PUSHI_EFF = 0x17  # Push effective address
    POP = 0x18        # Pop and discard
    SWAP = 0x19       # Swap top two values
    PUSHBP = 0x1A     # Push base pointer
    POPBP = 0x1B      # Pop base pointer
    SPTOBP = 0x1C     # Stack pointer to base pointer
    BPTOSP = 0x1D     # Base pointer to stack pointer
    ADDSP = 0x1E      # Add to stack pointer
    FETCHM = 0x1F     # Fetch from memory
    STO = 0x20        # Store to memory
    OFFSET = 0x21     # Array offset
    START = 0x22      # Start program
    SAVE_REG = 0x23   # Save to result register
    PUSH_REG = 0x24   # Push result register
    STRCMP = 0x25     # String compare
    EXIT_OP = 0x26    # Exit program
    SAY_OP = 0x27     # NPC says text
    RESPOND_OP = 0x28 # Player response
    OPNEG = 0x29      # Negate


# Opcodes that take an immediate operand
OPCODES_WITH_IMMEDIATE = {
    Opcode.JMP, Opcode.BEQ, Opcode.BNE, Opcode.BRA,
    Opcode.CALL, Opcode.CALLI, Opcode.PUSHI, Opcode.PUSHI_EFF
}


@dataclass
class Import:
    """An imported function or variable."""
    name: str
    id_or_addr: int
    unknown: int
    import_type: int  # 0x010F = variable, 0x0111 = function
    return_type: int  # 0x0000 = void, 0x0129 = int, 0x012B = string
    
    @property
    def is_function(self) -> bool:
        return self.import_type == 0x0111
    
    @property
    def is_variable(self) -> bool:
        return self.import_type == 0x010F


@dataclass
class Instruction:
    """A single VM instruction."""
    address: int
    opcode: Opcode
    operand: Optional[int] = None
    
    def __str__(self) -> str:
        if self.operand is not None:
            return f"{self.address:04X}: {self.opcode.name} {self.operand}"
        return f"{self.address:04X}: {self.opcode.name}"


@dataclass
class Conversation:
    """A parsed conversation."""
    slot: int
    string_block: int
    num_variables: int
    imports: List[Import]
    code: List[Instruction]
    raw_code: bytes
    
    def get_import_by_id(self, func_id: int) -> Optional[Import]:
        """Get an import by its function ID."""
        for imp in self.imports:
            if imp.is_function and imp.id_or_addr == func_id:
                return imp
        return None


class ConversationParser:
    """
    Parser for CNV.ARK conversation bytecode.
    
    Usage:
        parser = ConversationParser("path/to/CNV.ARK")
        parser.parse()
        
        # Get a specific conversation
        conv = parser.get_conversation(1)
        
        # Decompile to readable format
        code = parser.decompile(1)
    """
    
    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)
        self.ark_parser = CnvArkParser(filepath)
        self.conversations: Dict[int, Conversation] = {}
        self._parsed = False
    
    def parse(self) -> None:
        """Parse all conversations from CNV.ARK."""
        self.ark_parser.parse()
        
        for slot, data in self.ark_parser.get_all_conversations().items():
            if len(data) < 16:  # Minimum header size
                continue
            
            conv = self._parse_conversation(slot, data)
            if conv:
                self.conversations[slot] = conv
        
        self._parsed = True
    
    def _parse_conversation(self, slot: int, data: bytes) -> Optional[Conversation]:
        """Parse a single conversation block."""
        try:
            offset = 0
            
            # Parse header
            unknown1 = struct.unpack_from('<H', data, offset)[0]
            offset += 2
            
            unknown2 = struct.unpack_from('<H', data, offset)[0]
            offset += 2
            
            code_size = struct.unpack_from('<H', data, offset)[0]
            offset += 2
            
            unknown3 = struct.unpack_from('<H', data, offset)[0]
            offset += 2
            
            unknown4 = struct.unpack_from('<H', data, offset)[0]
            offset += 2
            
            string_block = struct.unpack_from('<H', data, offset)[0]
            offset += 2
            
            num_variables = struct.unpack_from('<H', data, offset)[0]
            offset += 2
            
            num_imports = struct.unpack_from('<H', data, offset)[0]
            offset += 2
            
            # Parse imports
            imports = []
            for _ in range(num_imports):
                if offset + 2 > len(data):
                    break
                    
                name_len = struct.unpack_from('<H', data, offset)[0]
                offset += 2
                
                if offset + name_len > len(data):
                    break
                
                name = data[offset:offset + name_len].decode('ascii', errors='replace').rstrip('\x00')
                offset += name_len
                
                if offset + 8 > len(data):
                    break
                
                id_or_addr = struct.unpack_from('<H', data, offset)[0]
                offset += 2
                
                unknown = struct.unpack_from('<H', data, offset)[0]
                offset += 2
                
                import_type = struct.unpack_from('<H', data, offset)[0]
                offset += 2
                
                return_type = struct.unpack_from('<H', data, offset)[0]
                offset += 2
                
                imports.append(Import(name, id_or_addr, unknown, import_type, return_type))
            
            # Parse code
            code_start = offset
            code_bytes = data[code_start:code_start + code_size * 2]
            code = self._parse_code(code_bytes)
            
            return Conversation(
                slot=slot,
                string_block=string_block,
                num_variables=num_variables,
                imports=imports,
                code=code,
                raw_code=code_bytes
            )
        except Exception as e:
            print(f"Error parsing conversation {slot}: {e}")
            return None
    
    def _parse_code(self, code_bytes: bytes) -> List[Instruction]:
        """Parse bytecode into instructions."""
        instructions = []
        offset = 0
        address = 0
        
        while offset < len(code_bytes):
            if offset + 2 > len(code_bytes):
                break
            
            word = struct.unpack_from('<H', code_bytes, offset)[0]
            offset += 2
            
            try:
                opcode = Opcode(word)
            except ValueError:
                # Unknown opcode - treat as data
                instructions.append(Instruction(address, Opcode.NOP, word))
                address += 1
                continue
            
            # Check if opcode has an immediate operand
            if opcode in OPCODES_WITH_IMMEDIATE:
                if offset + 2 > len(code_bytes):
                    instructions.append(Instruction(address, opcode))
                    break
                
                operand = struct.unpack_from('<H', code_bytes, offset)[0]
                offset += 2
                instructions.append(Instruction(address, opcode, operand))
                address += 2
            else:
                instructions.append(Instruction(address, opcode))
                address += 1
        
        return instructions
    
    def get_conversation(self, slot: int) -> Optional[Conversation]:
        """Get a parsed conversation by slot number."""
        if not self._parsed:
            self.parse()
        return self.conversations.get(slot)
    
    def get_all_conversations(self) -> Dict[int, Conversation]:
        """Get all parsed conversations."""
        if not self._parsed:
            self.parse()
        return self.conversations
    
    def decompile(self, slot: int) -> str:
        """Decompile a conversation to readable pseudo-code."""
        conv = self.get_conversation(slot)
        if not conv:
            return f"Conversation {slot} not found"
        
        lines = [
            f"; Conversation Slot {slot}",
            f"; String Block: 0x{conv.string_block:04X}",
            f"; Variables: {conv.num_variables}",
            f"; Imports: {len(conv.imports)}",
            ""
        ]
        
        # List imports
        if conv.imports:
            lines.append("; Imports:")
            for imp in conv.imports:
                itype = "func" if imp.is_function else "var"
                lines.append(f";   {itype} {imp.name} = {imp.id_or_addr}")
            lines.append("")
        
        # List code
        lines.append("; Code:")
        for instr in conv.code:
            comment = ""
            
            # Add comments for known operations
            if instr.opcode == Opcode.CALLI and instr.operand is not None:
                imp = conv.get_import_by_id(instr.operand)
                if imp:
                    comment = f"  ; {imp.name}()"
            elif instr.opcode == Opcode.SAY_OP:
                comment = "  ; NPC speaks"
            elif instr.opcode == Opcode.RESPOND_OP:
                comment = "  ; Player response"
            elif instr.opcode == Opcode.JMP and instr.operand is not None:
                comment = f"  ; goto {instr.operand:04X}"
            elif instr.opcode in (Opcode.BEQ, Opcode.BNE, Opcode.BRA) and instr.operand is not None:
                target = instr.address + 2 + instr.operand
                if instr.operand > 0x7FFF:  # Negative offset (signed)
                    target = instr.address + 2 - (0x10000 - instr.operand)
                comment = f"  ; -> {target:04X}"
            
            lines.append(f"  {instr}{comment}")
        
        return '\n'.join(lines)
    
    def extract_dialogue_refs(self, slot: int) -> List[int]:
        """Extract all string references from a conversation."""
        conv = self.get_conversation(slot)
        if not conv:
            return []
        
        refs = []
        for i, instr in enumerate(conv.code):
            # Look for PUSHI followed by SAY_OP
            if instr.opcode == Opcode.PUSHI and instr.operand is not None:
                if i + 1 < len(conv.code):
                    next_instr = conv.code[i + 1]
                    if next_instr.opcode == Opcode.SAY_OP:
                        refs.append(instr.operand)
        
        return refs
    
    def dump_summary(self) -> str:
        """Return a summary of all parsed conversations."""
        if not self._parsed:
            self.parse()
        
        lines = [
            "CNV.ARK Conversation Summary",
            "=" * 50,
            f"Total conversations: {len(self.conversations)}",
            ""
        ]
        
        for slot in sorted(self.conversations.keys()):
            conv = self.conversations[slot]
            funcs = [imp.name for imp in conv.imports if imp.is_function]
            func_str = ', '.join(funcs[:3])
            if len(funcs) > 3:
                func_str += f", ... (+{len(funcs)-3})"
            lines.append(
                f"  Slot {slot:3d}: block=0x{conv.string_block:04X}, "
                f"{len(conv.code):4d} ops, imports=[{func_str}]"
            )
        
        return '\n'.join(lines)


def main():
    """Test the conversation parser."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python conversation_parser.py <path_to_CNV.ARK> [slot]")
        sys.exit(1)
    
    parser = ConversationParser(sys.argv[1])
    parser.parse()
    
    if len(sys.argv) >= 3:
        slot = int(sys.argv[2])
        print(parser.decompile(slot))
    else:
        print(parser.dump_summary())
        
        # Show first conversation decompiled
        if parser.conversations:
            first_slot = min(parser.conversations.keys())
            print(f"\n\nFirst conversation (slot {first_slot}):")
            print("=" * 50)
            print(parser.decompile(first_slot))


if __name__ == '__main__':
    main()



