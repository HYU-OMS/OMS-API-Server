from flask_restful import Resource
from flask import request
from app import db_engine
from sqlalchemy import text
from datetime import datetime
from app.modules.pagination import Pagination
import app.modules.helper as helper
import json


class Group(Resource):
    def __init__(self):
        self.user_info = request.user_info

    def get(self):
        if self.user_info is None:
            return {"message": "JWT must be provided!"}, 401

        page = 1
        if 'page' in request.args:
            page = int(request.args['page'])

        with db_engine.connect() as connection:
            fetch_query = " SELECT `groups`.`id`, `groups`.`name`, `groups`.`creator_id`, `members`,`role`, " \
                          "`groups`.`created_at`, FROM `groups` " \
                          "JOIN `members` ON `groups`.`id` = `members`.`group_id` " \
                          "WHERE `members`.`user_id` = :user_id "
            count_query = "SELECT COUNT(`groups`.`id`) AS `cnt` FROM `groups` " \
                          "JOIN `members` ON `groups`.`id` = `members`.`group_id` " \
                          "WHERE `members`.`user_id` = :user_id "
            order_query = " ORDER BY `id` DESC "

            result, paging = Pagination(fetch=fetch_query,
                                        count=count_query,
                                        order=order_query,
                                        current_page=page,
                                        connection=connection,
                                        fetch_params={'user_id': self.user_info['id']}).get_result()

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

        if 'name' not in body:
            return {"message": "'name' not provided!"}, 400

        with db_engine.connect() as connection:
            with connection.begin() as transaction:
                query_str = "INSERT INTO `groups` SET `name` = :name, `creator_id` = :user_id, " \
                            "`created_at` = :cur_time, `updated_at` = :cur_time"
                query = connection.execute(text(query_str), name=body['name'], user_id=self.user_info['id'],
                                           cur_time=datetime.utcnow())

                new_group_id = query.lastrowid

                query_str = "INSERT INTO `members` SET `group_id` = :group_id, `user_id` = :user_id, `role` = '2', " \
                            "`created_at` = :cur_time, `updated_at` = :cur_time"
                query = connection.execute(text(query_str), group_id=new_group_id, user_id=self.user_info['id'],
                                           cur_time=datetime.utcnow())

        return {"group_id": new_group_id}, 200
