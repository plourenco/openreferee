from functools import wraps

import click
from flask import json as _json
from flask import jsonify, request
from sqlalchemy.exc import IntegrityError
from webargs.flaskparser import use_kwargs
from werkzeug.exceptions import Conflict, NotFound, Unauthorized

from .app import app, register_spec
from .db import db
from .defaults import DEFAULT_EDITABLES, SERVICE_INFO
from .models import Event
from .operations import (
    cleanup_event,
    setup_event_tags,
    setup_file_types,
    setup_requests_session,
)
from .schemas import EventInfoSchema, EventSchema


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
    """Get service info
    ---
    get:
      description: Get service info
      operationId: getServiceInfo
      tags: ["service", "information"]
      responses:
        200:
          description: Service Info
          content:
            application/json:
              schema: ServiceInfoSchema

    """
    return jsonify(SERVICE_INFO)


@app.route("/event/<identifier>", methods=("PUT",))
@use_kwargs(EventSchema, location="json")
def create_event(identifier, title, url, token, config_endpoints):
    """Create an Event.
    ---
    put:
      description: Create an Event
      operationId: createEvent
      tags: ["event", "create"]
      requestBody:
        content:
          application/json:
            schema: EventSchema
      parameters:
        - in: path
          schema: IdentifierParameter
      responses:
        201:
          description: Event Created
          content:
            application/json:
              schema: SuccessSchema
    """
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
    return jsonify({"success": True}), 201


@app.route("/event/<identifier>", methods=("DELETE",))
@require_event_token
def remove_event(event):
    """Remove an Event.
    ---
    delete:
      description: Remove an Event
      operationId: removeEvent
      tags: ["event", "remove"]
      security:
        - bearer_token: []
      parameters:
        - in: path
          schema: IdentifierParameter
      responses:
        204:
          description: Event Removed
          content:
            application/json:
              schema: SuccessSchema
    """
    cleanup_event(event)
    db.session.delete(event)
    db.session.commit()
    app.logger.info("Unregistered event %r", event)
    return jsonify({"success": True}), 204


@app.route("/event/<identifier>")
@require_event_token
def get_event_info(event):
    """Get information about an event
    ---
    get:
      description: Get information about an event
      operationId: getEvent
      tags: ["event", "get"]
      security:
        - bearer_token: []
      parameters:
        - in: path
          schema: IdentifierParameter
      responses:
        200:
          description: Event Info
          content:
            application/json:
              schema: EventInfoSchema
    """
    return EventInfoSchema().dump(event)


@app.cli.command("openapi")
@click.option(
    "--json", is_flag=True,
)
@click.option(
    "--test", "-t", is_flag=True, help="Specify a test server (useful for Swagger UI)",
)
@click.option("--host", "-h")
@click.option("--port", "-p")
def _openapi(test, json, host, port):
    """Generate OpenAPI metadata from Flask app."""
    with app.test_request_context():
        spec = register_spec(test=test, test_host=host, test_port=port)
        spec.path(view=info)
        spec.path(view=create_event)
        spec.path(view=remove_event)
        spec.path(view=get_event_info)

        if json:
            print(_json.dumps(spec.to_dict()))
        else:
            print(spec.to_yaml())
