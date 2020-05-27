# run it like this:
# FLASK_ENV=development FLASK_DEBUG=1 FLASK_APP=testsvc.py flask run -p 12345

from functools import wraps

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from webargs import fields
from webargs.flaskparser import use_kwargs
from werkzeug.exceptions import Conflict, HTTPException, NotFound, Unauthorized


SERVICE_INFO = {'version': '0.1-dev', 'name': 'Test Service'}


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///editingsvc'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
db.Model.metadata.naming_convention = {
    'fk': 'fk_%(table_name)s_%(column_names)s_%(referred_table_name)s',
    'pk': 'pk_%(table_name)s',
    'ix': 'ix_%(unique_index)s%(table_name)s_%(column_names)s',
    'ck': 'ck_%(table_name)s_%(constraint_name)s',
    'uq': 'uq_%(table_name)s_%(column_names)s',
    'column_names': lambda constraint, table: '_'.join((c if isinstance(c, basestring) else c.name)
                                                       for c in constraint.columns),
    'unique_index': lambda constraint, table: 'uq_' if constraint.unique else ''
}


class Event(db.Model):
    __tablename__ = 'events'
    identifier = db.Column(db.String, primary_key=True)
    title = db.Column(db.String, nullable=False)
    url = db.Column(db.String, nullable=False)
    token = db.Column(db.String, nullable=False)


db.create_all()


@app.errorhandler(HTTPException)
def _handle_http_exception(exc):
    return jsonify(error=exc.description), exc.code


@app.errorhandler(Exception)
def _handle_exception(exc):
    app.logger.exception('Request failed')
    return jsonify(error='Internal error'), 500


def require_event_token(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        identifier = kwargs.pop('identifier')
        event = Event.query.get(identifier)
        if event is None:
            raise NotFound('Unknown event')
        auth = request.headers.get('Authorization')
        token = None
        if auth and auth.startswith('Bearer '):
            token = auth[7:]
        if not token:
            raise Unauthorized('Token missing')
        elif token != event.token:
            raise Unauthorized('Invalid token')
        return fn(*args, event=event, **kwargs)

    return wrapper


@app.route('/info')
def info():
    return jsonify(SERVICE_INFO)


@app.route('/event/<identifier>', methods=('PUT',))
@use_kwargs({
    'title': fields.String(required=True),
    'url': fields.URL(schemes={'http', 'https'}, required=True),
    'token': fields.String(required=True),
})
def create_event(identifier, title, url, token):
    event = Event(identifier=identifier, title=title, url=url, token=token)
    db.session.add(event)
    try:
        db.session.flush()
    except IntegrityError:
        raise Conflict('Event already exists')
    db.session.commit()
    app.logger.info('Registered event %r', event)
    return '', 201


@app.route('/event/<identifier>', methods=('DELETE',))
@require_event_token
def remove_event(event):
    db.session.delete(event)
    db.session.commit()
    app.logger.info('Unregistered event %r', event)
    return '', 204


@app.route('/event/<identifier>')
@require_event_token
def get_event_info(event):
    return jsonify(service=SERVICE_INFO, title=event.title, url=event.url, can_disconnect=True)
