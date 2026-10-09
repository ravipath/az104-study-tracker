import os
from datetime import datetime, timezone

from flask import Flask, abort, redirect, render_template, url_for

app = Flask(__name__)

TOPICS = [
    {"id": 1, "name": "Manage Azure identities and governance", "completed": True},
    {"id": 2, "name": "Implement and manage storage", "completed": True},
    {"id": 3, "name": "Deploy and manage Azure compute resources", "completed": False},
    {"id": 4, "name": "Configure and manage virtual networking", "completed": False},
    {"id": 5, "name": "Monitor and maintain Azure resources", "completed": False},
]


@app.context_processor
def inject_settings():
    return {
        "app_message": os.getenv(
            "APP_MESSAGE",
            "Keep learning. Every deployment is practice."
        ),
        "environment": os.getenv("APP_ENV", "local"),
    }


@app.route("/")
def index():
    completed = sum(topic["completed"] for topic in TOPICS)
    total = len(TOPICS)
    progress = round(completed / total * 100) if total else 0

    return render_template(
        "index.html",
        topics=TOPICS,
        completed=completed,
        total=total,
        progress=progress,
    )


@app.route("/toggle/<int:topic_id>", methods=["POST"])
def toggle_topic(topic_id):
    topic = next((t for t in TOPICS if t["id"] == topic_id), None)

    if topic is None:
        abort(404)

    topic["completed"] = not topic["completed"]
    return redirect(url_for("index"))


@app.route("/health")
def health():
    return {
        "status": "healthy",
        "app": "az104-study-tracker",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, 200


if __name__ == "__main__":
    # Local development only. Azure uses its production web server.
    app.run(host="127.0.0.1", port=5000, debug=True)