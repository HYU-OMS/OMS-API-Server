from flask_restplus import Resource, fields
from flask import request
from app import app, db_engine, api
from sqlalchemy import text
import jwt
from time import time
from datetime import datetime
import requests
import json


ns = api.namespace('user', description="유저 관련 API (Facebook 로그인, Facebook Application ID : 433842833659960)")
user_post_payload = api.model('User_Post_Payload', {
    'userID': fields.String("Facebook User ID"),
    'accessToken': fields.String("Facebook Access Token")
})


@ns.route('')
class User(Resource):
    @ns.param("type", "동작 종류 (현재는 'facebook' 만 가능)", _in="query", required=True)
    @ns.doc(body=user_post_payload)
    @ns.response(200, "로그인 성공 시 JsonWebToken 반환")
    def post(self):
        if 'type' not in request.args:
            return {"message": "Argument 'type' must be provided!"}, 400

        body = request.get_json(silent=True, force=True)
        if body is None:
            return {"message": "Unable to get json post data!"}, 400

        if request.args['type'] == 'signup':
            """
            if 'name' not in body:
                return {"message": "'name' not provided!"}, 400

            if 'email' not in body:
                return {"message": "'email' not provided!"}, 400

            if 'password' not in body:
                return {"message": "'password' not provided!"}, 400

            email_validator = lepl.apps.rfc3696.Email()
            if not email_validator(body['email']):
                return {"message": "Provided email is invalid!"}, 400

            if len(body['name']) > 64:
                return {"message": "Length of 'name' must be smaller than 64!"}, 400

            if len(body['email']) > 64:
                return {"message": "Length of 'email' must be smaller than 64!"}, 400

            name = body['name']
            email = body['email']
            password = pbkdf2_sha256.hash(body['password'])

            with db_engine.connect() as connection:
                query_str = "SELECT * FROM `users` WHERE `email` = :email"
                chk_user = connection.execute(text(query_str), email=body['email']).first()

                if chk_user is not None:
                    return {"message": "Email already exists!"}, 403

                with connection.begin() as transaction:
                    query_str = "INSERT INTO `users` SET `name`= :name, `email` = :email, `password` = :password, " \
                                "`created_at` = :cur_time, `updated_at` = :cur_time"
                    query = connection.execute(text(query_str),
                                               name=name, email=email, password=password, cur_time=datetime.utcnow())

                    new_user_id = query.lastrowid

            return {"user_id": new_user_id}, 201
            """
            return {"message": "Please use Social authentication!"}, 503

        elif request.args['type'] == 'signin':
            """
                        if 'email' not in body:
                return {"message": "'email' not provided!"}, 400

            if 'password' not in body:
                return {"message": "'password' not provided!"}, 400

            with db_engine.connect() as connection:
                query_str = "SELECT * FROM `users` WHERE `email` = :email"
                chk_user = connection.execute(text(query_str), email=body['email']).first()

                if chk_user is None or pbkdf2_sha256.verify(body['password'], chk_user['password']) is False:
                    return {"message": "Wrong ID or Password!"}, 403

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
            """
            return {"message": "Please use Social authentication!"}, 503

        elif request.args['type'] == 'facebook':
            if 'userID' not in body:
                return {"message": "'userID' not provided!"}, 400

            if 'accessToken' not in body:
                return {"message": "'accessToken' not provided!"}, 400

            fb_user_id = body['userID']
            fb_access_token = body['accessToken']

            params = {"access_token": fb_access_token, "fields": "id,name"}
            res = requests.get("https://graph.facebook.com/v2.9/me", params=params)
            status_code = res.status_code
            content = json.loads(res.text)

            if not res.ok:
                return content['error'], status_code

            if content['id'] != fb_user_id:
                return {"message": "Provided 'userID' does not match with 'accessToken'!"}, 400

            with db_engine.connect() as connection:
                query_str = "SELECT * FROM `users` WHERE `fb_id` = :fb_id"
                chk_user = connection.execute(text(query_str), fb_id=fb_user_id).first()

                if chk_user is None:
                    with connection.begin() as transaction:
                        query_str = "INSERT INTO `users` SET `name` = :name, `fb_id` = :fb_id, `verified` = 1, " \
                                    "`created_at` = :cur_time, `updated_at` = :cur_time"
                        query = connection.execute(text(query_str), name=content['name'],
                                                   fb_id=fb_user_id, cur_time=datetime.utcnow())

                    query_str = "SELECT * FROM `users` WHERE `fb_id` = :fb_id"
                    chk_user = connection.execute(text(query_str), fb_id=fb_user_id).first()

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
            return {"message": "Invalid 'type' given!"}, 400
