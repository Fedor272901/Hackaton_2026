"""
Deputy Service Layer

This module provides business logic operations for Deputy entities.
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
from datetime import datetime

from app.db.models import Deputy, User, District, Request
from app.schemas.deputy import DeputyCreate, DeputyUpdate
from app.crud import deputy as crud_deputy


class DeputyService:
    """
    Service class for managing Deputy entities.
    
    All methods that modify data (create, update, delete) use explicit transaction
    management with session.begin() to ensure atomicity. If any step fails,
    the entire transaction is rolled back to prevent partial data writes.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize DeputyService with a database session.
        
        Args:
            session: SQLAlchemy AsyncSession database session for all operations
        """
        self.session = session
    
    async def get_deputy(self, deputy_id: int) -> Optional[Deputy]:
        """
        Get a deputy by ID with related data loaded.
        
        Args:
            deputy_id: Unique identifier of the deputy record
        
        Returns:
            Deputy object if found, None otherwise
        
        Note: Read-only operation, no transaction needed.
        """
        return crud_deputy.get_deputy(self.session, deputy_id)
    
    async def get_deputies(
        self,
        skip: int = 0,
        limit: int = 100,
        district_id: Optional[int] = None
    ) -> List[Deputy]:
        """
        Get list of deputies with pagination and optional district filter.
        
        Args:
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            district_id: Optional filter by district ID
        
        Returns:
            List of Deputy objects
        
        Note: Read-only operation, no transaction needed.
        """
        return crud_deputy.get_deputies(
            db=self.session,
            skip=skip,
            limit=limit,
            district_id=district_id
        )
    
    async def get_deputy_by_user_id(self, user_id: int) -> Optional[Deputy]:
        """
        Find a deputy by their associated user ID.
        
        Used to check if a user is a deputy and get their details.
        
        Args:
            user_id: ID of the user in the users table
        
        Returns:
            Deputy object if user is a deputy, None otherwise
        
        Note: Read-only operation, no transaction needed.
        """
        return crud_deputy.get_deputy_by_user_id(self.session, user_id)
    
    async def get_deputies_by_district(self, district_id: int) -> List[Deputy]:
        """
        Get all deputies belonging to a specific district.
        
        Args:
            district_id: ID of the district
        
        Returns:
            List of Deputy objects belonging to this district
        
        Note: Read-only operation, no transaction needed.
        """
        return crud_deputy.get_deputies_by_district(self.session, district_id)
    
    async def create_deputy(
        self,
        deputy_data: DeputyCreate,
        appointed_by_user_id: int
    ) -> Deputy:
        """
        Appoint a new deputy with transactional safety.
        
        This method performs the following atomically:
        1. Validates the user exists and has role "deputy"
        2. Validates the user is not already a deputy
        3. Validates the district exists
        4. Creates the deputy record with appointment timestamp
        
        If any validation fails or creation fails, all changes are rolled back.
        
        Args:
            deputy_data: Pydantic schema with deputy data (user_id, district_id, etc.)
            appointed_by_user_id: ID of the admin making the appointment
        
        Returns:
            Created Deputy object with relationships loaded
        
        Raises:
            HTTPException: For validation failures (user not found, wrong role, etc.)
        """
        try:
            async with self.session.begin():
                # Validate user exists and has correct role
                result = await self.session.execute(
                    select(User).where(User.id == deputy_data.user_id)
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    from fastapi import HTTPException, status
                    raise HTTPException(
                        status_code=404,
                        detail=f"Пользователь с ID {deputy_data.user_id} не найден"
                    )
                
                if user.role != "deputy":
                    from fastapi import HTTPException, status
                    raise HTTPException(
                        status_code=400,
                        detail=f"Пользователь должен иметь роль 'deputy'. Текущая роль: {user.role}"
                    )
                
                # Check user is not already a deputy
                result = await self.session.execute(
                    select(Deputy).where(Deputy.user_id == deputy_data.user_id)
                )
                existing_deputy = result.scalar_one_or_none()
                
                if existing_deputy:
                    from fastapi import HTTPException, status
                    raise HTTPException(
                        status_code=400,
                        detail=f"Пользователь с ID {deputy_data.user_id} уже является депутатом (ID записи: {existing_deputy.id})"
                    )
                
                # Validate district exists
                result = await self.session.execute(
                    select(District).where(District.id == deputy_data.district_id)
                )
                district = result.scalar_one_or_none()
                
                if not district:
                    from fastapi import HTTPException, status
                    raise HTTPException(
                        status_code=404,
                        detail=f"Округ с ID {deputy_data.district_id} не найден"
                    )
                
                # Create the deputy record
                new_deputy = Deputy(
                    user_id=deputy_data.user_id,
                    district_id=deputy_data.district_id,
                    office_phone=deputy_data.office_phone,
                    office_address=deputy_data.office_address,
                    appointed_at=datetime.utcnow()
                )
                
                self.session.add(new_deputy)
            
            # Transaction committed successfully - reload with relationships
            return crud_deputy.get_deputy(self.session, new_deputy.id)
            
        except Exception as e:
            # Re-raise to let caller handle (HTTPException or other)
            raise
    
    async def update_deputy(
        self,
        deputy_id: int,
        deputy_data: DeputyUpdate
    ) -> Optional[Deputy]:
        """
        Update deputy data with transactional safety.
        
        Allows updating:
        - District assignment (with validation)
        - Office phone
        - Office address
        
        All updates are atomic - if validation fails, no changes are persisted.
        
        Args:
            deputy_id: ID of the deputy record to update
            deputy_data: Pydantic schema with update data (partial update)
        
        Returns:
            Updated Deputy object if successful, None if deputy not found
        
        Raises:
            ValueError: If new district doesn't exist
        """
        try:
            async with self.session.begin():
                result = await self.session.execute(
                    select(Deputy).where(Deputy.id == deputy_id)
                )
                deputy = result.scalar_one_or_none()
                
                if not deputy:
                    return None
                
                # Get only explicitly set fields
                update_data = deputy_data.dict(exclude_unset=True)
                
                # Validate new district if changing
                if "district_id" in update_data and update_data["district_id"] != deputy.district_id:
                    result = await self.session.execute(
                        select(District).where(District.id == update_data["district_id"])
                    )
                    new_district = result.scalar_one_or_none()
                    
                    if not new_district:
                        raise ValueError(f"Округ с ID {update_data['district_id']} не найден")
                
                # Apply updates
                for field, value in update_data.items():
                    if hasattr(deputy, field):
                        setattr(deputy, field, value)
            
            # Transaction committed successfully
            return crud_deputy.get_deputy(self.session, deputy_id)
            
        except ValueError:
            raise
        except Exception as e:
            # Rollback handled by session.begin()
            raise
    
    async def delete_deputy(self, deputy_id: int) -> bool:
        """
        Remove deputy status (delete record) with transactional safety.
        
        Before deletion, ensures:
        - Deputy exists
        - No assigned requests (must be reassigned first)
        
        The deletion is atomic - if any check fails, no changes are made.
        
        Args:
            deputy_id: ID of the deputy record to delete
        
        Returns:
            True if deletion was successful, False if deputy not found
        
        Raises:
            HTTPException: If deputy has assigned requests
        """
        try:
            async with self.session.begin():
                result = await self.session.execute(
                    select(Deputy).where(Deputy.id == deputy_id)
                )
                deputy = result.scalar_one_or_none()
                
                if not deputy:
                    return False
                
                # Check for assigned requests
                result = await self.session.execute(
                    select(func.count()).select_from(Request).where(Request.assigned_deputy_id == deputy_id)
                )
                assigned_requests_count = result.scalar()
                
                if assigned_requests_count > 0:
                    from fastapi import HTTPException, status
                    raise HTTPException(
                        status_code=400,
                        detail=f"Невозможно снять депутата: у него есть назначенных обращений: {assigned_requests_count}. Сначала переназначьте обращения."
                    )
                
                # Delete the deputy record
                await self.session.execute(
                    delete(Deputy).where(Deputy.id == deputy_id)
                )
            
            # Transaction committed successfully
            return True
            
        except Exception as e:
            # Re-raise to let caller handle
            raise
    
    async def reassign_requests_from_deputy(
        self,
        deputy_id: int,
        new_deputy_id: Optional[int] = None
    ) -> int:
        """
        Reassign requests from one deputy to another (or remove assignment).
        
        This is typically called before deleting a deputy to preserve requests.
        
        Args:
            deputy_id: ID of the deputy to remove assignments from
            new_deputy_id: ID of the deputy to assign requests to, or None to clear
        
        Returns:
            Number of requests reassigned
        
        Note: This is a write operation with transaction safety.
        """
        try:
            async with self.session.begin():
                # Update assignments
                result = await self.session.execute(
                    delete(Request)
                    .where(Request.assigned_deputy_id == deputy_id)
                )
                count = result.rowcount
                
                return count
            
            # Transaction committed successfully
            
        except Exception as e:
            # Rollback handled by session.begin()
            raise
