from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from models.user import (
    User, UserLogin, SendOTPRequest, TwoFactorAuth, 
    VerifyTwoFactorAuth, VerifyOTP, ResetPassword, 
    UserInfo, MasterKeyData
)
from config import collection, collection_googleSignIn, collection_password, db
from bson.objectid import ObjectId
from services.user import UserHandler
import redis
import pyotp
import qrcode
from io import BytesIO
import base64
from datetime import datetime, timedelta
from jose import JWTError, jwt, ExpiredSignatureError
from fastapi import Header
import bcrypt


router = APIRouter()
user_handler = UserHandler(collection)

# Connect to Redis (make sure Redis is running)
r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)


OTP_EXPIRY_TIME = 60 * 5  # OTP expires after 5 minutes (300 seconds)

SECRET_KEY = "6006"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt




def get_current_user(authorization: str = Header(None)):
    if authorization is None:
        raise HTTPException(status_code=400, detail="Authorization header is missing")
    
    try:
        # Assuming the token starts with "Bearer "
        token = authorization.split(" ")[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        user_email = payload.get("email")
        
        if user_email is None:
            raise HTTPException(status_code=400, detail="Token does not contain email")

        return user_email
    
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired. Please log in again.")
    
    except JWTError:
        raise HTTPException(status_code=404, detail="Not authenticated")
    
    except Exception as e:
        # Catching any other unexpected errors
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")





@router.post("/send-otp")
async def send_otp(user: SendOTPRequest):

    user_email: str = Depends(get_current_user)
    try:
        # Generate OTP
        otp = user_handler.generate_otp()
        
        # Store OTP in Redis with an expiry time of 5 minutes
        res = r.setex(user.email or user_email , OTP_EXPIRY_TIME, otp)
        
        # Send email with OTP
        success = user_handler.send_otp_email(user.email or user_email, otp, user.purpose)
        
        if not success:
            return JSONResponse(content={"status_code": 500, "message": "Failed to send OTP. Please try again."})

        return JSONResponse(content={
            "status_code": 200, 
            "message": "OTP sent successfully. Please verify it.", 
            "result": res, 
            "otp": otp  # Remove in production
        })
    except Exception as e:
        return JSONResponse(content={
            "status_code": 500, 
            "message": f"Internal Server Error: {str(e)}"
        })

@router.post("/verify-otp")
async def verify_otp(user: VerifyOTP):
    try:
        # Get OTP from Redis for email verification
        otp_from_redis = r.get(user.email)

        if not otp_from_redis:
            return JSONResponse(content={
                "status_code": 400, 
                "message": "OTP has expired. Please request a new OTP."
            })

        if int(user.otp) == int(otp_from_redis):
            return JSONResponse(content={
                "status_code": 200, 
                "message": "OTP Verified successfully. Proceed to signup."
            })
        else:
            return JSONResponse(content={
                "status_code": 400, 
                "message": "Invalid OTP. Please try again."
            })
    except Exception as e:
        return JSONResponse(content={
            "status_code": 500, 
            "message": f"Internal Server Error: {str(e)}"
        })

@router.post("/signup")
async def create_user(user: User):
    try:
        otp_from_redis = r.get(user.email)
    
        existing_user = collection.find_one({"email": user.email})

        if not otp_from_redis:
            return JSONResponse(content={
                "status_code": 400, 
                "message": "OTP has expired. Please request a new OTP."
            })

        if existing_user:
            return JSONResponse(content={
                "status_code": 400, 
                "message": "User already exists. Please use a different email."
            })


        encoded_Password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt(14))

        if int(user.otp) == int(otp_from_redis):
            # OTP matched, save user to database
            user.otp = otp_from_redis
            user.isVerified = True
            user.password = encoded_Password
            
            collection.insert_one(dict(user))
            created_user = collection.find_one({"email": user.email})
            user_id = str(created_user["_id"])
            r.delete(user.email)
            
            userDataFromDB = UserInfo(
                userId=user_id, 
                name=created_user["name"], 
                email=created_user["email"], 
                isVerified=created_user["isVerified"], 
                is_2FA_Enabled=created_user.get("is_2FA_Enabled", False),
                is_google_user=created_user.get("is_google_user", False), 
                profile_picture=str(created_user.get("profile_picture", ""))
            )

            # Create access token
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"email": user.email, "id": user_id}, 
                expires_delta=access_token_expires
            )

            response = JSONResponse(content={
                "status_code": 200, 
                "token": access_token, 
                "message": "User created successfully", 
                "user": userDataFromDB.dict()
            })
            response.set_cookie(
                key="access_token", 
                value=f"Bearer {access_token}", 
                httponly=True, 
                secure=True, 
                max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
            )
            return response
        
        else:
            return JSONResponse(content={
                "status_code": 400, 
                "message": "Invalid OTP. Please try again."
            })

    except Exception as e:
        return JSONResponse(content={
            "status_code": 500, 
            "message": f"Internal Server Error: {str(e)}"
        })


