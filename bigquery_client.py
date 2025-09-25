"""
Simple BigQuery Client for LangGraph Order Analysis App
"""
import os
from typing import Dict, List, Any, Optional

from google.cloud import bigquery
from google.oauth2.credentials import Credentials
import structlog

logger = structlog.get_logger()


class BigQueryClient:
    """Simple BigQuery client wrapper"""

    def __init__(self, project_id: Optional[str] = None):
        # Use data warehouse project for both authentication and queries
        self.project_id = project_id 

        try:
            # Set environment variable to ensure consistent project usage
            os.environ["GOOGLE_CLOUD_PROJECT"] = self.project_id
            self.client = bigquery.Client(project=self.project_id)
            logger.info("BigQuery client initialized", project_id=self.project_id)
        except Exception as e:
            logger.error("Failed to initialize BigQuery client", error=str(e))
            self.client = None

    def execute_query(self, query: str, max_results: int = None, dry_run: bool = False) -> List[Dict[str, Any]]:
        """Execute a BigQuery query and return results as list of dictionaries"""
        if not self.client:
            raise RuntimeError("BigQuery client not initialized")

        try:
            logger.info("Executing BigQuery query",
                       query_preview=query[:200] + "..." if len(query) > 200 else query,
                       dry_run=dry_run,
                       max_results=max_results)

            # Configure job
            job_config = bigquery.QueryJobConfig()
            if dry_run:
                job_config.dry_run = True
                job_config.use_query_cache = False

            if max_results:
                job_config.maximum_bytes_billed = 100 * 1024 * 1024 * 1024  # 100GB limit

            job = self.client.query(query, job_config=job_config)

            if dry_run:
                # For dry run, return metadata about the query
                logger.info("Dry run completed",
                           total_bytes_processed=job.total_bytes_processed,
                           cache_hit=job.cache_hit)
                return [{
                    "dry_run": True,
                    "total_bytes_processed": job.total_bytes_processed,
                    "cache_hit": job.cache_hit,
                    "query_valid": True
                }]

            results = job.result(max_results=max_results)

            # Convert to list of dictionaries
            rows = []
            for row in results:
                rows.append(dict(row))

            logger.info("Query executed successfully", row_count=len(rows))
            return rows

        except Exception as e:
            logger.error("Query execution failed", error=str(e), query=query)
            raise

    def get_table_schema(self, dataset_id: str, table_id: str) -> List[Dict[str, str]]:
        """Get table schema information"""
        if not self.client:
            raise RuntimeError("BigQuery client not initialized")

        try:
            table_ref = self.client.dataset(dataset_id).table(table_id)
            table = self.client.get_table(table_ref)

            schema = []
            for field in table.schema:
                schema.append({
                    "name": field.name,
                    "type": field.field_type,
                    "mode": field.mode,
                    "description": field.description or ""
                })

            return schema

        except Exception as e:
            logger.error("Failed to get table schema", dataset_id=dataset_id, table_id=table_id, error=str(e))
            raise

    def list_tables(self, dataset_id: str) -> List[str]:
        """List tables in a dataset"""
        if not self.client:
            raise RuntimeError("BigQuery client not initialized")

        try:
            dataset_ref = self.client.dataset(dataset_id)
            tables = list(self.client.list_tables(dataset_ref))
            return [table.table_id for table in tables]

        except Exception as e:
            logger.error("Failed to list tables", dataset_id=dataset_id, error=str(e))
            raise