from flask_restful import Resource
from flask import request
from app import db_engine
from sqlalchemy import text
from datetime import datetime
import app.modules.helper as helper
import json


class Queue(Resource):
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
                return {"message": "Only member of this group can get queue data!"}, 403

            query_str = "SELECT `id`, `name` FROM `menus` WHERE `group_id` = :group_id"
            query = connection.execute(text(query_str), group_id=group_id)

            menu_list = [dict(row) for row in query]

            query_str = "SELECT `order_id`, `menu_id`, `set_reference_id`, `table_id`, `amount`, `created_at` " \
                        "FROM `order_transactions` " \
                        "WHERE `group_id` = :group_id AND `is_approved` = 1 AND `is_delivered` = 0"
            query = connection.execute(text(query_str), group_id=group_id)

            queue_data = json.loads(str(json.dumps([dict(row) for row in query], default=helper.json_serial)))

        queue_list = dict()

        for each_menu in menu_list:
            queue_list[int(each_menu['id'])] = list()

        for each_queue_data in queue_data:
            queue_list[int(each_queue_data['menu_id'])].append(each_queue_data)

        combined_queue_list = menu_list
        for each_menu in combined_queue_list:
            each_menu['queue'] = queue_list[each_menu['id']]

        return combined_queue_list, 200

    def put(self):
        if self.user_info is None:
            return {"message": "JWT must be provided!"}, 401

        body = request.get_json(silent=True, force=True)
        if body is None:
            return {"message": "Unable to get json post data!"}, 400

        if 'order_id' not in body:
            return {"message": "'order_id' not provided!"}, 400

        if 'menu_id' not in body:
            return {"message": "'menu_id' not provided!"}, 400

        if 'set_reference_id' not in body:
            return {"message": "'set_reference_id' not provided!"}, 400

        order_id = int(body['order_id'])
        menu_id = int(body['menu_id'])
        set_reference_id = int(body['set_reference_id'])

        with db_engine.connect() as connection:
            query_str = "SELECT * FROM `order_transactions` " \
                        "WHERE `order_id` = :order_id AND `menu_id` = :menu_id " \
                        "AND `set_reference_id` = :set_reference_id"
            chk_queue = connection.execute(text(query_str),
                                           order_id=order_id, menu_id=menu_id,
                                           set_reference_id=set_reference_id).first()

            if chk_queue is None:
                return {"message": "Requested queue('order_id', 'menu_id') not exists!"}, 404

            group_id = chk_queue['group_id']

            query_str = "SELECT * FROM `members` " \
                        "WHERE `group_id` = :group_id AND `user_id` = :user_id AND `role` > 0"
            chk_permission = connection.execute(text(query_str),
                                                group_id=group_id, user_id=self.user_info['id']).first()

            if chk_permission is None:
                return {"message": "You can't update queue status!"}, 403

            query_str = "UPDATE `order_transactions` SET `is_delivered` = 1, `updated_at` = :cur_time " \
                        "WHERE `order_id` = :order_id AND `menu_id` = :menu_id " \
                        "AND `set_reference_id` = :set_reference_id"
            query = connection.execute(text(query_str), cur_time=datetime.utcnow(),
                                       order_id=order_id, menu_id=menu_id, set_reference_id=set_reference_id)

        return {
            "order_id": order_id,
            "menu_id": menu_id,
            "set_reference_id": set_reference_id
        }, 200
