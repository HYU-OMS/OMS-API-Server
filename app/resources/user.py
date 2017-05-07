from flask_restplus import Resource, fields
from flask import request
from app import app, db_engine, api
from sqlalchemy import text
import jwt
from time import time
from datetime import datetime
from passlib.hash import pbkdf2_sha256
from uuid import uuid4
import lepl.apps.rfc3696


ns = api.namespace('user', description="유저 관련 API (회원가입, 로그인)")
user_post_payload = api.model('User_Post_Payload', {
    'name': fields.String("이름 (회원가입시에만 필요)"),
    'email': fields.String("이메일"),
    'password': fields.String("비밀번호")
})


@ns.route('')
class User(Resource):
    @ns.param("type", "동작 종류 ('signup' 또는 'signin')", _in="query", required=True)
    @ns.doc(body=user_post_payload)
    @ns.response(201, "회원가입 성공 시 새로 생성된 유저 고유번호 반환, 로그인 성공 시 JsonWebToken 반환")
    def post(self):
        if 'type' not in request.args:
            return {"message": "Argument 'type' must be provided!"}, 400

        body = request.get_json(silent=True, force=True)
        if body is None:
            return {"message": "Unable to get json post data!"}, 400

        if request.args['type'] == 'signup':
            if 'name' not in body:
                return {"message": "'name' not provided!"}, 400

            if 'email' not in body:
                return {"message": "'email' not provided!"}, 400

            if 'password' not in body:
                return {"message": "'password' not provided!"}, 400

            email_validator = lepl.apps.rfc3696.Email()
            if not email_validator(body['email']):
                return {"message": "Provided email is invalid!"}, 400

            name = body['name']
            email = body['email']
            password = pbkdf2_sha256.hash(body['password'])

            with db_engine.connect() as connection:
                query_str = "SELECT * FROM `users` WHERE `email` = :email"
                chk_user = connection.execute(text(query_str), email=body['email']).first()

                if chk_user is not None:
                    return {"message": "Email already exists!"}, 403

                with connection.begin() as transaction:
                    verification_uuid = str(uuid4())

                    query_str = "INSERT INTO `users` SET `name`= :name, `email` = :email, `password` = :password, " \
                                "`verification_uuid` = :uuid, `created_at` = :cur_time, `updated_at` = :cur_time"
                    query = connection.execute(text(query_str),
                                               name=name, email=email, password=password,
                                               uuid=verification_uuid, cur_time=datetime.utcnow())

                    new_user_id = query.lastrowid

            return {"user_id": new_user_id}, 201

        elif request.args['type'] == 'signin':
            if 'email' not in body:
                return {"message": "'email' not provided!"}, 400

            if 'password' not in body:
                return {"message": "'password' not provided!"}, 400

            with db_engine.connect() as connection:
                query_str = "SELECT * FROM `users` WHERE `email` = :email"
                chk_user = connection.execute(text(query_str), email=body['email']).first()

                if chk_user is None or pbkdf2_sha256.verify(body['password'], chk_user['password']) is False:
                    return {"message": "Wrong ID or Password!"}, 403

                # 현재 이메일 인증 기능을 사용하지 않음.
                # if chk_user['verified'] != 1:
                #     return {"message": "This account is not verified yet!"}, 403

                if chk_user['enabled'] != 1:
                    return {"message": "This account has been disabled. Please contact system administrator!"}

            return {
                "jwt": jwt.encode({
                    'user_id': chk_user['id'],
                    'user_name': chk_user['name'],
                    'user_email': chk_user['email'],
                    'exp': int(time()) + 86400
                }, key=app.config['JWT_SECRET_KEY'], algorithm='HS512').decode('utf-8')
            }, 200
        else:
            return {"message": "'type' must be 'signin' or 'signup'!"}, 400
