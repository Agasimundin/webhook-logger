from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)

# Connect to MongoDB (local)
client = MongoClient("mongodb://localhost:27017/")
db = client['webhookDB']
collection = db['events']

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        event_type = request.headers.get('X-GitHub-Event')

        print("✅ Received event:", event_type)
        print("📦 Payload:", data)

        if event_type == "push":
            author = data['pusher']['name']
            to_branch = data['ref'].split('/')[-1]
            timestamp = datetime.utcnow().isoformat()

            collection.insert_one({
                "author": author,
                "action": "push",
                "from_branch": None,
                "to_branch": to_branch,
                "timestamp": timestamp
            })

        elif event_type == "pull_request":
            action = data['action']
            pr = data['pull_request']

            author = pr['user']['login']
            from_branch = pr['head']['ref']
            to_branch = pr['base']['ref']
            timestamp = datetime.utcnow().isoformat()

            if action == "opened":
                collection.insert_one({
                    "author": author,
                    "action": "pull_request",
                    "from_branch": from_branch,
                    "to_branch": to_branch,
                    "timestamp": timestamp
                })

            elif action == "closed" and pr.get("merged"):
                collection.insert_one({
                    "author": author,
                    "action": "merge",
                    "from_branch": from_branch,
                    "to_branch": to_branch,
                    "timestamp": timestamp
                })

        return '', 204

    except Exception as e:
        print("❌ Error:", str(e))
        return 'Error processing webhook', 500

@app.route('/get-logs', methods=['GET'])
def get_logs():
    logs = list(collection.find({}, {'_id': 0}))
    return jsonify(logs)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(port=5000)