@router.post("/signin")
async def signin_user(user: UserLogin):
    try:
        existing_user = collection.find_one({"email": user.email})

        if not existing_user:
            return JSONResponse(
                status_code=404,
                content={
                    "status_code": 404, 
                    "message": "User not found"
                }
            )

        stored_password = existing_user["password"]
        
        # Check password using bcrypt.checkpw
        if not bcrypt.checkpw(user.password.encode('utf-8'), stored_password):
            return JSONResponse(
                status_code=401,
                content={
                    "status_code": 401, 
                    "message": "Invalid password"
                }
            )

        user_id = str(existing_user["_id"])

        userDataFromDB = UserInfo(
            userId=user_id, 
            name=existing_user["name"], 
            email=existing_user["email"], 
            isVerified=existing_user["isVerified"], 
            is_2FA_Enabled=existing_user.get("is_2FA_Enabled", False),
            is_google_user=existing_user.get("is_google_user", False), 
            profile_picture=str(existing_user.get("profile_picture", ""))
        )

        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"email": user.email, "id": user_id}, 
            expires_delta=access_token_expires
        )

        response = JSONResponse(
            status_code=200,
            content={
                "status_code": 200, 
                "token": access_token, 
                "message": "User Logged In Successfully", 
                "user": userDataFromDB.dict()
            }
        )
        response.set_cookie(
            key="access_token", 
            value=f"Bearer {access_token}", 
            httponly=True, 
            secure=True, 
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
        return response
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status_code": 500, 
                "message": f"Unable to Sign In User: {str(e)}"
            }
        )











@router.delete('/delete-account')
async def delete_account(user_email: str = Depends(get_current_user)):
    try:
        # Find user to verify they exist
        existing_user = collection.find_one({"email": user_email})
        
        if not existing_user:
            return JSONResponse(
                content={
                "status_code": 404, 
                "message": "User not found"
            })
        
        # Delete the user from the database
        result = collection.delete_one({"email": user_email})
        
        if result.deleted_count == 1:
            # If user was also authenticated with Google, remove from that collection too
            if existing_user.get("is_google_user", False):
                collection_googleSignIn.delete_one({"email": user_email})
                
            # Clear any data in Redis associated with this user
            r.delete(user_email)
            
            return JSONResponse(content={
                "status_code": 200, 
                "message": "Account deleted successfully"
            })
        else:
            return JSONResponse(content={
                "status_code": 500, 
                "message": "Failed to delete account"
            })
            
    except Exception as e:
        return JSONResponse(content={
            "status_code": 500, 
            "message": f"Failed to delete account: {str(e)}"
        })

@router.get("/")
async def get_all_users():
    try:
        users = collection.find()
        user_list = []
        for user in users:
            user["_id"] = str(user["_id"])
            user_list.append(user)
        return JSONResponse(content={
            "status_code": 200, 
            "users": user_list
        })
    except Exception as e:
        return JSONResponse(content={
            "status_code": 500, 
            "message": f"Failed to retrieve users: {str(e)}"
        })

@router.get("/user-info")
async def get_user_info(current_user: str = Depends(get_current_user)):
    try:
        user = collection.find_one({"email": current_user})

        if not user:
            return JSONResponse(content={
                "status_code": 404, 
                "message": "User not found"
            })
        
        userDataFromDB = UserInfo(
            userId=str(user["_id"]), 
            name=user["name"], 
            email=user["email"], 
            isVerified=user["isVerified"], 
            is_2FA_Enabled=user.get("is_2FA_Enabled", False),
            profile_picture=str(user.get("profile_picture", "")), 
            is_google_user=user.get("is_google_user", False)
        )

        return JSONResponse(content={
            "status_code": 200, 
            "user": userDataFromDB.dict()
        })
    except Exception as e:
        return JSONResponse(content={
            "status_code": 500, 
            "message": f"Failed to retrieve user info: {str(e)}"
        })

@router.post('/2fa/enable')
async def enable_2fa(user: TwoFactorAuth):
    try:
        existing_user = collection.find_one({"email": user.email})

        if not existing_user:
            return JSONResponse(content={
                "status_code": 404, 
                "message": "User not found"
            })

        # Generate a secret key for 2FA
        secret = pyotp.random_base32()
        existing_user["_2fa_secret"] = secret
        collection.update_one({"email": user.email}, {"$set": existing_user})

        # Generate a QR code for the secret
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(user.email, issuer_name="PassVault")
        qr = qrcode.make(uri)
        buf = BytesIO()
        qr.save(buf, format='PNG')
        qr_code = base64.b64encode(buf.getvalue()).decode('utf-8')

        return JSONResponse(content={
            "status_code": 200,
            "qrCode": f"data:image/png;base64,{qr_code}"
        })
    except Exception as e:
        return JSONResponse(content={
            "status_code": 500, 
            "message": f"Failed to enable 2FA: {str(e)}"
        })

