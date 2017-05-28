from flask_restplus import Resource
from flask import request, make_response
from app import db_engine, api
from sqlalchemy import text
import app.modules.helper as helper
import json
import pandas
import tempfile
import os


class Download(Resource):
    def get(self):
        if request.user_info is None:
            return {"message": "JWT must be provided!"}, 401

        if 'type' not in request.args:
            return {"message": "'type' not specified!"}, 400

        action_type = request.args['type']

        if action_type == 'orders':
            if 'group_id' not in request.args:
                return {"message": "To get order list, please specify 'group_id'!"}, 400

            group_id = int(request.args['group_id'])

            with db_engine.connect() as connection:
                query_str = "SELECT * FROM `groups` WHERE `id` = :group_id AND `creator_id` = :creator_id"
                chk_if_creator = connection.execute(text(query_str), group_id=group_id,
                                                    creator_id=request.user_info['id']).first()

                if chk_if_creator is None:
                    return {"message": "Only creator of this group can get order list data!"}, 403

                query_str = "SELECT `id`, `order_menus`, `order_setmenus`, " \
                            "`table_id`, `total_price`, `created_at`, `updated_at` " \
                            "FROM `orders` " \
                            "WHERE `group_id` = :group_id AND `status` = 1 " \
                            "ORDER BY `id` ASC"
                query = connection.execute(text(query_str), group_id=group_id)

                order_list = [dict(row) for row in query]
                order_list = json.loads(str(json.dumps(order_list, default=helper.json_serial)))

            tmp_json_filename = tempfile.mktemp() + ".json"
            tmp_xlsx_filename = tempfile.mktemp() + ".xlsx"

            f = open(tmp_json_filename, "w")
            f.write(str(json.dumps(order_list)))
            f.close()

            pandas.read_json(tmp_json_filename).to_excel(tmp_xlsx_filename)

            f = open(tmp_xlsx_filename, "rb")
            data = f.read()
            f.close()

            os.remove(tmp_json_filename)
            os.remove(tmp_xlsx_filename)

            download_filename = "Group_" + str(group_id) + ".xlsx"

            resp = make_response(data)
            resp.headers['Content-Type'] = 'application/octet-stream'
            resp.headers['Content-Disposition'] = "attachment; filename=" + download_filename

            return resp

        return {"message": "Invalid 'type'!"}, 400
