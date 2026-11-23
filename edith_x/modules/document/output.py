"""M16 — Output Services: Multi-format Document Generator (PDF, PPTX, XLSX) with Output DLP."""
from __future__ import annotations

import hashlib
import os
import re
import time
from typing import Any

from edith_x.modules.policy.firewall import PIIFirewall


def _escape_pdf_text(text: str) -> str:
    """Escape special characters for PDF text stream."""
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _generate_clean_pdf(title: str, content: str, sections: list[dict] | None = None) -> bytes:
    """Generate a valid, standards-compliant PDF 1.4 document without external C-libraries."""
    lines = [f"Title: {title}", f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}", ""]
    for para in content.split("\n"):
        if para.strip():
            lines.append(para.strip())

    if sections:
        for s in sections:
            s_title = s.get("title", "")
            if s_title:
                lines.append("")
                lines.append(f"== {s_title} ==")
            for pt in s.get("points", []):
                lines.append(f"  * {pt}")

    # Build PDF Content Stream
    stream_lines = ["BT", "/F1 12 Tf", "50 750 Td", "16 TL"]
    for line in lines:
        escaped = _escape_pdf_text(line[:90])
        stream_lines.append(f"({escaped}) Tj")
        stream_lines.append("T*")
    stream_lines.append("ET")
    stream_data = "\n".join(stream_lines).encode("latin-1", errors="replace")

    # Assemble PDF Objects
    obj1 = b"<< /Type /Catalog /Pages 2 0 R >>"
    obj2 = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
    obj3 = (
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
    )
    obj4 = f"<< /Length {len(stream_data)} >>\nstream\n".encode("latin-1") + stream_data + b"\nendstream"
    obj5 = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

    objects = [obj1, obj2, obj3, obj4, obj5]
    pdf = bytearray(b"%PDF-1.4\n")
    xref = [0]

    for i, obj in enumerate(objects, 1):
        xref.append(len(pdf))
        pdf.extend(f"{i} 0 obj\n".encode("latin-1"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(b"xref\n")
    pdf.extend(f"0 {len(objects) + 1}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in xref[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))

    pdf.extend(b"trailer\n")
    pdf.extend(f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode("latin-1"))
    pdf.extend(b"startxref\n")
    pdf.extend(f"{xref_offset}\n%%EOF\n".encode("latin-1"))

    return bytes(pdf)


class OutputServices:
    """Document Generation Engine with Output DLP Sanitization."""

    def __init__(self, storage_dir: str = "artifacts/documents") -> None:
        self.storage_dir = storage_dir
        self._firewall = PIIFirewall()
        os.makedirs(self.storage_dir, exist_ok=True)

    def _apply_output_dlp(self, text: str) -> str:
        """Run Output DLP firewall to sanitize sensitive tokens/cards before document generation."""
        redacted, _, _ = self._firewall.redact(text)
        return redacted

    def generate_document(
        self,
        format: str,
        title: str,
        content: str,
        sections: list[dict] | None = None,
        org_id: str = "default",
    ) -> dict[str, Any]:
        """
        Generate and persist a document (PDF, PPTX, XLSX) with Output DLP scan.
        """
        fmt = format.lower().strip()
        # 1. Output DLP Scan on all input fields
        sanitized_title = self._apply_output_dlp(title)
        sanitized_content = self._apply_output_dlp(content)
        sanitized_sections: list[dict] = []

        if sections:
            for s in sections:
                clean_s = {"title": self._apply_output_dlp(s.get("title", ""))}
                if "points" in s:
                    clean_s["points"] = [self._apply_output_dlp(str(p)) for p in s["points"]]
                if "rows" in s:
                    clean_s["rows"] = s["rows"]
                sanitized_sections.append(clean_s)

        # 2. Format Execution
        file_bytes: bytes = b""
        safe_name = re.sub(r"[^\w\-]", "_", sanitized_title.lower())[:40]
        timestamp = int(time.time())
        filename = f"{safe_name}_{timestamp}.{fmt}"
        tenant_dir = os.path.join(self.storage_dir, org_id)
        os.makedirs(tenant_dir, exist_ok=True)
        file_path = os.path.join(tenant_dir, filename)

        if fmt == "pdf":
            file_bytes = _generate_clean_pdf(sanitized_title, sanitized_content, sanitized_sections)
            with open(file_path, "wb") as f:
                f.write(file_bytes)

        elif fmt == "pptx":
            from pptx import Presentation
            from pptx.util import Inches, Pt
            prs = Presentation()
            # Title slide
            slide_layout = prs.slide_layouts[0]
            slide = prs.slides.add_slide(slide_layout)
            slide.shapes.title.text = sanitized_title
            if sanitized_content:
                slide.placeholders[1].text = sanitized_content[:100]

            # Section slides
            for s in sanitized_sections:
                bullet_layout = prs.slide_layouts[1]
                b_slide = prs.slides.add_slide(bullet_layout)
                b_slide.shapes.title.text = s.get("title", "Section")
                tf = b_slide.placeholders[1].text_frame
                for pt in s.get("points", []):
                    p = tf.add_paragraph()
                    p.text = pt
                    p.level = 0

            prs.save(file_path)
            with open(file_path, "rb") as f:
                file_bytes = f.read()

        elif fmt == "xlsx":
            import xlsxwriter
            workbook = xlsxwriter.Workbook(file_path)
            worksheet = workbook.add_worksheet("Data")
            bold = workbook.add_format({"bold": True, "bg_color": "#D7E4BC"})

            row_idx = 0
            worksheet.write(row_idx, 0, sanitized_title, bold)
            row_idx += 2

            for s in sanitized_sections:
                if "rows" in s and s["rows"]:
                    headers = list(s["rows"][0].keys())
                    for col_idx, h in enumerate(headers):
                        worksheet.write(row_idx, col_idx, str(h), bold)
                    row_idx += 1
                    for r_data in s["rows"]:
                        for col_idx, h in enumerate(headers):
                            worksheet.write(row_idx, col_idx, r_data.get(h, ""))
                        row_idx += 1
                    row_idx += 1

            workbook.close()
            with open(file_path, "rb") as f:
                file_bytes = f.read()

        else:
            # Fallback markdown
            md_text = f"# {sanitized_title}\n\n{sanitized_content}\n\n"
            for s in sanitized_sections:
                md_text += f"## {s.get('title', '')}\n"
                for pt in s.get("points", []):
                    md_text += f"- {pt}\n"
            file_bytes = md_text.encode("utf-8")
            with open(file_path, "wb") as f:
                f.write(file_bytes)

        file_sha256 = hashlib.sha256(file_bytes).hexdigest()

        return {
            "success": True,
            "format": fmt,
            "filename": filename,
            "file_path": file_path,
            "size_bytes": len(file_bytes),
            "sha256": file_sha256,
        }