@router.post('/2fa/verify')
async def verify_2fa(user: VerifyTwoFactorAuth):
    try:
        existing_user = collection.find_one({"email": user.email})

        if not existing_user:
            return JSONResponse(content={
                "status_code": 404, 
                "message": "User not found"
            })

        if "_2fa_secret" not in existing_user:
            return JSONResponse(content={
                "status_code": 400, 
                "message": "2FA is not enabled for this user"
            })

        totp = pyotp.TOTP(existing_user["_2fa_secret"])

        if totp.verify(user.verification_code):
            existing_user["is_2FA_Enabled"] = True
            collection.update_one({"email": user.email}, {"$set": existing_user})
            return JSONResponse(content={
                "status_code": 200, 
                "message": "2FA verification successful"
            })
        else:
            return JSONResponse(content={
                "status_code": 400, 
                "message": "Invalid verification code"
            })
    except Exception as e:
        return JSONResponse(content={
            "status_code": 500, 
            "message": f"Failed to verify 2FA: {str(e)}"
        })



@router.post('/reset-2fa')
async def enable_2fa( userData:dict, user_email: str = Depends(get_current_user)):
    try:
        otp_from_redis = r.get(user_email)

        existing_user = collection.find_one({"email": user_email})

        if not existing_user:
            return JSONResponse(content={
                "status_code": 404, 
                "message": "User not found"
            })

        # Reset 2FA 
        if( otp_from_redis == userData.get('otp')):

            secret = ''
            existing_user["_2fa_secret"] = secret
            existing_user["is_2FA_Enabled"] = False
            collection.update_one({"email": user_email}, {"$set": existing_user})
            r.delete(user_email)

            return JSONResponse(content={
                "status_code": 200,
                "message": "2FA Reset Successfully"
            })
        else:
             return JSONResponse(content={
                "status_code": 400,
                "message": "Failed To reset! Resend The OTP"
            })
    except Exception as e:
        return JSONResponse(content={
            "status_code": 500, 
            "message": f"Failed to reset 2FA: {str(e)}"
        })


@router.post('/reset-password')
async def reset_password(user: ResetPassword):
    try:
        existing_user = collection.find_one({"email": user.email})

        if not existing_user:
            return JSONResponse(content={
                "status_code": 404, 
                "message": "User not found"
            })

        # Verify OTP
        otp_from_redis = r.get(user.email)
        if not otp_from_redis or user.otp != otp_from_redis:
            return JSONResponse(content={
                "status_code": 400, 
                "message": "Invalid OTP. Please try again."
            })

        # Check if new password is different from current password
        if existing_user["password"] == user.newPassword:
            return JSONResponse(content={
                "status_code": 400, 
                "message": "New password must be different from the old one."
            })

        # Update password
        collection.update_one(
            {"email": user.email}, 
            {"$set": {"password": user.newPassword}}
        )

        # Clear OTP from Redis after successful reset
        r.delete(user.email)

        return JSONResponse(content={
            "status_code": 200, 
            "message": "Password reset successful"
        })

    except Exception as e:
        return JSONResponse(content={
            "status_code": 500, 
            "message": f"Password reset failed: {str(e)}"
        })


@router.post('/set-masterKeyHash')
async def setup_master_key(
    data: MasterKeyData, 
    user_email: str = Depends(get_current_user)
):
    try:
        existing_user = collection.find_one({"email": user_email})

        if not existing_user:
            return JSONResponse(content={
                "status_code": 404, 
                "message": "User not found"
            })

        # Update master key verification details
        update_result = collection.update_one(
            {"email": user_email}, 
            {"$set": {
                "master_key_verification": data.verification_hash,
                "master_key_salt": data.salt,
                "master_key_iv": data.iv
            }}
        )

        if update_result.modified_count == 0:
            return JSONResponse(content={
                "status_code": 400, 
                "message": "Failed to update master key"
            })

        return JSONResponse(content={
            "status_code": 200, 
            "message": "Master key setup successful"
        })

    except Exception as e:
        return JSONResponse(content={
            "status_code": 500, 
            "message": f"Failed to setup master key: {str(e)}"
        })



@router.get('/get-masterKeyHash')
async def get_master_key_verification_hash(
    user_email: str = Depends(get_current_user)
):
    try:
        user = collection.find_one({"email": user_email})

        if not user:
            return JSONResponse(content={
                "status_code": 404, 
                "message": "User not found"
            })

        # Check if master key data exists
        master_key_fields = [
            "master_key_verification", 
            "master_key_salt", 
            "master_key_iv"
        ]

        if not all(field in user for field in master_key_fields):
            return JSONResponse(content={
                "status_code": 200,
                "data": {
                    "is_setup": False,
                    "verification_hash": None,
                    "salt": None,
                    "iv": None
                }
            })
        

    

        return {
            "status_code": 200,
            "is_setup": True,
             "verification_hash": user["master_key_verification"],
             "salt": user["master_key_salt"],
             "iv": user["master_key_iv"]
        }

    except Exception as e:
        return JSONResponse(content={
            "status_code": 500, 
            "message": f"Failed to get master key data: {str(e)}"
        })


