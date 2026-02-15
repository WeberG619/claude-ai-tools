"""
Multi-Server Examples using Weber SDK.

Shows how to use multiple MCP servers together.
"""

import asyncio
from weber_sdk import Weber


async def revit_to_excel_export():
    """Export Revit data to Excel."""
    async with Weber() as w:
        # Get walls from Revit
        await w.voice.speak("Exporting Revit walls to Excel")

        walls = await w.revit2026.get_walls()
        print(f"Found {len(walls)} walls")

        # Prepare data for Excel
        table_data = [
            {
                "ID": wall["id"],
                "Type": wall["type_name"],
                "Level": wall["level"],
                "Length": wall["length"],
                "Height": wall["height"],
            }
            for wall in walls
        ]

        # Check Excel is running
        status = await w.excel.get_status()
        if not status.get("running"):
            await w.voice.speak("Please start Excel first")
            return

        # Write to Excel
        await w.excel.write_table("A1", table_data)
        await w.excel.auto_fit_columns()

        # Format header
        await w.excel.format_range(
            f"A1:E1",
            bold=True,
            bg_color="#4472C4",
        )

        await w.voice.speak(f"Exported {len(walls)} walls to Excel")


async def project_report():
    """Generate a project report with voice summary."""
    async with Weber() as w:
        # Gather data from Revit
        doc = await w.revit2026.get_document_info()
        levels = await w.revit2026.get_levels()
        walls = await w.revit2026.get_walls()
        rooms = await w.revit2026.get_rooms()

        # Calculate totals
        total_wall_length = sum(w.get("length", 0) for w in walls)
        total_room_area = sum(r.get("area", 0) for r in rooms)

        # Create report summary
        report = f"""
        Project Report: {doc.get('name', 'Unknown')}

        Levels: {len(levels)}
        Walls: {len(walls)}
        Rooms: {len(rooms)}

        Total Wall Length: {total_wall_length:.1f} ft
        Total Room Area: {total_room_area:.1f} sq ft
        """
        print(report)

        # Voice summary
        voice_summary = f"""
        Project report complete.
        The model contains {len(levels)} levels, {len(walls)} walls, and {len(rooms)} rooms.
        Total wall length is {total_wall_length:.0f} feet.
        Total room area is {total_room_area:.0f} square feet.
        """
        await w.voice.speak(voice_summary)


async def automated_workflow():
    """Automated workflow combining multiple servers."""
    async with Weber() as w:
        await w.voice.speak("Starting automated workflow")

        # Step 1: Query Revit
        await w.voice.speak("Step 1: Gathering model data")
        rooms = await w.revit2026.get_rooms()
        print(f"Found {len(rooms)} rooms")

        # Step 2: Process in Excel
        await w.voice.speak("Step 2: Analyzing in Excel")
        status = await w.excel.get_status()
        if status.get("running"):
            # Create summary in Excel
            summary = [
                {"Room": r["name"], "Number": r["number"], "Area": r["area"]}
                for r in rooms
            ]
            await w.excel.write_table("A1", summary)

        # Step 3: Report completion
        await w.voice.speak(f"Workflow complete. Processed {len(rooms)} rooms.")


async def discover_and_list():
    """Discover and list all available servers."""
    from weber_sdk import discover_servers

    servers = discover_servers(include_disabled=True)

    print("Discovered MCP Servers:\n")
    for name, config in sorted(servers.items()):
        status = "DISABLED" if config.disabled else "enabled"
        print(f"  {name}:")
        print(f"    Status: {status}")
        print(f"    Command: {config.command}")
        if config.comment:
            print(f"    Description: {config.comment}")
        print()


if __name__ == "__main__":
    print("=== Discover Servers ===")
    asyncio.run(discover_and_list())

    # Uncomment to run workflows
    # print("\n=== Revit to Excel Export ===")
    # asyncio.run(revit_to_excel_export())

    # print("\n=== Project Report ===")
    # asyncio.run(project_report())
