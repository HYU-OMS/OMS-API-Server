from flask_restful import Resource
from flask import request
from app import db_engine
from sqlalchemy import text
from datetime import datetime
from app.modules.pagination import Pagination
import app.modules.helper as helper
import json


class Order(Resource):
    def __init__(self):
        self.user_info = request.user_info

    def get(self):
        if self.user_info is None:
            return {"message": "JWT must be provided!"}, 401

        if 'group_id' not in request.args:
            return {"message": "Argument 'group_id' must be provided!"}, 400

        page = 1
        if 'page' in request.args:
            page = int(request.args['page'])

        show_only_pending = 0
        if 'show_only_pending' in request.args:
            show_only_pending = int(request.args['show_only_pending'])

        group_id = int(request.args['group_id'])

        with db_engine.connect() as connection:
            if show_only_pending == 1:
                fetch_query = " SELECT `orders`.`id`, `orders`.`user_id`, `users`.`name`, `orders`.`table_id`, " \
                              "`orders`.`total_price`, `orders`.`created_at`, " \
                              "`orders`.`updated_at` FROM `orders` " \
                              "JOIN `users` ON `users`.`id` = `orders`.`user_id` " \
                              "WHERE `orders`.`group_id` = :group_id AND `orders`.`status` = 0 "
                count_query = " SELECT COUNT(`orders`.`id`) AS `cnt` FROM `orders` " \
                              "WHERE `orders`.`group_id` = :group_id AND `orders`.`status` = 0 "
            else:
                fetch_query = " SELECT `orders`.`id`, `orders`.`user_id`, `users`.`name`, `orders`.`table_id`, " \
                              "`orders`.`total_price`, `orders`.`status`, `orders`.`created_at`, " \
                              "`orders`.`updated_at` FROM `orders` " \
                              "JOIN `users` ON `users`.`id` = `orders`.`user_id` " \
                              "WHERE `orders`.`group_id` = :group_id "
                count_query = " SELECT COUNT(`orders`.`id`) AS `cnt` FROM `orders` " \
                              "WHERE `orders`.`group_id` = :group_id "

            order_query = " ORDER BY `id` DESC "

            result, paging = Pagination(fetch=fetch_query,
                                        count=count_query,
                                        order=order_query,
                                        current_page=page,
                                        connection=connection,
                                        fetch_params={
                                            'user_id': self.user_info['id'],
                                            'group_id': group_id
                                        }).get_result()

        return json.loads(str(json.dumps({
            'list': result,
            'pagination': paging
        }, default=helper.json_serial))), 200

    def post(self):
        if self.user_info is None:
            return {"message": "JWT must be provided!"}, 401

        body = request.get_json(silent=True, force=True)
        if body is None:
            return {"message": "Unable to get json post data!"}, 400

        if 'group_id' not in body:
            return {"message": "'group_id' not provided!"}, 400

        if 'table_id' not in body:
            return {"message": "'table_id' not provided!"}, 400

        if 'menu_list' not in body:
            return {"message": "'menu_list' not provided!"}, 400

        if 'setmenu_list' not in body:
            return {"message": "'setmenu_list' not provided!"}, 400

        if isinstance(body['menu_list'], list) is False:
            return {"message": "'menu_list' must be JSON array!"}, 400

        if isinstance(body['setmenu_list'], list) is False:
            return {"message": "'setmenu_list' must be JSON array!"}, 400

        group_id = int(body['group_id'])
        table_id = body['table_id']
        menu_list = body['menu_list']
        setmenu_list = body['setmenu_list']

        if len(menu_list) == 0 and len(setmenu_list) == 0:
            return {"message": "Either 'menu_list' or 'setmenu_list' must be provided!"}, 400

        with db_engine.connect() as connection:
            query_str = "SELECT * FROM `members` WHERE `group_id` = :group_id AND `user_id` = :user_id"
            chk_member = connection.execute(text(query_str),
                                                group_id=group_id, user_id=self.user_info['id']).first()

            if chk_member is None:
                return {"message": "You are not a member of this group!"}, 403

            total_price = int(0)

            query_str = "SELECT `id`, `name`, `price`, `is_enabled` FROM `menus` WHERE `group_id` = :group_id"
            query = connection.execute(text(query_str), group_id=group_id)

            menu_data = [dict(row) for row in query]

            group_menus = dict()
            for content in menu_data:
                group_menus[content['id']] = {
                    "name": content['name'],
                    "price": content['price'],
                    "is_enabled": content['is_enabled']
                }

            for menu_info in menu_list:
                if 'id' not in menu_info or 'amount' not in menu_info:
                    return {"message": "Array 'menu_list' has been malformed!"}, 400

                if menu_info['id'] not in group_menus:
                    return {"message": "MenuID " + str(menu_info['id']) + " not belongs to this group!"}, 400

                if int(group_menus[menu_info['id']]['is_enabled']) == 0:
                    return {"message": str(group_menus[menu_info['id']]['name']) + " has been disabled!"}, 403

                total_price += (int(menu_info['amount']) * int(group_menus[menu_info['id']]['price']))

            query_str = "SELECT `id`, `name`, `price`, `is_enabled` FROM `setmenus` WHERE `group_id` = :group_id"
            query = connection.execute(text(query_str), group_id=group_id)

            setmenu_data = [dict(row) for row in query]

            group_setmenus = dict()
            for content in setmenu_data:
                group_setmenus[content['id']] = {
                    "name": content['name'],
                    "price": content['price'],
                    "is_enabled": content['is_enabled']
                }

            for setmenu_info in setmenu_list:
                if 'id' not in setmenu_info or 'amount' not in setmenu_info:
                    return {"message": "Array 'setmenu_list' has been malformed!"}, 400

                if setmenu_info['id'] not in group_setmenus:
                    return {"message": "SetMenuID " + str(setmenu_info['id']) + " not belongs to this group!"}, 400

                if int(group_menus[setmenu_info['id']]['is_enabled']) == 0:
                    return {"message": str(group_setmenus[setmenu_info['id']]['name']) + " has been disabled!"}, 403

                total_price += (int(setmenu_info['amount']) * int(group_setmenus[setmenu_info['id']]['price']))

            with connection.begin() as transaction:
                query_str = "INSERT INTO `orders` SET `user_id` = :user_id, `group_id` = :group_id, " \
                            "`table_id` = :table_id, `total_price` = :total_price, " \
                            "`created_at` = :cur_time, `updated_at` = :cur_time"
                query = connection.execute(text(query_str), user_id=self.user_info['id'], group_id=group_id,
                                           table_id=table_id, total_price=total_price, cur_time=datetime.utcnow())

                new_order_id = query.lastrowid

                query_str = "INSERT INTO `order_transactions` SET `order_id` = :order_id, `menu_id` = :menu_id, " \
                            "`amount` = :amount, `created_at` = :cur_time, `updated_at` = :cur_time"

                for content in menu_list:
                    query = connection.execute(text(query_str), order_id=new_order_id,
                                               menu_id=content['id'], amount=content['amount'],
                                               cur_time=datetime.utcnow())

                query_str = "INSERT INTO `order_transactions` " \
                            "(order_id, menu_id, set_reference_id, amount, created_at, updated_at) " \
                            "SELECT :order_id AS `order_id`, `menu_id`, :setmenu_id AS `set_reference_id`, " \
                            ":amount AS `amount`, :cur_time AS `created_at`, :cur_time AS `updated_at` " \
                            "FROM `set_contents` WHERE `set_id` = :setmenu_id"

                for content in setmenu_list:
                    query = connection.execute(text(query_str), order_id=new_order_id, setmenu_id=content['id'],
                                               amount=content['amount'], cur_time=datetime.utcnow())

                query_str = "UPDATE `order_transactions` SET `group_id` = :group_id, `table_id` = :table_id " \
                            "WHERE `order_id` = :order_id"
                query = connection.execute(text(query_str), group_id=group_id, table_id=table_id, order_id=new_order_id)

        return {"order_id": new_order_id}, 200


