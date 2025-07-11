"""
Minimal Flask app to mock some API endpoints.
"""

import logging  # noqa: TID251

from flask import Flask

app = Flask(__name__)

# Set up logging to stdout
logging.basicConfig(level=logging.INFO)


@app.route("/file/<int:size>/download")
def serve_download(size: int) -> bytes:
    return b"A" * size


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=False)
