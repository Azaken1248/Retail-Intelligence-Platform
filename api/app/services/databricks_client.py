"""
Databricks SQL Warehouse service layer.

Provides a singleton abstraction over the Databricks SQL Connector so that
routers and the MCP server never manage connections directly. All queries
are executed as read-only operations against the Gold layer.
"""

import logging

from databricks import sql

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class DatabricksService:
    """Abstraction layer for Databricks SQL Warehouse connectivity."""

    def __init__(self) -> None:
        settings = get_settings()
        self.server_hostname = settings.databricks_host
        self.http_path = settings.databricks_http_path
        self.access_token = settings.databricks_token
        self.gold_schema = settings.gold_schema

    # ── Private ──────────────────────────────────────────────────────

    def _get_connection(self):
        """Open a new DBSQL connection using configured credentials."""
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

    # ── Public API ───────────────────────────────────────────────────

    def execute_query(self, query: str) -> list[dict]:
        """Execute a read-only SQL query and return rows as dictionaries."""
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
        """Convenience method to read an entire Gold-layer view."""
        query = f"SELECT * FROM {self.gold_schema}.{view_name}"
        if limit:
            query += f" LIMIT {limit}"
        return self.execute_query(query)

    def health_ping(self) -> bool:
        """Return True if the Databricks connection is alive."""
        try:
            self.execute_query("SELECT 1")
            return True
        except Exception:
            return False


# ── Singleton ────────────────────────────────────────────────────────
db_service = DatabricksService()
