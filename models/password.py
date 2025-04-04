from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import List
from bson.objectid import ObjectId
from typing import Optional




class PasswordItem(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()))
    email: str
    title: str  
    password: str


class SavedPassword(BaseModel):
    email: EmailStr  # Validates as a proper email
    passwords: List[PasswordItem] = Field(default_factory=list)  # A list of password entries

    def dict(self, *args, **kwargs):
        data = super().dict(*args, **kwargs)
        data['passwords'] = [password.dict(by_alias=True) for password in self.passwords]
        return data

class ShowAllPasswords(BaseModel):
    email: EmailStr

class UpdatePasswordRequest(BaseModel):
    email: str
    password_id: str
    password: str

class DeletePasswordRequest(BaseModel):
    email: str
    password_id: str