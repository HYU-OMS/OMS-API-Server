from flask_restplus import Resource, fields
from flask import request
from app import db_engine, api
from sqlalchemy import text
from app.modules.pagination import Pagination
import app.modules.helper as helper
import json

ns = api.namespace('order', description="주문 관련 API (주문 내역 조회, 새 주문 넣기, 주문 승인/취소)")
order_get_success = api.model('Order_Get_Success', {
    "list": fields.List(fields.Raw({
        "id": "주문 고유번호",
        "user_id": "주문을 넣은 유저 고유번호",
        "name": "주문을 넣은 유저 이름",
        "table_id": "해당 주문을 받은 테이블 이름",
        "status": "주문 처리 상태 (0: 대기, 1: 승인, -1: 취소)",
        "total_price": "총 주문 금액",
        "created_at": "주문을 받은 시간 (datetime ISO format)"
    })),
    "pagination": fields.List(fields.Raw({
        'num': "pagination 번호",
        'text': 'pagination 단추에서 표시할 텍스트',
        'current': "현재 선택된 page면 true, 아닐 경우 false"
    }))
})
order_post_payload = api.model('Order_Post_Payload', {
    "group_id": fields.Integer("그룹 고유번호"),
    "table_id": fields.String("테이블 이름"),
    "menu_list": fields.List(fields.Raw({
        "id": "메뉴 고유번호",
        "amount": "주문 수량"
    })),
    "setmenu_list": fields.List(fields.Raw({
        "id": "세트메뉴 고유번호",
        "amount": "주문 수량"
    }))
})
order_post_success = api.model('Order_Post_Success', {
    "order_id": fields.Integer("새로 생성된 주문 번호"),
    "total_price": fields.Integer("주문 총 금액")
})
order_each_get_success = api.model('OrderEach_Get_Success', {
    "order_id": fields.Integer("주문 고유번호"),
    "order_menus": fields.List(fields.Raw({
        "id": "메뉴 고유번호",
        "name": "메뉴 이름",
        "amount": "메뉴 수량"
    })),
    "order_setmenus": fields.List(fields.Raw({
        "id": "메뉴 고유번호",
        "name": "세트메뉴 이름",
        "amount": "세트메뉴 수량"
    }))
})


@ns.route('')
@ns.param("jwt", "로그인 시 얻은 JWT를 입력", _in="query", required=True)
class Order(Resource):
    @ns.param("group_id", "그룹 고유번호", _in="query", required=True)
    @ns.param("show_only_pending", "처리되지 않은 주문만 볼 것인지 지정 (0: 전부 보기, 1: 처리 대기중인 것만 보기)", _in="query", required=False)
    @ns.response(200, "현재 주문 내역을 가져온다.", model=order_get_success)
    def get(self):
        if request.user_info is None:
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
                              "`orders`.`total_price`, `orders`.`status`, `orders`.`created_at` FROM `orders` " \
                              "JOIN `users` ON `users`.`id` = `orders`.`user_id` " \
                              "WHERE `orders`.`group_id` = :group_id AND `orders`.`status` = 0 "
                count_query = " SELECT COUNT(`orders`.`id`) AS `cnt` FROM `orders` " \
                              "WHERE `orders`.`group_id` = :group_id AND `orders`.`status` = 0 "
                order_query = " ORDER BY `orders`.`id` ASC "
            else:
                fetch_query = " SELECT `orders`.`id`, `orders`.`user_id`, `users`.`name`, `orders`.`table_id`, " \
                              "`orders`.`total_price`, `orders`.`status`, `orders`.`created_at` FROM `orders` " \
                              "JOIN `users` ON `users`.`id` = `orders`.`user_id` " \
                              "WHERE `orders`.`group_id` = :group_id "
                count_query = " SELECT COUNT(`orders`.`id`) AS `cnt` FROM `orders` " \
                              "WHERE `orders`.`group_id` = :group_id "
                order_query = " ORDER BY `orders`.`id` DESC "

            result, paging = Pagination(fetch=fetch_query,
                                        count=count_query,
                                        order=order_query,
                                        current_page=page,
                                        connection=connection,
                                        fetch_params={
                                            'user_id': request.user_info['id'],
                                            'group_id': group_id
                                        }).get_result()

        return json.loads(str(json.dumps({
            'list': result,
            'pagination': paging
        }, default=helper.json_serial))), 200

    @ns.doc(body=order_post_payload)
    @ns.response(201, "주문 요청 성공", model=order_post_success)
    def post(self):
        if request.user_info is None:
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

        if len(body['table_id']) > 64:
            return {"message": "Length of 'table_id' must be smaller than 64!"}, 400

        group_id = int(body['group_id'])
        table_id = body['table_id']
        menu_list = body['menu_list']
        setmenu_list = body['setmenu_list']

        if len(menu_list) == 0 and len(setmenu_list) == 0:
            return {"message": "Either 'menu_list' or 'setmenu_list' must be provided!"}, 400

        order_menus = []
        order_setmenus = []

        with db_engine.connect() as connection:
            query_str = "SELECT * FROM `members` WHERE `group_id` = :group_id AND `user_id` = :user_id"
            chk_member = connection.execute(text(query_str),
                                                group_id=group_id, user_id=request.user_info['id']).first()

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
                order_menus.append({
                    "id": menu_info['id'],
                    "name": group_menus[menu_info['id']]['name'],
                    "amount": menu_info['amount']
                })

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

                if int(group_setmenus[setmenu_info['id']]['is_enabled']) == 0:
                    return {"message": str(group_setmenus[setmenu_info['id']]['name']) + " has been disabled!"}, 403

                total_price += (int(setmenu_info['amount']) * int(group_setmenus[setmenu_info['id']]['price']))
                order_setmenus.append({
                    "id": setmenu_info['id'],
                    "name": group_setmenus[setmenu_info['id']]['name'],
                    "amount": setmenu_info['amount']
                })

            with connection.begin() as transaction:
                query_str = "INSERT INTO `orders` SET `user_id` = :user_id, `group_id` = :group_id, " \
                            "`table_id` = :table_id, `total_price` = :total_price, `order_menus` = :menu_list, " \
                            "`order_setmenus` = :setmenu_list"
                query = connection.execute(text(query_str), user_id=request.user_info['id'], group_id=group_id,
                                           table_id=table_id, total_price=total_price, menu_list=json.dumps(order_menus),
                                           setmenu_list=json.dumps(order_setmenus))

                new_order_id = query.lastrowid

                query_str = "INSERT INTO `order_transactions` SET `order_id` = :order_id, `menu_id` = :menu_id, " \
                            "`amount` = :amount"

                for content in menu_list:
                    query = connection.execute(text(query_str), order_id=new_order_id,
                                               menu_id=content['id'], amount=content['amount'])

                for content in setmenu_list:
                    setmenu_id = int(content['id'])
                    set_amount = int(content['amount'])

                    query_str = "SELECT * FROM `set_contents` WHERE `set_id` = :setmenu_id"
                    query = connection.execute(text(query_str), setmenu_id=setmenu_id)

                    set_data = [dict(row) for row in query]

                    for each_data in set_data:
                        menu_id = int(each_data['menu_id'])
                        menu_amount = int(each_data['amount'])

                        query_str = "UPDATE `order_transactions` SET `amount` = `amount` + :amount " \
                                    "WHERE `order_id` = :order_id AND `menu_id` = :menu_id"
                        query = connection.execute(text(query_str),
                                                   amount=(menu_amount * set_amount),
                                                   order_id=new_order_id, menu_id=menu_id)

                query_str = "UPDATE `order_transactions` SET `group_id` = :group_id, `table_id` = :table_id " \
                            "WHERE `order_id` = :order_id"
                query = connection.execute(text(query_str), group_id=group_id, table_id=table_id, order_id=new_order_id)

        return {"order_id": new_order_id, "total_price": total_price}, 201


