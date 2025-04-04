from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: Optional[str] = None
    google_id: Optional[str] = None
    profile_picture: Optional[str] = None
    is_google_user: bool = False


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    profile_picture: Optional[str] = None

















class GoogleAuthRequest(BaseModel):
    name: str
    email: str
    google_id: str
    
    isVerified: bool = True
    is_2FA_Enabled: bool = False
    is_google_user: bool = True
    profile_picture: Optional[str] = None
