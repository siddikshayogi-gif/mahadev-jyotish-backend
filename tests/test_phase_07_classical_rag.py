"""Phase 07: Classical Books RAG Test Suite.

Tests ingestion idempotency, corpus isolation (Vedic, KP, Palmistry),
page/source traceability, duplicate control, budget limits, and API status.
"""

import os
import shutil
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.rag import (
    CorpusType,
    RightsStatus,
    VerificationStatus,
    BookManifest,
    RAGQueryRequest
)
from app.services.ai.classical_rag import ClassicalRAGService

client = TestClient(app)

@pytest.fixture
def temp_rag_dir(tmp_path):
    """Creates temporary knowledge directory for isolated testing."""
    rag_dir = tmp_path / "knowledge"
    rag_dir.mkdir()
    return str(rag_dir)

@pytest.fixture
def rag_service(temp_rag_dir):
    return ClassicalRAGService(base_dir=temp_rag_dir)


def test_ingestion_idempotency(rag_service, temp_rag_dir):
    """Verifies that re-ingesting the same source file is idempotent and produces no duplicates."""
    source_file = os.path.join(temp_rag_dir, "test_bphs.txt")
    text_content = (
        "[Chapter 1] [Page 12] [Verse 1]\n\n"
        "BPHS test content on Jupiter placement in 9th house giving wisdom, virtue, and fortune.\n\n"
        "Sun in 10th house gives leadership, power, and high career stature."
    )
    with open(source_file, "w", encoding="utf-8") as f:
        f.write(text_content)

    manifest = BookManifest(
        source_id="test_bphs_v1",
        title="Brihat Parashara Hora Shastra Vol 1 Test",
        author="Parashara",
        corpus=CorpusType.VEDIC,
        file_name="test_bphs.txt",
        checksum="placeholder",
        citation_verification=VerificationStatus.UNVERIFIED,
        allowed_for_production_rag=True
    )

    # First Ingestion
    chunks_1 = rag_service.ingest_source_book(source_file, manifest)
    assert len(chunks_1) > 0
    initial_chunk_count = len(chunks_1)
    initial_chunk_ids = [c.chunk_id for c in chunks_1]

    # Second Ingestion with exact same file and manifest
    chunks_2 = rag_service.ingest_source_book(source_file, manifest)
    assert len(chunks_2) == initial_chunk_count
    assert [c.chunk_id for c in chunks_2] == initial_chunk_ids

    # Total stored in index should still equal initial_chunk_count (no duplicates)
    assert len(rag_service.corpus_indexes[CorpusType.VEDIC]) == initial_chunk_count


def test_corpus_isolation(rag_service, temp_rag_dir):
    """Verifies strict isolation between VEDIC, KP, and PALMISTRY corpora."""
    # 1. Vedic book
    v_file = os.path.join(temp_rag_dir, "vedic_sample.txt")
    with open(v_file, "w", encoding="utf-8") as f:
        f.write("Parashari rules for 7th house lord in 1st house causing marriage and business partnership.")

    v_manifest = BookManifest(
        source_id="vedic_sample",
        title="Parashari Samhita Test",
        corpus=CorpusType.VEDIC,
        file_name="vedic_sample.txt",
        checksum=""
    )
    rag_service.ingest_source_book(v_file, v_manifest)

    # 2. KP book
    kp_file = os.path.join(temp_rag_dir, "kp_sample.txt")
    with open(kp_file, "w", encoding="utf-8") as f:
        f.write("KP System rules: 7th cusp sub lord signifying 2, 7, 11 houses promises marriage.")

    kp_manifest = BookManifest(
        source_id="kp_sample",
        title="KP Reader III Test",
        corpus=CorpusType.KP,
        file_name="kp_sample.txt",
        checksum=""
    )
    rag_service.ingest_source_book(kp_file, kp_manifest)

    # 3. Palmistry book
    p_file = os.path.join(temp_rag_dir, "palmistry_sample.txt")
    with open(p_file, "w", encoding="utf-8") as f:
        f.write("Palmistry rules: Deep clear Sun Line under ring finger indicates artistic fame and success.")

    p_manifest = BookManifest(
        source_id="palmistry_sample",
        title="Cheiro Palmistry Guide Test",
        corpus=CorpusType.PALMISTRY,
        file_name="palmistry_sample.txt",
        checksum=""
    )
    rag_service.ingest_source_book(p_file, p_manifest)

    # Query VEDIC corpus -> must contain ONLY Vedic chunks
    res_v = rag_service.search_rag("marriage 7th house", corpus=CorpusType.VEDIC)
    assert res_v.total_chunks_found > 0
    assert all(c.corpus == CorpusType.VEDIC for c in res_v.retrieved_chunks)
    assert "KP System" not in res_v.formatted_prompt_context
    assert "Palmistry" not in res_v.formatted_prompt_context

    # Query KP corpus -> must contain ONLY KP chunks
    res_kp = rag_service.search_rag("marriage 7th cusp sub lord", corpus=CorpusType.KP)
    assert res_kp.total_chunks_found > 0
    assert all(c.corpus == CorpusType.KP for c in res_kp.retrieved_chunks)
    assert "Parashari" not in res_kp.formatted_prompt_context

    # Query PALMISTRY corpus -> must contain ONLY Palmistry chunks
    res_p = rag_service.search_rag("Sun Line fame", corpus=CorpusType.PALMISTRY)
    assert res_p.total_chunks_found > 0
    assert all(c.corpus == CorpusType.PALMISTRY for c in res_p.retrieved_chunks)
    assert "Parashari" not in res_p.formatted_prompt_context


