from flask import Flask, jsonify, request
from flask_cors import CORS
import pymongo
import configparser
from pymongo import MongoClient
from bson import ObjectId
import os

app = Flask(__name__)

config = configparser.ConfigParser()
config.read(os.path.dirname(os.path.abspath(__file__))+"/cloud-secrets.cfg")
try:
    mongo = MongoClient(config["mongodb"]["URI"])
    files = mongo["cloud"]["files"]
    messages = mongo["cloud"]["messages"]
    app.secret_key = config["mongodb"]["URI"]
    print(f"Connected to MongoDB successfully")
except Exception as error:
    print(f"Error connecting to MongoDB:\n {error}")

@app.route("/handle_access", methods=["POST"])
def handle_access():
    try:
        data = request.json
        message_id = data.get("messageId")
        action = data.get("action")
        file_name = data.get("file")
        requester = data.get("requester")
        
        messages.update_one(
            {"_id": ObjectId(message_id)},
            {
                "$set": {
                    "processed": True,
                    "status": "granted" if action == "grant" else "denied"
                }
            }
        )
        
        if action == "grant":
            files.update_one(
                {"fileName": file_name},
                {
                    "$addToSet": {"accessList": requester}
                }
            )
        
        return jsonify({
            "success": True,
            "message": f"Access {action}ed successfully"
        })
    
    except Exception as error:
        return jsonify({"success": False, "error": str(error)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)
