from pymongo import MongoClient
import json

client = MongoClient("mongodb://localhost:27017")
db = client["RERA-DETAILS"]
coll = db["DETAILS"]

doc = coll.find_one({"report_id": "138ba78eee47075873f2558b"})
print(json.dumps(doc, indent=2, default=str))
