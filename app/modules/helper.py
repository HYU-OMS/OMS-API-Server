from flask import request, make_response, jsonify
from app import db_engine, app
from sqlalchemy import text
import jwt
from datetime import datetime, timezone


# Request 요청 시 사전 수행 작업 (DB connection 생성 및 JWT 확인)
def before_request():
    request.user_info = None

    token = request.args.get('jwt', None)
    decoded_token = None
    if token is not None:
        try:
            decoded_token = jwt.decode(jwt=token, key=app.config['JWT_SECRET_KEY'], verify=True)
        except jwt.exceptions.DecodeError as err:
            return make_response(jsonify({"message": "Failed to decode jwt!"}), 401)
        except jwt.exceptions.ExpiredSignatureError as err:
            return make_response(jsonify({"message": "Provided jwt has been expired!"}), 401)

    if decoded_token is not None:
        with db_engine.connect() as connection:
            query_str = "SELECT * FROM `users` WHERE `id` = :id AND `enabled` = 1"
            result = connection.execute(text(query_str), id=decoded_token['user_id']).fetchone()

            if result is None:
                return make_response(jsonify({"message": "Requested user not found!"}), 404)
            else:
                result = dict(result)
                if result['auth_uuid'] != decoded_token['auth_uuid']:
                    return make_response(jsonify({"message": "Duplicate sign-in is not allowed!"}), 403)

                request.user_info = result

    return None


# Request 처리 완료 후 Response 직전 수행 작업
def after_request(response):
    return response


# JSON array serializer
def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, datetime):
        serial = obj.replace(tzinfo=timezone.utc).isoformat()
        return serial
    raise TypeError ("Type not serializable")
