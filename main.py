from fastapi import FastAPI
from routers import api_router  
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://pass-vault-frontend.vercel.app",
                   "https://passvault-f36db.firebaseapp.com", 
                   "https://passvault-f36db.web.app"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Welcome to The PassVault Backend Server"}
