"""Classical RAG Service Engine.

Provides server-side ingestion, chunking, corpus-isolated retrieval, and citation traceability
for classical astrology and palmistry source texts.
"""

import os
import re
import glob
import json
import hashlib
import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from app.schemas.rag import (
    CorpusType,
    RightsStatus,
    VerificationStatus,
    BookManifest,
    TextChunk,
    RAGQueryRequest,
    RAGQueryResult,
    CorpusStatusResult
)

# Root knowledge directory
_root_knowledge = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../knowledge"))
_backend_knowledge = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../knowledge"))
KNOWLEDGE_BASE_DIR = _root_knowledge if os.path.exists(_root_knowledge) else _backend_knowledge

class ClassicalRAGService:
    """Server-side ingestion, vector/hybrid search, and citation service for classical sources."""

    def __init__(self, base_dir: str = KNOWLEDGE_BASE_DIR):
        self.base_dir = base_dir
        self.source_books_dir = os.path.join(base_dir, "source_books")
        self.processed_dir = os.path.join(base_dir, "processed")
        self.metadata_dir = os.path.join(base_dir, "metadata")
        self.indexes_dir = os.path.join(base_dir, "indexes")

        self._ensure_directories()

        # Separate corpus indexes
        self.corpus_indexes: Dict[CorpusType, List[TextChunk]] = {
            CorpusType.VEDIC: [],
            CorpusType.KP: [],
            CorpusType.PALMISTRY: []
        }
        # Simple tag index for faster retrieval
        self.tag_indexes: Dict[CorpusType, Dict[str, List[int]]] = {
            CorpusType.VEDIC: {},
            CorpusType.KP: {},
            CorpusType.PALMISTRY: {}
        }
        self.manifests: Dict[str, BookManifest] = {}
        self.token_cache = {}

        # Load any existing persisted chunks and manifests
        self.load_persisted_data()

    def _ensure_tag_index(self, corpus: CorpusType):
        """Ensures tag index and token cache are built for the corpus."""
        if not self.tag_indexes.get(corpus):
            self._build_tag_index(corpus)

    def _build_tag_index(self, corpus: CorpusType):
        self.tag_indexes[corpus] = {}
        for i, chunk in enumerate(self.corpus_indexes[corpus]):
            key = (corpus, i)
            if key not in self.token_cache:
                self.token_cache[key] = set(re.findall(r'[\u0900-\u097F\w]+', chunk.text.lower()))

            tags = chunk.metadata.get("tags", [])
            for tag in tags:
                if tag not in self.tag_indexes[corpus]:
                    self.tag_indexes[corpus][tag] = []
                self.tag_indexes[corpus][tag].append(i)
        print(f"DEBUG: Built tag index for {corpus.value}")

    def _ensure_directories(self):
        for path in [
            self.source_books_dir,
            os.path.join(self.source_books_dir, "palmistry"),
            os.path.join(self.source_books_dir, "vedic"),
            os.path.join(self.source_books_dir, "kp"),
            self.processed_dir,
            self.metadata_dir,
            self.indexes_dir
        ]:
            os.makedirs(path, exist_ok=True)

    def compute_file_checksum(self, file_path: str) -> str:
        """Computes SHA256 checksum of a file for idempotency checking."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def compute_text_checksum(self, text: str) -> str:
        """Computes SHA256 checksum of raw text string."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def load_persisted_data(self):
        """Loads manifests and ingested chunks from disk into memory."""
        # Load manifests
        manifests_file = os.path.join(self.metadata_dir, "manifests.json")
        if os.path.exists(manifests_file):
            try:
                with open(manifests_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        m = BookManifest(**item)
                        self.manifests[m.source_id] = m
            except Exception:
                pass

        # Load processed chunks or index files
        for corpus in CorpusType:
            corpus_chunks: List[TextChunk] = []
            index_file = os.path.join(self.indexes_dir, f"{corpus.value.lower()}_index.json")
            if os.path.exists(index_file):
                try:
                    with open(index_file, "r", encoding="utf-8") as f:
                        chunks_data = json.load(f)
                        for cd in chunks_data:
                            corpus_chunks.append(TextChunk.model_construct(**cd))
                except Exception:
                    pass
            else:
                chunk_files = glob.glob(os.path.join(self.processed_dir, f"{corpus.value.lower()}_*.json"))
                for cf in chunk_files:
                    try:
                        with open(cf, "r", encoding="utf-8") as f:
                            chunks_data = json.load(f)
                            for cd in chunks_data:
                                corpus_chunks.append(TextChunk.model_construct(**cd))
                    except Exception:
                        pass
            self.corpus_indexes[corpus] = corpus_chunks

    def _save_manifests(self):
        manifests_file = os.path.join(self.metadata_dir, "manifests.json")
        manifest_list = [m.model_dump() for m in self.manifests.values()]
        with open(manifests_file, "w", encoding="utf-8") as f:
            json.dump(manifest_list, f, indent=2)

    def parse_markers(self, text_segment: str) -> Tuple[Optional[str], Optional[int], Optional[str], Optional[str]]:
        """Parses part, chapter, page, and verse markers IF EXPLICITLY present in text.

        NEVER invents or fills in missing chapter/page numbers.
        """
        part: Optional[str] = None
        chapter: Optional[str] = None
        page: Optional[int] = None
        verse: Optional[str] = None

        # Part patterns e.g. [Part 1], [Book 2]
        part_match = re.search(r"\[(?:Part|Book)\s*([\w\d\.\-]+)\]", text_segment, re.IGNORECASE)
        if part_match:
            part = f"Part {part_match.group(1)}"

        # Chapter patterns e.g. [Chapter 4], [Ch. 12], [Adhyaya 5]
        ch_match = re.search(r"\[(?:Chapter|Ch\.|Adhyaya)\s*([\w\d\.\-]+)\]", text_segment, re.IGNORECASE)
        if ch_match:
            chapter = f"Chapter {ch_match.group(1)}"

        # Page patterns e.g. [Page 45], [Pg 102]
        pg_match = re.search(r"\[(?:Page|Pg\.)\s*(\d+)\]", text_segment, re.IGNORECASE)
        if pg_match:
            page = int(pg_match.group(1))

        # Verse patterns e.g. [Verse 12], [Sloka 5], [Stanza 8], [Combination 10]
        v_match = re.search(r"\[(?:Verse|Sloka|Stanza|Combination|Verse\.)\s*([\d\.\-]+)\]", text_segment, re.IGNORECASE)
        if v_match:
            verse = f"Verse {v_match.group(1)}"

        return part, chapter, page, verse

    def normalize_text(self, text: str) -> str:
        """Deterministic text normalization without changing meaning."""
        # Normalize line endings
        text = re.sub(r"\r\n", "\n", text)
        # Remove null/control characters
        text = "".join(ch for ch in text if ord(ch) >= 32 or ch == "\n")
        # Normalize repeated whitespace (but preserve paragraph breaks)
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
        text = "\n".join(lines)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text

    def detect_tags(self, text: str) -> List[str]:
        """Lexical tagging of chunks based on astrological keywords."""
        tags = []
        text_lower = text.lower()

        keyword_map = {
            "natal": ["natal", "birth", "janma", "जन्म"],
            "lagna": ["lagna", "ascendant", "rising sign", "लग्न"],
            "bhava": ["bhava", "house", "भाव"],
            "planet": ["planet", "graha", "sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu", "ketu", "ग्रह", "सूर्य", "चन्द्र", "मंगल", "बुध", "गुरु", "शुक्र", "शनि", "राहु", "केतु"],
            "dasha": ["dasha", "period", "vimshottari", "दशा"],
            "yoga": ["yoga", "combination", "योग"],
            "career": ["career", "profession", "job", "business", "work", "tenth house", "10th house", "व्यवसाय", "नौकरी", "कर्म"],
            "marriage": ["marriage", "wife", "husband", "spouse", "wedding", "seventh house", "7th house", "विवाह", "शादी", "पत्नी", "पति"],
            "finance": ["wealth", "money", "finance", "paisa", "dhan", "second house", "2nd house", "eleventh house", "11th house", "धन", "पैसे", "वित्त"],
            "health": ["health", "disease", "illness", "sixth house", "6th house", "eighth house", "8th house", "स्वास्थ्य", "रोग", "बीमारी"],
            "transit": ["transit", "gochar", "गोचर"],
            "ashtakavarga": ["ashtakavarga", "bindu", "अष्टकवर्ग"],
            "prashna": ["prashna", "prasna", "horary", "query", "प्रश्न"],
            "muhurta": ["muhurta", "election", "auspicious", "मुहूर्त"],
            "timing": ["timing", "when", "kab", "कब", "समय"],
            # Palmistry Topics
            "hand_shape": ["hand shape", "type of hand", "conic", "spatulate", "square", "elementary", "philosophic", "psychic", "mixed", "हस्त", "आकार"],
            "thumb": ["thumb", "will", "logic", "अंगूठा"],
            "fingers": ["fingers", "index", "middle", "ring", "little", "fingertips", "उंगलियां"],
            "mount_jupiter": ["mount of jupiter", "jupiter mount", "गुरु पर्वत"],
            "mount_saturn": ["mount of saturn", "saturn mount", "शनि पर्वत"],
            "mount_apollo_sun": ["mount of apollo", "mount of sun", "apollo mount", "sun mount", "सूर्य पर्वत"],
            "mount_mercury": ["mount of mercury", "mercury mount", "बुध पर्वत"],
            "mount_mars": ["mount of mars", "mars mount", "lower mars", "upper mars", "मंगल पर्वत"],
            "mount_moon": ["mount of moon", "luna", "moon mount", "चन्द्र पर्वत"],
            "mount_venus": ["mount of venus", "venus mount", "शुक्र पर्वत"],
            "life_line": ["life line", "line of life", "vitality", "जीवन रेखा"],
            "head_line": ["head line", "line of head", "intelligence", "mentality", "मस्तिष्क रेखा"],
            "heart_line": ["heart line", "line of heart", "emotions", "हृदय रेखा"],
            "fate_line": ["fate line", "line of fate", "destiny", "career line", "भाग्य रेखा"],
            "sun_line": ["sun line", "line of sun", "apollo line", "success", "सूर्य रेखा"],
            "health_line": ["health line", "line of health", "hepatica", "स्वास्थ रेखा"],
            "marriage_line": ["marriage line", "union line", "विवाह रेखा"],
            "symbols_marks": ["triangle", "star", "cross", "square", "island", "circle", "grille", "spot", "त्रिकोण", "तारा"]
        }

        for tag, keywords in keyword_map.items():
            if any(kw in text_lower for kw in keywords):
                tags.append(tag)

        return tags

    def _create_and_add_chunk(
        self,
        chunks_list: List[TextChunk],
        text: str,
        manifest: BookManifest,
        index: int,
        part: Optional[str],
        chapter: Optional[str],
        page: Optional[int],
        verse: Optional[str]
    ):
        c_id = hashlib.sha256(f"{manifest.source_id}:{index}:{text}".encode()).hexdigest()[:16]
        tags = self.detect_tags(text)

        chunk = TextChunk(
            chunk_id=c_id,
            source_id=manifest.source_id,
            book_title=manifest.title,
            corpus=manifest.corpus,
            chapter=chapter,
            page=page,
            verse=verse,
            verification_status=manifest.citation_verification,
            text=text,
            checksum=self.compute_text_checksum(text),
            metadata={
                "author": manifest.author,
                "language": manifest.language,
                "rights_status": manifest.rights_status.value,
                "original_filename": manifest.file_name,
                "notes": manifest.notes,
                "part": part,
                "tags": tags
            }
        )
        chunks_list.append(chunk)

    def ingest_source_book(
        self,
        file_path: str,
        manifest: BookManifest,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        deduplicate: bool = True
    ) -> List[TextChunk]:
        """Ingests a source book file with SHA256 checksum idempotency and chunk deduplication."""
        checksum = self.compute_file_checksum(file_path)

        # Idempotency check
        if manifest.source_id in self.manifests:
            existing_m = self.manifests[manifest.source_id]
            if existing_m.checksum == checksum and existing_m.total_chunks > 0:
                existing_chunks = [
                    c for c in self.corpus_indexes[manifest.corpus]
                    if c.source_id == manifest.source_id
                ]
                if existing_chunks:
                    return existing_chunks

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            raw_text = f.read()

        cleaned_text = self.normalize_text(raw_text)
        if not cleaned_text:
            return []

        # Strategy: split by double newline
        raw_paragraphs = [p.strip() for p in cleaned_text.split("\n\n") if p.strip()]
        print(f"  Debug: Found {len(raw_paragraphs)} raw paragraphs after split.")

        chunks_list: List[TextChunk] = []
        book_hashes = set()
        
        current_part: Optional[str] = None
        current_chapter: Optional[str] = None
        current_page: Optional[int] = None

        chunk_counter = 0
        skipped_dup = 0

        # Buffer for grouping small paragraphs into target chunk size
        current_chunk_words = []
        current_word_count = 0

        for para in raw_paragraphs:
            # Check for header markers
            pt, ch, pg, vr = self.parse_markers(para)
            if pt: current_part = pt
            if ch: current_chapter = ch
            if pg: current_page = pg

            # Basic internal deduplication for short blocks
            if len(para) < 200:
                h = hashlib.md5(para.lower().encode('utf-8')).hexdigest()
                if h in book_hashes:
                    skipped_dup += 1
                    continue
                book_hashes.add(h)

            para_words = para.split()
            para_word_count = len(para_words)

            if para_word_count > chunk_size:
                # Flush buffer
                if current_chunk_words:
                    self._create_and_add_chunk(
                        chunks_list, " ".join(current_chunk_words), manifest, chunk_counter,
                        current_part, current_chapter, current_page, vr
                    )
                    chunk_counter += 1
                    current_chunk_words = []
                    current_word_count = 0

                step = chunk_size - chunk_overlap
                for i in range(0, para_word_count, step):
                    sub_text = " ".join(para_words[i:i + chunk_size])
                    self._create_and_add_chunk(
                        chunks_list, sub_text, manifest, chunk_counter,
                        current_part, current_chapter, current_page, vr
                    )
                    chunk_counter += 1
            else:
                if current_word_count + para_word_count > chunk_size:
                    self._create_and_add_chunk(
                        chunks_list, " ".join(current_chunk_words), manifest, chunk_counter,
                        current_part, current_chapter, current_page, vr
                    )
                    chunk_counter += 1
                    # Implement overlap by taking last few words
                    overlap_words = " ".join(current_chunk_words).split()[-chunk_overlap:]
                    current_chunk_words = overlap_words + [para]
                    current_word_count = len(" ".join(current_chunk_words).split())
                else:
                    current_chunk_words.append(para)
                    current_word_count += para_word_count

        if current_chunk_words:
            self._create_and_add_chunk(
                chunks_list, " ".join(current_chunk_words), manifest, chunk_counter,
                current_part, current_chapter, current_page, vr
            )

        print(f"  Debug: Skipped {skipped_dup} short duplicates.")

        # Update manifest
        manifest.checksum = checksum
        manifest.total_chunks = len(chunks_list)
        manifest.ingested_at = datetime.now(timezone.utc).isoformat()
        self.manifests[manifest.source_id] = manifest
        self._save_manifests()

        # Update index
        self.corpus_indexes[manifest.corpus] = [
            c for c in self.corpus_indexes[manifest.corpus]
            if c.source_id != manifest.source_id
        ]
        self.corpus_indexes[manifest.corpus].extend(chunks_list)

        # Save files
        out_chunk_file = os.path.join(self.processed_dir, f"{manifest.corpus.value.lower()}_{manifest.source_id}.json")
        with open(out_chunk_file, "w", encoding="utf-8") as f:
            json.dump([c.model_dump() for c in chunks_list], f)

        out_index_file = os.path.join(self.indexes_dir, f"{manifest.corpus.value.lower()}_index.json")
        with open(out_index_file, "w", encoding="utf-8") as f:
            json.dump([c.model_dump() for c in self.corpus_indexes[manifest.corpus]], f)

        self._build_tag_index(manifest.corpus)
        return chunks_list

    def search_rag(
        self,
        query: str,
        corpus: CorpusType = CorpusType.VEDIC,
        top_k: int = 3,
        max_total_chars: int = 1500,
        min_score: float = 0.05,
        required_tags: Optional[List[str]] = None,
        preferred_books: Optional[List[str]] = None,
        excluded_books: Optional[List[str]] = None
    ) -> RAGQueryResult:
        """Retrieves relevant classical source passages with strict corpus isolation."""
        query_clean = query.strip().lower()
        if not query_clean:
            return RAGQueryResult(query=query, corpus=corpus)

        corpus_chunks = self.corpus_indexes.get(corpus, [])
        if not corpus_chunks:
            return RAGQueryResult(query=query, corpus=corpus, formatted_prompt_context="[No relevant classical sources found in corpus]")

        self._ensure_tag_index(corpus)

        # Tokenize query with Devanagari support
        query_terms = set(re.findall(r"[\u0900-\u097F\w]{2,}", query_clean)) # Min 2 chars to filter noise
        if not query_terms:
            return RAGQueryResult(query=query, corpus=corpus)

        # Detect tags from query to use for boosting
        query_tags = self.detect_tags(query_clean)

        # Candidate selection via tags
        candidate_indices = None
        if required_tags:
            candidate_indices = set()
            for tag in required_tags:
                if tag in self.tag_indexes[corpus]:
                    candidate_indices.update(self.tag_indexes[corpus][tag])

        scored_chunks: List[Tuple[float, TextChunk]] = []

        search_indices = candidate_indices if candidate_indices is not None else range(len(corpus_chunks))

        for idx in search_indices:
            chunk = corpus_chunks[idx]
            if excluded_books and chunk.source_id in excluded_books:
                continue

            chunk_terms = self.token_cache.get((corpus, idx))
            if not chunk_terms:
                continue

            matched_terms = query_terms.intersection(chunk_terms)
            matched_count = len(matched_terms)
            if matched_count == 0:
                continue

            # Improved scoring
            # Base score from term overlap
            score = (matched_count / len(query_terms)) * 0.8

            # Length boost/penalty
            text_len = len(chunk.text)
            if text_len > 500: score += 0.1
            if text_len < 150: score *= 0.5

            # Tag match boost
            chunk_tags = chunk.metadata.get("tags", [])
            for tag in query_tags:
                if tag in chunk_tags:
                    score += 0.2

            # Penalize potential title pages or headers
            text_lower = chunk.text.lower()
            header_keywords = ["published", "edition", "all rights reserved", "contents", "preface", "foreword", "by"]
            if any(kw in text_lower[:200] for kw in header_keywords):
                # Stronger penalty for headers
                score *= 0.3

            # Penalize chunks with too many short words (OCR noise)
            words = chunk.text.split()
            if words:
                avg_len = sum(len(w) for w in words) / len(words)
                if avg_len < 3.0:
                    score *= 0.5

            if preferred_books and chunk.source_id in preferred_books:
                score *= 2.0

            if score >= min_score:
                chunk.score = round(score, 4)
                scored_chunks.append((score, chunk))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)

        # Deduplicate and limit - performance optimized
        deduped_chunks: List[TextChunk] = []
        chunk_to_idx = {id(c): i for i, c in enumerate(corpus_chunks)}

        for _, chunk in scored_chunks[:100]:
            is_dup = False
            chunk_idx = chunk_to_idx.get(id(chunk))
            words_chunk = self.token_cache.get((corpus, chunk_idx)) or set()

            for existing in deduped_chunks:
                existing_idx = chunk_to_idx.get(id(existing))
                words_existing = self.token_cache.get((corpus, existing_idx)) or set()

                intersection_len = len(words_existing.intersection(words_chunk))
                if intersection_len == 0: continue

                overlap = intersection_len / max(1, len(words_existing.union(words_chunk)))
                if overlap > 0.7:
                    is_dup = True
                    break
            if not is_dup:
                deduped_chunks.append(chunk)
                if len(deduped_chunks) >= top_k * 2:
                    break

        final_chunks: List[TextChunk] = []
        accumulated_chars = 0
        for chunk in deduped_chunks:
            if accumulated_chars + len(chunk.text) > max_total_chars and final_chunks:
                break
            final_chunks.append(chunk)
            accumulated_chars += len(chunk.text)
            if len(final_chunks) >= top_k:
                break

        citations = []
        for c in final_chunks:
            loc = f" ({', '.join(filter(None, [c.chapter, f'Pg. {c.page}' if c.page else None, c.verse]))})" if any([c.chapter, c.page, c.verse]) else ""

            status_val = c.verification_status.value if hasattr(c.verification_status, 'value') else str(c.verification_status)
            status = f" [{status_val}]"

            cite = f"{c.book_title}{loc}{status}"
            if cite not in citations: citations.append(cite)

        return RAGQueryResult(
            query=query,
            corpus=corpus,
            retrieved_chunks=final_chunks,
            total_chunks_found=len(final_chunks),
            citations=citations,
            formatted_prompt_context=self.format_chunks_for_prompt(final_chunks)
        )

    def format_chunks_for_prompt(self, chunks: List[TextChunk]) -> str:
        if not chunks: return "[No classical text evidence retrieved]"
        blocks = ["--- RETRIEVED CLASSICAL SOURCE EVIDENCE ---"]
        for idx, c in enumerate(chunks, 1):
            loc = f" | {', '.join(filter(None, [c.chapter, f'Pg. {c.page}' if c.page else None, c.verse]))}" if any([c.chapter, c.page, c.verse]) else ""
            blocks.append(f"[{idx}] Source: {c.book_title}{loc}\n\"{c.text}\"")
        return "\n\n".join(blocks)

    def get_corpus_status(self) -> CorpusStatusResult:
        total_chunks = 0
        for corpus in CorpusType:
            total_chunks += len(self.corpus_indexes.get(corpus, []))

        vedic_books = [m for m in self.manifests.values() if m.corpus == CorpusType.VEDIC]
        kp_books = [m for m in self.manifests.values() if m.corpus == CorpusType.KP]
        palmistry_books = [m for m in self.manifests.values() if m.corpus == CorpusType.PALMISTRY]
        return CorpusStatusResult(
            vedic_status=f"INGESTED ({len(vedic_books)} books)",
            kp_status=f"INGESTED ({len(kp_books)} books)",
            palmistry_status=f"INGESTED ({len(palmistry_books)} books)",
            is_ready_for_production=bool(self.manifests),
            total_books_ingested=len(self.manifests),
            total_chunks_indexed=total_chunks,
            message="Production classical books ingested." if self.manifests else "No books found."
        )
