from flask_restful import Resource
from flask import request
from app import app, db_engine
from sqlalchemy import text
import jwt
from time import time
from datetime import datetime
from passlib.hash import pbkdf2_sha256


class User(Resource):
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

            with db_engine.connect() as connection:
                query_str = "SELECT * FROM `users` WHERE `email` = :email"
                chk_user = connection.execute(text(query_str), email=body['email']).first()

                if chk_user is not None:
                    return {"message": "Email already exists!"}, 403

                query_str = "INSERT INTO `users` SET `name`= :name, `email` = :email, " \
                            "`password` = :password, `created_at` = :cur_time, `updated_at` = :cur_time"
                query = connection.execute(text(query_str),
                                           name=body['name'],
                                           email=body['email'],
                                           password=pbkdf2_sha256.hash(body['password']),
                                           cur_time=datetime.utcnow())

            return {"user_id": int(query.lastrowid)}, 200

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
