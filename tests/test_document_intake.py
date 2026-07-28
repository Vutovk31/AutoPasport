import hashlib

import pytest

from app.document_intake import DocumentIntakeError, validate_document_intake


def test_accepts_pdf_work_order_and_normalizes_filename():
    payload = b"%PDF-1.7\nsynthetic document"

    result = validate_document_intake(
        document_type="work_order",
        filename="../../order.pdf",
        media_type="application/pdf; charset=binary",
        data=payload,
        max_upload_bytes=1024,
    )

    assert result.document_type == "work_order"
    assert result.original_name == "order.pdf"
    assert result.media_type == "application/pdf"
    assert result.suffix == ".pdf"
    assert result.size_bytes == len(payload)
    assert result.sha256 == hashlib.sha256(payload).hexdigest()


@pytest.mark.parametrize(
    ("document_type", "media_type", "payload", "expected_suffix"),
    [
        ("receipt", "image/jpeg", b"\xff\xd8\xffsynthetic", ".jpg"),
        ("diagnostic_report", "image/png", b"\x89PNG\r\n\x1a\nsynthetic", ".png"),
        ("service_act", "application/pdf", b"%PDF-synthetic", ".pdf"),
        ("estimate", "application/pdf", b"%PDF-synthetic", ".pdf"),
    ],
)
def test_accepts_supported_automotive_documents(document_type, media_type, payload, expected_suffix):
    result = validate_document_intake(
        document_type=document_type,
        filename="document",
        media_type=media_type,
        data=payload,
        max_upload_bytes=1024,
    )

    assert result.suffix == expected_suffix


def test_rejects_unknown_document_type():
    with pytest.raises(DocumentIntakeError, match="Unsupported document type"):
        validate_document_intake(
            document_type="correspondence",
            filename="message.pdf",
            media_type="application/pdf",
            data=b"%PDF-message",
            max_upload_bytes=1024,
        )


def test_rejects_spoofed_media_type():
    with pytest.raises(DocumentIntakeError, match="does not match"):
        validate_document_intake(
            document_type="receipt",
            filename="receipt.jpg",
            media_type="image/jpeg",
            data=b"%PDF-not-a-jpeg",
            max_upload_bytes=1024,
        )


def test_rejects_empty_and_oversized_documents():
    with pytest.raises(DocumentIntakeError, match="empty"):
        validate_document_intake(
            document_type="receipt",
            filename="receipt.jpg",
            media_type="image/jpeg",
            data=b"",
            max_upload_bytes=1024,
        )

    with pytest.raises(DocumentIntakeError, match="exceeds"):
        validate_document_intake(
            document_type="receipt",
            filename="receipt.jpg",
            media_type="image/jpeg",
            data=b"\xff\xd8\xfftoo-large",
            max_upload_bytes=4,
        )
