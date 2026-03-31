from flask import jsonify

def error(msg, status=400, **extra):
    data = {"error": msg}
    data.update(extra)
    return jsonify(data), status

def success(data=None, status=200, **extra):
    payload = data or {}
    payload.update(extra)
    return jsonify(payload), status
