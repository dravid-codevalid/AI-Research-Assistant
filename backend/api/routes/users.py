"""Users route — CRUD endpoints for user management."""

from fastapi import APIRouter, HTTPException

from api.schemas.users import CreateUserRequest, UserResponse
from infrastructure.database import async_session_factory
from adapters.repositories.user_repository import SqlAlchemyUserRepository
from domain.entities.user import User

import uuid
from datetime import datetime, timezone
from fastapi import Depends
from api.auth_utils import get_current_user

router = APIRouter(tags=["users"])


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(request: CreateUserRequest) -> UserResponse:
    """Create a new user."""
    async with async_session_factory() as session:
        repo = SqlAlchemyUserRepository(session)

        user = User(
            id=str(uuid.uuid4()),
            name=request.name,
            email=request.email,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        created = await repo.create(user)
        await session.commit()

        return UserResponse(
            id=created.id,
            name=created.name,
            email=created.email,
            is_admin=created.is_admin,
            created_at=created.created_at,
        )


@router.get("/users", response_model=list[UserResponse])
async def list_users(current_user: User = Depends(get_current_user)) -> list[UserResponse]:
    """List all users."""
    async with async_session_factory() as session:
        repo = SqlAlchemyUserRepository(session)
        
        if not current_user.is_admin:
            return [
                UserResponse(
                    id=current_user.id, name=current_user.name, email=current_user.email, is_admin=current_user.is_admin, created_at=current_user.created_at
                )
            ]
            
        users = await repo.list_all()

        return [
            UserResponse(
                id=u.id, name=u.name, email=u.email, is_admin=u.is_admin, created_at=u.created_at
            )
            for u in users
        ]


@router.get("/users/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Get the current authenticated user."""
    return UserResponse(
        id=current_user.id, 
        name=current_user.name, 
        email=current_user.email, 
        is_admin=current_user.is_admin, 
        created_at=current_user.created_at
    )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str) -> UserResponse:
    """Get a user by ID."""
    async with async_session_factory() as session:
        repo = SqlAlchemyUserRepository(session)
        user = await repo.get_by_id(user_id)

        if not user:
            raise HTTPException(status_code=404, detail=f"User '{user_id}' not found.")

        return UserResponse(
            id=user.id, name=user.name, email=user.email, is_admin=user.is_admin, created_at=user.created_at
        )
