"""
Base Excel exporter class with styles and helper methods.
"""

from pathlib import Path
from typing import List, Any

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


class XlsxExporterBase:
    """Base class for Excel export with shared styles and helpers."""
    
    # Styles
    HEADER_FONT = Font(bold=True, color="FFFFFF") if OPENPYXL_AVAILABLE else None
    HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid") if OPENPYXL_AVAILABLE else None
    HEADER_ALIGNMENT = Alignment(horizontal="center", vertical="center", wrap_text=True) if OPENPYXL_AVAILABLE else None
    ALT_ROW_FILL = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid") if OPENPYXL_AVAILABLE else None
    THIN_BORDER = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    ) if OPENPYXL_AVAILABLE else None
    
    def __init__(self, output_path: str | Path):
        if not OPENPYXL_AVAILABLE:
            raise ImportError("openpyxl is required. Install with: pip install openpyxl")
        self.output_path = Path(output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)
        self.wb = Workbook()
        self.wb.remove(self.wb.active)
    
    def _create_sheet(self, name: str, headers: List[str]) -> Any:
        """Create a new sheet with headers."""
        ws = self.wb.create_sheet(name)
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = self.HEADER_FONT
            cell.fill = self.HEADER_FILL
            cell.alignment = self.HEADER_ALIGNMENT
            cell.border = self.THIN_BORDER
        ws.freeze_panes = 'A2'
        return ws
    
    def _auto_column_width(self, ws, min_width: int = 8, max_width: int = 80):
        """Auto-adjust column widths based on content."""
        for column_cells in ws.columns:
            max_length = 0
            column = column_cells[0].column_letter
            for cell in column_cells:
                try:
                    if cell.value:
                        cell_len = len(str(cell.value))
                        if '\n' in str(cell.value):
                            cell_len = max(len(line) for line in str(cell.value).split('\n'))
                        max_length = max(max_length, cell_len)
                except:
                    pass
            adjusted_width = min(max(max_length + 2, min_width), max_width)
            ws.column_dimensions[column].width = adjusted_width
    
    def _add_row(self, ws, row_num: int, values: List[Any], alternate: bool = False):
        """Add a row of values to the sheet."""
        for col, value in enumerate(values, 1):
            cell = ws.cell(row=row_num, column=col, value=value)
            cell.border = self.THIN_BORDER
            if alternate:
                cell.fill = self.ALT_ROW_FILL
    
    def save(self, filename: str = "ultima_underworld_data.xlsx") -> Path:
        """Save the workbook."""
        filepath = self.output_path / filename
        self.wb.save(filepath)
        return filepath
