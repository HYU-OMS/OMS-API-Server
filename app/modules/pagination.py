from sqlalchemy import text
import math
from app import db_engine


class Pagination:
    def __init__(self, fetch, count, order, current_page, connection=None, list_num=10, page_num=4, fetch_params=None):
        self.connection = connection
        self.sql_query = {'count': count, 'fetch': fetch, 'order': order}
        self.list_num = int(list_num)
        self.page_num = int(page_num)
        self.current_page = int(current_page)
        self.fetch_params = fetch_params if fetch_params is not None else dict()

    def get_result(self):
        auto_close = False
        if self.connection is None:
            auto_close = True
            self.connection = db_engine.connect()

        total_cnt = self.connection.execute(text(self.sql_query['count']), self.fetch_params).fetchone()['cnt']
        total_page = int(math.ceil(float(total_cnt) / self.list_num))
        current_page = max(1, min(self.current_page, total_page))
        current_block = int(math.ceil(float(current_page) / self.page_num))
        start_page = (current_block - 1) * self.page_num + 1
        end_page = current_block * self.page_num
        total_block = int(math.ceil(float(total_page) / self.page_num))
        start_num = (current_page - 1) * self.list_num

        list_query_str = "{} {} LIMIT {}, {}".format(self.sql_query['fetch'], self.sql_query['order'], start_num, self.list_num)

        query = self.connection.execute(text(list_query_str), self.fetch_params)
        result = [dict(row) for row in query]

        if auto_close:
            self.connection.close()

        paging = []

        if start_page > 1:
            paging.append({'num': start_page - 1, 'text': '«', 'current': False})

        i = start_page
        while i <= end_page and i <= total_page:
            paging.append({'num': i, 'text': i, 'current': (i == current_page)})
            i += 1

        if current_block < total_block:
            paging.append({'num': end_page + 1, 'text': '»', 'current': False})

        if total_page == 1:
            paging = []

        return result, paging
