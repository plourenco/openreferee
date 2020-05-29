# run it like this:
# FLASK_ENV=development FLASK_DEBUG=1 FLASK_APP=testsvc.py flask run -p 12345

from functools import wraps

from flask import jsonify, request
from sqlalchemy.exc import IntegrityError
from webargs import fields
from webargs.flaskparser import use_kwargs
from werkzeug.exceptions import Conflict, NotFound, Unauthorized

from .app import app
from .db import db
from .defaults import DEFAULT_EDITABLES, SERVICE_INFO
from .models import Event
from .operations import (
    cleanup_event,
    setup_event_tags,
    setup_file_types,
    setup_requests_session,
)


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
