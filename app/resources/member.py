from flask_restplus import Resource, fields
from flask import request
from app import db_engine, api
from sqlalchemy import text
from datetime import datetime


ns = api.namespace('member', description="멤버 관련 API (목록 조회, 새로 추가, 권한 변경)")
member_post_payload = api.model('Member_Post_Payload', {
    'user_id': fields.Integer("유저 고유번호 (둘 중 하나는 필수, 둘 다 주어지면 user_id 우선으로 적용)"),
    'user_email': fields.String("유저 이메일 (둘 중 하나는 필수)")
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

        group_id = int(body['group_id'])

        with db_engine.connect() as connection:
            query_str = "SELECT * FROM `members` WHERE `group_id` = :group_id AND `user_id` = :user_id"
            chk_permission = connection.execute(text(query_str),
                                                group_id=group_id, user_id=request.user_info['id']).first()

            if chk_permission is None or int(chk_permission['role']) < 2:
                return {"message": "You are not a admin of this group!"}, 403

            if 'user_id' not in body:
                if 'email' not in body:
                    return {"message": "Either 'user_id' or 'email' must be provided!"}, 400

                query_str = "SELECT * FROM `users` WHERE `email` = :email"
                chk_user = connection.execute(text(query_str), email=body['email']).first()

                if chk_user is None:
                    return {"message": "Requested 'email' not exists!"}, 404

                user_id = int(chk_user['id'])
            else:
                query_str = "SELECT * FROM `users` WHERE `id` = :user_id"
                chk_user = connection.execute(text(query_str), user_id=body['user_id']).first()

                if chk_user is None:
                    return {"message": "Requested 'user_id' not exists!"}, 404

                user_id = int(body['user_id'])

            query_str = "SELECT * FROM `members` WHERE `group_id` = :group_id AND `user_id` = :user_id"
            chk_member_exists = connection.execute(text(query_str),
                                                   group_id=group_id, user_id=user_id).first()

            if chk_member_exists is not None:
                return {"message": "Requested user is already member of this group!"}, 403

            query_str = "INSERT INTO `members` SET `group_id` = :group_id, `user_id` = :user_id," \
                        "`created_at` = :cur_time, `updated_at` = :cur_time"
            query = connection.execute(text(query_str), group_id=body['group_id'], user_id=user_id,
                                       cur_time=datetime.utcnow())

        return {
            "user_id": user_id,
            "group_id": group_id
        }, 200

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
                return {"message": "Requested combination of 'group_id' and 'user_id' not exists!"}, 404

            query_str = "SELECT * FROM `groups` WHERE `id` = :group_id AND `creator_id` = :user_id"
            chk_creator = connection.execute(text(query_str), group_id=group_id, user_id=user_id).first()

            if chk_creator is not None:
                return {"message": "Can't change role of group creator!"}, 403

            query_str = "UPDATE `members` SET `role` = :role, `updated_at` = :cur_time" \
                        " WHERE `group_id` = :group_id AND `user_id` = :user_id"
            query = connection.execute(text(query_str), role=role, cur_time=datetime.utcnow(),
                                       group_id=group_id, user_id=user_id)

        return {
            "group_id": group_id,
            "user_id": user_id,
            "role": role
        }, 200