@router.post('/reset-master-key')
async def reset_master_key(
    data: dict, 
    user_email: str = Depends(get_current_user)
):
    try:
        # Find user
        existing_user = collection.find_one({"email": user_email})
        
        if not existing_user:
            return JSONResponse(content={
                "status_code": 404, 
                "message": "User not found"
            })
        
        # Verify OTP
        otp_from_redis = r.get(user_email)
        if not otp_from_redis or data.get("otp") != otp_from_redis:
            return JSONResponse(content={
                "status_code": 400, 
                "message": "Invalid or expired OTP"
            })
        
        # Check if 2FA is enabled and verify
        if existing_user.get("is_2FA_Enabled", False):
            if "_2fa_secret" not in existing_user:
                return JSONResponse(content={
                    "status_code": 400, 
                    "message": "2FA is enabled but not properly configured"
                })
                
            totp = pyotp.TOTP(existing_user["_2fa_secret"])
            if not data.get("twoFactorCode") or not totp.verify(data.get("twoFactorCode")):
                return JSONResponse(content={
                    "status_code": 400, 
                    "message": "Invalid 2FA verification code"
                })
        
        # Delete all passwords associated with the user
        passwords_collection = db["password"]
        delete_result = passwords_collection.delete_many({"email": str(existing_user["email"])})
        
        # Remove master key data
        update_result = collection.update_one(
            {"email": user_email}, 
            {"$unset": {
                "master_key_verification": "",
                "master_key_salt": "",
                "master_key_iv": ""
            }}
        )
        
        # Clear Redis OTP
        r.delete(user_email)
        
        return JSONResponse(content={
            "status_code": 200, 
            "message": "Master key reset successful. All passwords have been removed.",
            "passwords_deleted": delete_result.deleted_count
        })
        
    except Exception as e:
        return JSONResponse(content={
            "status_code": 500, 
            "message": f"Failed to reset master key: {str(e)}"
        })







# 2ND Edition 
# from fastapi import APIRouter, HTTPException, Depends
# from fastapi.responses import JSONResponse
# from models.user import (
#     User, UserLogin, SendOTPRequest, TwoFactorAuth, 
#     VerifyTwoFactorAuth, VerifyOTP, ResetPassword, 
#     UserInfo, MasterKeyData
# )
# from config import collection, collection_googleSignIn, collection_password, db
# from bson.objectid import ObjectId
# from services.user import UserHandler
# import redis
# import pyotp
# import qrcode
# from io import BytesIO
# import base64
# from datetime import datetime, timedelta
# from jose import JWTError, jwt, ExpiredSignatureError
# from fastapi import Header
# import bcrypt



# router = APIRouter()
# user_handler = UserHandler(collection)

# # Connect to Redis (make sure Redis is running)
# r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)


# OTP_EXPIRY_TIME = 60 * 5  # OTP expires after 5 minutes (300 seconds)

# SECRET_KEY = "6006"
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 30

# def create_access_token(data: dict, expires_delta: timedelta = None):
#     to_encode = data.copy()
#     if expires_delta:
#         expire = datetime.utcnow() + expires_delta
#     else:
#         expire = datetime.utcnow() + timedelta(minutes=15)
#     to_encode.update({"exp": expire})
#     encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
#     return encoded_jwt




# def get_current_user(authorization: str = Header(None)):
#     if authorization is None:
#         raise HTTPException(status_code=400, detail="Authorization header is missing")
    
#     try:
#         # Assuming the token starts with "Bearer "
#         token = authorization.split(" ")[1]
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
#         user_email = payload.get("email")
        
#         if user_email is None:
#             raise HTTPException(status_code=400, detail="Token does not contain email")

#         return user_email
    
#     except ExpiredSignatureError:
#         raise HTTPException(status_code=401, detail="Token has expired. Please log in again.")
    
#     except JWTError:
#         raise HTTPException(status_code=404, detail="Not authenticated")
    
#     except Exception as e:
#         # Catching any other unexpected errors
#         raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")





# @router.post("/send-otp")
# async def send_otp(user: SendOTPRequest):

#     user_email: str = Depends(get_current_user)
#     try:
#         # Generate OTP
#         otp = user_handler.generate_otp()
        
#         # Store OTP in Redis with an expiry time of 5 minutes
#         res = r.setex(user.email or user_email , OTP_EXPIRY_TIME, otp)
        
#         # Send email with OTP
#         success = user_handler.send_otp_email(user.email or user_email, otp, user.purpose)
        
