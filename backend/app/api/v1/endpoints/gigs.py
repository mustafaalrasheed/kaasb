"""
Kaasb Platform - Deprecated /gigs router alias

All gig routes have been renamed to /services (matches the Arabic UI's
"خدمة" / khidma). This module re-exports the canonical service router;
api/v1/router.py mounts it at ``/gigs`` with ``deprecated=True`` so
existing clients continue to work for one release. Remove once all
clients have migrated.
"""

from app.api.v1.endpoints.services import router

__all__ = ["router"]
