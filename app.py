from flask import Flask
from flask_cors import CORS

from user_api import user_api
from scan_api import scan_api
from qr_api import qr_api
from model_api import model_api
from stats_api import stats_api

app = Flask(__name__)
CORS(app)

# Blueprint 등록
app.register_blueprint(user_api)
app.register_blueprint(scan_api)
app.register_blueprint(qr_api)
app.register_blueprint(model_api)
app.register_blueprint(stats_api)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)