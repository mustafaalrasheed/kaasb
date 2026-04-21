"""
Kaasb Platform - Deprecated shim for app.services.gig_service
Renamed to app.services.catalog_service (matches the service/خدمة rename).

Exports ``GigService`` as an alias of ``CatalogService`` so any remaining
call sites keep working during the deprecation window. Delete this file
once all imports move to ``app.services.catalog_service``.
"""

from app.services.catalog_service import CatalogService

GigService = CatalogService

__all__ = ["GigService", "CatalogService"]
