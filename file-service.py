from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import pymongo
import configparser
import requests
from pymongo import MongoClient
import datetime

app = Flask(__name__)

config = configparser.ConfigParser()
config.read(os.path.dirname(os.path.abspath(__file__))+"/cloud-secrets.cfg")
try:
    mongo = MongoClient(config["mongodb"]["URI"])
    files = mongo["cloud"]["files"]
    app.secret_key = config["mongodb"]["URI"]
    print(f"Connected to MongoDB successfully")
except Exception as error:
    print(f"Error connecting to MongoDB:\n {error}")

@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        file_name = request.form["fileName"]
        info = request.form["info"]
        access = request.form["access"]
        action = request.form["action"]
        request_access = request.form.get("requestAccess") == "on"
        passkey = request.form.get("passkey") if access == "private" else None
        file = request.files["file"]

        if not file_name or not file:
            return jsonify({"success": False, "error": "File name and file are required."}), 400

        project_root = os.path.dirname(os.path.abspath(__file__))
        upload_dir = os.path.join(project_root, "static", "uploads")
        
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)

        file_path = os.path.join(upload_dir, file_name)
        file.save(file_path)

        relative_file_path = f"/static/uploads/{file_name}"

        file_data = {
            "username": request.form["username"],  
            "fileName": file_name,
            "filePath": relative_file_path,
            "info": info,
            "access": access,
            "action": action,
            "requestAccess": request_access,
            "passkey": passkey,
            "uploadedAt": datetime.datetime.now(),
            "accessList": [request.form["username"]]
        }

        files.insert_one(file_data)

        return jsonify({"success": True, "message": "File uploaded successfully."})

    except Exception as error:
        return jsonify({"success": False, "error": str(error)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
