from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_restplus import Api

app = Flask(__name__)
CORS(app, supports_credentials=True, max_age=86400)
app.config.from_object('config')
api = Api(app=app,
          catch_all_404s=True,
          title="2017 OMS API",
          description="2017년도 한양대학교 주문관리시스템 API description page",
          contact="한양대학교 한기훈",
          contact_email="kordreamfollower@gmail.com",
          prefix="/api")

db = None
db_engine = None
if db is None and db_engine is None:
    db = SQLAlchemy(app)
    db_engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'],
                                 encoding='utf-8',
                                 connect_args=app.config['DATABASE_CONNECT_OPTIONS'],
                                 pool_size=20, max_overflow=0)

from app.modules import helper
app.before_request(helper.before_request)

from app.resources import *
api.add_resource(user.User, '/user')
api.add_resource(group.Group, '/group')
api.add_resource(group.GroupEach, '/group/<int:group_id>')
api.add_resource(member.Member, '/member')
api.add_resource(menu.Menu, '/menu')
api.add_resource(menu.MenuEach, '/menu/<int:menu_id>')
api.add_resource(setmenu.Setmenu, '/setmenu')
api.add_resource(setmenu.SetmenuEach, '/setmenu/<int:setmenu_id>')
api.add_resource(order.Order, '/order')
api.add_resource(order.OrderEach, '/order/<int:order_id>')
api.add_resource(queue.Queue, '/queue')
