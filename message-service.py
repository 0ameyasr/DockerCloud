from flask import Flask, jsonify, request
from flask_cors import CORS
import pymongo
import configparser
import requests
from pymongo import MongoClient
import datetime
import os

app = Flask(__name__)

config = configparser.ConfigParser()
config.read(os.path.dirname(os.path.abspath(__file__))+"/cloud-secrets.cfg")
try:
    mongo = MongoClient(config["mongodb"]["URI"])
    messages = mongo["cloud"]["messages"]
    app.secret_key = config["mongodb"]["URI"]
    print(f"Connected to MongoDB successfully")
except Exception as error:
    print(f"Error connecting to MongoDB:\n {error}")

@app.route("/send_request", methods=["POST"])
def send_request():
    try:
        recipient = request.form["recipient"]
        reason = request.form["content"]
        file_name = request.form["fileName"]
        
        if len(reason) < 20:
            return jsonify({
                "success": False, 
                "error": "Reason must be at least 20 characters long."
            }), 400
        
        message_data = {
            "from": request.form["username"], 
            "to": recipient,
            "reason": reason,
            "file": file_name,
            "sent": datetime.datetime.now()
        }
        
        mongo["cloud"]["messages"].insert_one(message_data)
        
        return jsonify({"success": True, "message": "Request sent successfully."})
    
    except Exception as error:
        return jsonify({"success": False, "error": str(error)})

@app.route("/get_messages", methods=["GET"])
def get_messages():
    try:
        user = request.args.get("user")
        
        messages_list = list(mongo["cloud"]["messages"].find({
            "$or": [
                {"from": user},
                {"to": user}
            ]
        }).sort("sent", -1))
        
        for message in messages_list:
            message["_id"] = str(message["_id"])
            message["sent"] = message["sent"].strftime("%Y-%m-%d %H:%M:%S")
        
        return jsonify({"success": True, "messages": messages_list})
    
    except Exception as error:
        return jsonify({"success": False, "error": str(error)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
