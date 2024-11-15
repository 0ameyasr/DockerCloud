from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import pymongo
import configparser
import requests
from pymongo import MongoClient
import datetime
import uuid

app = Flask(__name__)
CORS(app)  

config = configparser.ConfigParser()
config.read(os.path.dirname(os.path.abspath(__file__))+"/cloud-secrets.cfg")
try:
    mongo = MongoClient(config["mongodb"]["URI"])
    files = mongo["cloud"]["files"]
    app.secret_key = config["mongodb"]["URI"]
    print(f"Connected to MongoDB successfully")
except Exception as error:
    print(f"Error connecting to MongoDB:\n {error}")

UPLOAD_FOLDER = "/app/static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/uploads/<path:filename>")
def serve_file(filename):
    try:
        return send_from_directory(UPLOAD_FOLDER, filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 404

@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        original_file_name = request.form["fileName"]
        info = request.form["info"]
        access = request.form["access"]
        action = request.form["action"]
        request_access = request.form.get("requestAccess") == "on"
        passkey = request.form.get("passkey") if access == "private" else None
        file = request.files["file"]

        if not original_file_name or not file:
            return jsonify({"success": False, "error": "File name and file are required."}), 400

        unique_id = str(uuid.uuid4())
        file_name = f"{unique_id}_{original_file_name}"

        file_path = os.path.join(UPLOAD_FOLDER, file_name)
        file.save(file_path)

        relative_url_path = f"/uploads/{file_name}"

        file_data = {
            "username": request.form["username"],
            "originalFileName": original_file_name,
            "fileName": file_name,
            "filePath": relative_url_path,
            "info": info,
            "access": access,
            "action": action,
            "requestAccess": request_access,
            "passkey": passkey,
            "uploadedAt": datetime.datetime.now(),
            "accessList": [request.form["username"]]
        }

        files.insert_one(file_data)
        return jsonify({
            "success": True, 
            "message": "File uploaded successfully.",
            "filePath": relative_url_path
        })

    except Exception as error:
        return jsonify({"success": False, "error": str(error)})

@app.route("/delete", methods=["POST"])
def delete_file():
    try:
        file_path = request.json.get("filePath")
        if not file_path:
            return jsonify({"success": False, "error": "File path is required."}), 400

        filename = os.path.basename(file_path)
        absolute_file_path = os.path.join(UPLOAD_FOLDER, filename)

        if os.path.exists(absolute_file_path):
            os.remove(absolute_file_path)
        else:
            return jsonify({"success": False, "error": "File not found on server."}), 404

        files.delete_one({"filePath": file_path})
        return jsonify({"success": True, "message": "File deleted successfully."})

    except Exception as error:
        return jsonify({"success": False, "error": str(error)})

@app.route("/debug/uploads")
def list_uploads():
    try:
        files_list = os.listdir(UPLOAD_FOLDER)
        return jsonify({
            "files": files_list,
            "upload_folder": UPLOAD_FOLDER,
            "file_count": len(files_list)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)