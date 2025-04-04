from fastapi import FastAPI, APIRouter
from .user import router as UserRouter
from .userPassword import router as PassRoute
from .googleUser import router as GoogleUserRouter


api_router = APIRouter()

api_router.include_router(
    UserRouter, 
    prefix="/user", 
    tags=["User"]
)

api_router.include_router(
    PassRoute,
    prefix="/password",
    tags=["Password"]
)

api_router.include_router(
    GoogleUserRouter,
    prefix="/google",
    tags=["Google"]
)