#         if not success:
#             return JSONResponse(
#                 status_code=500,
#                 content={"status_code": 500, "message": "Failed to send OTP. Please try again."}
#             )

#         return JSONResponse(
#             status_code=200,
#             content={
#                 "status_code": 200, 
#                 "message": "OTP sent successfully. Please verify it.", 
#                 "result": res, 
#                 "otp": otp  # Remove in production
#             }
#         )
#     except Exception as e:
#         return JSONResponse(
#             status_code=500,
#             content={
#                 "status_code": 500, 
#                 "message": f"Internal Server Error: {str(e)}"
#             }
#         )

# @router.post("/verify-otp")
# async def verify_otp(user: VerifyOTP):
#     try:
#         # Get OTP from Redis for email verification
#         otp_from_redis = r.get(user.email)

#         if not otp_from_redis:
#             return JSONResponse(
#                 status_code=400,
#                 content={
#                     "status_code": 400, 
#                     "message": "OTP has expired. Please request a new OTP."
#                 }
#             )

#         if int(user.otp) == int(otp_from_redis):
#             return JSONResponse(
#                 status_code=200,
#                 content={
#                     "status_code": 200, 
#                     "message": "OTP Verified successfully. Proceed to signup."
#                 }
#             )
#         else:
#             return JSONResponse(
#                 status_code=400,
#                 content={
#                     "status_code": 400, 
#                     "message": "Invalid OTP. Please try again."
#                 }
#             )
#     except Exception as e:
#         return JSONResponse(
#             status_code=500,
#             content={
#                 "status_code": 500, 
#                 "message": f"Internal Server Error: {str(e)}"
#             }
#         )

# @router.post("/signup")
# async def create_user(user: User):
#     try:
#         otp_from_redis = r.get(user.email)
    
#         existing_user = collection.find_one({"email": user.email})

#         if not otp_from_redis:
#             return JSONResponse(
#                 status_code=400,
#                 content={
#                     "status_code": 400, 
#                     "message": "OTP has expired. Please request a new OTP."
#                 }
#             )

#         if existing_user:
#             return JSONResponse(
#                 status_code=400,
#                 content={
#                     "status_code": 400, 
#                     "message": "User already exists. Please use a different email."
#                 }
#             )


#         encoded_Password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt(14))

#         if int(user.otp) == int(otp_from_redis):
#             # OTP matched, save user to database
#             user.otp = otp_from_redis
#             user.isVerified = True
#             user.password = encoded_Password
            
#             collection.insert_one(dict(user))
#             created_user = collection.find_one({"email": user.email})
#             user_id = str(created_user["_id"])
#             r.delete(user.email)
            
#             userDataFromDB = UserInfo(
#                 userId=user_id, 
#                 name=created_user["name"], 
#                 email=created_user["email"], 
#                 isVerified=created_user["isVerified"], 
#                 is_2FA_Enabled=created_user.get("is_2FA_Enabled", False),
#                 is_google_user=created_user.get("is_google_user", False), 
#                 profile_picture=str(created_user.get("profile_picture", ""))
#             )

#             # Create access token
#             access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#             access_token = create_access_token(
#                 data={"email": user.email, "id": user_id}, 
#                 expires_delta=access_token_expires
#             )

#             response = JSONResponse(
#                 status_code=200,
#                 content={
#                     "status_code": 200, 
#                     "token": access_token, 
#                     "message": "User created successfully", 
#                     "user": userDataFromDB.dict()
#                 }
#             )
#             response.set_cookie(
#                 key="access_token", 
#                 value=f"Bearer {access_token}", 
#                 httponly=True, 
#                 secure=True, 
#                 max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
#             )
#             return response
        
#         else:
#             return JSONResponse(
#                 status_code=400,
#                 content={
#                     "status_code": 400, 
#                     "message": "Invalid OTP. Please try again."
#                 }
#             )

#     except Exception as e:
#         return JSONResponse(
#             status_code=500,
#             content={
#                 "status_code": 500, 
#                 "message": f"Internal Server Error: {str(e)}"
#             }
#         )


# @router.post("/signin")
# async def signin_user(user: UserLogin):
#     try:
#         existing_user = collection.find_one({"email": user.email})

#         if not existing_user:
#             return JSONResponse(
#                 status_code=404,
#                 content={
#                     "status_code": 404, 
#                     "message": "User not found"
#                 }
#             )

#         stored_password = existing_user["password"]
        
#         # Check password using bcrypt.checkpw
#         if not bcrypt.checkpw(user.password.encode('utf-8'), stored_password):
#             return JSONResponse(
#                 status_code=401,
#                 content={
#                     "status_code": 401, 
#                     "message": "Invalid password"
#                 }
#             )

#         user_id = str(existing_user["_id"])

