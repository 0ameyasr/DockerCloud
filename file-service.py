from flask import Flask,render_template,jsonify
from flask_cors import CORS
import os, sys
import pymongo,requests
import configparser
from pymongo import MongoClient

app = Flask(__name__)

config = configparser.ConfigParser()
config.read(os.path.dirname(os.path.abspath(__file__))+"/cloud-secrets.cfg")
try:
    mongo = MongoClient(config["mongodb"]["URI"])
    users = mongo["cloud"]["users"]
    files = mongo["cloud"]["files"]
    app.secret_key = config["mongodb"]["URI"]
    print(f"Connected to MongoDB successfully")
except Exception as error:
    print(f"Error connecting to MongoDB:\n {error}")

@app.route("/upload/<file>")
def upload(file):
    try:
        files.insert_one({
            "name": file["name"],
            "content": file["content"],
            "info": file["info"],
            "access": file["access"],
            "req": file["request"],
            "actions": file["actions"]
        })
        return jsonify({
            "success":"True"
        })
    except Exception as error:
        return jsonify({
            "success":"False",
            "error":str(error),
        })

if __name__ == "__main__":
    app.run(host="0.0.0.0",port=5001,debug=True)