from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.pool import NullPool
from flask_restful import Api

app = Flask(__name__)
CORS(app, supports_credentials=True)
app.config.from_object('config')
api = Api(app, catch_all_404s=True)

db = None
db_engine = None
if db is None and db_engine is None:
    db = SQLAlchemy(app)
    db_engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'],
                                 encoding='utf-8',
                                 connect_args=app.config['DATABASE_CONNECT_OPTIONS'],
                                 poolclass=NullPool)

from app.modules import helper
app.before_request(helper.before_request)

from app.resources.user import User
from app.resources.group import Group
from app.resources.member import Member
from app.resources.menu import Menu, MenuEdit
from app.resources.setmenu import Setmenu, SetmenuEach
from app.resources.order import Order, OrderEach
from app.resources.queue import Queue

api.add_resource(User, '/api/user')
api.add_resource(Group, '/api/group')
api.add_resource(Member, '/api/member')
api.add_resource(Menu, '/api/menu')
api.add_resource(MenuEdit, '/api/menu/<int:menu_id>')
api.add_resource(Setmenu, '/api/setmenu')
api.add_resource(SetmenuEach, '/api/setmenu/<int:setmenu_id>')
api.add_resource(Order, '/api/order')
api.add_resource(OrderEach, '/api/order/<int:order_id>')
api.add_resource(Queue, '/api/queue')
