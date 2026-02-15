"""
Revit service wrapper for RevitMCPBridge.

Provides typed methods for Revit automation via named pipes.
Supports both Revit 2025 and 2026.
"""

from typing import Any, Literal

from weber_sdk.services.base import BaseService


WallType = Literal[
    "Basic Wall",
    "Generic - 8\"",
    "Interior - 4\" Partition",
    "Interior - 5\" Partition",
    "Exterior - Brick on CMU",
]


class RevitService(BaseService):
    """
    Revit service for Revit automation via RevitMCPBridge.

    Connects to Revit through named pipes.
    Available for both Revit 2025 and 2026.
    """

    def __init__(self, *args: Any, version: str = "2026", **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.version = version

    # ========================================================================
    # Document Information
    # ========================================================================

    async def get_document_info(self) -> dict[str, Any]:
        """
        Get information about the active Revit document.

        Returns:
            Dictionary with document info including:
            - name: Document name
            - path: Full file path
            - is_family: Whether it's a family document
            - is_workshared: Whether worksharing is enabled
        """
        return await self.call("get_document_info")

    async def get_active_view(self) -> dict[str, Any]:
        """
        Get information about the active view.

        Returns:
            Dictionary with view info including:
            - name: View name
            - type: View type (FloorPlan, Section, etc.)
            - scale: View scale
            - detail_level: Detail level
        """
        return await self.call("get_active_view")

    async def list_views(self, view_type: str | None = None) -> list[dict[str, Any]]:
        """
        List all views in the document.

        Args:
            view_type: Optional filter by view type

        Returns:
            List of view dictionaries
        """
        kwargs: dict = {}
        if view_type:
            kwargs["view_type"] = view_type
        result = await self.call("list_views", **kwargs)
        return result if isinstance(result, list) else []

    # ========================================================================
    # Element Queries
    # ========================================================================

    async def get_walls(
        self,
        level_name: str | None = None,
        wall_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get all walls in the model.

        Args:
            level_name: Optional filter by level name
            wall_type: Optional filter by wall type name

        Returns:
            List of wall dictionaries with:
            - id: Element ID
            - type_name: Wall type name
            - level: Level name
            - length: Wall length
            - height: Wall height
            - start_point: Start coordinates
            - end_point: End coordinates
        """
        kwargs: dict = {}
        if level_name:
            kwargs["level_name"] = level_name
        if wall_type:
            kwargs["wall_type"] = wall_type
        result = await self.call("get_walls", **kwargs)
        return result if isinstance(result, list) else []

    async def get_rooms(self, level_name: str | None = None) -> list[dict[str, Any]]:
        """
        Get all rooms in the model.

        Args:
            level_name: Optional filter by level name

        Returns:
            List of room dictionaries with:
            - id: Element ID
            - name: Room name
            - number: Room number
            - level: Level name
            - area: Room area
            - perimeter: Room perimeter
        """
        kwargs: dict = {}
        if level_name:
            kwargs["level_name"] = level_name
        result = await self.call("get_rooms", **kwargs)
        return result if isinstance(result, list) else []

    async def get_doors(self, level_name: str | None = None) -> list[dict[str, Any]]:
        """
        Get all doors in the model.

        Args:
            level_name: Optional filter by level name

        Returns:
            List of door dictionaries
        """
        kwargs: dict = {}
        if level_name:
            kwargs["level_name"] = level_name
        result = await self.call("get_doors", **kwargs)
        return result if isinstance(result, list) else []

    async def get_windows(self, level_name: str | None = None) -> list[dict[str, Any]]:
        """
        Get all windows in the model.

        Args:
            level_name: Optional filter by level name

        Returns:
            List of window dictionaries
        """
        kwargs: dict = {}
        if level_name:
            kwargs["level_name"] = level_name
        result = await self.call("get_windows", **kwargs)
        return result if isinstance(result, list) else []

    async def get_levels(self) -> list[dict[str, Any]]:
        """
        Get all levels in the model.

        Returns:
            List of level dictionaries with:
            - id: Element ID
            - name: Level name
            - elevation: Level elevation
        """
        result = await self.call("get_levels")
        return result if isinstance(result, list) else []

    async def get_element_by_id(self, element_id: int) -> dict[str, Any]:
        """
        Get element information by ID.

        Args:
            element_id: Revit element ID

        Returns:
            Element dictionary
        """
        return await self.call("get_element_by_id", element_id=element_id)

    # ========================================================================
    # Element Creation
    # ========================================================================

    async def create_wall(
        self,
        start_point: tuple[float, float, float],
        end_point: tuple[float, float, float],
        level_name: str,
        wall_type: str | None = None,
        height: float | None = None,
    ) -> dict[str, Any]:
        """
        Create a wall.

        Args:
            start_point: (x, y, z) coordinates for start
            end_point: (x, y, z) coordinates for end
            level_name: Level to place wall on
            wall_type: Optional wall type name
            height: Optional wall height (defaults to level height)

        Returns:
            Created wall info with element ID
        """
        kwargs: dict[str, Any] = {
            "start_point": list(start_point),
            "end_point": list(end_point),
            "level_name": level_name,
        }
        if wall_type:
            kwargs["wall_type"] = wall_type
        if height is not None:
            kwargs["height"] = height

        return await self.call("create_wall", **kwargs)

    async def create_room(
        self,
        point: tuple[float, float, float],
        level_name: str,
        name: str | None = None,
        number: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a room at a point.

        Args:
            point: (x, y, z) coordinates
            level_name: Level name
            name: Optional room name
            number: Optional room number

        Returns:
            Created room info
        """
        kwargs: dict[str, Any] = {
            "point": list(point),
            "level_name": level_name,
        }
        if name:
            kwargs["name"] = name
        if number:
            kwargs["number"] = number

        return await self.call("create_room", **kwargs)

    async def place_door(
        self,
        wall_id: int,
        point: tuple[float, float, float],
        door_type: str | None = None,
    ) -> dict[str, Any]:
        """
        Place a door in a wall.

        Args:
            wall_id: Host wall element ID
            point: (x, y, z) placement coordinates
            door_type: Optional door type name

        Returns:
            Placed door info
        """
        kwargs: dict[str, Any] = {
            "wall_id": wall_id,
            "point": list(point),
        }
        if door_type:
            kwargs["door_type"] = door_type

        return await self.call("place_door", **kwargs)

    # ========================================================================
    # Element Modification
    # ========================================================================

    async def delete_element(self, element_id: int) -> dict[str, Any]:
        """
        Delete an element by ID.

        Args:
            element_id: Element ID to delete

        Returns:
            Delete result
        """
        return await self.call("delete_element", element_id=element_id)

    async def move_element(
        self,
        element_id: int,
        translation: tuple[float, float, float],
    ) -> dict[str, Any]:
        """
        Move an element.

        Args:
            element_id: Element ID to move
            translation: (x, y, z) translation vector

        Returns:
            Move result
        """
        return await self.call(
            "move_element",
            element_id=element_id,
            translation=list(translation),
        )

    async def set_parameter(
        self,
        element_id: int,
        parameter_name: str,
        value: Any,
    ) -> dict[str, Any]:
        """
        Set an element parameter value.

        Args:
            element_id: Element ID
            parameter_name: Parameter name
            value: New value

        Returns:
            Set result
        """
        return await self.call(
            "set_parameter",
            element_id=element_id,
            parameter_name=parameter_name,
            value=value,
        )

    async def get_parameter(
        self,
        element_id: int,
        parameter_name: str,
    ) -> Any:
        """
        Get an element parameter value.

        Args:
            element_id: Element ID
            parameter_name: Parameter name

        Returns:
            Parameter value
        """
        return await self.call(
            "get_parameter",
            element_id=element_id,
            parameter_name=parameter_name,
        )

    # ========================================================================
    # Transactions
    # ========================================================================

    async def start_transaction(self, name: str = "SDK Transaction") -> dict[str, Any]:
        """
        Start a transaction for model modifications.

        Args:
            name: Transaction name

        Returns:
            Transaction start result
        """
        return await self.call("start_transaction", name=name)

    async def commit_transaction(self) -> dict[str, Any]:
        """
        Commit the current transaction.

        Returns:
            Commit result
        """
        return await self.call("commit_transaction")

    async def rollback_transaction(self) -> dict[str, Any]:
        """
        Rollback the current transaction.

        Returns:
            Rollback result
        """
        return await self.call("rollback_transaction")

    # ========================================================================
    # Sheets & Views
    # ========================================================================

    async def list_sheets(self) -> list[dict[str, Any]]:
        """
        List all sheets in the document.

        Returns:
            List of sheet dictionaries
        """
        result = await self.call("list_sheets")
        return result if isinstance(result, list) else []

    async def create_sheet(
        self,
        number: str,
        name: str,
        titleblock_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new sheet.

        Args:
            number: Sheet number
            name: Sheet name
            titleblock_name: Optional titleblock family name

        Returns:
            Created sheet info
        """
        kwargs: dict[str, Any] = {
            "number": number,
            "name": name,
        }
        if titleblock_name:
            kwargs["titleblock_name"] = titleblock_name

        return await self.call("create_sheet", **kwargs)

    async def place_view_on_sheet(
        self,
        sheet_id: int,
        view_id: int,
        point: tuple[float, float] | None = None,
    ) -> dict[str, Any]:
        """
        Place a view on a sheet.

        Args:
            sheet_id: Sheet element ID
            view_id: View element ID
            point: Optional placement point (x, y)

        Returns:
            Placement result
        """
        kwargs: dict[str, Any] = {
            "sheet_id": sheet_id,
            "view_id": view_id,
        }
        if point:
            kwargs["point"] = list(point)

        return await self.call("place_view_on_sheet", **kwargs)

    # ========================================================================
    # Export
    # ========================================================================

    async def export_to_pdf(
        self,
        output_path: str,
        sheet_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """
        Export sheets to PDF.

        Args:
            output_path: Output PDF file path
            sheet_ids: Optional list of sheet IDs (defaults to all)

        Returns:
            Export result
        """
        kwargs: dict[str, Any] = {"output_path": output_path}
        if sheet_ids:
            kwargs["sheet_ids"] = sheet_ids

        return await self.call("export_to_pdf", **kwargs)

    async def export_to_dwg(
        self,
        output_folder: str,
        view_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """
        Export views to DWG.

        Args:
            output_folder: Output folder path
            view_ids: Optional list of view IDs

        Returns:
            Export result
        """
        kwargs: dict[str, Any] = {"output_folder": output_folder}
        if view_ids:
            kwargs["view_ids"] = view_ids

        return await self.call("export_to_dwg", **kwargs)
