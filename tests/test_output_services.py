"""Tests for M16 Output Services (PDF, PPTX, XLSX Generation & Output DLP)."""
import os
import pytest
from edith_x.modules.document.output import OutputServices
from edith_x.modules.execution.service import EnterpriseToolRegistry


def test_generate_pdf_with_output_dlp():
    service = OutputServices(storage_dir="tests/test_artifacts")
    # Provide content with accidental leaked card and token
    title = "Q4 Financial Disclosures"
    content = "Summary: Operational margin reached 24%.\nAudit note: card 4532 0150 1234 5678 on file."

    result = service.generate_document(
        format="pdf",
        title=title,
        content=content,
        org_id="org_compliance",
    )

    assert result["success"] is True
    assert result["format"] == "pdf"
    assert os.path.exists(result["file_path"])
    assert result["size_bytes"] > 100

    # Read generated PDF bytes and verify card is redacted by Output DLP
    with open(result["file_path"], "rb") as f:
        pdf_bytes = f.read()
    assert b"4532 0150 1234 5678" not in pdf_bytes
    assert b"[REDACTED_CREDIT_CARD]" in pdf_bytes


def test_generate_pptx_slides():
    service = OutputServices(storage_dir="tests/test_artifacts")
    sections = [
        {"title": "Overview", "points": ["Revenue up 15%", "CAC reduced by 22%"]},
        {"title": "Architecture", "points": ["Multi-tenant vector isolation", "Sub-ms semantic cache"]},
    ]

    result = service.generate_document(
        format="pptx",
        title="Executive AI Architecture",
        content="Board of Directors Review",
        sections=sections,
        org_id="org_exec",
    )

    assert result["success"] is True
    assert result["format"] == "pptx"
    assert os.path.exists(result["file_path"])
    assert result["size_bytes"] > 500


def test_generate_xlsx_sheet():
    service = OutputServices(storage_dir="tests/test_artifacts")
    rows = [
        {"Quarter": "Q1", "Revenue": 1200000, "Savings": 45000},
        {"Quarter": "Q2", "Revenue": 1450000, "Savings": 58000},
        {"Quarter": "Q3", "Revenue": 1600000, "Savings": 72000},
    ]

    result = service.generate_document(
        format="xlsx",
        title="Cost Optimization Report",
        content="Quarterly Financials",
        sections=[{"title": "Quarterly Ledger", "rows": rows}],
        org_id="org_finance",
    )

    assert result["success"] is True
    assert result["format"] == "xlsx"
    assert os.path.exists(result["file_path"])
    assert result["size_bytes"] > 500


def test_fastmcp_tool_registration():
    registry = EnterpriseToolRegistry()
    assert registry.has_tool("generate_document")
    tool = registry.get_tool("generate_document")
    assert tool is not None
    assert "format" in tool.parameters["properties"]
