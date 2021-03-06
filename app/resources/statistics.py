from flask_restplus import Resource, fields
from flask import request
from app import db_engine, api
from sqlalchemy import text
import app.modules.helper as helper
import json

ns = api.namespace('statistics', description="통계 API")
statistics_get_success = api.model('Statistics_Get_Success', {
    "sales_per_menu": fields.List(fields.Raw({
        "menu_id": "메뉴 고유번호",
        "cnt": "메뉴별 판매 비율"
    })),
    "delays_per_menu": fields.List(fields.Raw({
        'menu_id': "각 메뉴의 고유번호",
        'avg_delay': '메뉴별 대기열 처리 평균 시간'
    })),
    "order_rank_list": fields.List(fields.Raw({
        'name': "유저 이름",
        'user_id': "유저 고유번호",
        'cnt': '해당 그룹에서 이 유저가 받은 주문 수량의 합'
    })),
    "order_status_per_hour": fields.List(fields.Raw({
        'time_elapsed': "현재로부터 지난 시간 (Hour 단위)",
        'cnt': '해당 시간 구간에 들어온 주문 수'
    }))
})


@ns.route('')
@ns.param("jwt", "로그인 시 얻은 JWT를 입력 (group_id 를 명시할 경우는 필수)", _in="query", required=False)
class Statistics(Resource):
    @ns.param("group_id", "그룹 고유번호, 비워둘 경우 시간대별 주문 현황만 가져옴.", _in="query", required=False)
    @ns.response(200, "통계 정보를 가져온다.", model=statistics_get_success)
    def get(self):
        group_id = None
        if 'group_id' in request.args and request.args['group_id'] != "":
            group_id = int(request.args['group_id'])

            if request.user_info is None:
                return {"message": "JWT must be provided!"}, 401

        with db_engine.connect() as connection:
            if group_id is not None:
                query_str = "SELECT * FROM `members` WHERE `group_id` = :group_id AND `user_id` = :user_id"
                chk_member = connection.execute(text(query_str), group_id=group_id, user_id=request.user_info['id']).first()

                if chk_member is None:
                    return {"message": "Only member of this group can get statistics!"}, 403

                query_str = "SELECT `menu_id`, SUM(`amount`) AS `cnt` FROM `order_transactions` " \
                            "WHERE `group_id` = :group_id AND `is_approved` = 1 GROUP BY `menu_id`"
                query = connection.execute(text(query_str), group_id=group_id)
                sales_per_menu = [dict(row) for row in query]

                total_sales_count = 0
                for each_menu_data in sales_per_menu:
                    total_sales_count += int(each_menu_data['cnt'])

                for each_menu_data in sales_per_menu:
                    each_menu_data['cnt'] = round(float(each_menu_data['cnt']) / float(total_sales_count) * 100.0)

                query_str = "SELECT `menu_id`, " \
                            "CAST(AVG((UNIX_TIMESTAMP(`updated_at`) - UNIX_TIMESTAMP(`created_at`)) / `amount`) " \
                            "AS UNSIGNED) AS `avg_delay` FROM `order_transactions` " \
                            "WHERE `group_id` = :group_id AND `is_delivered` = 1 GROUP BY `menu_id`"
                query = connection.execute(text(query_str), group_id=group_id)
                delays_per_menu = [dict(row) for row in query]

                query_str = "SELECT `users`.`name`, `orders`.`user_id`, COUNT(`orders`.`id`) AS `cnt` FROM `orders` " \
                            "JOIN `users` ON `users`.`id` = `orders`.`user_id` " \
                            "WHERE `orders`.`group_id` = :group_id AND `orders`.`status` = 1 " \
                            "GROUP BY `orders`.`user_id` " \
                            "ORDER BY `cnt` DESC"
                query = connection.execute(text(query_str), group_id=group_id)
                order_rank_list = [dict(row) for row in query]

                query_str = "SELECT CAST(((UNIX_TIMESTAMP(NOW()) - UNIX_TIMESTAMP(`created_at`)) / 3600) " \
                            "AS UNSIGNED) AS `time_elapsed`, COUNT(`id`) AS `cnt` FROM `orders` " \
                            "WHERE `group_id` = :group_id AND `status` = 1 " \
                            "AND UNIX_TIMESTAMP(`created_at`) > (UNIX_TIMESTAMP(NOW()) - 86400) " \
                            "GROUP BY `time_elapsed`"
                query = connection.execute(text(query_str), group_id=group_id)
                order_status_per_hour = [dict(row) for row in query]

                result = json.loads(str(json.dumps({
                    "sales_per_menu": sales_per_menu,
                    "delays_per_menu": delays_per_menu,
                    "order_rank_list": order_rank_list,
                    "order_status_per_hour": order_status_per_hour
                }, default=helper.json_serial)))
            else:
                query_str = "SELECT CAST(((UNIX_TIMESTAMP(NOW()) - UNIX_TIMESTAMP(`created_at`)) / 3600) AS UNSIGNED) " \
                            "AS `time_elapsed`, COUNT(`id`) AS `cnt` FROM `orders` " \
                            "WHERE `status` = 1 AND UNIX_TIMESTAMP(`created_at`) > (UNIX_TIMESTAMP(NOW()) - 86400) " \
                            "GROUP BY `time_elapsed`"
                query = connection.execute(text(query_str))
                order_status_per_hour = [dict(row) for row in query]

                result = json.loads(str(json.dumps({
                    "order_status_per_hour": order_status_per_hour
                }, default=helper.json_serial)))

        return result, 200
