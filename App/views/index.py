from flask import (
    Blueprint,
    redirect,
    render_template,
    request,
    send_from_directory,
    jsonify,
    url_for,
)
from App.controllers import create_user, initialize

index_views = Blueprint("index_views", __name__, template_folder="../templates")


@index_views.route("/", methods=["GET"])
def index_page():
    # return render_template('index.html')
    return redirect(url_for("auth_views.login"))


@index_views.route("/init", methods=["GET"])
def init():
    initialize()
    return jsonify(message="db initialized!")


@index_views.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"})


## ---------------------------------------------------------------------------------
# DO NOT RUN: """Temporary route to seed the database – REMOVE AFTER USE"""
@index_views.route("/run-seed")
def run_seed():
    import subprocess
    import sys

    try:
        # Run seed.py and capture output
        result = subprocess.run(
            [sys.executable, "seed.py"], capture_output=True, text=True, timeout=30
        )
        return f"<pre>STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}</pre>"
    except Exception as e:
        return f"<pre>Error: {str(e)}</pre>"
