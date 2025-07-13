# ─────────────────────────────────────────────────────────────
#  app.py  – GitHub Webhook Receiver  (IST timestamp version)
# ─────────────────────────────────────────────────────────────
from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime
from pytz import timezone
import logging
import os

app = Flask(__name__)

# ─────────────────────────────────────────────────────────────
# MongoDB connection
# ─────────────────────────────────────────────────────────────
MONGO_URI  = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client     = MongoClient(MONGO_URI)
db         = client["webhookDB"]
collection = db["events"]

# ─────────────────────────────────────────────────────────────
# Helper: formatted IST timestamp  →  "13 July 2025 - 02:45 PM IST"
# ─────────────────────────────────────────────────────────────
def ist_timestamp() -> str:
    ist = timezone('Asia/Kolkata')
    dt  = datetime.now(ist)
    # day with suffix (1st, 2nd, 3rd, 4th…)
    day = dt.day
    suffix = "th" if 11 <= day <= 13 else {1:"st",2:"nd",3:"rd"}.get(day % 10, "th")
    return dt.strftime(f"%-d{suffix} %B %Y - %I:%M %p IST")

# ─────────────────────────────────────────────────────────────
# Webhook route
# ─────────────────────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data       = request.json
        event_type = request.headers.get("X-GitHub-Event")
        app.logger.info("📥 %s", event_type)

        # ------------------ PUSH ------------------------------------------
        if event_type == "push":
            doc = {
                "request_id": data["after"],                  # commit SHA
                "author":      data["pusher"]["name"],
                "action":      "push",
                "from_branch": None,
                "to_branch":   data["ref"].split("/")[-1],
                "timestamp":   ist_timestamp()
            }
            collection.insert_one(doc)

        # ------------------ PULL REQUEST / MERGE -------------------------
        elif event_type == "pull_request":
            pr            = data["pull_request"]
            action        = data["action"]
            common = {
                "request_id": str(pr["id"]),
                "from_branch": pr["head"]["ref"],
                "to_branch":   pr["base"]["ref"],
                "timestamp":   ist_timestamp()
            }

            # PR opened
            if action == "opened":
                collection.insert_one({
                    **common,
                    "author": pr["user"]["login"],
                    "action": "pull_request"
                })

            # PR merged
            elif action == "closed" and pr.get("merged"):
                collection.insert_one({
                    **common,
                    "author": pr["merged_by"]["login"],
                    "action": "merge"
                })

        return ("", 204)     # tell GitHub all good

    except Exception:
        app.logger.exception("Webhook processing error")
        return ("Error", 500)

# ─────────────────────────────────────────────────────────────
# REST endpoint for UI
# ─────────────────────────────────────────────────────────────
@app.route("/get-logs")
def get_logs():
    docs = list(collection.find({}, {"_id": 0}).sort("timestamp", -1))
    return jsonify(docs)

# ─────────────────────────────────────────────────────────────
# Front‑end
# ─────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    app.run(port=5000, debug=True)
