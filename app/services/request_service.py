"""
Request Service Layer

This module provides business logic operations for Request entities.
All write operations (create, update, delete) are wrapped in explicit transactions
to ensure atomicity and data consistency.

The service layer acts as an intermediary between API endpoints and CRUD functions,
providing:
- Transaction management with automatic rollback on errors
- Business logic validation
- Centralized error handling
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from typing import Optional, List
from datetime import datetime

from app.db.models import Request, RequestStatus, RequestCategory, RequestPhoto, StatusHistory, Message, User, District, Deputy
from app.schemas.requests import RequestCreate, RequestUpdate
from app.crud import request as request_crud


class RequestService:
    """
    Service class for managing Request entities.
    
    All methods that modify data (create, update, delete) use explicit transaction
    management with session.begin() to ensure atomicity. If any step fails,
    the entire transaction is rolled back to prevent partial data writes.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize RequestService with a database session.
        
        Args:
            session: SQLAlchemy AsyncSession database session for all operations
        """
        self.session = session
    
    async def get_request_statuses(self) -> List[RequestStatus]:
        """
        Get all possible request statuses.
        
        Returns:
            List of RequestStatus objects
        
        Note: This is a read-only operation, no transaction needed.
        """
        result = await self.session.execute(select(RequestStatus))
        return list(result.scalars().all())
    
    async def get_request_categories(self) -> List[RequestCategory]:
        """
        Get all request categories.
        
        Returns:
            List of RequestCategory objects
        
        Note: This is a read-only operation, no transaction needed.
        """
        result = await self.session.execute(select(RequestCategory))
        return list(result.scalars().all())
    
    async def get_request_by_id(self, request_id: int) -> Optional[Request]:
        """
        Get a single request by ID with all related data loaded.
        
        Args:
            request_id: Unique identifier of the request
        
        Returns:
            Request object if found, None otherwise
        
        Note: This is a read-only operation, no transaction needed.
        """
        return request_crud.get_request_by_id(self.session, request_id)
    
    async def get_requests(
        self,
        skip: int = 0,
        limit: int = 20,
        user_id: Optional[int] = None,
        district_id: Optional[int] = None,
        category_id: Optional[int] = None,
        status_id: Optional[int] = None,
        assigned_deputy_id: Optional[int] = None,
        include_closed: bool = True
    ) -> dict:
        """
        Get list of requests with filtering and pagination.
        
        Args:
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            user_id: Filter by author user ID
            district_id: Filter by district ID
            category_id: Filter by category ID
            status_id: Filter by status ID
            assigned_deputy_id: Filter by assigned deputy ID
            include_closed: Whether to include closed requests
        
        Returns:
            Dictionary with 'items', 'total', 'skip', 'limit' keys
        
        Note: This is a read-only operation, no transaction needed.
        """
        return request_crud.get_requests(
            db=self.session,
            skip=skip,
            limit=limit,
            user_id=user_id,
            district_id=district_id,
            category_id=category_id,
            status_id=status_id,
            assigned_deputy_id=assigned_deputy_id,
            include_closed=include_closed
        )
    
    async def create_request(self, request_data: RequestCreate, user_id: int) -> Request:
        """
        Create a new request with full transactional safety.
        
        This method performs multiple database operations atomically:
        1. Validates that district and category exist (data integrity)
        2. Gets or creates the default "new" status
        3. Creates the request record
        4. Adds associated photos if provided
        5. Records status change history
        6. Creates a system message about request creation
        
        If any step fails, all changes are rolled back to prevent orphaned records.
        
        Args:
            request_data: Pydantic schema containing request data
            user_id: ID of the user creating the request
        
        Returns:
            Created Request object with all relationships loaded
        
        Raises:
            ValueError: If district or category does not exist
            Exception: Re-raises any exception after rollback
        
        Transaction behavior:
            Uses session.begin() for automatic commit/rollback.
            All operations are atomic - either all succeed or none are persisted.
        """
        try:
            # Start explicit transaction block
            # All operations within this block will be committed together or rolled back
            async with self.session.begin():
                # Data integrity: ensuring foreign key references exist before commit
                # Проверяем существование района перед созданием обращения
                result = await self.session.execute(
                    select(District).where(District.id == request_data.district_id)
                )
                district = result.scalar_one_or_none()
                if not district:
                    raise ValueError(f"Район с ID {request_data.district_id} не найден")
                
                # Data integrity: ensuring foreign key references exist before commit
                # Проверяем существование категории перед созданием обращения
                result = await self.session.execute(
                    select(RequestCategory).where(RequestCategory.id == request_data.category_id)
                )
                category = result.scalar_one_or_none()
                if not category:
                    raise ValueError(f"Категория с ID {request_data.category_id} не найдена")
                
                # Get or create default "new" status
                result = await self.session.execute(
                    select(RequestStatus).where(RequestStatus.code == "new")
                )
                default_status = result.scalar_one_or_none()
                
                if not default_status:
                    default_status = RequestStatus(code="new", name="Новое")
                    self.session.add(default_status)
                    await self.session.flush()  # Flush to get the ID without committing
                
                # Create the request
                request = Request(
                    user_id=user_id,
                    district_id=request_data.district_id,
                    category_id=request_data.category_id,
                    status_id=default_status.id,
                    title=request_data.title,
                    description=request_data.description,
                    address=request_data.address,
                    latitude=request_data.latitude,
                    longitude=request_data.longitude,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                self.session.add(request)
                await self.session.flush()  # Get the generated ID
                
                # Add photos if provided
                if request_data.photo_urls:
                    for photo_url in request_data.photo_urls:
                        photo = RequestPhoto(
                            request_id=request.id,
                            file_url=photo_url,
                            created_at=datetime.utcnow()
                        )
                        self.session.add(photo)
                
                # Record status change history
                status_history = StatusHistory(
                    request_id=request.id,
                    new_status_id=default_status.id,
                    changed_by_user_id=user_id,
                    created_at=datetime.utcnow()
                )
                self.session.add(status_history)
                
                # Create system message about request creation
                system_message = Message(
                    request_id=request.id,
                    user_id=user_id,
                    text="Обращение создано",
                    is_system=True,
                    created_at=datetime.utcnow()
                )
                self.session.add(system_message)
            
            # Transaction committed successfully - now fetch the complete request
            # The session.begin() context manager handles commit automatically
            # If any exception occurred above, rollback happens automatically
            return request_crud.get_request_by_id(self.session, request.id)
            
        except ValueError:
            # Re-raise ValueError as-is (business logic error)
            raise
        except Exception as e:
            # session.begin() handles rollback automatically on exception
            # Re-raise to let the caller handle the error
            raise
    
    async def update_request(
        self,
        request_id: int,
        request_update: RequestUpdate,
        changed_by_user_id: int
    ) -> Optional[Request]:
        """
        Update a request with transactional safety.
        
        This method handles:
        - Validates that district/category exist if being updated (data integrity)
        - General field updates
        - Status changes with history tracking
        - System message creation for status changes
        - Setting closed_at timestamp when status becomes "closed"
        
        All operations are atomic - if any step fails, no changes are persisted.
        
        Args:
            request_id: ID of the request to update
            request_update: Pydantic schema with update data
            changed_by_user_id: ID of the user making the change
        
        Returns:
            Updated Request object if successful, None if request not found
        
        Raises:
            ValueError: If new status/district/category ID is invalid
        
        Transaction behavior:
            Uses session.begin() for automatic commit/rollback.
            On error, session.rollback() protects request, status_history, and message
            tables from partial writes (all or nothing).
        """
        try:
            async with self.session.begin():
                result = await self.session.execute(
                    select(Request).where(Request.id == request_id)
                )
                request = result.scalar_one_or_none()
                
                if not request:
                    return None
                
                old_status_id = request.status_id
                
                # Get only fields that were explicitly set in the request
                update_data = request_update.dict(exclude_unset=True)
                
                # Data integrity: ensuring foreign key references exist before commit
                # Проверяем существование нового района при смене district_id
                if "district_id" in update_data and update_data["district_id"] != request.district_id:
                    result = await self.session.execute(
                        select(District).where(District.id == update_data["district_id"])
                    )
                    new_district = result.scalar_one_or_none()
                    if not new_district:
                        raise ValueError(f"Район с ID {update_data['district_id']} не найден")
                
                # Data integrity: ensuring foreign key references exist before commit
                # Проверяем существование новой категории при смене category_id
                if "category_id" in update_data and update_data["category_id"] != request.category_id:
                    result = await self.session.execute(
                        select(RequestCategory).where(RequestCategory.id == update_data["category_id"])
                    )
                    new_category = result.scalar_one_or_none()
                    if not new_category:
                        raise ValueError(f"Категория с ID {update_data['category_id']} не найдена")
                
                # Special handling for status change
                if "status_id" in update_data and update_data["status_id"] != old_status_id:
                    # Verify new status exists
                    result = await self.session.execute(
                        select(RequestStatus).where(RequestStatus.id == update_data["status_id"])
                    )
                    new_status = result.scalar_one_or_none()
                    
                    if not new_status:
                        raise ValueError(f"Статус с ID {update_data['status_id']} не найден")
                    
                    # Set closed_at if status is changing to "closed"
                    if new_status.code == "closed":
                        request.closed_at = datetime.utcnow()
                    
                    # Record status change history
                    status_history = StatusHistory(
                        request_id=request_id,
                        old_status_id=old_status_id,
                        new_status_id=update_data["status_id"],
                        changed_by_user_id=changed_by_user_id,
                        created_at=datetime.utcnow()
                    )
                    self.session.add(status_history)
                    
                    # Create system message about status change
                    result = await self.session.execute(
                        select(RequestStatus).where(RequestStatus.id == old_status_id)
                    )
                    old_status = result.scalar_one_or_none()
                    
                    system_message = Message(
                        request_id=request_id,
                        user_id=changed_by_user_id,
                        text=f"Статус изменен с '{old_status.name}' на '{new_status.name}'",
                        is_system=True,
                        created_at=datetime.utcnow()
                    )
                    self.session.add(system_message)
                
                # Update other fields
                for field, value in update_data.items():
                    if hasattr(request, field):
                        setattr(request, field, value)
                
                request.updated_at = datetime.utcnow()
            
            # Transaction committed successfully
            return request_crud.get_request_by_id(self.session, request_id)
            
        except ValueError:
            # Re-raise ValueError as-is (business logic error)
            raise
        except Exception as e:
            # session.begin() handles rollback automatically
            # Any other exception causes full rollback
            raise
    
    async def assign_deputy(
        self,
        request_id: int,
        deputy_id: int,
        assigned_by_user_id: int
    ) -> Optional[Request]:
        """
        Assign a deputy to a request with transactional safety.
        
        This method:
        1. Validates that the request exists
        2. Validates that the deputy exists and belongs to the same district
        3. Updates the request's assigned_deputy_id
        4. Creates a system message about the assignment
        
        All operations are atomic to prevent assigning a deputy without logging it.
        
        Args:
            request_id: ID of the request
            deputy_id: ID of the deputy to assign
            assigned_by_user_id: ID of the user making the assignment (admin)
        
        Returns:
            Updated Request object if successful, None if request not found
        
        Raises:
            ValueError: If deputy doesn't exist or doesn't belong to the same district
        """
        try:
            async with self.session.begin():
                result = await self.session.execute(
                    select(Request).where(Request.id == request_id)
                )
                request = result.scalar_one_or_none()
                
                if not request:
                    return None
                
                # Verify deputy exists and belongs to the same district
                result = await self.session.execute(
                    select(Deputy).where(Deputy.id == deputy_id)
                )
                deputy = result.scalar_one_or_none()
                
                if not deputy:
                    raise ValueError(f"Депутат с ID {deputy_id} не найден")
                
                if deputy.district_id != request.district_id:
                    raise ValueError("Депутат не привязан к району этого обращения")
                
                # Update assignment
                request.assigned_deputy_id = deputy_id
                request.updated_at = datetime.utcnow()
                
                # Get deputy's user info for the message
                result = await self.session.execute(
                    select(User).where(User.id == deputy.user_id)
                )
                deputy_user = result.scalar_one_or_none()
                
                # Create system message about assignment
                message_text = f"Обращение назначено депутату {deputy_user.first_name} {deputy_user.last_name}"
                
                system_message = Message(
                    request_id=request_id,
                    user_id=assigned_by_user_id,
                    text=message_text,
                    is_system=True,
                    created_at=datetime.utcnow()
                )
                self.session.add(system_message)
            
            # Transaction committed successfully
            return request_crud.get_request_by_id(self.session, request_id)
            
        except ValueError:
            raise
        except Exception as e:
            # Rollback handled by session.begin()
            raise
    
    async def add_message_to_request(
        self,
        request_id: int,
        user_id: int,
        text: str,
        is_system: bool = False
    ) -> Optional[Message]:
        """
        Add a message to a request with transactional safety.
        
        This method:
        1. Verifies the request exists
        2. Creates the message
        3. Updates the request's updated_at timestamp
        
        Both operations are atomic to ensure messages are always associated
        with an updated request.
        
        Args:
            request_id: ID of the request
            user_id: ID of the user sending the message
            text: Message text content
            is_system: Whether this is a system-generated message
        
        Returns:
            Created Message object if successful, None if request not found
        """
        try:
            async with self.session.begin():
                result = await self.session.execute(
                    select(Request).where(Request.id == request_id)
                )
                request = result.scalar_one_or_none()
                
                if not request:
                    return None
                
                # Create the message
                message = Message(
                    request_id=request_id,
                    user_id=user_id,
                    text=text,
                    is_system=is_system,
                    created_at=datetime.utcnow()
                )
                
                self.session.add(message)
                await self.session.flush()  # Get the message ID
                
                # Update request's updated_at
                request.updated_at = datetime.utcnow()
            
            # Refresh message to get all data
            self.session.refresh(message)
            return message
            
        except Exception as e:
            # Rollback handled by session.begin()
            raise
    
    async def get_request_messages(
        self,
        request_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> dict:
        """
        Get messages for a request with pagination.
        
        Args:
            request_id: ID of the request
            skip: Number of messages to skip
            limit: Maximum number of messages to return
        
        Returns:
            Dictionary with 'items', 'total', 'skip', 'limit' keys
        
        Note: Read-only operation, no transaction needed.
        """
        return request_crud.get_request_messages(
            self.session, request_id, skip, limit
        )
    
    async def get_request_status_history(self, request_id: int) -> List[StatusHistory]:
        """
        Get status change history for a request.
        
        Args:
            request_id: ID of the request
        
        Returns:
            List of StatusHistory records ordered by date descending
        
        Note: Read-only operation, no transaction needed.
        """
        return request_crud.get_request_status_history(self.session, request_id)
    
    async def delete_request(self, request_id: int) -> bool:
        """
        Delete a request with full transactional safety.
        
        This method deletes all related data in the correct order:
        1. Messages
        2. Photos
        3. Status history
        4. The request itself
        
        All deletions are atomic - if any deletion fails, none are persisted.
        
        Args:
            request_id: ID of the request to delete
        
        Returns:
            True if deletion was successful, False if request not found
        """
        try:
            async with self.session.begin():
                result = await self.session.execute(
                    select(Request).where(Request.id == request_id)
                )
                request = result.scalar_one_or_none()
                
                if not request:
                    return False
                
                # Delete related data first (cascade might handle this, but being explicit)
                await self.session.execute(
                    delete(Message).where(Message.request_id == request_id)
                )
                
                await self.session.execute(
                    delete(RequestPhoto).where(RequestPhoto.request_id == request_id)
                )
                
                await self.session.execute(
                    delete(StatusHistory).where(StatusHistory.request_id == request_id)
                )
                
                # Finally delete the request itself
                await self.session.delete(request)
            
            # Transaction committed successfully
            return True
            
        except Exception as e:
            # Rollback handled by session.begin()
            raise
    
    async def get_statistics(self, district_id: Optional[int] = None) -> dict:
        """
        Get statistics about requests.
        
        Args:
            district_id: Optional filter by district ID
        
        Returns:
            Dictionary containing:
            - total_requests: Total count
            - by_status: Breakdown by status
            - by_category: Breakdown by category
            - average_resolution_days: Average time to close requests
        
        Note: Read-only operation, no transaction needed.
        """
        return request_crud.get_statistics(self.session, district_id)
    
    async def check_duplicate_request(
        self,
        user_id: int,
        text: str,
        hours: int = 24
    ) -> bool:
        """
        Check if user has submitted similar requests recently.
        
        Args:
            user_id: ID of the user
            text: Text to compare against existing requests
            hours: Time window in hours to check (default 24)
        
        Returns:
            True if duplicate found, False otherwise
        
        Note: Read-only operation, no transaction needed.
        """
        return request_crud.check_duplicate_request(
            self.session, user_id, text, hours
        )
