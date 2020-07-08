from marshmallow import Schema, EXCLUDE
from webargs import fields

from .defaults import SERVICE_INFO


class ListEndpointSchema(Schema):
    create = fields.String(required=True)
    list = fields.String(required=True)


class EventEndpointsSchema(Schema):
    tags = fields.Nested(ListEndpointSchema)
    editable_types = fields.String(required=True)
    file_types = fields.Dict(
        keys=fields.String(), values=fields.Nested(ListEndpointSchema), required=True,
    )


class EditableEndpointsSchema(Schema):
    revisions = fields.Nested({
        'replace': fields.String(required=True)
    })
    file_upload = fields.String(required=True)


class EventSchema(Schema):
    title = fields.String(required=True)
    url = fields.URL(schemes={"http", "https"}, required=True)
    token = fields.String(required=True)
    endpoints = fields.Nested(EventEndpointsSchema, required=True,)


class EventInfoServiceSchema(Schema):
    version = fields.String()
    name = fields.String()


class EventInfoSchema(Schema):
    title = fields.String(required=True)
    url = fields.URL(schemes={"http", "https"}, required=True)
    can_disconnect = fields.Boolean(required=True, default=True)
    service = fields.Nested(
        EventInfoServiceSchema, required=True, default=SERVICE_INFO,
    )


class FileSchema(Schema):
    uuid = fields.String()
    filename = fields.String(required=True)
    content_type = fields.String()
    external_download_url = fields.String(required=True)
    file_type = fields.Integer(required=True)


class EditableSchema(Schema):
    files = fields.List(fields.Nested(FileSchema, unknown=EXCLUDE, required=True))
    endpoints = fields.Nested(EditableEndpointsSchema, required=True)


class SuccessSchema(Schema):
    success = fields.Boolean(required=True)


class ServiceInfoSchema(Schema):
    name = fields.String(required=True)
    version = fields.String(required=True)


class IdentifierParameter(Schema):
    identifier = fields.String(
        required=True, description="The unique ID which represents the event"
    )