@ns.route('/<int:order_id>')
@ns.param("jwt", "로그인 시 얻은 JWT를 입력", _in="query", required=True)
class OrderEach(Resource):
    @ns.response(200, "주문 내용 조회 성공", model=order_each_get_success)
    def get(self, order_id):
        if request.user_info is None:
            return {"message": "JWT must be provided!"}, 401

        with db_engine.connect() as connection:
            query_str = "SELECT `group_id`, `order_menus`, `order_setmenus` FROM `orders` WHERE `id` = :order_id"
            order_info = connection.execute(text(query_str), order_id=order_id).first()

            if order_info is None:
                return {"message": "Requested 'order_id' not exists!"}, 404

            group_id = int(order_info['group_id'])

            query_str = "SELECT * FROM `members` WHERE `group_id` = :group_id AND `user_id` = :user_id"
            chk_permission = connection.execute(text(query_str),
                                                group_id=group_id, user_id=request.user_info['id']).first()

            if chk_permission is None:
                return {"message": "Only member of this group can get order info!"}, 403

            order_data = json.loads(json.dumps(dict(order_info), default=helper.json_serial))
            order_data['order_menus'] = json.loads(order_data['order_menus'])
            order_data['order_setmenus'] = json.loads(order_data['order_setmenus'])
            del order_data['group_id']
            order_data['order_id'] = order_id

        return order_data, 200

    @ns.param("is_approved", "주문 승인 여부 (1: 승인, 0: 취소)", _in="query", required=True)
    @ns.response(200, "주문 상태 변경 성공")
    def put(self, order_id):
        if request.user_info is None:
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
                                                group_id=group_id, user_id=request.user_info['id']).first()

            if chk_permission is None:
                return {"message": "You can't update status of this order!"}, 403

            if is_approved == 1:
                order_status = 1
            else:
                order_status = -1

            with connection.begin() as transaction:
                query_str = "UPDATE `orders` SET `status` = :order_status WHERE `id` = :order_id"
                query = connection.execute(text(query_str), order_status=order_status, order_id=order_id)

                query_str = "UPDATE `order_transactions` SET `is_approved` = :is_approved WHERE `order_id` = :order_id"
                query = connection.execute(text(query_str), is_approved=is_approved, order_id=order_id)

        return {"order_id": order_id, "is_approved": is_approved}, 200
