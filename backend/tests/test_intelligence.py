from app.services.document_intelligence import (
    analyse_document,
    extract_dates,
    extract_identifiers,
    extract_title,
)


def test_identifiers_are_extracted_from_codes():
    assert "ISO-27001" in extract_identifiers("Certified under ISO-27001 and SOC/2 controls.")


def test_iso_and_month_name_dates_are_found():
    dates = extract_dates("Issued 2026-01-15 and reviewed on March 3, 2026.")
    assert "2026-01-15" in dates
    assert any("March" in d for d in dates)


def test_title_is_first_meaningful_line():
    assert extract_title("\n 12 \n Vendor Continuity Policy\nbody", "fallback.txt") == "Vendor Continuity Policy"


def test_title_falls_back_to_filename_when_no_text():
    assert extract_title("", "fallback.txt") == "fallback.txt"


def test_analyse_document_fills_all_fields():
    text = "Vendor Continuity Policy\nISO-27001 controls apply from 2026-01-15.\n" + (
        "Backup restoration is tested every quarter for critical vendor services. " * 3
    )
    result = analyse_document([text], "policy.txt")
    assert result.title == "Vendor Continuity Policy"
    assert "ISO-27001" in result.identifiers
    assert "2026-01-15" in result.dates
    assert result.keywords
    assert result.key_points
