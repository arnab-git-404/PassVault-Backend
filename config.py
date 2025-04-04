from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

DATABASE_URL  = "mongodb://localhost:27017/"

client = MongoClient(DATABASE_URL  , server_api = ServerApi('1') )

db = client.PassVault
collection = db["user"]
collection_password = db["password"]
collection_googleSignIn = db["googleUser"]