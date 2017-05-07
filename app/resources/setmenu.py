from flask_restplus import Resource, fields
from flask import request
from app import db_engine, api
from sqlalchemy import text
from datetime import datetime

ns = api.namespace('setmenu', description="세트메뉴 관련 API (세트메뉴 조회, 새로 추가, 가격 및 상태 변경)")
setmenu_get_success = api.model('Setmenu_Get_Success', {
    "list": fields.List(fields.Raw({
        "id": "메뉴 고유번호",
        "name": "메뉴 이름",
        "price": "메뉴 가격",
        "is_enabled": "현재 주문 가능한지 여부"
    }))
})
setmenu_post_payload = api.model('Setmenu_Post_Payload', {
    "group_id": fields.Integer("그룹 고유번호"),
    "name": fields.String("메뉴 이름"),
    "price": fields.Integer("메뉴 가격"),
    "menu_list": fields.List(fields.Integer("각 메뉴의 고유번호를 지정 (eg. [1, 1, 2, 2, 3]"))
})
setmenu_each_get_success = api.model('SetmenuEach_Get_Success', {
    "list": fields.List(fields.Raw({
        "name": "세트메뉴 구성하는 각 메뉴의 이름",
        "amount": "세트메뉴 구성하는 각 메뉴의 수량"
    }))
})
setmenu_put_payload = api.model('Setmenu_Put_Payload', {
    "price": fields.Integer("세트메뉴 가격"),
    "is_enabled": fields.Integer("주문가능여부 (0: 불가, 1: 가능)")
})

@ns.route('')
@ns.param("jwt", "로그인 시 얻은 JWT를 입력", _in="query", required=True)
class Setmenu(Resource):
    @ns.param("group_id", "그룹 고유번호", _in="query", required=True)
    @ns.response(200, "세트메뉴 목록 조회 성공", model=setmenu_get_success)
    def get(self):
        if request.user_info is None:
            return {"message": "JWT must be provided!"}, 401

        if 'group_id' not in request.args:
            return {"message": "Argument 'group_id' must be provided!"}, 400

        group_id = int(request.args['group_id'])

        with db_engine.connect() as connection:
            query_str = "SELECT * FROM `members` WHERE `group_id` = :group_id AND `user_id` = :user_id"
            member_check = connection.execute(text(query_str), group_id=group_id, user_id=request.user_info['id']).first()

            if member_check is None:
                return {"message": "Only member of this group can view menu list!"}, 403

            query_str = "SELECT `id`, `name`, `price`, `is_enabled` FROM `setmenus` WHERE `group_id` = :group_id"
            query = connection.execute(text(query_str), group_id=group_id)

            setmenu_list = [dict(row) for row in query]

            for setmenu in setmenu_list:
                query_str = "SELECT `id`, `name`, `price` FROM `menus` " \
                            "WHERE `id` = ANY(SELECT `menu_id` FROM `set_contents` WHERE `set_id` = :set_id)"
                query = connection.execute(text(query_str), set_id=setmenu['id'])

                menu_list = [dict(row) for row in query]
                setmenu.update(dict(menu_list=menu_list))

        return {"list": setmenu_list}, 200

    @ns.doc(body=setmenu_post_payload)
    @ns.response(201, "새 세트메뉴 등록 성공")
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

        if 'menu_list' not in body:
            return {"message": "'menu_list' not provided!"}, 400

        if isinstance(body['menu_list'], list) is False:
            return {"message": "'menu_list' must be JSON array!"}, 400

        group_id = int(body['group_id'])
        name = body['name']
        price = int(body['price'])
        menu_list = body['menu_list']

        if len(menu_list) == 0:
            return {"message": "'menu_list' array is empty!"}, 400

        set_content = dict()
        for menu_id in menu_list:
            if str(menu_id) not in set_content:
                set_content[str(menu_id)] = 1
            else:
                set_content[str(menu_id)] += 1

        with db_engine.connect() as connection:
            query_str = "SELECT * FROM `members` WHERE `group_id` = :group_id AND `user_id` = :user_id"
            chk_permission = connection.execute(text(query_str),
                                                group_id=group_id, user_id=request.user_info['id']).first()

            if chk_permission is None or int(chk_permission['role']) < 1:
                return {"message": "You can't add setmenu in this group!"}, 403

            for menu_id in menu_list:
                query_str = "SELECT * FROM `menus` WHERE `id` = :menu_id AND `group_id` = :group_id"
                menu_check = connection.execute(text(query_str), menu_id=menu_id, group_id=group_id).first()

                if menu_check is None:
                    return {"message": "Invalid 'menu_id' for this group!"}, 403

            with connection.begin() as transaction:
                query_str = "INSERT INTO `setmenus` SET `name` = :name, `price` = :price, `group_id` = :group_id," \
                            "`created_at` = :cur_time, `updated_at` = :cur_time"
                query = connection.execute(text(query_str), name=name, price=price, group_id=group_id,
                                           cur_time=datetime.utcnow())

                new_setmenu_id = query.lastrowid

                for key in set_content:
                    query_str = "INSERT INTO `set_contents` SET " \
                                "`set_id` = :set_id, `menu_id` = :menu_id, `amount` = :amount"
                    query = connection.execute(text(query_str),
                                               set_id=new_setmenu_id, menu_id=int(key), amount=int(set_content[key]))

        return {"setmenu_id": new_setmenu_id}, 201


