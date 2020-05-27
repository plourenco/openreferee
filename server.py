# run it like this:
# FLASK_ENV=development FLASK_DEBUG=1 FLASK_APP=testsvc.py flask run -p 12345

from functools import wraps

import requests
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from webargs import fields
from webargs.flaskparser import use_kwargs
from werkzeug.exceptions import (
    Conflict,
    HTTPException,
    NotFound,
    Unauthorized,
    UnprocessableEntity,
)


SERVICE_INFO = {"version": "0.1-dev", "name": "Test Service"}
DEFAULT_TAGS = {
    "ERR_WRONG_TITLE": {"title": "Wrong Title", "color": "red", "system": True},
    "ERR_SILLY_TITLE": {"title": "Silly Title", "color": "orange", "system": True},
    "OK_TITLE": {"title": "Title OK", "color": "green", "system": True},
}
DEFAULT_EDITABLES = {"paper", "poster"}
DEFAULT_FILE_TYPES = {
    "paper": [
        {
            "name": "PDF",
            "extensions": ["pdf"],
            "allow_multiple_files": False,
            "required": True,
            "publishable": True,
            "filename_template": "{code}_paper",
        },
        {
            "name": "Source Files",
            "extensions": ["tex", "doc"],
            "allow_multiple_files": True,
            "required": True,
            "publishable": False,
        },
    ],
    "poster": [
        {
            "name": "PDF",
            "extensions": ["pdf"],
            "allow_multiple_files": False,
            "required": True,
            "publishable": True,
            "filename_template": "{code}_poster",
        },
        {
            "name": "Source Files",
            "extensions": ["ai", "svg"],
            "allow_multiple_files": False,
            "required": True,
            "publishable": False,
        },
    ],
}

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql:///editingsvc"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
db.Model.metadata.naming_convention = {
    "fk": "fk_%(table_name)s_%(column_names)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
    "ix": "ix_%(unique_index)s%(table_name)s_%(column_names)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "uq": "uq_%(table_name)s_%(column_names)s",
    "column_names": lambda constraint, table: "_".join(
        (c if isinstance(c, basestring) else c.name) for c in constraint.columns
    ),
    "unique_index": lambda constraint, table: "uq_" if constraint.unique else "",
}


class Event(db.Model):
    __tablename__ = "events"
    identifier = db.Column(db.String, primary_key=True)
    title = db.Column(db.String, nullable=False)
    url = db.Column(db.String, nullable=False)
    token = db.Column(db.String, nullable=False)
    config_endpoints = db.Column(db.JSON, nullable=False)


db.create_all()


def setup_requests_session(token):
    session = requests.Session()
    session.headers = {"Authorization": "Bearer {}".format(token)}
    # XXX: Remove this
    session.verify = False
    return session


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


def require_event_token(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        identifier = kwargs.pop("identifier")
        event = Event.query.get(identifier)
        if event is None:
            raise NotFound("Unknown event")
        auth = request.headers.get("Authorization")
        token = None
        if auth and auth.startswith("Bearer "):
            token = auth[7:]
        if not token:
            raise Unauthorized("Token missing")
        elif token != event.token:
            raise Unauthorized("Invalid token")
        return fn(*args, event=event, **kwargs)

    return wrapper


@app.route("/info")
def info():
    return jsonify(SERVICE_INFO)


def get_event_tags(session, event):
    tag_endpoint = event.config_endpoints["tags"]["list"]

    app.logger.info("Fetching available tags...")
    response = session.get(tag_endpoint)
    response.raise_for_status()
    return {t["code"]: t for t in response.json()}


def setup_event_tags(session, event):
    tag_endpoint = event.config_endpoints["tags"]["create"]
    available_tags = get_event_tags(session, event)

    app.logger.info("Adding missing tags...")
    for code, data in DEFAULT_TAGS.viewitems():
        if code in available_tags:
            # tag already available in Indico event
            continue
        response = session.post(tag_endpoint, json=dict(data, code=code))
        response.raise_for_status()
        app.logger.info("Added '{}'...".format(code))


def cleanup_event_tags(session, event):
    available_tags = get_event_tags(session, event)
    for tag_name in DEFAULT_TAGS:
        if tag_name not in available_tags:
            continue
        tag = available_tags[tag_name]
        if not tag["is_used_in_revision"]:
            # delete tag, as it's unused
            response = session.delete(tag["url"])
            response.raise_for_status()
            app.logger.info("Deleted tag '{}'".format(tag["title"]))


def get_file_types(session, event, editable):
    endpoint = event.config_endpoints["file_types"][editable]["list"]
    app.logger.info("Fetching available file types ({})...".format(editable))
    response = session.get(endpoint)
    response.raise_for_status()
    return {t["name"]: t for t in response.json()}


def setup_file_types(session, event):
    for editable in DEFAULT_EDITABLES:
        available_file_types = get_file_types(session, event, editable)
        for type_data in DEFAULT_FILE_TYPES[editable]:
            if type_data["name"] in available_file_types:
                continue
            endpoint = event.config_endpoints["file_types"][editable]["create"]
            response = session.post(endpoint, json=type_data)
            response.raise_for_status()
            app.logger.info("Added '{}' to '{}'".format(type_data["name"], type_data))


def cleanup_file_types(session, event):
    for editable in DEFAULT_EDITABLES:
        available_types = get_file_types(session, event, editable)
        for ftype in DEFAULT_FILE_TYPES[editable]:
            server_type = available_types[ftype["name"]]
            if not server_type["is_used_in_condition"] and not server_type["is_used"]:
                response = session.delete(server_type["url"])
                response.raise_for_status()
                app.logger.info("Deleted file type '{}'".format(server_type["name"]))


def cleanup_event(event):
    session = setup_requests_session(event.token)
    cleanup_event_tags(session, event)
    cleanup_file_types(session, event)


@app.route("/event/<identifier>", methods=("PUT",))
@use_kwargs(
    {
        "title": fields.String(required=True),
        "url": fields.URL(schemes={"http", "https"}, required=True),
        "token": fields.String(required=True),
        "config_endpoints": fields.Nested(
            {
                "tags": fields.Nested(
                    {
                        "create": fields.String(required=True),
                        "list": fields.String(required=True),
                    }
                ),
                "editable_types": fields.String(required=True),
                "file_types": fields.Dict(
                    keys=fields.String(),
                    values=fields.Nested(
                        {
                            "create": fields.String(required=True),
                            "list": fields.String(required=True),
                        }
                    ),
                    required=True,
                ),
            },
            required=True,
        ),
    }
)
def create_event(identifier, title, url, token, config_endpoints):
    event = Event(
        identifier=identifier,
        title=title,
        url=url,
        token=token,
        config_endpoints=config_endpoints,
    )
    db.session.add(event)
    try:
        db.session.flush()
    except IntegrityError:
        raise Conflict("Event already exists")
    app.logger.info("Registered event %r", event)

    session = setup_requests_session(token)
    setup_event_tags(session, event)

    response = session.post(
        config_endpoints["editable_types"],
        json={"editable_types": list(DEFAULT_EDITABLES)},
    )
    response.raise_for_status()

    setup_file_types(session, event)

    db.session.commit()
    return "", 201


@app.route("/event/<identifier>", methods=("DELETE",))
@require_event_token
def remove_event(event):
    cleanup_event(event)
    db.session.delete(event)
    db.session.commit()
    app.logger.info("Unregistered event %r", event)
    return "", 204


@app.route("/event/<identifier>")
@require_event_token
def get_event_info(event):
    return jsonify(
        service=SERVICE_INFO, title=event.title, url=event.url, can_disconnect=True
    )
