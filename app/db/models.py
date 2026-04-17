from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime,
    Float,
    Boolean,
)
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base


# ---------------------
# USERS
# ---------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # citizen / deputy / admin

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # связи
    requests = relationship("Request", back_populates="user")
    messages = relationship("Message", back_populates="user")

    role_requests = relationship(
        "RoleRequest", foreign_keys="[RoleRequest.user_id]", back_populates="user"
    )

    processed_role_requests = relationship(
        "RoleRequest", foreign_keys="[RoleRequest.processed_by_admin_id]"
    )


# ---------------------
# ROLE REQUESTS
# ---------------------
class RoleRequest(Base):
    __tablename__ = "role_requests"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    requested_role = Column(String, nullable=False)
    status = Column(String, nullable=False)

    user_comment = Column(Text)
    admin_comment = Column(Text)

    processed_by_admin_id = Column(Integer, ForeignKey("users.id"))

    created_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime)

    # связи
    user = relationship("User", foreign_keys=[user_id], back_populates="role_requests")
    processed_by_admin = relationship("User", foreign_keys=[processed_by_admin_id])


# ---------------------
# DISTRICTS
# ---------------------
class District(Base):
    __tablename__ = "districts"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)

    # позже будет PostGIS
    geometry = Column(Text)

    # связи
    deputies = relationship("Deputy", back_populates="district")
    requests = relationship("Request", back_populates="district")


# ---------------------
# DEPUTIES
# ---------------------
class Deputy(Base):
    __tablename__ = "deputies"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    district_id = Column(Integer, ForeignKey("districts.id"))

    appointed_at = Column(DateTime, default=datetime.utcnow)

    # связи
    user = relationship("User")
    district = relationship("District", back_populates="deputies")
    assigned_requests = relationship("Request", back_populates="assigned_deputy")


# ---------------------
# REQUEST CATEGORIES
# ---------------------
class RequestCategory(Base):
    __tablename__ = "request_categories"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)

    # связи
    requests = relationship("Request", back_populates="category")


# ---------------------
# REQUEST STATUSES
# ---------------------
class RequestStatus(Base):
    __tablename__ = "request_statuses"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)

    # связи
    requests = relationship("Request", back_populates="status")


# ---------------------
# REQUESTS (ОБРАЩЕНИЯ)
# ---------------------
class Request(Base):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"))
    district_id = Column(Integer, ForeignKey("districts.id"))
    category_id = Column(Integer, ForeignKey("request_categories.id"))
    status_id = Column(Integer, ForeignKey("request_statuses.id"))

    assigned_deputy_id = Column(Integer, ForeignKey("deputies.id"), nullable=True)

    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)

    address = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = Column(DateTime)

    # связи
    user = relationship("User", back_populates="requests")
    district = relationship("District", back_populates="requests")
    category = relationship("RequestCategory", back_populates="requests")
    status = relationship("RequestStatus", back_populates="requests")
    assigned_deputy = relationship("Deputy", back_populates="assigned_requests")

    photos = relationship("RequestPhoto", back_populates="request")
    messages = relationship("Message", back_populates="request")
    history = relationship("StatusHistory", back_populates="request")


# ---------------------
# REQUEST PHOTOS
# ---------------------
class RequestPhoto(Base):
    __tablename__ = "request_photos"

    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("requests.id"))

    file_url = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # связи
    request = relationship("Request", back_populates="photos")


# ---------------------
# MESSAGES
# ---------------------
class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("requests.id"))
    user_id = Column(Integer, ForeignKey("users.id"))

    text = Column(Text, nullable=False)
    is_system = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    # связи
    request = relationship("Request", back_populates="messages")
    user = relationship("User", back_populates="messages")


# ---------------------
# STATUS HISTORY
# ---------------------
class StatusHistory(Base):
    __tablename__ = "status_history"

    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("requests.id"))

    old_status_id = Column(Integer, ForeignKey("request_statuses.id"))
    new_status_id = Column(Integer, ForeignKey("request_statuses.id"))

    changed_by_user_id = Column(Integer, ForeignKey("users.id"))

    created_at = Column(DateTime, default=datetime.utcnow)

    # связи
    request = relationship("Request", back_populates="history")
