"""
Service Layer Module

This module provides service classes that encapsulate business logic
and ensure transactional safety for CRUD operations.

Services:
- RequestService: Operations for Request entities
- DeputyService: Operations for Deputy entities  
- DistrictService: Operations for District entities
- UserService: Operations for User entities
- RequestStatusService: Operations for RequestStatus entities
- CategoryService: Operations for RequestCategory entities

Each service method wraps database operations in explicit transactions
using session.begin() for automatic commit/rollback behavior.
"""

from app.services.request_service import RequestService
from app.services.deputy_service import DeputyService
from app.services.district_service import DistrictService
from app.services.user_service import UserService
from app.services.request_status_service import RequestStatusService
from app.services.category_service import CategoryService

__all__ = [
    "RequestService",
    "DeputyService",
    "DistrictService",
    "UserService",
    "RequestStatusService",
    "CategoryService"
]