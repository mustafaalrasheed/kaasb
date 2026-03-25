"""
Kaasb Platform - Base Service
Common patterns shared across all services.
"""

import math
from typing import Any, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseService:
    """Base class for all services — provides DB session and shared utilities."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def paginated_response(
        *,
        items: list[Any],
        total: int,
        page: int,
        page_size: int,
        key: str = "items",
    ) -> dict[str, Any]:
        """Build a standardized pagination response dict.

        Args:
            items: The list of results for the current page.
            total: Total number of matching records.
            page: Current page number (1-based).
            page_size: Number of items per page.
            key: The dict key name for the items list (e.g., "jobs", "users").

        Returns:
            Dict with items, total, page, page_size, total_pages.
        """
        return {
            key: items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, math.ceil(total / page_size)) if page_size > 0 else 1,
        }

    @staticmethod
    def clamp_page_size(page_size: int, maximum: int = 100) -> int:
        """Clamp page_size to a safe maximum."""
        return min(max(page_size, 1), maximum)
