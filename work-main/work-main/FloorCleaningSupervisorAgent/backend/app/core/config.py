from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DATABASE = os.getenv("MONGO_DATABASE")
print("MONGO_URI =", MONGO_URI)
print("MONGO_DATABASE =", MONGO_DATABASE)