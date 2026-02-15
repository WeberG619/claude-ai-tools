"""
Revit Automation Examples using Weber SDK.

Requires Revit to be running with RevitMCPBridge installed.
"""

import asyncio
from weber_sdk import Weber


async def revit_basics():
    """Basic Revit operations."""
    async with Weber() as w:
        # Get document info
        doc = await w.revit2026.get_document_info()
        print(f"Document: {doc.get('name')}")
        print(f"Path: {doc.get('path')}")

        # Get active view
        view = await w.revit2026.get_active_view()
        print(f"Active view: {view.get('name')} ({view.get('type')})")


async def revit_query_elements():
    """Query elements from the model."""
    async with Weber() as w:
        # Get all levels
        levels = await w.revit2026.get_levels()
        print(f"Found {len(levels)} levels:")
        for level in levels:
            print(f"  {level.get('name')} @ elevation {level.get('elevation')}")

        # Get walls on a specific level
        walls = await w.revit2026.get_walls(level_name="Level 1")
        print(f"\nFound {len(walls)} walls on Level 1:")
        for wall in walls[:5]:  # First 5
            print(f"  {wall.get('type_name')} - Length: {wall.get('length')}")

        # Get rooms
        rooms = await w.revit2026.get_rooms()
        print(f"\nFound {len(rooms)} rooms:")
        for room in rooms[:5]:
            print(f"  {room.get('number')}: {room.get('name')} - Area: {room.get('area')}")


async def revit_create_walls():
    """Create walls in the model."""
    async with Weber() as w:
        # Start a transaction
        await w.revit2026.start_transaction("Create Walls from SDK")

        try:
            # Create a rectangular room outline
            # Units are typically in feet
            origin = (0, 0, 0)
            width = 20  # feet
            depth = 15  # feet

            # Create four walls
            walls = []

            # Bottom wall
            wall = await w.revit2026.create_wall(
                start_point=(0, 0, 0),
                end_point=(width, 0, 0),
                level_name="Level 1",
            )
            walls.append(wall)

            # Right wall
            wall = await w.revit2026.create_wall(
                start_point=(width, 0, 0),
                end_point=(width, depth, 0),
                level_name="Level 1",
            )
            walls.append(wall)

            # Top wall
            wall = await w.revit2026.create_wall(
                start_point=(width, depth, 0),
                end_point=(0, depth, 0),
                level_name="Level 1",
            )
            walls.append(wall)

            # Left wall
            wall = await w.revit2026.create_wall(
                start_point=(0, depth, 0),
                end_point=(0, 0, 0),
                level_name="Level 1",
            )
            walls.append(wall)

            # Commit transaction
            await w.revit2026.commit_transaction()
            print(f"Created {len(walls)} walls")

        except Exception as e:
            # Rollback on error
            await w.revit2026.rollback_transaction()
            print(f"Error: {e}")
            raise


async def revit_create_room():
    """Create a room after creating walls."""
    async with Weber() as w:
        await w.revit2026.start_transaction("Create Room from SDK")

        try:
            # Place room at center of the wall rectangle
            room = await w.revit2026.create_room(
                point=(10, 7.5, 0),  # Center of 20x15 rectangle
                level_name="Level 1",
                name="Office",
                number="101",
            )
            await w.revit2026.commit_transaction()
            print(f"Created room: {room}")

        except Exception as e:
            await w.revit2026.rollback_transaction()
            raise


async def revit_export():
    """Export views and sheets."""
    async with Weber() as w:
        # List sheets
        sheets = await w.revit2026.list_sheets()
        print(f"Found {len(sheets)} sheets")

        # Export to PDF (example path)
        # await w.revit2026.export_to_pdf(
        #     output_path="C:/Output/project.pdf",
        #     sheet_ids=[sheet["id"] for sheet in sheets[:5]]
        # )


async def revit_modify_elements():
    """Modify existing elements."""
    async with Weber() as w:
        # Get a wall
        walls = await w.revit2026.get_walls(level_name="Level 1")
        if not walls:
            print("No walls found")
            return

        wall_id = walls[0]["id"]

        await w.revit2026.start_transaction("Modify Wall")

        try:
            # Get a parameter
            mark = await w.revit2026.get_parameter(wall_id, "Mark")
            print(f"Current Mark: {mark}")

            # Set a parameter
            await w.revit2026.set_parameter(wall_id, "Mark", "SDK-001")

            # Move the element
            # await w.revit2026.move_element(wall_id, translation=(5, 0, 0))

            await w.revit2026.commit_transaction()

        except Exception as e:
            await w.revit2026.rollback_transaction()
            raise


if __name__ == "__main__":
    print("=== Revit Basics ===")
    asyncio.run(revit_basics())

    # Uncomment to run other examples
    # print("\n=== Query Elements ===")
    # asyncio.run(revit_query_elements())

    # print("\n=== Create Walls ===")
    # asyncio.run(revit_create_walls())
