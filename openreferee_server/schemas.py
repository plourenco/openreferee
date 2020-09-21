from marshmallow import EXCLUDE, Schema
from webargs import fields

from .defaults import SERVICE_INFO


class ListEndpointSchema(Schema):
    create = fields.String(required=True)
    list = fields.String(required=True)


class EventEndpointsSchema(Schema):
    tags = fields.Nested(ListEndpointSchema)
    editable_types = fields.String(required=True)
    file_types = fields.Dict(
        keys=fields.String(),
        values=fields.Nested(ListEndpointSchema),
        required=True,
    )


class EditableEndpointsSchema(Schema):
    revisions = fields.Nested(
        {
            "details": fields.String(required=True),
            "replace": fields.String(required=True),
        }
    )
    file_upload = fields.String(required=True)


class EventSchema(Schema):
    title = fields.String(required=True)
    url = fields.URL(schemes={"http", "https"}, required=True)
    token = fields.String(required=True)
    endpoints = fields.Nested(
        EventEndpointsSchema,
        required=True,
    )


class EventInfoServiceSchema(Schema):
    version = fields.String()
    name = fields.String()


class EventInfoSchema(Schema):
    title = fields.String(required=True)
    url = fields.URL(schemes={"http", "https"}, required=True)
    can_disconnect = fields.Boolean(required=True, default=True)
    service = fields.Nested(
        EventInfoServiceSchema,
        required=True,
        default=SERVICE_INFO,
    )


class FileSchema(Schema):
    uuid = fields.String(required=True)
    filename = fields.String(required=True)
    content_type = fields.String()
    # Only sent by unclaimed files, should be moved if this schema is re-used otherwise
    signed_download_url = fields.String(required=True)
    file_type = fields.Integer(required=True)


class TagSchema(Schema):
    id = fields.Integer(required=True)
    code = fields.String(required=True)
    title = fields.String(required=True)
    color = fields.String()
    system = fields.Boolean()
    verbose_title = fields.String()
    is_used_in_revision = fields.Boolean()
    url = fields.String()


class RevisionStateSchema(Schema):
    name = fields.String(required=True)
    title = fields.String(allow_none=True)
    css_class = fields.String(allow_none=True)


class EditingUserSchema(Schema):
    id = fields.Integer(required=True)
    full_name = fields.String(required=True)
    identifier = fields.String(required=True)
    avatar_bg_color = fields.String()


class EditableSchema(Schema):
    id = fields.Integer(required=True)
    type = fields.String()
    state = fields.String(required=True)
    editor = fields.Nested(EditingUserSchema, allow_none=True)
    timeline_url = fields.String()
    revision_count = fields.Integer()


class RevisionSchema(Schema):
    comment = fields.String(required=True)
    submitter = fields.Nested(EditingUserSchema, required=True)
    editor = fields.Nested(EditingUserSchema, allow_none=True)
    files = fields.List(fields.Nested(FileSchema, unknown=EXCLUDE, required=True))
    initial_state = fields.Nested(RevisionStateSchema)
    final_state = fields.Nested(RevisionStateSchema)
    tags = fields.List(fields.Nested(TagSchema))


class CreateEditableSchema(Schema):
    editable = fields.Nested(EditableSchema, required=True)
    revision = fields.Nested(RevisionSchema, unknown=EXCLUDE, required=True)
    endpoints = fields.Nested(EditableEndpointsSchema, required=True)


class ReviewEditableSchema(Schema):
    action = fields.String(required=True)
    revision = fields.Nested(RevisionSchema, unknown=EXCLUDE, required=True)
    endpoints = fields.Nested(EditableEndpointsSchema, required=True)


class ReviewResponseSchema(Schema):
    publish = fields.Boolean()
    tags = fields.String()
    comment = fields.String()
    comments = fields.List(fields.String())


class SuccessSchema(Schema):
    success = fields.Boolean(required=True)


class ServiceInfoSchema(Schema):
    name = fields.String(required=True)
    version = fields.String(required=True)


class IdentifierParameter(Schema):
    identifier = fields.String(
        required=True, description="The unique ID which represents the event"
    )


class EditableParameters(Schema):
    class Meta:
        # avoid inconsistency when generating openapi locally and during CI
        ordered = True

    identifier = fields.String(
        required=True, description="The unique ID which represents the event"
    )
    contrib_id = fields.Integer(
        required=True, description="The unique ID which represents the contribution"
    )
    editable_type = fields.String(
        required=True, description="The name which represents the editable type"
    )


class ReviewParameters(EditableParameters):
    revision_id = fields.String(
        required=True, description="The unique ID which represents the revision"
    )
