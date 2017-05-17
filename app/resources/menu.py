from flask_restplus import Resource, fields
from flask import request
from app import db_engine, api
from sqlalchemy import text


ns = api.namespace('menu', description="메뉴 관련 API (메뉴 조회, 새로 추가, 가격 및 상태 변경)")
menu_get_success = api.model('Menu_Get_Success', {
    "list": fields.List(fields.Raw({
        "id": "메뉴 고유번호",
        "name": "메뉴 이름",
        "price": "메뉴 가격",
        "is_enabled": "현재 주문 가능한지 여부"
    }))
})
menu_post_payload = api.model('Menu_Post_Payload', {
    "group_id": fields.Integer("그룹 고유번호"),
    "name": fields.String("메뉴 이름"),
    "price": fields.Integer("메뉴 가격")
})
menu_put_payload = api.model('Menu_Put_Payload', {
    "price": fields.Integer("메뉴 가격"),
    "is_enabled": fields.Integer("주문가능여부 (0: 불가, 1: 가능)")
})


@ns.route('')
@ns.param("jwt", "로그인 시 얻은 JWT를 입력", _in="query", required=True)
class Menu(Resource):
    @ns.param("group_id", "그룹 고유번호", _in="query", required=True)
    @ns.response(200, "메뉴 목록 조회 성공", model=menu_get_success)
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
                return {"message": "Only member of this group can view menu list!"}, 403

            query_str = "SELECT `id`, `name`, `price`, `is_enabled` FROM `menus` " \
                        "WHERE `group_id` = :group_id"
            query = connection.execute(text(query_str), group_id=group_id)

            menu_list = [dict(row) for row in query]

        return {"list": menu_list}, 200

    @ns.doc(body=menu_post_payload)
    @ns.response(201, "새 메뉴 등록 성공")
    def post(self):
        if request.user_info is None:
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

        if len(body['name']) > 64:
            return {"message": "Length of 'name' must be smaller than 64!"}, 400

        group_id = int(body['group_id'])
        price = int(body['price'])

        with db_engine.connect() as connection:
            query_str = "SELECT * FROM `members` WHERE `group_id` = :group_id AND `user_id` = :user_id"
            chk_permission = connection.execute(text(query_str),
                                                group_id=group_id, user_id=request.user_info['id']).first()

            if chk_permission is None:
                return {"message": "You can't add menu in this group!"}, 403

            query_str = "INSERT INTO `menus` SET `name` = :name, `price` = :price, `group_id` = :group_id"

            query = connection.execute(text(query_str), name=body['name'], price=price, group_id=group_id)

            new_menu_id = query.lastrowid

        return {"menu_id": new_menu_id}, 201


@ns.route('/<int:menu_id>')
@ns.param("jwt", "로그인 시 얻은 JWT를 입력", _in="query", required=True)
class MenuEach(Resource):
    @ns.doc(body=menu_put_payload)
    @ns.response(200, "메뉴 정보 변경 성공")
    def put(self, menu_id):
        if request.user_info is None:
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
                                                group_id=group_id, user_id=request.user_info['id']).first()

            if chk_permission is None:
                return {"message": "You can't update menu in this group!"}, 403

            with connection.begin() as transaction:
                query_str = "UPDATE `menus` SET `price` = :price, `is_enabled` = :is_enabled WHERE `id` = :menu_id"
                query = connection.execute(text(query_str), price=price, is_enabled=is_enabled, menu_id=menu_id)

                if is_enabled == 0:
                    query_str = "SELECT * FROM `set_contents` WHERE `menu_id` = :menu_id"
                    query = connection.execute(text(query_str), menu_id=menu_id)

                    set_contents = [dict(row) for row in query]

                    for set_content in set_contents:
                        query_str = "UPDATE `setmenus` SET `is_enabled` = 0 WHERE `id` = :setmenu_id"
                        query = connection.execute(text(query_str), setmenu_id=set_content['set_id'])

        return {"menu_id": menu_id}, 200