#         userDataFromDB = UserInfo(
#             userId=user_id, 
#             name=existing_user["name"], 
#             email=existing_user["email"], 
#             isVerified=existing_user["isVerified"], 
#             is_2FA_Enabled=existing_user.get("is_2FA_Enabled", False),
#             is_google_user=existing_user.get("is_google_user", False), 
#             profile_picture=str(existing_user.get("profile_picture", ""))
#         )

#         # Create access token
#         access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#         access_token = create_access_token(
#             data={"email": user.email, "id": user_id}, 
#             expires_delta=access_token_expires
#         )

#         response = JSONResponse(
#             status_code=200,
#             content={
#                 "status_code": 200, 
#                 "token": access_token, 
#                 "message": "User Logged In Successfully", 
#                 "user": userDataFromDB.dict()
#             }
#         )
#         response.set_cookie(
#             key="access_token", 
#             value=f"Bearer {access_token}", 
#             httponly=True, 
#             secure=True, 
#             max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
#         )
        
#         return response
    
#     except Exception as e:
#         return JSONResponse(
#             status_code=500,
#             content={
#                 "status_code": 500, 
#                 "message": f"Unable to Sign In User: {str(e)}"
#             }
#         )


# @router.delete('/delete-account')
# async def delete_account(user_email: str = Depends(get_current_user)):
#     try:
#         # Find user to verify they exist
#         existing_user = collection.find_one({"email": user_email})
        
#         if not existing_user:
#             return JSONResponse(
#                 status_code=404,
#                 content={
#                     "status_code": 404, 
#                     "message": "User not found"
#                 }
#             )
        
#         # Delete the user from the database
#         result = collection.delete_one({"email": user_email})
        
#         if result.deleted_count == 1:
#             # If user was also authenticated with Google, remove from that collection too
#             if existing_user.get("is_google_user", False):
#                 collection_googleSignIn.delete_one({"email": user_email})
                
#             # Clear any data in Redis associated with this user
#             r.delete(user_email)
            
#             return JSONResponse(
#                 status_code=200,
#                 content={
#                     "status_code": 200, 
#                     "message": "Account deleted successfully"
#                 }
#             )
#         else:
#             return JSONResponse(
#                 status_code=500,
#                 content={
#                     "status_code": 500, 
#                     "message": "Failed to delete account"
#                 }
#             )
            
#     except Exception as e:
#         return JSONResponse(
#             status_code=500,
#             content={
#                 "status_code": 500, 
#                 "message": f"Failed to delete account: {str(e)}"
#             }
#         )

# @router.get("/")
# async def get_all_users():
#     try:
#         users = collection.find()
#         user_list = []
#         for user in users:
#             user["_id"] = str(user["_id"])
#             user_list.append(user)
#         return JSONResponse(
#             status_code=200,
#             content={
#                 "status_code": 200, 
#                 "users": user_list
#             }
#         )
#     except Exception as e:
#         return JSONResponse(
#             status_code=500,
#             content={
#                 "status_code": 500, 
#                 "message": f"Failed to retrieve users: {str(e)}"
#             }
#         )

# @router.get("/user-info")
# async def get_user_info(current_user: str = Depends(get_current_user)):
#     try:
#         user = collection.find_one({"email": current_user})

#         if not user:
#             return JSONResponse(
#                 status_code=404,
#                 content={
#                     "status_code": 404, 
#                     "message": "User not found"
#                 }
#             )
        
#         userDataFromDB = UserInfo(
#             userId=str(user["_id"]), 
#             name=user["name"], 
#             email=user["email"], 
#             isVerified=user["isVerified"], 
#             is_2FA_Enabled=user.get("is_2FA_Enabled", False),
#             profile_picture=str(user.get("profile_picture", "")), 
#             is_google_user=user.get("is_google_user", False)
#         )

#         return JSONResponse(
#             status_code=200,
#             content={
#                 "status_code": 200, 
#                 "user": userDataFromDB.dict()
#             }
#         )
#     except Exception as e:
#         return JSONResponse(
#             status_code=500,
#             content={
#                 "status_code": 500, 
#                 "message": f"Failed to retrieve user info: {str(e)}"
#             }
#         )

# @router.post('/2fa/enable')
# async def enable_2fa(user: TwoFactorAuth):
#     try:
#         existing_user = collection.find_one({"email": user.email})

#         if not existing_user:
#             return JSONResponse(
#                 status_code=404,
#                 content={
#                     "status_code": 404, 
#                     "message": "User not found"
#                 }
#             )

#         # Generate a secret key for 2FA
#         secret = pyotp.random_base32()
#         existing_user["_2fa_secret"] = secret
#         collection.update_one({"email": user.email}, {"$set": existing_user})

#         # Generate a QR code for the secret
#         totp = pyotp.TOTP(secret)
#         uri = totp.provisioning_uri(user.email, issuer_name="PassVault")
#         qr = qrcode.make(uri)
#         buf = BytesIO()
#         qr.save(buf, format='PNG')
#         qr_code = base64.b64encode(buf.getvalue()).decode('utf-8')