@ns.route('/<int:setmenu_id>')
@ns.param("jwt", "로그인 시 얻은 JWT를 입력", _in="query", required=True)
class SetmenuEach(Resource):
    @ns.response(200, "세트메뉴 구성 목록 조회 성공", model=setmenu_each_get_success)
    def get(self, setmenu_id):
        if request.user_info is None:
            return {"message": "JWT must be provided!"}, 401

        with db_engine.connect() as connection:
            query_str = "SELECT * FROM `setmenus` WHERE `id` = :setmenu_id"
            set_basic_info = connection.execute(text(query_str), setmenu_id=setmenu_id).first()

            if set_basic_info is None:
                return {"message": "Requested 'setmenu_id' not found!"}, 404

            group_id = int(set_basic_info['group_id'])

            query_str = "SELECT * FROM `members` WHERE `group_id` = :group_id AND `user_id` = :user_id"
            chk_member = connection.execute(text(query_str), group_id=group_id, user_id=request.user_info['id']).first()

            if chk_member is None:
                return {"message": "Only member of this group can get setmenu info!"}, 403

            query_str = "SELECT `menus`.`name`, `set_contents`.`amount` FROM `menus` " \
                        "JOIN `set_contents` ON `menus`.`id` = `set_contents`.`menu_id` " \
                        "WHERE `set_contents`.`set_id` = :setmenu_id"
            query = connection.execute(text(query_str), setmenu_id=setmenu_id)

            setmenu_info = [dict(row) for row in query]

        return {"list": setmenu_info}, 200

    @ns.doc(body=setmenu_put_payload)
    @ns.response(200, "세트메뉴 정보 변경 성공")
    def put(self, setmenu_id):
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
            query_str = "SELECT * FROM `setmenus` WHERE `id` = :setmenu_id"
            setmenu_info = connection.execute(text(query_str), setmenu_id=setmenu_id).first()

            if setmenu_info is None:
                return {"message", "Requested 'setmenu_id' not found!"}, 404

            group_id = setmenu_info['group_id']

            query_str = "SELECT * FROM `members` WHERE `group_id` = :group_id AND `user_id` = :user_id"
            check_permission = connection.execute(text(query_str),
                                                  group_id=group_id, user_id=request.user_info['id']).first()

            if check_permission is None:
                return {"message": "You can't update setmenu in this group!"}, 403

            query_str = "UPDATE `setmenus` SET `price` = :price, `is_enabled` = :is_enabled, `updated_at` = :cur_time " \
                        "WHERE `id` = :setmenu_id"
            query = connection.execute(text(query_str), price=price, is_enabled=is_enabled,
                                       cur_time=datetime.utcnow(), setmenu_id=setmenu_id)

        return {"setmenu_id": setmenu_id}, 200
