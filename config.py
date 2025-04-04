from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

DATABASE_URL  = "mongodb+srv://arnab:anik@cluster0.ccmsv.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

client = MongoClient(DATABASE_URL  , server_api = ServerApi('1') )

db = client.PassVault
collection = db["user"]
collection_password = db["password"]
collection_googleSignIn = db["googleUser"]
