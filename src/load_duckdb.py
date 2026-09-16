import os
import json
import logging
from typing import List, Dict, Any

import duckdb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("DUCKDB_PATH", "warehouse.duckdb")


class DuckDBLoader:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self.con = duckdb.connect(self.db_path)

    def load_records(self, table_name: str, records: List[Dict[str, Any]], write_disposition: str = "append"):
        if not records:
            logger.info("No records to load for %s", table_name)
            return

        tmp_path = f"_tmp_{table_name}.jsonl"
        with open(tmp_path, "w") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")

        table_exists = self.con.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_name = ?",
            [table_name],
        ).fetchone()[0] > 0

        if not table_exists or write_disposition == "replace":
            self.con.execute(
                f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_json_auto('{tmp_path}')"
            )
        else:
            self.con.execute(
                f"INSERT INTO {table_name} SELECT * FROM read_json_auto('{tmp_path}')"
            )

        os.remove(tmp_path)
        logger.info("Loaded %d records into %s (%s)", len(records), table_name, self.db_path)

    def close(self):
        self.con.close()
