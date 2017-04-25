from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Resource, Api


app = Flask(__name__)
CORS(app, supports_credentials=True)
app.config.from_object('config')
api = Api(app)

db = None
db_engine = None
if db is None and db_engine is None:
    db = SQLAlchemy(app)
    db_engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'],
                                 encoding='utf-8',
                                 connect_args=app.config['DATABASE_CONNECT_OPTIONS'])

from app.modules import helper
app.before_request(helper.before_request)

from app.resources.user import User
from app.resources.group import Group

api.add_resource(User, '/api/user')
api.add_resource(Group, '/api/group')
