import io
import logging
from typing import Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from app.services.storage_service import storage_service

logger = logging.getLogger("analytics.pdf_exporter")


class PDFExporter:
    async def export(self, report_data: Dict[str, Any], file_key: str) -> str:
        """Generate a PDF document using ReportLab and save to storage_service."""
        logger.info(f"Generating PDF export: {file_key}")

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)

        styles = getSampleStyleSheet()

        # Define Custom Styles matching agency guidelines
        title_style = ParagraphStyle(
            name="TitleStyle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=colors.HexColor("#1B5E20"),  # Dark green
            alignment=0,  # Left align
            spaceAfter=15,
        )

        h2_style = ParagraphStyle(
            name="H2Style",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=colors.HexColor("#333333"),
            spaceBefore=12,
            spaceAfter=8,
        )

        meta_style = ParagraphStyle(
            name="MetaStyle", fontName="Helvetica-Oblique", fontSize=9, textColor=colors.HexColor("#666666"), spaceAfter=20
        )

        body_style = ParagraphStyle(
            name="BodyStyle",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            textColor=colors.HexColor("#444444"),
        )

        table_header_style = ParagraphStyle(
            name="TableHeader", parent=body_style, fontName="Helvetica-Bold", fontSize=9, textColor=colors.whitesmoke
        )

        story = []

        # 1. Title
        story.append(
            Paragraph(f"{report_data.get('report_type', 'N/A').replace('_', ' ').upper()} SUMMARY REPORT", title_style)
        )
        story.append(Paragraph(f"Generated at: {report_data.get('generated_at', '')}", meta_style))
        story.append(Spacer(1, 10))

        # 2. Summary Table
        story.append(Paragraph("Key Summary Indicators", h2_style))
        summary = report_data.get("summary", {})

        summary_data = []
        for k, v in summary.items():
            k_p = Paragraph(f"<b>{k.replace('_', ' ').title()}</b>", body_style)
            v_p = Paragraph(str(v), body_style)
            summary_data.append([k_p, v_p])

        if summary_data:
            summary_table = Table(summary_data, colWidths=[200, 300])
            summary_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F8E9")),  # light green tint
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C8E6C9")),
                        ("PADDING", (0, 0), (-1, -1), 6),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            story.append(summary_table)
        else:
            story.append(Paragraph("No summary indicators computed.", body_style))

        story.append(Spacer(1, 20))

        # 3. Records Table
        story.append(Paragraph("Detailed Records Log", h2_style))
        data_list = report_data.get("data", [])
        if data_list:
            headers = list(data_list[0].keys())

            # Format table data
            table_records = []

            # Add Headers row
            header_row = [Paragraph(f"<b>{h.replace('_', ' ').title()}</b>", table_header_style) for h in headers]
            table_records.append(header_row)

            # Add Rows
            for row in data_list:
                row_p = [Paragraph(str(row.get(h)), body_style) for h in headers]
                table_records.append(row_p)

            # ColWidth logic
            col_count = len(headers)
            col_width = 540 / col_count

            records_table = Table(table_records, colWidths=[col_width] * col_count)
            records_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E7D32")),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
                        ("PADDING", (0, 0), (-1, -1), 5),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            story.append(records_table)
        else:
            story.append(Paragraph("No records found matching filters.", body_style))

        # Build PDF Doc
        doc.build(story)

        pdf_bytes = buffer.getvalue()
        saved_path = await storage_service.save_file(pdf_bytes, file_key)
        return saved_path


pdf_exporter = PDFExporter()
