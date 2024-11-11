from flask import Flask,render_template,jsonify,request,session,redirect
from flask_cors import CORS
from pymongo import MongoClient
import os, sys
import configparser

app = Flask(__name__)
config = configparser.ConfigParser()
config.read(os.path.dirname(os.path.abspath(__file__))+"/cloud-secrets.cfg")
mongo = MongoClient(config["mongodb"]["URI"])
users = mongo["cloud"]["users"]
files = mongo["cloud"]["files"]

