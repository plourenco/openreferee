from marshmallow import Schema
from webargs import fields

from .defaults import SERVICE_INFO


class EventEndpointsSchema(Schema):
    tags = fields.Nested(
        {"create": fields.String(required=True), "list": fields.String(required=True)}
    )
    editable_types = fields.String(required=True)
    file_types = fields.Dict(
        keys=fields.String(),
        values=fields.Nested(
            {
                "create": fields.String(required=True),
                "list": fields.String(required=True),
            }
        ),
        required=True,
    )


class EventSchema(Schema):
    title = fields.String(required=True)
    url = fields.URL(schemes={"http", "https"}, required=True)
    token = fields.String(required=True)
    config_endpoints = fields.Nested(EventEndpointsSchema, required=True,)


class EventInfoSchema(Schema):
    title = fields.String(required=True)
    url = fields.URL(schemes={"http", "https"}, required=True)
    can_disconnect = fields.Boolean(required=True, default=True)
    service = fields.Nested(
        {"version": fields.String(), "name": fields.String()},
        required=True,
        default=SERVICE_INFO,
    )


class SuccessSchema(Schema):
    success = fields.Boolean(required=True)


class ServiceInfoSchema(Schema):
    name = fields.String(required=True)
    version = fields.String(required=True)


class IdentifierParameter(Schema):
    identifier = fields.String(
        required=True, description="The unique ID which represents the event"
    )
