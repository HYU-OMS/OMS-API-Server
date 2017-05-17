from flask_restplus import Resource, fields
from flask import request
from app import db_engine, api
from sqlalchemy import text
import app.modules.helper as helper
import json

ns = api.namespace('queue', description="대기열 관련 API (메뉴별 대기열 조회, 대기열 item 제거)")
queue_get_success = api.model('Queue_Get_Success', {
    "list": fields.List(fields.Raw({
        "order_id": "주문 고유번호",
        "menu_id": "메뉴 고유번호",
        "table_id": "테이블 이름",
        "amount": "수량",
        "created_at": "주문을 받은 시간 (datetime ISO format)"
    }))
})
queue_put_payload = api.model('Queue_Put_Payload', {
    "order_id": fields.Integer("주문 고유번호"),
    "menu_id": fields.Integer("메뉴 고유번호")
})


@ns.route('')
@ns.param("jwt", "로그인 시 얻은 JWT를 입력", _in="query", required=True)
class Queue(Resource):
    @ns.param("group_id", "그룹 고유번호", _in="query", required=True)
    @ns.response(200, "대기열 조회 성공", model=queue_get_success)
    def get(self):
        if request.user_info is None:
            return {"message": "JWT must be provided!"}, 401

        if 'group_id' not in request.args:
            return {"message": "Argument 'group_id' must be provided!"}, 400

        group_id = int(request.args['group_id'])

        with db_engine.connect() as connection:
            query_str = "SELECT * FROM `members` WHERE `group_id` = :group_id AND `user_id` = :user_id"
            chk_member = connection.execute(text(query_str), group_id=group_id, user_id=request.user_info['id']).first()

            if chk_member is None:
                return {"message": "Only member of this group can get queue data!"}, 403

            query_str = "SELECT `id`, `name` FROM `menus` WHERE `group_id` = :group_id"
            query = connection.execute(text(query_str), group_id=group_id)

            menu_list = [dict(row) for row in query]

            query_str = "SELECT `order_id`, `menu_id`, `table_id`, `amount`, `created_at` " \
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

        return {"list": combined_queue_list}, 200

    @ns.doc(body=queue_put_payload)
    @ns.response(200, "대기열에서 해당 item을 성공적으로 제거함")
    def put(self):
        if request.user_info is None:
            return {"message": "JWT must be provided!"}, 401

        body = request.get_json(silent=True, force=True)
        if body is None:
            return {"message": "Unable to get json post data!"}, 400

        if 'order_id' not in body:
            return {"message": "'order_id' not provided!"}, 400

        if 'menu_id' not in body:
            return {"message": "'menu_id' not provided!"}, 400

        order_id = int(body['order_id'])
        menu_id = int(body['menu_id'])

        with db_engine.connect() as connection:
            query_str = "SELECT * FROM `order_transactions` " \
                        "WHERE `order_id` = :order_id AND `menu_id` = :menu_id "
            chk_queue = connection.execute(text(query_str),
                                           order_id=order_id, menu_id=menu_id).first()

            if chk_queue is None:
                return {"message": "Requested queue('order_id', 'menu_id') not exists!"}, 404

            group_id = chk_queue['group_id']

            query_str = "SELECT * FROM `members` " \
                        "WHERE `group_id` = :group_id AND `user_id` = :user_id AND `role` > 0"
            chk_permission = connection.execute(text(query_str),
                                                group_id=group_id, user_id=request.user_info['id']).first()

            if chk_permission is None:
                return {"message": "You can't update queue status!"}, 403

            query_str = "UPDATE `order_transactions` SET `is_delivered` = 1 " \
                        "WHERE `order_id` = :order_id AND `menu_id` = :menu_id "
            query = connection.execute(text(query_str), order_id=order_id, menu_id=menu_id)

        return {"order_id": order_id, "menu_id": menu_id}, 200
