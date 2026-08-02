from flask import Flask
from flask_cors import CORS

from frame_routes import frame_bp   # Week 5 — dummy /api/frame/analyze
from pose_routes import pose_bp     # Week 6 — real /pose/detect (MediaPipe)

app = Flask(__name__)
CORS(app)

app.register_blueprint(frame_bp)
app.register_blueprint(pose_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
