"""
Request Status Service Layer

This module provides business logic operations for RequestStatus entities.
All write operations (create, update, delete) are wrapped in explicit transactions
to ensure atomicity and data consistency.

The service layer acts as an intermediary between API endpoints and CRUD functions,
providing:
- Transaction management with automatic rollback on errors
- Business logic validation
- Centralized error handling
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional

from app.db.models import RequestStatus
from app.schemas.request_status import StatusCreate, StatusUpdate


class RequestStatusService:
    """
    Service class for managing RequestStatus entities.
    
    All methods that modify data (create, update, delete) use explicit transaction
    management with session.begin() to ensure atomicity. If any step fails,
    the entire transaction is rolled back to prevent partial data writes.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize RequestStatusService with a database session.
        
        Args:
            session: SQLAlchemy AsyncSession database session for all operations
        """
        self.session = session
    
    async def get_status(self, status_id: int) -> Optional[RequestStatus]:
        """
        Get a status by ID.
        
        Args:
            status_id: Unique identifier of the status
        
        Returns:
            RequestStatus object if found, None otherwise
        
        Note: Read-only operation, no transaction needed.
        """
        result = await self.session.execute(
            select(RequestStatus).where(RequestStatus.id == status_id)
        )
        return result.scalar_one_or_none()
    
    async def get_status_by_code(self, code: str) -> Optional[RequestStatus]:
        """
        Get a status by its code.
        
        Args:
            code: Unique code of the status
        
        Returns:
            RequestStatus object if found, None otherwise
        
        Note: Read-only operation, no transaction needed.
        """
        result = await self.session.execute(
            select(RequestStatus).where(RequestStatus.code == code)
        )
        return result.scalar_one_or_none()
    
    async def get_statuses(self) -> List[RequestStatus]:
        """
        Get all statuses ordered by ID.
        
        Returns:
            List of RequestStatus objects
        
        Note: Read-only operation, no transaction needed.
        """
        result = await self.session.execute(
            select(RequestStatus).order_by(RequestStatus.id)
        )
        return list(result.scalars().all())
    
    async def create_status(self, status_data: StatusCreate) -> RequestStatus:
        """
        Create a new status with transactional safety.
        
        This method:
        1. Checks if status code already exists
        2. Creates the status
        3. Commits the transaction atomically
        
        If code already exists or creation fails, the transaction is rolled back.
        
        Args:
            status_data: Pydantic schema containing status data
        
        Returns:
            Created RequestStatus object
        
        Raises:
            ValueError: If status code already exists
        """
        try:
            async with self.session.begin():
                # Check if code already exists
                result = await self.session.execute(
                    select(RequestStatus).where(RequestStatus.code == status_data.code)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    raise ValueError(f"Статус с кодом '{status_data.code}' уже существует")
                
                # Create the status
                status = RequestStatus(
                    code=status_data.code,
                    name=status_data.name,
                )
                
                self.session.add(status)
            
            # Transaction committed successfully
            return status
            
        except ValueError:
            # Re-raise business logic errors
            raise
        except Exception as e:
            # session.begin() handles rollback automatically
            raise
    
    async def update_status(self, status_id: int, status_data: StatusUpdate) -> Optional[RequestStatus]:
        """
        Update status data with transactional safety.
        
        Allows updating status code and name.
        Validates uniqueness of code if changed.
        
        All updates are atomic - if validation fails, no changes are persisted.
        
        Args:
            status_id: ID of the status to update
            status_data: Pydantic schema with update data (partial update)
        
        Returns:
            Updated RequestStatus object if successful, None if status not found
        
        Raises:
            ValueError: If new code already exists
        """
        try:
            async with self.session.begin():
                result = await self.session.execute(
                    select(RequestStatus).where(RequestStatus.id == status_id)
                )
                status = result.scalar_one_or_none()
                
                if not status:
                    return None
                
                # Get only explicitly set fields
                update_data = status_data.dict(exclude_unset=True)
                
                # Validate new code if changing
                if "code" in update_data and update_data["code"] != status.code:
                    result = await self.session.execute(
                        select(RequestStatus).where(RequestStatus.code == update_data["code"])
                    )
                    existing = result.scalar_one_or_none()
                    
                    if existing:
                        raise ValueError(f"Статус с кодом '{update_data['code']}' уже существует")
                
                # Apply updates
                for field, value in update_data.items():
                    if hasattr(status, field):
                        setattr(status, field, value)
            
            # Transaction committed successfully
            self.session.refresh(status)
            return status
            
        except ValueError:
            raise
        except Exception as e:
            # Rollback handled by session.begin()
            raise
    
    async def delete_status(self, status_id: int) -> bool:
        """
        Delete a status with transactional safety.
        
        Before deletion, ensures:
        - Status exists
        
        The deletion is atomic - if any check fails, no changes are made.
        
        Args:
            status_id: ID of the status to delete
        
        Returns:
            True if deletion was successful, False if status not found
        """
        try:
            async with self.session.begin():
                result = await self.session.execute(
                    select(RequestStatus).where(RequestStatus.id == status_id)
                )
                status = result.scalar_one_or_none()
                
                if not status:
                    return False
                
                # Delete the status
                await self.session.execute(
                    delete(RequestStatus).where(RequestStatus.id == status_id)
                )
            
            # Transaction committed successfully
            return True
            
        except Exception as e:
            # Rollback handled by session.begin()
            raise
