"""
Kaasb Platform - Deprecated shim for app.models.gig
Renamed to app.models.service (matches the Arabic UI's "خدمة" / khidma).
This module re-exports the new names under their old aliases so existing
imports continue to work until all call sites are updated.

TODO: Delete this file once all imports have been migrated to app.models.service.
"""

from app.models.service import (
    Service,
    ServiceCategory,
    ServiceOrder,
    ServiceOrderDelivery,
    ServiceOrderStatus,
    ServicePackage,
    ServicePackageTier,
    ServiceStatus,
    ServiceSubcategory,
)

# Legacy aliases — same classes, old names.
Gig = Service
GigOrder = ServiceOrder
GigPackage = ServicePackage
OrderDelivery = ServiceOrderDelivery
Category = ServiceCategory
Subcategory = ServiceSubcategory
GigStatus = ServiceStatus
GigOrderStatus = ServiceOrderStatus
GigPackageTier = ServicePackageTier

__all__ = [
    "Gig", "GigOrder", "GigPackage", "OrderDelivery",
    "Category", "Subcategory",
    "GigStatus", "GigOrderStatus", "GigPackageTier",
    "Service", "ServiceOrder", "ServicePackage", "ServiceOrderDelivery",
    "ServiceCategory", "ServiceSubcategory",
    "ServiceStatus", "ServiceOrderStatus", "ServicePackageTier",
]
