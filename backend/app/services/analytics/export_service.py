import json
import uuid
import logging
from typing import Dict, Any
from app.services.storage_service import storage_service
from app.services.analytics.pdf_exporter import pdf_exporter
from app.services.analytics.csv_exporter import csv_exporter
from app.services.analytics.xlsx_exporter import xlsx_exporter

logger = logging.getLogger("analytics.export_service")


class ExportService:
    async def generate_export(self, report_data: Dict[str, Any], format: str) -> str:
        """Route report data to the specified format generator and save in storage."""
        format_upper = format.upper()
        report_id = uuid.uuid4()
        file_key = f"reports/report_{report_id}.{format_upper.lower()}"

        logger.info(f"Routing export request for format: {format_upper} to key: {file_key}")

        if format_upper == "PDF":
            return await pdf_exporter.export(report_data, file_key)
        elif format_upper == "CSV":
            return await csv_exporter.export(report_data, file_key)
        elif format_upper == "XLSX":
            return await xlsx_exporter.export(report_data, file_key)
        elif format_upper == "JSON":
            # Direct JSON write
            json_bytes = json.dumps(report_data, indent=2).encode("utf-8")
            saved_path = await storage_service.save_file(json_bytes, file_key)
            return saved_path
        else:
            raise ValueError(f"Unsupported export format: {format_upper}")


export_service = ExportService()
