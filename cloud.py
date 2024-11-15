from flask import Flask, render_template, jsonify, request, session, redirect, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
import os
import configparser
import datetime
import requests
from bson import ObjectId

app = Flask(__name__)
CORS(app)
config = configparser.ConfigParser()
config.read(os.path.dirname(os.path.abspath(__file__))+"/cloud-secrets.cfg")

try:
    mongo = MongoClient(config["mongodb"]["URI"])
    users = mongo["cloud"]["users"]
    files = mongo["cloud"]["files"]
    app.secret_key = config["app"]["SECRET_KEY"]
    print("Connected to MongoDB successfully")
except Exception as error:
    print(f"Error connecting to MongoDB:\n {error}")

FILE_SERVICE_URL = "http://file-service:5001"
MESSAGE_SERVICE_URL = "http://message-service:5002"
SECURITY_SERVICE_URL = "http://security-service:5003"
UPLOAD_FOLDER = "/app/static/uploads"

@app.route("/uploads/<path:filename>")
def serve_file(filename):
    """Proxy route to serve files from the upload directory"""
    try:
        response = requests.get(f"{FILE_SERVICE_URL}/uploads/{filename}")
        if response.status_code == 200:
            return response.content, 200, {'Content-Type': response.headers['Content-Type']}
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/")
def home():
    if "user" not in session:
        session["user"] = None
        session["login"] = False 

    public_files = files.find({"access": "public"})
    session["files"] = [
        {
            **file,
            "_id": str(file["_id"]),
            "accessList": file.get("accessList", []),
            "fileUrl": f"/uploads/{os.path.basename(file['filePath'])}" if 'filePath' in file else None
        } 
        for file in public_files
    ]
    
    if session["user"]:
        response = requests.get(
            f"{MESSAGE_SERVICE_URL}/get_messages",
            params={"user": session["user"]}
        )
        if response.status_code == 200:
            session["messages"] = response.json().get("messages", [])
        else:
            session["messages"] = []

        resources = files.find({
            "$or": [
                {"username": session["user"]},
                {"accessList": {"$regex": session["user"], "$options": "i"}}
            ]
        })
        session["resources"] = [
            {
                **file,
                "_id": str(file["_id"]),
                "fileUrl": f"/uploads/{os.path.basename(file['filePath'])}" if 'filePath' in file else None
            } 
            for file in resources
        ]
    else:
        session["messages"] = []
    
    return render_template("ui.html")

@app.route("/upload", methods=["POST"])
def upload_file():
    if "user" not in session or not session["user"]:
        return jsonify({"success": False, "error": "User not logged in."}), 401

    try:
        files = {
            'file': (request.files['file'].filename, request.files['file'])
        }
        data = {
            **request.form,
            'username': session['user']
        }
        
        response = requests.post(
            f"{FILE_SERVICE_URL}/upload",
            files=files,
            data=data
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                result['fileUrl'] = f"/uploads/{os.path.basename(result.get('filePath', ''))}"
            return jsonify(result), 200
        return jsonify(response.json()), response.status_code
    except Exception as error:
        return jsonify({"success": False, "error": str(error)})

@app.route("/login", methods=["POST"])
def login():
    try:
        user = request.form["username"]
        password = request.form["password"]
        existing_user = users.find_one({"username": user})

        if existing_user and existing_user["password"] == password:
            session["user"] = user
            session["login"] = True
            return jsonify({"success": True})
        elif existing_user and existing_user["password"] != password:
            return jsonify({"success": False, "error": "Incorrect password."})
        else:
            users.insert_one({"username": user, "password": password})
            session["user"] = user
            session["login"] = True
            return jsonify({"success": True})
    except Exception as error:
        return jsonify({"success": False, "error": str(error)})


@app.route("/send_request", methods=["POST"])
def send_request():
    if "user" not in session or not session["user"]:
        return jsonify({"success": False, "error": "User not logged in."}), 401
    
    try:
        data = {
            **request.form,
            'username': session['user']
        }
        
        response = requests.post(
            f"{MESSAGE_SERVICE_URL}/send_request",
            data=data
        )
        
        return jsonify(response.json()), response.status_code
    except Exception as error:
        return jsonify({"success": False, "error": str(error)})

@app.route("/get_messages", methods=["GET"])
def get_messages():
    if "user" not in session or not session["user"]:
        return jsonify({"success": False, "error": "User not logged in."}), 401
    
    try:
        response = requests.get(
            f"{MESSAGE_SERVICE_URL}/get_messages",
            params={"user": session["user"]}
        )
        
        return jsonify(response.json()), response.status_code
    except Exception as error:
        return jsonify({"success": False, "error": str(error)})

@app.route("/handle_access", methods=["POST"])
def handle_access():
    if "user" not in session or not session["user"]:
        return jsonify({"success": False, "error": "User not logged in."}), 401
    
    try:
        response = requests.post(
            f"{SECURITY_SERVICE_URL}/handle_access",
            json=request.json
        )
        
        return jsonify(response.json()), response.status_code
    except Exception as error:
        return jsonify({"success": False, "error": str(error)})
    
@app.route("/delete_file", methods=["POST"])
def delete_file():
    if "user" not in session or not session["user"]:
        return jsonify({"success": False, "error": "User not logged in."}), 401
    
    try:
        file_path = request.json.get("filePath")
        if not file_path:
            return jsonify({"success": False, "error": "File path is required."}), 400

        response = requests.post(
            f"{FILE_SERVICE_URL}/delete",
            json={"filePath": file_path}
        )

        return jsonify(response.json()), response.status_code

    except Exception as error:
        return jsonify({"success": False, "error": str(error)})


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/debug/files")
def debug_files():
    """Debug route to check file paths and URLs"""
    try:
        all_files = files.find({})
        debug_info = [{
            "id": str(f["_id"]),
            "originalFileName": f.get("originalFileName"),
            "storedPath": f.get("filePath"),
            "fileUrl": f"/uploads/{os.path.basename(f['filePath'])}" if 'filePath' in f else None,
            "access": f.get("access")
        } for f in all_files]
        return jsonify({"files": debug_info})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
if __name__ == "__main__":
    app.run(host="0.0.0.0",port=5050, debug=True)