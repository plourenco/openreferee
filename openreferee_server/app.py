from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException, UnprocessableEntity


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql:///editingsvc"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    return app


app = create_app()


@app.errorhandler(UnprocessableEntity)
def handle_unprocessableentity(exc):
    data = getattr(exc, "data", None)
    if data and "messages" in data:
        # this error came from a webargs parsing failure
        response = jsonify(webargs_errors=data["messages"])
        response.status_code = exc.code
        return response
    if exc.response:
        return exc
    return "Unprocessable Entity"


@app.errorhandler(HTTPException)
def _handle_http_exception(exc):
    return jsonify(error=exc.description), exc.code


@app.errorhandler(Exception)
def _handle_exception(exc):
    app.logger.exception("Request failed")
    return jsonify(error="Internal error"), 500
