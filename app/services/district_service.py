"""
District Service Layer

This module provides business logic operations for District entities.
All write operations (create, update, delete) are wrapped in explicit transactions
to ensure atomicity and data consistency.

The service layer acts as an intermediary between API endpoints and CRUD functions,
providing:
- Transaction management with automatic rollback on errors
- Business logic validation
- Centralized error handling
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from typing import List, Optional

from app.db.models import District, Deputy, Request
from app.schemas.district import DistrictCreate, DistrictUpdate
from app.crud import district as crud_district


class DistrictService:
    """
    Service class for managing District entities.
    
    All methods that modify data (create, update, delete) use explicit transaction
    management with session.begin() to ensure atomicity. If any step fails,
    the entire transaction is rolled back to prevent partial data writes.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize DistrictService with a database session.
        
        Args:
            session: SQLAlchemy AsyncSession database session for all operations
        """
        self.session = session
    
    async def get_district(self, district_id: int) -> Optional[District]:
        """
        Get a district by ID.
        
        Args:
            district_id: Unique identifier of the district
        
        Returns:
            District object if found, None otherwise
        
        Note: Read-only operation, no transaction needed.
        """
        return crud_district.get_district(self.session, district_id)
    
    async def get_districts(self, skip: int = 0, limit: int = 100) -> List[District]:
        """
        Get list of districts with pagination.
        
        Args:
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
        
        Returns:
            List of District objects
        
        Note: Read-only operation, no transaction needed.
        """
        return crud_district.get_districts(self.session, skip=skip, limit=limit)
    
    async def get_district_with_deputies(self, district_id: int) -> Optional[District]:
        """
        Get a district with its deputies loaded.
        
        Uses joinedload to avoid N+1 query problem.
        
        Args:
            district_id: ID of the district
        
        Returns:
            District object with deputies relationship loaded, or None
        
        Note: Read-only operation, no transaction needed.
        """
        return crud_district.get_district_with_deputies(self.session, district_id)
    
    async def get_deputies_by_district(self, district_id: int) -> List[Deputy]:
        """
        Get list of deputies by district ID.
        
        Args:
            district_id: ID of the district
        
        Returns:
            List of Deputy objects
        
        Note: Read-only operation, no transaction needed.
        """
        return crud_district.get_deputies_by_district(self.session, district_id)
    
    async def create_district(self, district_data: DistrictCreate) -> District:
        """
        Create a new district with transactional safety.
        
        Validates that no district with the same name exists before creation.
        The entire operation is atomic - if validation fails, no changes are made.
        
        Args:
            district_data: Pydantic schema with district data (name, description)
        
        Returns:
            Created District object with assigned ID
        
        Raises:
            HTTPException: If district with same name already exists
        """
        try:
            async with self.session.begin():
                # Check for duplicate name
                result = await self.session.execute(
                    select(District).where(District.name == district_data.name)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    from fastapi import HTTPException, status
                    raise HTTPException(
                        status_code=400,
                        detail=f"Округ с названием '{district_data.name}' уже существует"
                    )
                
                # Create the district
                new_district = District(
                    name=district_data.name,
                    description=district_data.description
                )
                
                self.session.add(new_district)
            
            # Transaction committed successfully
            return new_district
            
        except Exception as e:
            # Re-raise to let caller handle
            raise
    
    async def update_district(
        self,
        district_id: int,
        district_data: DistrictUpdate
    ) -> Optional[District]:
        """
        Update district data with transactional safety.
        
        Allows updating name and description. Validates that new name is unique
        (not used by another district).
        
        All updates are atomic - if validation fails, no changes are persisted.
        
        Args:
            district_id: ID of the district to update
            district_data: Pydantic schema with update data (partial update)
        
        Returns:
            Updated District object if successful, None if district not found
        
        Raises:
            HTTPException: If new name is already taken by another district
        """
        try:
            async with self.session.begin():
                result = await self.session.execute(
                    select(District).where(District.id == district_id)
                )
                district = result.scalar_one_or_none()
                
                if not district:
                    return None
                
                # Get only explicitly set fields
                update_data = district_data.dict(exclude_unset=True)
                
                # Validate name uniqueness if changing
                if district_data.name is not None and district_data.name != district.name:
                    result = await self.session.execute(
                        select(District).where(
                            District.name == district_data.name,
                            District.id != district_id
                        )
                    )
                    duplicate = result.scalar_one_or_none()
                    
                    if duplicate:
                        from fastapi import HTTPException, status
                        raise HTTPException(
                            status_code=400,
                            detail=f"Округ с названием '{district_data.name}' уже существует"
                        )
                
                # Apply updates
                for field, value in update_data.items():
                    if hasattr(district, field):
                        setattr(district, field, value)
            
            # Transaction committed successfully
            return district
            
        except Exception as e:
            # Re-raise to let caller handle
            raise
    
    async def delete_district(self, district_id: int) -> bool:
        """
        Delete a district with transactional safety.
        
        Before deletion, validates:
        - District exists
        - No deputies assigned to this district
        - No requests in this district
        
        The deletion is atomic - if any check fails, no changes are made.
        
        Args:
            district_id: ID of the district to delete
        
        Returns:
            True if deletion was successful, False if district not found
        
        Raises:
            HTTPException: If district has deputies or requests
        """
        try:
            async with self.session.begin():
                result = await self.session.execute(
                    select(District).where(District.id == district_id)
                )
                district = result.scalar_one_or_none()
                
                if not district:
                    return False
                
                # Check for deputies in this district
                result = await self.session.execute(
                    select(func.count()).select_from(Deputy).where(Deputy.district_id == district_id)
                )
                deputies_count = result.scalar()
                
                if deputies_count > 0:
                    from fastapi import HTTPException, status
                    raise HTTPException(
                        status_code=400,
                        detail=f"Невозможно удалить округ: в нём числится депутатов: {deputies_count}. Сначала переназначьте депутатов."
                    )
                
                # Check for requests in this district
                result = await self.session.execute(
                    select(func.count()).select_from(Request).where(Request.district_id == district_id)
                )
                requests_count = result.scalar()
                
                if requests_count > 0:
                    from fastapi import HTTPException, status
                    raise HTTPException(
                        status_code=400,
                        detail=f"Невозможно удалить округ: в нём есть обращений: {requests_count}. Сначала архивируйте обращения."
                    )
                
                # Delete the district
                await self.session.execute(
                    delete(District).where(District.id == district_id)
                )
            
            # Transaction committed successfully
            return True
            
        except Exception as e:
            # Re-raise to let caller handle
            raise
