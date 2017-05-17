from flask_restplus import Resource, fields
from flask import request
from app import db_engine, api
from sqlalchemy import text


ns = api.namespace('member', description="멤버 관련 API (목록 조회, 새로 추가, 권한 변경)")
member_post_payload = api.model('Member_Post_Payload', {
    'group_id': fields.Integer("그룹 고유번호"),
    "signup_code": fields.Integer("가입을 위해 필요한 그룹 인증코드")
})
member_put_payload = api.model('Member_Put_Payload', {
    "group_id": fields.Integer("그룹 고유번호"),
    "user_id": fields.Integer("유저 고유번호"),
    "role": fields.Integer("권한 값 (0: 일반 유저, 1: 중간 관리자, 2: 최고 관리자)")
})
member_get_success = api.model('Member_Get_Success', {
    "members_list": fields.List(fields.Raw({
        "id": "유저 고유번호",
        "name": "유저 이름",
        "role": "권한 값 (0: 일반 유저, 1: 중간 관리자, 2: 최고 관리자)"
    }))
})


@ns.route('')
@ns.param("jwt", "로그인 시 얻은 JWT를 입력", _in="query", required=True)
class Member(Resource):
    @ns.param("group_id", "그룹 고유번호 (정수값)", _in="query", required=True)
    @ns.response(200, "멤버 목록", model=member_get_success, as_list=True)
    def get(self):
        if request.user_info is None:
            return {"message": "JWT must be provided!"}, 401

        if 'group_id' not in request.args:
            return {"message": "Argument 'group_id' must be provided!"}, 400

        group_id = int(request.args['group_id'])

        with db_engine.connect() as connection:
            query_str = "SELECT * FROM `members` WHERE `group_id` = :group_id AND `user_id` = :user_id"
            chk_member = connection.execute(text(query_str),
                                            group_id=group_id, user_id=request.user_info['id']).first()

            if chk_member is None:
                return {"message": "You are not a member of this group!"}, 403

            query_str = "SELECT `users`.`name`, `users`.`id`, `members`.`role` FROM `members` " \
                        "JOIN `users` ON `users`.`id` = `members`.`user_id` " \
                        "WHERE `members`.`group_id` = :group_id " \
                        "ORDER BY `users`.`id` ASC"
            query = connection.execute(text(query_str), group_id=group_id)

            members_list = [dict(row) for row in query]

        return {"list": members_list}, 200

    @ns.doc(body=member_post_payload)
    @ns.response(201, "현재 그룹에 새로운 멤버 등록을 성공함")
    def post(self):
        if request.user_info is None:
            return {"message": "JWT must be provided!"}, 401

        body = request.get_json(silent=True, force=True)
        if body is None:
            return {"message": "Unable to get json post data!"}, 400

        if 'group_id' not in body:
            return {"message": "'group_id' not provided!"}, 400

        if 'signup_code' not in body:
            return {"message": "'signup_code' not provided!"}, 400

        if len(body['signup_code']) > 64:
            return {"message": "Maximum length of 'signup_code' is 64!"}, 400

        group_id = int(body['group_id'])
        signup_code = body['signup_code']

        with db_engine.connect() as connection:
            query_str = "SELECT * FROM `groups` WHERE `id` = :group_id"
            chk_group = connection.execute(text(query_str), group_id=group_id).first()

            if chk_group is None:
                return {"message": "Requested 'group_id' not found!"}, 404

            if chk_group['signup_code'] is None:
                return {"message": "Signup for this group is currently disabled!"}, 403
            elif chk_group['signup_code'] == signup_code:
                query_str = "SELECT * FROM `members` WHERE `group_id` = :group_id AND `user_id` = :user_id"
                chk_member = connection.execute(text(query_str),
                                                group_id=group_id, user_id=request.user_info['id']).first()

                if chk_member is not None:
                    return {"message": "Already a member of this group!"}, 403

                with connection.begin() as transaction:
                    query_str = "INSERT INTO `members` SET `group_id` = :group_id, `user_id` = :user_id, `role` = 0"
                    query = connection.execute(text(query_str), group_id=group_id, user_id=request.user_info['id'])
            else:
                return {"message": "Requested 'group_id' and 'signup_code' mismatch!"}, 403

        return {"group_id": group_id, "user_id": request.user_info['id']}, 200

    @ns.doc(body=member_put_payload)
    @ns.response(200, "권한 변경 성공")
    def put(self):
        if request.user_info is None:
            return {"message": "JWT must be provided!"}, 401

        body = request.get_json(silent=True, force=True)
        if body is None:
            return {"message": "Unable to get json post data!"}, 400

        if 'group_id' not in body:
            return {"message": "'group_id' not provided!"}, 400

        if 'user_id' not in body:
            return {"message": "'user_id' not provided!"}, 400

        if 'role' not in body:
            return {"message": "'role' not provided!"}, 400

        group_id = int(body['group_id'])
        user_id = int(body['user_id'])
        role = int(body['role'])

        if role < 0 or role > 2:
            return {"message": "'role' must be 0 or 1 or 2!"}, 400

        with db_engine.connect() as connection:
            query_str = "SELECT * FROM `members` WHERE `group_id` = :group_id AND `user_id` = :user_id AND `role` = 2"
            chk_permission = connection.execute(text(query_str),
                                                group_id=group_id, user_id=request.user_info['id']).first()

            if chk_permission is None:
                return {"message": "You are not a admin of this group!"}, 403

            query_str = "SELECT * FROM `members` WHERE `group_id` = :group_id AND `user_id` = :user_id"
            chk_user = connection.execute(text(query_str), group_id=group_id, user_id=user_id).first()

            if chk_user is None:
                return {"message": "Requested 'user_id' is not a member of this group!"}, 404

            query_str = "SELECT * FROM `groups` WHERE `id` = :group_id AND `creator_id` = :user_id"
            chk_creator = connection.execute(text(query_str), group_id=group_id, user_id=user_id).first()

            if chk_creator is not None:
                return {"message": "Can't change role of group creator!"}, 403

            query_str = "UPDATE `members` SET `role` = :role WHERE `group_id` = :group_id AND `user_id` = :user_id"
            query = connection.execute(text(query_str), role=role, group_id=group_id, user_id=user_id)

        return {
            "group_id": group_id,
            "user_id": user_id,
            "role": role
        }, 200

    @ns.param("group_id", "그룹 고유번호 (정수값)", _in="query", required=True)
    @ns.param("user_id", "유저 고유번호 (정수값)", _in="query", required=True)
    @ns.response(201, "현재 그룹에서 해당 멤버 제거 성공")
    def delete(self):
        if request.user_info is None:
            return {"message": "JWT must be provided!"}, 401

        if 'group_id' not in request.args:
            return {"message": "'group_id' not provided!"}, 400

        if 'user_id' not in request.args:
            return {"message": "'user_id' not provided!"}, 400

        group_id = int(request.args['group_id'])
        user_id = int(request.args['user_id'])

        with db_engine.connect() as connection:
            query_str = "SELECT * FROM `members` WHERE `group_id` = :group_id AND `user_id` = :user_id AND `role` = 2"
            chk_permission = connection.execute(text(query_str),
                                                group_id=group_id, user_id=request.user_info['id']).first()

            if chk_permission is None:
                return {"message": "You are not a admin of this group!"}, 403

            query_str = "SELECT * FROM `members` WHERE `group_id` = :group_id AND `user_id` = :user_id"
            chk_user = connection.execute(text(query_str), group_id=group_id, user_id=user_id).first()

            if chk_user is None:
                return {"message": "Requested 'user_id' is not a member of this group!"}, 404

            query_str = "SELECT * FROM `groups` WHERE `id` = :group_id AND `creator_id` = :user_id"
            chk_creator = connection.execute(text(query_str), group_id=group_id, user_id=user_id).first()

            if chk_creator is not None:
                return {"message": "Can't delete group creator!"}, 403

            with connection.begin() as transaction:
                query_str = "DELETE FROM `members` WHERE `group_id` = :group_id AND `user_id` = :user_id"
                query = connection.execute(text(query_str), group_id=group_id, user_id=user_id)

        return {
            "group_id": group_id,
            "user_id": user_id
        }, 200
