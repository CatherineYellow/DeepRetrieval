import os
import sys
from func_timeout import func_timeout, FunctionTimedOut

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wikisql_lib.dbengine import DBEngine
from wikisql_lib.query import Query
from wikisql_lib.common import count_lines



# reference: lib at https://github.com/salesforce/WikiSQL/tree/master

class WikiSQLDatabaseSearcher:
    def __init__(self):
        self.timeout = 30

    def search(self, sql_query: str, db_path: str, db_id: str=None):
        try:
            results = func_timeout(self.timeout, self._search, args=(sql_query, db_path, db_id))

        except FunctionTimedOut:
            # print("Function timed out!")
            results = []

        return results

    def _search(self, sql_query: str, db_path: str, db_id: str=None):
        engine = DBEngine(db_path)
        wikisql_query = Query.from_sequence(sql_query)
        results = engine.execute_query(db_id, wikisql_query, lower=True)
        return results
