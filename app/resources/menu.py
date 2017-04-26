from flask_restful import Resource
from flask import request
from app import db_engine
from sqlalchemy import text
from datetime import datetime


class Menu(Resource):
    def __init__(self):
        self.user_info = request.user_info

    def get(self):
        if self.user_info is None:
            return {"message": "JWT must be provided!"}, 401

        if 'group_id' not in request.args:
            return {"message": "Argument 'group_id' must be provided!"}, 400

        group_id = int(request.args['group_id'])

        with db_engine.connect() as connection:
            query_str = "SELECT * FROM `members` WHERE `group_id` = :group_id AND `user_id` = :user_id"
            chk_member = connection.execute(text(query_str), group_id=group_id, user_id=self.user_info['id']).first()

            if chk_member is None:
                return {"message": "Only member of this group can view menu list!"}, 403

            query_str = "SELECT `id`, `name`, `price`, `is_enabled`, `category` FROM `menus` " \
                        "WHERE `group_id` = :group_id"
            query = connection.execute(text(query_str), group_id=group_id)

            menu_list = [dict(row) for row in query]

        return {"list": menu_list}, 200

    def post(self):
        if self.user_info is None:
            return {"message": "JWT must be provided!"}, 401

        body = request.get_json(silent=True, force=True)
        if body is None:
            return {"message": "Unable to get json post data!"}, 400

        if 'group_id' not in body:
            return {"message": "'group_id' not provided!"}, 400

        if 'name' not in body:
            return {"message": "'name' not provided!"}, 400

        if 'price' not in body:
            return {"message": "'price' not provided!"}, 400

        group_id = int(body['group_id'])
        price = int(body['price'])

        with db_engine.connect() as connection:
            query_str = "SELECT * FROM `members` WHERE `group_id` = :group_id AND `user_id` = :user_id"
            chk_permission = connection.execute(text(query_str),
                                                group_id=group_id, user_id=self.user_info['id']).first()

            if chk_permission is None:
                return {"message": "You can't add menu in this group!"}, 403

            query_str = "INSERT INTO `menus` SET `name` = :name, `price` = :price, `group_id` = :group_id," \
                        "`created_at` = :cur_time, `updated_at` = :cur_time"

            query = connection.execute(text(query_str), name=body['name'], price=price, group_id=group_id,
                                       cur_time=datetime.utcnow())

            new_menu_id = query.lastrowid

        return {"menu_id": new_menu_id}, 200


class MenuEdit(Resource):
    def __init__(self):
        self.user_info = request.user_info

    def put(self, menu_id):
        if self.user_info is None:
            return {"message": "JWT must be provided!"}, 401

        body = request.get_json(silent=True, force=True)
        if body is None:
            return {"message": "Unable to get json post data!"}, 400

        if 'price' not in body:
            return {"message": "'price' not provided!"}, 400

        if 'is_enabled' not in body:
            return {"message": "'is_enabled' not provided!"}, 400

        price = int(body['price'])
        is_enabled = int(body['is_enabled'])

        with db_engine.connect() as connection:
            query_str = "SELECT * FROM `menus` WHERE `id` = :menu_id"
            menu_info = connection.execute(text(query_str), menu_id=menu_id).first()

            if menu_info is None:
                return {"message", "Requested 'menu_id' not found!"}, 404

            group_id = menu_info['group_id']

            query_str = "SELECT * FROM `members` WHERE `group_id` = :group_id AND `user_id` = :user_id"
            chk_permission = connection.execute(text(query_str),
                                                group_id=group_id, user_id=self.user_info['id']).first()

            if chk_permission is None:
                return {"message": "You can't update menu in this group!"}, 403

            with connection.begin() as transaction:
                query_str = "UPDATE `menus` SET `price` = :price, `is_enabled` = :is_enabled, " \
                            "`updated_at` = :cur_time WHERE `id` = :menu_id"
                query = connection.execute(text(query_str), price=price, is_enabled=is_enabled,
                                           cur_time=datetime.utcnow(), menu_id=menu_id)

                if is_enabled == 0:
                    query_str = "SELECT * FROM `set_contents` WHERE `menu_id` = :menu_id"
                    query = connection.execute(text(query_str), menu_id=menu_id)

                    set_contents = [dict(row) for row in query]

                    for set_content in set_contents:
                        query_str = "UPDATE `setmenus` SET `is_enabled` = 0, `updated_at` = :cur_time " \
                                    "WHERE `id` = :setmenu_id"
                        query = connection.execute(text(query_str), cur_time=datetime.utcnow(),
                                                   setmenu_id=set_content['set_id'])

        return {"menu_id": menu_id}, 200
