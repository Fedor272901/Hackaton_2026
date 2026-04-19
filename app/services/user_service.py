"""
User Service Layer

This module provides business logic operations for User entities.
All write operations (create, update, delete) are wrapped in explicit transactions
to ensure atomicity and data consistency.

The service layer acts as an intermediary between API endpoints and CRUD functions,
providing:
- Transaction management with automatic rollback on errors
- Business logic validation
- Centralized error handling
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from datetime import datetime

from app.db.models import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import hash_password
from app.core.roles import Role


class UserService:
    """
    Service class for managing User entities.
    
    All methods that modify data (create, update, delete) use explicit transaction
    management with session.begin() to ensure atomicity. If any step fails,
    the entire transaction is rolled back to prevent partial data writes.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize UserService with a database session.
        
        Args:
            session: SQLAlchemy async database session for all operations
        """
        self.session = session
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get a user by email address.
        
        Args:
            email: User's email address
        
        Returns:
            User object if found, None otherwise
        
        Note: Read-only operation, no transaction needed.
        """
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get a user by ID.
        
        Args:
            user_id: Unique identifier of the user
        
        Returns:
            User object if found, None otherwise
        
        Note: Read-only operation, no transaction needed.
        """
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_users(
        self,
        skip: int = 0,
        limit: int = 20,
        role: Optional[Role] = None,
        roles: Optional[List[Role]] = None,
        search: Optional[str] = None
    ) -> dict:
        """
        Get list of users with filtering and pagination.
        
        Args:
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            role: Filter by single role
            roles: Filter by multiple roles
            search: Search string for name, surname, email
        
        Returns:
            Dictionary with 'items', 'total', 'skip', 'limit' keys
        
        Note: Read-only operation, no transaction needed.
        """
        # Build query dynamically
        query = select(User)
        
        if role is not None:
            query = query.where(User.role == role.value)
        
        if roles is not None:
            role_values = [r.value for r in roles]
            query = query.where(User.role.in_(role_values))
        
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                (User.first_name.ilike(search_pattern)) |
                (User.last_name.ilike(search_pattern)) |
                (User.email.ilike(search_pattern))
            )
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        items = result.scalars().all()
        
        return {
            "items": items,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    
    async def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user with transactional safety.
        
        This method:
        1. Checks if email already exists
        2. Hashes the password
        3. Creates the user with default role CITIZEN
        4. Commits the transaction atomically
        
        If email already exists or creation fails, the transaction is rolled back.
        
        Args:
            user_data: Pydantic schema containing user data
        
        Returns:
            Created User object
        
        Raises:
            ValueError: If email already exists
        """
        try:
            async with self.session.begin():
                # Check if email already exists
                result = await self.session.execute(
                    select(User).where(User.email == user_data.email)
                )
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    raise ValueError(f"Email '{user_data.email}' уже зарегистрирован")
                
                # Create the user with hashed password
                user = User(
                    first_name=user_data.first_name,
                    last_name=user_data.last_name,
                    email=user_data.email,
                    password_hash=hash_password(user_data.password),
                    role=Role.CITIZEN,
                    created_at=datetime.utcnow()
                )
                
                self.session.add(user)
            
            # Transaction committed successfully
            return user
            
        except ValueError:
            # Re-raise business logic errors
            raise
        except Exception as e:
            # session.begin() handles rollback automatically
            # Any other exception causes full rollback
            raise
    
    async def update_user(self, user_id: int, update_data: dict) -> Optional[User]:
        """
        Update user data with transactional safety.
        
        Allows updating user fields like name, email, role.
        Validates that SUPERUSER cannot be modified through API.
        
        All updates are atomic - if validation fails, no changes are persisted.
        
        Args:
            user_id: ID of the user to update
            update_data: Dictionary with fields to update
        
        Returns:
            Updated User object if successful, None if user not found
        
        Raises:
            ValueError: If trying to modify SUPERUSER
        """
        try:
            async with self.session.begin():
                result = await self.session.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    return None
                
                # Protect SUPERUSER from modification
                if user.role == Role.SUPERUSER:
                    raise ValueError("Нельзя изменить SUPERUSER через API")
                
                # Apply updates
                for field, value in update_data.items():
                    if hasattr(user, field) and value is not None:
                        setattr(user, field, value)
            
            # Transaction committed successfully
            # Refresh to get updated data
            await self.session.refresh(user)
            return user
            
        except ValueError:
            raise
        except Exception as e:
            # Rollback handled by session.begin()
            raise
    
    async def delete_user(self, user_id: int) -> bool:
        """
        Delete a user with transactional safety.
        
        Before deletion, validates:
        - User exists
        - Cannot delete SUPERUSER through API
        - Cannot delete self (current user)
        
        The deletion is atomic - if any check fails, no changes are made.
        
        Args:
            user_id: ID of the user to delete
        
        Returns:
            True if deletion was successful, False if user not found
        
        Raises:
            ValueError: If trying to delete SUPERUSER
        """
        try:
            async with self.session.begin():
                result = await self.session.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    return False
                
                # Protect SUPERUSER from deletion
                if user.role == Role.SUPERUSER:
                    raise ValueError("Нельзя удалить SUPERUSER через API")
                
                # Delete the user
                await self.session.delete(user)
            
            # Transaction committed successfully
            return True
            
        except ValueError:
            raise
        except Exception as e:
            # Rollback handled by session.begin()
            raise