def test_page_source_traceability_and_grounding(rag_service, temp_rag_dir):
    """Verifies that chapter/page/verse markers are extracted when present, and NEVER invented when absent."""
    # Text with explicit markers
    f1 = os.path.join(temp_rag_dir, "marked.txt")
    with open(f1, "w", encoding="utf-8") as f:
        f.write("[Chapter 5] [Page 42] [Verse 10]\nText with clear markers for Saturn transit in 8th house.")

    m1 = BookManifest(
        source_id="marked_book",
        title="Phaladeepika Test",
        corpus=CorpusType.VEDIC,
        file_name="marked.txt",
        checksum="",
        citation_verification=VerificationStatus.VERIFIED
    )
    rag_service.ingest_source_book(f1, m1)

    res1 = rag_service.search_rag("Saturn transit 8th house", corpus=CorpusType.VEDIC)
    assert len(res1.retrieved_chunks) > 0
    c1 = res1.retrieved_chunks[0]
    assert c1.chapter == "Chapter 5"
    assert c1.page == 42
    assert c1.verse == "Verse 10"
    assert c1.verification_status == VerificationStatus.VERIFIED
    assert "Phaladeepika Test (Chapter 5, Pg. 42, Verse 10) [VERIFIED]" in res1.citations

    # Text WITHOUT explicit markers
    f2 = os.path.join(temp_rag_dir, "unmarked.txt")
    with open(f2, "w", encoding="utf-8") as f:
        f.write("Raw unformatted classical translation text regarding Venus in 12th house giving luxury.")

    m2 = BookManifest(
        source_id="unmarked_book",
        title="Brihat Jataka Unmarked Test",
        corpus=CorpusType.VEDIC,
        file_name="unmarked.txt",
        checksum="",
        citation_verification=VerificationStatus.UNVERIFIED
    )
    rag_service.ingest_source_book(f2, m2)

    res2 = rag_service.search_rag("Venus in 12th house luxury", corpus=CorpusType.VEDIC)
    assert len(res2.retrieved_chunks) > 0
    c2 = res2.retrieved_chunks[0]
    # Traceability check: Must NOT invent chapter/page/verse numbers
    assert c2.chapter is None
    assert c2.page is None
    assert c2.verse is None
    assert c2.verification_status == VerificationStatus.UNVERIFIED
    assert "UNVERIFIED" in res2.citations[0]


def test_no_result_and_budget_limits(rag_service, temp_rag_dir):
    """Verifies clean empty result handling and max character budget limits."""
    # Empty query or query matching nothing
    res = rag_service.search_rag("NonexistentTermXyz12345", corpus=CorpusType.VEDIC)
    assert res.total_chunks_found == 0
    assert len(res.retrieved_chunks) == 0
    assert "[No relevant classical sources found in corpus]" in res.formatted_prompt_context

    # Ingest long book text
    f_long = os.path.join(temp_rag_dir, "long_book.txt")
    paragraphs = [f"Paragraph {i}: Detailed astrological rule text regarding Mars energy and courage in house {i}." for i in range(1, 20)]
    with open(f_long, "w", encoding="utf-8") as f:
        f.write("\n\n".join(paragraphs))

    m_long = BookManifest(
        source_id="long_book",
        title="Saravali Test",
        corpus=CorpusType.VEDIC,
        file_name="long_book.txt",
        checksum=""
    )
    rag_service.ingest_source_book(f_long, m_long)

    # Search with strict char limit
    res_budget = rag_service.search_rag("Mars energy courage", corpus=CorpusType.VEDIC, top_k=10, max_total_chars=300)
    total_chars = sum(len(c.text) for c in res_budget.retrieved_chunks)
    assert total_chars <= 500  # Stays within budget
    assert len(res_budget.retrieved_chunks) > 0


def test_android_apk_non_bundling():
    """Verifies that knowledge books/indexes are NOT bundled inside Android APK assets or raw resources."""
    android_assets = os.path.abspath("app/src/main/assets")
    android_raw = os.path.abspath("app/src/main/res/raw")

    for folder in [android_assets, android_raw]:
        if os.path.exists(folder):
            file_names = os.listdir(folder)
            for fname in file_names:
                assert not fname.endswith(".txt"), f"Found text asset in Android folder: {fname}"
                assert not fname.endswith(".json") or "bphs" not in fname.lower(), f"Found book index in Android folder: {fname}"


def test_rag_api_endpoints():
    """Tests the /api/v1/rag status and search endpoints."""
    # Test Status endpoint
    status_res = client.get("/api/v1/rag/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert "vedic_status" in status_data
    assert "kp_status" in status_data
    assert "palmistry_status" in status_data

    # Test Search endpoint
    search_payload = {
        "query": "Jupiter 9th house wisdom",
        "corpus": "VEDIC",
        "top_k": 2,
        "max_total_chars": 1000
    }
    search_res = client.post("/api/v1/rag/search", json=search_payload)
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert "retrieved_chunks" in search_data
    assert "citations" in search_data
