from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv
from flask import send_from_directory

load_dotenv()

app = Flask(__name__)
CORS(app)

client = MongoClient(os.getenv("MONGO_URI"))
db = client['webhook_db']
collection = db['events']

@app.route('/webhook', methods=['POST'])
def webhook():
    event = request.headers.get('X-GitHub-Event')
    payload = request.json

    # Parse event type and map to schema
    doc = {}
    if event == "push":
        doc = {
            "request_id": payload['after'],
            "author": payload['pusher']['name'],
            "action": "PUSH",
            "from_branch": None,
            "to_branch": payload['ref'].split('/')[-1],
            "timestamp": datetime.utcnow().isoformat()
        }
    elif event == "pull_request":
        action = payload['action']
        if action in ["opened", "closed"]:
            doc = {
                "request_id": str(payload['pull_request']['id']),
                "author": payload['pull_request']['user']['login'],
                "action": "PULL_REQUEST" if action == "opened" else "MERGE",
                "from_branch": payload['pull_request']['head']['ref'],
                "to_branch": payload['pull_request']['base']['ref'],
                "timestamp": payload['pull_request']['created_at'] if action == "opened" else payload['pull_request']['merged_at']
            }
    if doc:
        collection.insert_one(doc)
    return '', 204

@app.route('/events', methods=['GET'])
def get_events():
    events = list(collection.find({}, {'_id': 0}).sort('timestamp', -1).limit(20))
    return jsonify(events)

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

if __name__ == '__main__':
    app.run(port=5000)