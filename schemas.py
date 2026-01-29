from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class MediaItemResponse(BaseModel):
    id: int
    title: str
    category: str
    url: str
    uploaded_at: datetime

    class Config:
        from_attributes = True

class MediaItemCreate(BaseModel):
    title: str
    category: str
    file_path: str