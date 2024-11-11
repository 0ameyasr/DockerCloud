from flask import Flask, render_template, jsonify, request, session, redirect
from flask_cors import CORS
from pymongo import MongoClient
import os, sys
import configparser
import datetime
from bson import ObjectId


app = Flask(__name__)
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
            "accessList": file.get("accessList", [])
        } 
        for file in public_files
    ]
    
    if session["user"]:
        messages = list(mongo["cloud"]["messages"].find({
            "$or": [
                {"from": session["user"]},
                {"to": session["user"]}
            ]
        }).sort("sent", -1))

        for message in messages:
            message["_id"] = str(message["_id"])
            message["sent"] = message["sent"].strftime("%Y-%m-%d %H:%M:%S")
            
        session["messages"] = messages

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
            } 
            for file in resources
        ]
    else:
        session["messages"] = []
    
    return render_template("ui.html")


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

@app.route("/upload", methods=["POST"])
def upload_file():
    if "user" not in session or not session["user"]:
        return jsonify({"success": False, "error": "User not logged in."}), 401

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
            "username": session["user"],
            "fileName": file_name,
            "filePath": relative_file_path,
            "info": info,
            "access": access,
            "action": action,
            "requestAccess": request_access,
            "passkey": passkey,
            "uploadedAt": datetime.datetime.now(),
            "accessList": [session["user"]]
        }

        files.insert_one(file_data)

        return jsonify({"success": True, "message": "File uploaded successfully."})
    except Exception as error:
        return jsonify({"success": False, "error": str(error)})

@app.route("/send_request", methods=["POST"])
def send_request():
    if "user" not in session or not session["user"]:
        return jsonify({"success": False, "error": "User not logged in."}), 401
    
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
            "from": session["user"],
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
    if "user" not in session or not session["user"]:
        return jsonify({"success": False, "error": "User not logged in."}), 401
    
    try:
        messages = list(mongo["cloud"]["messages"].find({
            "$or": [
                {"from": session["user"]},
                {"to": session["user"]}
            ]
        }).sort("sent", -1))  
        
        for message in messages:
            message["_id"] = str(message["_id"])
            message["sent"] = message["sent"].strftime("%Y-%m-%d %H:%M:%S")
            
        return jsonify({"success": True, "messages": messages})
    except Exception as error:
        return jsonify({"success": False, "error": str(error)})

@app.route("/handle_access", methods=["POST"])
def handle_access():
    if "user" not in session or not session["user"]:
        return jsonify({"success": False, "error": "User not logged in."}), 401
    
    try:
        data = request.json
        message_id = data.get("messageId")
        action = data.get("action")
        file_name = data.get("file")
        requester = data.get("requester")
        
        mongo["cloud"]["messages"].update_one(
            {"_id": ObjectId(message_id)},
            {
                "$set": {
                    "processed": True,
                    "status": "granted" if action == "grant" else "denied"
                }
            }
        )
        
        if action == "grant":
            mongo["cloud"]["files"].update_one(
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
    
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(port=5050, debug=True)
