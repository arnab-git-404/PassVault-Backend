from typing import Optional
from pydantic import BaseModel


class User(BaseModel):
    name: str
    email: str
    password: str
    otp: str
    isVerified: bool = False
    is_2FA_Enabled: bool = False
    is_google_user: bool = False
    profile_picture: str = None



class UserInfo(BaseModel):
    userId: str
    name:str
    email:str
    isVerified: bool = False
    is_2FA_Enabled: bool = False
    is_google_user: bool = False
    profile_picture: str 


class MasterKeyData(BaseModel):
    verification_hash: str
    salt: str
    iv: str


class UserLogin(BaseModel):
    email: str
    password: str



class SendOTPRequest(BaseModel):
    email: Optional[str] = None
    purpose: str





class VerifyOTP(BaseModel):
    email: str
    otp: str

class ResetPassword(BaseModel):
    email: str
    otp: str
    newPassword: str

class TwoFactorAuth(BaseModel):
    email: str
    _2fa_secret: str

class VerifyTwoFactorAuth(BaseModel):
    email: str
    verification_code: str


