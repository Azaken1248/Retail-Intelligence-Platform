import logging

from databricks import sql

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class DatabricksService:

    def __init__(self) -> None:
        settings = get_settings()
        self.server_hostname = settings.databricks_host
        self.http_path = settings.databricks_http_path
        self.access_token = settings.databricks_token
        self.gold_schema = settings.gold_schema

    def _get_connection(self):
        if not all([self.server_hostname, self.http_path, self.access_token]):
            raise ConnectionError(
                "Databricks credentials not configured. "
                "Set DATABRICKS_HOST, DATABRICKS_HTTP_PATH, and DATABRICKS_TOKEN "
                "environment variables."
            )
        return sql.connect(
            server_hostname=self.server_hostname,
            http_path=self.http_path,
            access_token=self.access_token,
        )

    def execute_query(self, query: str) -> list[dict]:
        logger.info("Executing query: %s…", query[:120])
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    columns = [desc[0] for desc in cursor.description]
                    return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception:
            logger.exception("Query execution failed")
            raise

    def get_view(self, view_name: str, limit: int | None = None) -> list[dict]:
        query = f"SELECT * FROM {self.gold_schema}.{view_name}"
        if limit:
            query += f" LIMIT {limit}"
        return self.execute_query(query)

    def health_ping(self) -> bool:
        try:
            self.execute_query("SELECT 1")
            return True
        except Exception:
            return False


db_service = DatabricksService()
