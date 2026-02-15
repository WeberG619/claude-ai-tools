"""
Excel Automation Examples using Weber SDK.

Requires Excel to be running on Windows.
"""

import asyncio
from weber_sdk import Weber


async def excel_basics():
    """Basic Excel operations."""
    async with Weber() as w:
        # Check if Excel is running
        status = await w.excel.get_status()
        if not status.get("running"):
            print("Excel is not running. Please start Excel first.")
            return

        print(f"Excel {status.get('version')} is running")
        print(f"Active workbook: {status.get('active_workbook', 'None')}")

        # List open workbooks
        workbooks = await w.excel.list_workbooks()
        print(f"Open workbooks: {workbooks.get('count', 0)}")


async def excel_read_write():
    """Read and write cell data."""
    async with Weber() as w:
        # Read a cell
        value = await w.excel.read_cell("A1")
        print(f"A1 = {value}")

        # Write a cell
        await w.excel.write_cell("A1", "Hello from Weber SDK!")

        # Read a range
        data = await w.excel.read_range("A1:C5")
        print("Range A1:C5:")
        for row in data:
            print(f"  {row}")

        # Write a range
        new_data = [
            ["Name", "Age", "City"],
            ["Alice", 30, "NYC"],
            ["Bob", 25, "LA"],
            ["Charlie", 35, "Chicago"],
        ]
        await w.excel.write_range("E1", new_data)


async def excel_tables():
    """Work with tables (dictionaries)."""
    async with Weber() as w:
        # Write data as a table
        employees = [
            {"Name": "Alice", "Department": "Engineering", "Salary": 75000},
            {"Name": "Bob", "Department": "Marketing", "Salary": 65000},
            {"Name": "Charlie", "Department": "Finance", "Salary": 80000},
        ]
        await w.excel.write_table("A1", employees)

        # Read table back
        table = await w.excel.read_table("A1:C4", has_headers=True)
        for row in table:
            print(f"{row['Name']} works in {row['Department']}")


async def excel_formatting():
    """Apply cell formatting."""
    async with Weber() as w:
        # Format header row
        await w.excel.format_range(
            "A1:C1",
            bold=True,
            bg_color="#4472C4",
            font_color="#FFFFFF",
        )

        # Format numbers as currency
        await w.excel.format_range(
            "C2:C10",
            number_format="$#,##0.00",
        )

        # Auto-fit columns
        await w.excel.auto_fit_columns()


async def excel_bulk_operations():
    """Efficient bulk operations with screen updating disabled."""
    async with Weber() as w:
        # Disable screen updating for faster bulk operations
        await w.excel.toggle_screen_updating(False)
        await w.excel.set_calculation_mode("manual")

        try:
            # Perform many operations
            for i in range(100):
                await w.excel.write_cell(f"A{i+1}", f"Row {i+1}")

        finally:
            # Re-enable screen updating
            await w.excel.set_calculation_mode("automatic")
            await w.excel.toggle_screen_updating(True)


if __name__ == "__main__":
    print("=== Excel Basics ===")
    asyncio.run(excel_basics())

    # Uncomment to run other examples
    # print("\n=== Read/Write ===")
    # asyncio.run(excel_read_write())

    # print("\n=== Tables ===")
    # asyncio.run(excel_tables())
