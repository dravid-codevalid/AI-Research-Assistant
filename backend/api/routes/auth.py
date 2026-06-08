from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from api.auth_utils import verify_password, get_password_hash, create_access_token
from infrastructure.database import async_session_factory
from adapters.repositories.user_repository import SqlAlchemyUserRepository
from domain.entities.user import User
import uuid
from datetime import datetime, timezone

router = APIRouter(tags=["auth"])

class UserCreate(BaseModel):
    name: str
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/auth/register", response_model=Token)
async def register(request: UserCreate):
    async with async_session_factory() as session:
        repo = SqlAlchemyUserRepository(session)
        
        # Check if email exists
        existing = await repo.get_by_email(request.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
            
        hashed_pw = get_password_hash(request.password)
        user = User(
            id=str(uuid.uuid4()),
            name=request.name,
            email=request.email,
            hashed_password=hashed_pw,
            is_admin=False,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        await repo.create(user)
        await session.commit()
        
        access_token = create_access_token(data={"sub": user.email})
        return {"access_token": access_token, "token_type": "bearer"}

@router.post("/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    async with async_session_factory() as session:
        repo = SqlAlchemyUserRepository(session)
        user = await repo.get_by_email(form_data.username) # OAuth2 uses username for email usually
        
        if not user or not user.hashed_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        if not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        access_token = create_access_token(data={"sub": user.email})
        return {"access_token": access_token, "token_type": "bearer"}