#         return JSONResponse(
#             status_code=200,
#             content={
#                 "status_code": 200,
#                 "qrCode": f"data:image/png;base64,{qr_code}"
#             }
#         )
#     except Exception as e:
#         return JSONResponse(
#             status_code=500,
#             content={
#                 "status_code": 500, 
#                 "message": f"Failed to enable 2FA: {str(e)}"
#             }
#         )

# @router.post('/2fa/verify')
# async def verify_2fa(user: VerifyTwoFactorAuth):
#     try:
#         existing_user = collection.find_one({"email": user.email})

#         if not existing_user:
#             return JSONResponse(
#                 status_code=404,
#                 content={
#                     "status_code": 404, 
#                     "message": "User not found"
#                 }
#             )

#         if "_2fa_secret" not in existing_user:
#             return JSONResponse(
#                 status_code=400,
#                 content={
#                     "status_code": 400, 
#                     "message": "2FA is not enabled for this user"
#                 }
#             )

#         totp = pyotp.TOTP(existing_user["_2fa_secret"])

#         if totp.verify(user.verification_code):
#             existing_user["is_2FA_Enabled"] = True
#             collection.update_one({"email": user.email}, {"$set": existing_user})
#             return JSONResponse(
#                 status_code=200,
#                 content={
#                     "status_code": 200, 
#                     "message": "2FA verification successful"
#                 }
#             )
#         else:
#             return JSONResponse(
#                 status_code=400,
#                 content={
#                     "status_code": 400, 
#                     "message": "Invalid verification code"
#                 }
#             )
#     except Exception as e:
#         return JSONResponse(
#             status_code=500,
#             content={
#                 "status_code": 500, 
#                 "message": f"Failed to verify 2FA: {str(e)}"
#             }
#         )


# @router.post('/reset-2fa')
# async def enable_2fa(userData:dict, user_email: str = Depends(get_current_user)):
#     try:
#         otp_from_redis = r.get(user_email)

#         existing_user = collection.find_one({"email": user_email})

#         if not existing_user:
#             return JSONResponse(
#                 status_code=404,
#                 content={
#                     "status_code": 404, 
#                     "message": "User not found"
#                 }
#             )

#         # Reset 2FA 
#         if(otp_from_redis == userData.get('otp')):
#             secret = ''
#             existing_user["_2fa_secret"] = secret
#             existing_user["is_2FA_Enabled"] = False
#             collection.update_one({"email": user_email}, {"$set": existing_user})
#             r.delete(user_email)

#             return JSONResponse(
#                 status_code=200,
#                 content={
#                     "status_code": 200,
#                     "message": "2FA Reset Successfully"
#                 }
#             )
#         else:
#             return JSONResponse(
#                 status_code=400,
#                 content={
#                     "status_code": 400,
#                     "message": "Failed To reset! Resend The OTP"
#                 }
#             )
#     except Exception as e:
#         return JSONResponse(
#             status_code=500,
#             content={
#                 "status_code": 500, 
#                 "message": f"Failed to reset 2FA: {str(e)}"
#             }
#         )


# @router.post('/reset-password')
# async def reset_password(user: ResetPassword):
#     try:
#         existing_user = collection.find_one({"email": user.email})

#         if not existing_user:
#             return JSONResponse(
#                 status_code=404,
#                 content={
#                     "status_code": 404, 
#                     "message": "User not found"
#                 }
#             )

#         # Verify OTP
#         otp_from_redis = r.get(user.email)
#         if not otp_from_redis or user.otp != otp_from_redis:
#             return JSONResponse(
#                 status_code=400,
#                 content={
#                     "status_code": 400, 
#                     "message": "Invalid OTP. Please try again."
#                 }
#             )

#         # Hash the new password
#         encoded_password = bcrypt.hashpw(user.newPassword.encode('utf-8'), bcrypt.gensalt(14))

#         # Check if new password is different from current password
#         if not bcrypt.checkpw(user.newPassword.encode('utf-8'), existing_user["password"]):
#             # Update password with hashed password
#             collection.update_one(
#                 {"email": user.email}, 
#                 {"$set": {"password": encoded_password}}
#             )

#             # Clear OTP from Redis after successful reset
#             r.delete(user.email)

#             return JSONResponse(
#                 status_code=200,
#                 content={
#                     "status_code": 200, 
#                     "message": "Password reset successful"
#                 }
#             )
#         else:
#             return JSONResponse(
#                 status_code=400,
#                 content={
#                     "status_code": 400, 
#                     "message": "New password must be different from the old one."
#                 }
#             )

#     except Exception as e:
#         return JSONResponse(
#             status_code=500,
#             content={
#                 "status_code": 500, 
#                 "message": f"Password reset failed: {str(e)}"
#             }
#         )


