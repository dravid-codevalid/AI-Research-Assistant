from pydantic import BaseModel, Field, field_validator
from typing import Optional


class FeedbackCreate(BaseModel):
    user_id: Optional[str] = None
    workspace_id: Optional[str] = None
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5 stars")
    category: str = Field(..., description="Category of feedback, e.g., UI/UX, Bug, etc.")
    comment: str = Field(..., description="Text commentary from user")

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        valid_categories = {"UI/UX", "Bug", "Feature Request", "Accuracy", "Other"}
        if value not in valid_categories:
            raise ValueError(f"Category must be one of {valid_categories}")
        return value


class FeedbackResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    workspace_id: Optional[str] = None
    rating: int
    category: str
    comment: str
    created_at: str

    class Config:
        from_attributes = True
