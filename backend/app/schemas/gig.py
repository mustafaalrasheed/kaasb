"""
Kaasb Platform - Deprecated shim for app.schemas.gig
Renamed to app.schemas.service (matches the Arabic UI's "خدمة" / khidma).
This module re-exports the new names under their old aliases so existing
imports continue to work until all call sites are updated.

TODO: Delete this file once all imports have been migrated to app.schemas.service.
"""

from app.schemas.service import (
    CategoryOut,
    CategoryWithSubsOut,
    DeliverBody,
    FreelancerBrief,
    OrderDeliveryOut,
    RequirementAnswer,
    RequirementQuestion,
    ServiceCreate,
    ServiceListItem,
    ServiceOrderCreate,
    ServiceOrderOut,
    ServiceOrderUpdate,
    ServiceOut,
    ServicePackageIn,
    ServicePackageOut,
    ServiceRequirementsSubmit,
    ServiceSearchParams,
    ServiceUpdate,
    SubcategoryOut,
)

# Legacy aliases — same schemas, old names.
GigCreate = ServiceCreate
GigUpdate = ServiceUpdate
GigOut = ServiceOut
GigListItem = ServiceListItem
GigPackageIn = ServicePackageIn
GigPackageOut = ServicePackageOut
GigOrderCreate = ServiceOrderCreate
GigOrderOut = ServiceOrderOut
GigOrderUpdate = ServiceOrderUpdate
GigRequirementsSubmit = ServiceRequirementsSubmit
GigSearchParams = ServiceSearchParams

__all__ = [
    "CategoryOut", "SubcategoryOut", "CategoryWithSubsOut",
    "FreelancerBrief", "RequirementQuestion", "RequirementAnswer",
    "DeliverBody", "OrderDeliveryOut",
    "GigCreate", "GigUpdate", "GigOut", "GigListItem",
    "GigPackageIn", "GigPackageOut",
    "GigOrderCreate", "GigOrderOut", "GigOrderUpdate",
    "GigRequirementsSubmit", "GigSearchParams",
    "ServiceCreate", "ServiceUpdate", "ServiceOut", "ServiceListItem",
    "ServicePackageIn", "ServicePackageOut",
    "ServiceOrderCreate", "ServiceOrderOut", "ServiceOrderUpdate",
    "ServiceRequirementsSubmit", "ServiceSearchParams",
]
