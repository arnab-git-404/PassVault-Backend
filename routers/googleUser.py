from fastapi import APIRouter, HTTPException, status, Body, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi.responses import JSONResponse
import os
from typing import Optional
from datetime import timedelta
from models.googleSignIn import GoogleAuthRequest
from models.user import UserInfo
from config import collection


router = APIRouter()


def user_helper(user) -> dict:
    return {

        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "is_2FA_Enabled": user.get("is_2FA_Enabled"),
        "is_google_user": user.get("is_google_user"),
        "profile_picture": user.get("profile_picture"),

    }





# async def get_user_by_email(email: str):
#     user =  collection.find_one({"email": email})
#     if user:
#         return user
#     return None

async def get_user_by_email(email: str):
    user = collection.find_one({"email": email})  # Add await here
    if user:
        return user_helper(user)  # Convert to consistent format
    return None


# async def get_user_by_google_id(google_id: str):
#     user =  collection.find_one({"google_id": google_id})
#     if user:
#         return user
#     return None

async def get_user_by_google_id(google_id: str):
    user =  collection.find_one({"google_id": google_id})  # Add await here
    if user:
        return user_helper(user)  # Convert to consistent format
    return None



# async def create_user(user_data: dict):
#     user_data["created_at"] = datetime.now()

#     user =  collection.insert_one(user_data)

#     new_user =  collection.find_one({"_id": user.inserted_id})
#     return user_helper(new_user)

async def create_user(user_data: dict):
    user_data["created_at"] = datetime.now()
    user = await collection.insert_one(user_data)  # Add await here
    new_user = await collection.find_one({"_id": user.inserted_id})  # Add await here
    return user_helper(new_user)



# async def update_user(email: str, data: dict):
#     user =  collection.find_one({"email": email})

#     if user:
#         updated_user =  collection.update_one(
#             {"email": email}, {"$set": data}
#         )

#         if updated_user:
#             return True
        
#     return False


async def update_user(email: str, data: dict):
    user =  collection.find_one({"email": email})  # Add await here
    if user:
        updated_user = collection.update_one(  # Add await here
            {"email": email}, {"$set": data}
        )
        if updated_user:
            return True
    return False




# JWT Configuration
# SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key")  # Change in production
SECRET_KEY = "6006"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt




@router.post("/google-auth")
async def google_authentication(user_data: GoogleAuthRequest = Body(...)):

    # Check if user exists by email
    user = await get_user_by_email(user_data.email)
    # print(user)


    if user:
        # User exists, update Google ID if needed
        if not user.get("google_id"):
            await update_user(
                user_data.email, 
                {
                    "google_id": user_data.google_id, 
                    "is_google_user": True
                }
            )
            
            user = await get_user_by_email(user_data.email)
    else:
        
        # Create new user
        new_user = {
            "name": user_data.name,
            "email": user_data.email,
            "google_id": user_data.google_id,


            "isVerified": user_data.isVerified,
            "is_2FA_Enabled": user_data.is_2FA_Enabled,
            "is_google_user": user_data.is_google_user,
            "profile_picture": user_data.profile_picture
        }

        user = await create_user(new_user)
        print("Google User Details: ",user)


    # Generate JWT token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"email": user["email"], "id": str(user["id"]) }, expires_delta=access_token_expires)

    # Create a single dictionary to hold all response data
    response_data = {
        "status_code": 200,
        "message": "Authentication successful",
        "token": access_token,
        "user": {
            "id": str(user["id"]),
            "name": user["name"],
            "email": user["email"],
            "is_2FA_Enabled": user.get("is_2FA_Enabled"),
            "is_google_user": user.get("is_google_user"),
            "profile_picture": user.get("profile_picture")
        }
    }

    response = JSONResponse(content={
        "status_code": 200,
        "message": "Authentication successful",
        "token": access_token,
        "user": {
            "id": str(user["id"]),
            "name": user["name"],
            "email": user["email"],
            "is_2FA_Enabled": user.get("is_2FA_Enabled"),
            "is_google_user": user.get("is_google_user"),
            "profile_picture": user.get("profile_picture")
        }
    }
    )
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True, secure=True, max_age=ACCESS_TOKEN_EXPIRE_MINUTES)

    return response