class OrderEach(Resource):
    def __init__(self):
        self.user_info = request.user_info

    def put(self, order_id):
        if self.user_info is None:
            return {"message": "JWT must be provided!"}, 401

        body = request.get_json(silent=True, force=True)
        if body is None:
            return {"message": "Unable to get json post data!"}, 400

        if 'is_approved' not in body:
            return {"message": "'is_approved' not provided!"}, 400

        is_approved = int(body['is_approved'])

        if is_approved < 0 or is_approved > 1:
            return {"message": "'is_approved' must be 0 or 1!"}, 400

        with db_engine.connect() as connection:
            query_str = "SELECT * FROM `orders` WHERE `id` = :order_id"
            order_info = connection.execute(text(query_str), order_id=order_id).first()

            if order_info is None:
                return {"message": "Requested 'order_id' not exists!"}, 404

            if int(order_info['status']):
                return {"message": "Status of requested 'order_id' is not 'pending'!"}, 403

            group_id = int(order_info['group_id'])

            query_str = "SELECT * FROM `members` WHERE `group_id` = :group_id AND `user_id` = :user_id AND `role` > 0"
            chk_permission = connection.execute(text(query_str),
                                                group_id=group_id, user_id=self.user_info['id']).first()

            if chk_permission is None:
                return {"message": "You can't update status of this order!"}, 403

            if is_approved == 1:
                order_status = 1
            else:
                order_status = -1

            with connection.begin() as transaction:
                query_str = "UPDATE `orders` SET `status` = :order_status, `updated_at` = :cur_time " \
                            "WHERE `id` = :order_id"
                query = connection.execute(text(query_str), order_status=order_status,
                                           cur_time=datetime.utcnow(), order_id=order_id)

                query_str = "UPDATE `order_transactions` SET `is_approved` = :is_approved, `updated_at` = :cur_time " \
                            "WHERE `order_id` = :order_id"
                query = connection.execute(text(query_str), is_approved=is_approved,
                                           cur_time=datetime.utcnow(), order_id=order_id)

        return {"order_id": order_id, "is_approved": is_approved}, 200
