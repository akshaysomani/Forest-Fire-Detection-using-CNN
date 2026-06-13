import csv
import io
import logging
from typing import Dict, Any
from app.services.storage_service import storage_service

logger = logging.getLogger("analytics.csv_exporter")


class CSVExporter:
    async def export(self, report_data: Dict[str, Any], file_key: str) -> str:
        """Generate a CSV buffer and save it to storage_service."""
        logger.info(f"Generating CSV export: {file_key}")
        
        output = io.StringIO()
        writer = csv.writer(output)

        # 1. Title & Header Info
        writer.writerow(["REPORT TYPE", report_data.get("report_type", "N/A").upper()])
        writer.writerow(["GENERATED AT", report_data.get("generated_at", "")])
        writer.writerow([])

        # 2. Write Summary Section
        writer.writerow(["--- SUMMARY ---"])
        summary = report_data.get("summary", {})
        for k, v in summary.items():
            writer.writerow([k.replace("_", " ").title(), v])
        writer.writerow([])

        # 3. Write Data Table
        writer.writerow(["--- REPORT DATA ---"])
        data_list = report_data.get("data", [])
        if data_list:
            headers = list(data_list[0].keys())
            writer.writerow(headers)
            for row in data_list:
                writer.writerow([row.get(h) for h in headers])
        else:
            writer.writerow(["No records found matching filters."])

        # Save to storage
        csv_bytes = output.getvalue().encode("utf-8")
        saved_path = await storage_service.save_file(csv_bytes, file_key)
        return saved_path


csv_exporter = CSVExporter()