# @router.post('/set-masterKeyHash')
# async def setup_master_key(
#     data: MasterKeyData, 
#     user_email: str = Depends(get_current_user)
# ):
#     try:
#         existing_user = collection.find_one({"email": user_email})

#         if not existing_user:
#             return JSONResponse(
#                 status_code=404,
#                 content={
#                     "status_code": 404, 
#                     "message": "User not found"
#                 }
#             )

#         # Update master key verification details
#         update_result = collection.update_one(
#             {"email": user_email}, 
#             {"$set": {
#                 "master_key_verification": data.verification_hash,
#                 "master_key_salt": data.salt,
#                 "master_key_iv": data.iv
#             }}
#         )

#         if update_result.modified_count == 0:
#             return JSONResponse(
#                 status_code=400,
#                 content={
#                     "status_code": 400, 
#                     "message": "Failed to update master key"
#                 }
#             )

#         return JSONResponse(
#             status_code=200,
#             content={
#                 "status_code": 200, 
#                 "message": "Master key setup successful"
#             }
#         )

#     except Exception as e:
#         return JSONResponse(
#             status_code=500,
#             content={
#                 "status_code": 500, 
#                 "message": f"Failed to setup master key: {str(e)}"
#             }
#         )


# @router.get('/get-masterKeyHash')
# async def get_master_key_verification_hash(
#     user_email: str = Depends(get_current_user)
# ):
#     try:
#         user = collection.find_one({"email": user_email})

#         if not user:
#             return JSONResponse(
#                 status_code=404,
#                 content={
#                     "status_code": 404, 
#                     "message": "User not found"
#                 }
#             )

#         # Check if master key data exists
#         master_key_fields = [
#             "master_key_verification", 
#             "master_key_salt", 
#             "master_key_iv"
#         ]

#         if not all(field in user for field in master_key_fields):
#             return JSONResponse(
#                 status_code=200,
#                 content={
#                     "status_code": 200,
#                     "data": {
#                         "is_setup": False,
#                         "verification_hash": None,
#                         "salt": None,
#                         "iv": None
#                     }
#                 }
#             )
        
#         return JSONResponse(
#             status_code=200,
#             content={
#                 "status_code": 200,
#                 "is_setup": True,
#                 "verification_hash": user["master_key_verification"],
#                 "salt": user["master_key_salt"],
#                 "iv": user["master_key_iv"]
#             }
#         )

#     except Exception as e:
#         return JSONResponse(
#             status_code=500,
#             content={
#                 "status_code": 500, 
#                 "message": f"Failed to get master key data: {str(e)}"
#             }
#         )


# @router.post('/reset-master-key')
# async def reset_master_key(
#     data: dict, 
#     user_email: str = Depends(get_current_user)
# ):
#     try:
#         # Find user
#         existing_user = collection.find_one({"email": user_email})
        
#         if not existing_user:
#             return JSONResponse(
#                 status_code=404,
#                 content={
#                     "status_code": 404, 
#                     "message": "User not found"
#                 }
#             )
        
#         # Verify OTP
#         otp_from_redis = r.get(user_email)
#         if not otp_from_redis or data.get("otp") != otp_from_redis:
#             return JSONResponse(
#                 status_code=400,
#                 content={
#                     "status_code": 400, 
#                     "message": "Invalid or expired OTP"
#                 }
#             )
        
#         # Check if 2FA is enabled and verify
#         if existing_user.get("is_2FA_Enabled", False):
#             if "_2fa_secret" not in existing_user:
#                 return JSONResponse(
#                     status_code=400,
#                     content={
#                         "status_code": 400, 
#                         "message": "2FA is enabled but not properly configured"
#                     }
#                 )
                
#             totp = pyotp.TOTP(existing_user["_2fa_secret"])
#             if not data.get("twoFactorCode") or not totp.verify(data.get("twoFactorCode")):
#                 return JSONResponse(
#                     status_code=400,
#                     content={
#                         "status_code": 400, 
#                         "message": "Invalid 2FA verification code"
#                     }
#                 )
        
#         # Delete all passwords associated with the user
#         passwords_collection = db["password"]
#         delete_result = passwords_collection.delete_many({"email": str(existing_user["email"])})
        
#         # Remove master key data
#         update_result = collection.update_one(
#             {"email": user_email}, 
#             {"$unset": {
#                 "master_key_verification": "",
#                 "master_key_salt": "",
#                 "master_key_iv": ""
#             }}
#         )
        
#         # Clear Redis OTP
#         r.delete(user_email)
        
#         return JSONResponse(
#             status_code=200,
#             content={
#                 "status_code": 200, 
#                 "message": "Master key reset successful. All passwords have been removed.",
#                 "passwords_deleted": delete_result.deleted_count
#             }
#         )
        
#     except Exception as e:
#         return JSONResponse(
#             status_code=500,
#             content={
#                 "status_code": 500, 
#                 "message": f"Failed to reset master key: {str(e)}"
#             }
#         )