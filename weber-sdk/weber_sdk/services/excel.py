"""
Excel service wrapper for excel-mcp.

Provides typed methods for Excel automation via xlwings.
"""

from typing import Any, Literal

from weber_sdk.services.base import BaseService


CalculationMode = Literal["automatic", "manual", "semi_automatic"]


class ExcelService(BaseService):
    """
    Excel service for Excel automation.

    Uses xlwings to control running Excel instances.
    Requires Excel to be running on Windows.
    """

    # ========================================================================
    # Status & Connection
    # ========================================================================

    async def get_status(self) -> dict[str, Any]:
        """
        Check if Excel is running and get version, workbook info.

        Returns:
            Dictionary with Excel status including:
            - running: bool
            - version: str
            - visible: bool
            - workbook_count: int
            - active_workbook: str (if any)
            - active_sheet: str (if any)
        """
        return await self.call("get_excel_status")

    async def list_workbooks(self) -> dict[str, Any]:
        """
        List all currently open workbooks.

        Returns:
            Dictionary with count and list of workbooks
        """
        return await self.call("list_open_workbooks")

    async def get_workbook_info(self) -> dict[str, Any]:
        """
        Get detailed information about the active workbook.

        Returns:
            Dictionary with sheets, named ranges, and metadata
        """
        return await self.call("get_active_workbook_info")

    # ========================================================================
    # Workbook Operations
    # ========================================================================

    async def open(self, path: str) -> dict[str, Any]:
        """
        Open a workbook file.

        Args:
            path: Path to the Excel file

        Returns:
            Workbook info
        """
        return await self.call("open_workbook", path=path)

    async def create(self) -> dict[str, Any]:
        """
        Create a new workbook.

        Returns:
            New workbook info
        """
        return await self.call("create_workbook")

    async def save(self, path: str | None = None) -> dict[str, Any]:
        """
        Save the active workbook.

        Args:
            path: Optional new path (Save As)

        Returns:
            Save result
        """
        kwargs: dict = {}
        if path:
            kwargs["path"] = path
        return await self.call("save_workbook", **kwargs)

    async def close(self, save: bool = True) -> dict[str, Any]:
        """
        Close the active workbook.

        Args:
            save: Whether to save before closing

        Returns:
            Close result
        """
        return await self.call("close_workbook", save=save)

    # ========================================================================
    # Sheet Operations
    # ========================================================================

    async def list_sheets(self) -> list[str]:
        """
        List all sheets in the active workbook.

        Returns:
            List of sheet names
        """
        result = await self.call("list_sheets")
        if isinstance(result, dict):
            return result.get("sheets", [])
        return []

    async def activate_sheet(self, name: str) -> dict[str, Any]:
        """
        Activate a sheet by name.

        Args:
            name: Sheet name

        Returns:
            Activation result
        """
        return await self.call("activate_sheet", name=name)

    async def add_sheet(self, name: str | None = None) -> dict[str, Any]:
        """
        Add a new sheet.

        Args:
            name: Optional sheet name

        Returns:
            New sheet info
        """
        kwargs: dict = {}
        if name:
            kwargs["name"] = name
        return await self.call("add_sheet", **kwargs)

    async def delete_sheet(self, name: str) -> dict[str, Any]:
        """
        Delete a sheet.

        Args:
            name: Sheet name to delete

        Returns:
            Delete result
        """
        return await self.call("delete_sheet", name=name)

    # ========================================================================
    # Cell Operations
    # ========================================================================

    async def read_cell(self, address: str) -> Any:
        """
        Read a single cell value.

        Args:
            address: Cell address (e.g., "A1", "B5")

        Returns:
            Cell value
        """
        return await self.call("read_cell", address=address)

    async def write_cell(self, address: str, value: Any) -> dict[str, Any]:
        """
        Write a value to a single cell.

        Args:
            address: Cell address
            value: Value to write

        Returns:
            Write result
        """
        return await self.call("write_cell", address=address, value=value)

    async def read_range(self, address: str) -> list[list[Any]]:
        """
        Read a range of cells.

        Args:
            address: Range address (e.g., "A1:C10")

        Returns:
            2D list of values
        """
        result = await self.call("read_range", address=address)
        if isinstance(result, dict):
            return result.get("data", [])
        return result if isinstance(result, list) else []

    async def write_range(self, address: str, data: list[list[Any]]) -> dict[str, Any]:
        """
        Write data to a range of cells.

        Args:
            address: Starting cell address
            data: 2D list of values

        Returns:
            Write result
        """
        return await self.call("write_range", address=address, data=data)

    # ========================================================================
    # Formatting
    # ========================================================================

    async def format_range(
        self,
        address: str,
        bold: bool | None = None,
        italic: bool | None = None,
        font_size: int | None = None,
        font_color: str | None = None,
        bg_color: str | None = None,
        number_format: str | None = None,
    ) -> dict[str, Any]:
        """
        Apply formatting to a range.

        Args:
            address: Range address
            bold: Make text bold
            italic: Make text italic
            font_size: Font size
            font_color: Font color (hex or name)
            bg_color: Background color
            number_format: Number format string

        Returns:
            Format result
        """
        kwargs: dict[str, Any] = {"address": address}
        if bold is not None:
            kwargs["bold"] = bold
        if italic is not None:
            kwargs["italic"] = italic
        if font_size is not None:
            kwargs["font_size"] = font_size
        if font_color is not None:
            kwargs["font_color"] = font_color
        if bg_color is not None:
            kwargs["bg_color"] = bg_color
        if number_format is not None:
            kwargs["number_format"] = number_format

        return await self.call("format_range", **kwargs)

    async def auto_fit_columns(self, address: str | None = None) -> dict[str, Any]:
        """
        Auto-fit column widths.

        Args:
            address: Optional range to auto-fit (defaults to used range)

        Returns:
            Auto-fit result
        """
        kwargs: dict = {}
        if address:
            kwargs["address"] = address
        return await self.call("auto_fit_columns", **kwargs)

    # ========================================================================
    # Settings
    # ========================================================================

    async def set_calculation_mode(self, mode: CalculationMode) -> dict[str, Any]:
        """
        Set Excel calculation mode.

        Args:
            mode: 'automatic', 'manual', or 'semi_automatic'

        Returns:
            Mode change result
        """
        return await self.call("set_calculation_mode", mode=mode)

    async def toggle_screen_updating(self, enabled: bool) -> dict[str, Any]:
        """
        Enable or disable screen updating.

        Disable during bulk operations for performance.

        Args:
            enabled: True to enable, False to disable

        Returns:
            Toggle result
        """
        return await self.call("toggle_screen_updating", enabled=enabled)

    # ========================================================================
    # Convenience Methods
    # ========================================================================

    async def read_table(self, address: str, has_headers: bool = True) -> list[dict[str, Any]]:
        """
        Read a range as a table with headers.

        Args:
            address: Range address
            has_headers: First row contains headers

        Returns:
            List of dictionaries (one per row)
        """
        data = await self.read_range(address)
        if not data:
            return []

        if has_headers:
            headers = data[0]
            return [dict(zip(headers, row)) for row in data[1:]]
        else:
            # Generate column names
            headers = [f"Column{i+1}" for i in range(len(data[0]))]
            return [dict(zip(headers, row)) for row in data]

    async def write_table(
        self,
        address: str,
        data: list[dict[str, Any]],
        write_headers: bool = True,
    ) -> dict[str, Any]:
        """
        Write a list of dictionaries as a table.

        Args:
            address: Starting cell address
            data: List of dictionaries
            write_headers: Whether to write headers

        Returns:
            Write result
        """
        if not data:
            return {"success": False, "error": "No data to write"}

        headers = list(data[0].keys())
        rows = [[row.get(h, "") for h in headers] for row in data]

        if write_headers:
            rows.insert(0, headers)

        return await self.write_range(address, rows)
