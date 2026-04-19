"""
Category Service Layer

This module provides business logic operations for RequestCategory entities.
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

from app.db.models import RequestCategory
from app.schemas.category import CategoryCreate, CategoryUpdate


class CategoryService:
    """
    Service class for managing RequestCategory entities.
    
    All methods that modify data (create, update, delete) use explicit transaction
    management with session.begin() to ensure atomicity. If any step fails,
    the entire transaction is rolled back to prevent partial data writes.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize CategoryService with a database session.
        
        Args:
            session: SQLAlchemy AsyncSession database session for all operations
        """
        self.session = session
    
    async def get_category(self, category_id: int) -> Optional[RequestCategory]:
        """
        Get a category by ID.
        
        Args:
            category_id: Unique identifier of the category
        
        Returns:
            RequestCategory object if found, None otherwise
        
        Note: Read-only operation, no transaction needed.
        """
        result = await self.session.execute(
            select(RequestCategory).where(RequestCategory.id == category_id)
        )
        return result.scalar_one_or_none()
    
    async def get_categories(self) -> List[RequestCategory]:
        """
        Get all categories ordered by ID.
        
        Returns:
            List of RequestCategory objects
        
        Note: Read-only operation, no transaction needed.
        """
        result = await self.session.execute(
            select(RequestCategory).order_by(RequestCategory.id)
        )
        return list(result.scalars().all())
    
    async def create_category(self, category_data: CategoryCreate) -> RequestCategory:
        """
        Create a new category with transactional safety.
        
        This method:
        1. Creates the category
        2. Commits the transaction atomically
        
        If creation fails, the transaction is rolled back.
        
        Args:
            category_data: Pydantic schema containing category data
        
        Returns:
            Created RequestCategory object
        """
        try:
            async with self.session.begin():
                # Create the category
                category = RequestCategory(
                    name=category_data.name,
                    description=category_data.description,
                )
                
                self.session.add(category)
            
            # Transaction committed successfully
            return category
            
        except Exception as e:
            # session.begin() handles rollback automatically
            raise
    
    async def update_category(self, category_id: int, category_data: CategoryUpdate) -> Optional[RequestCategory]:
        """
        Update category data with transactional safety.
        
        Allows updating category name and description.
        
        All updates are atomic - if validation fails, no changes are persisted.
        
        Args:
            category_id: ID of the category to update
            category_data: Pydantic schema with update data (partial update)
        
        Returns:
            Updated RequestCategory object if successful, None if category not found
        """
        try:
            async with self.session.begin():
                result = await self.session.execute(
                    select(RequestCategory).where(RequestCategory.id == category_id)
                )
                category = result.scalar_one_or_none()
                
                if not category:
                    return None
                
                # Get only explicitly set fields
                update_data = category_data.dict(exclude_unset=True)
                
                # Apply updates
                for field, value in update_data.items():
                    if hasattr(category, field):
                        setattr(category, field, value)
            
            # Transaction committed successfully
            self.session.refresh(category)
            return category
            
        except Exception as e:
            # Rollback handled by session.begin()
            raise
    
    async def delete_category(self, category_id: int) -> bool:
        """
        Delete a category with transactional safety.
        
        Before deletion, ensures:
        - Category exists
        
        The deletion is atomic - if any check fails, no changes are made.
        
        Args:
            category_id: ID of the category to delete
        
        Returns:
            True if deletion was successful, False if category not found
        """
        try:
            async with self.session.begin():
                result = await self.session.execute(
                    select(RequestCategory).where(RequestCategory.id == category_id)
                )
                category = result.scalar_one_or_none()
                
                if not category:
                    return False
                
                # Delete the category
                await self.session.execute(
                    delete(RequestCategory).where(RequestCategory.id == category_id)
                )
            
            # Transaction committed successfully
            return True
            
        except Exception as e:
            # Rollback handled by session.begin()
            raise
