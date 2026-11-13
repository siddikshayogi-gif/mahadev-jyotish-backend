"""Astrology Knowledge Service.

Orchestrates the retrieval of classical astrology and palmistry knowledge
based on question intent and selected methodology.
"""

from typing import List, Optional
from app.services.ai.classical_rag import ClassicalRAGService
from app.schemas.rag import CorpusType, RAGQueryResult
from app.schemas.ai_chat import AstrologyMethodDecision, AstrologyMethod

class AstrologyKnowledgeService:
    """Manages astrology book retrieval and RAG context construction."""

    def __init__(self, rag_service: Optional[ClassicalRAGService] = None):
        self.rag_service = rag_service or ClassicalRAGService()

    def _merge_results(self, query: str, results: List[RAGQueryResult]) -> RAGQueryResult:
        """Merge multiple corpus searches into one compact evidence result."""
        chunks = []
        citations = []
        seen = set()
        for result in results:
            for chunk in result.retrieved_chunks:
                if chunk.chunk_id not in seen:
                    seen.add(chunk.chunk_id)
                    chunks.append(chunk)
            for citation in result.citations:
                if citation not in citations:
                    citations.append(citation)

        chunks.sort(key=lambda c: (c.score or 0.0), reverse=True)
        chunks = chunks[:8]
        context = self.rag_service.format_chunks_for_prompt(chunks)
        # HYBRID result uses VEDIC as the envelope only; every chunk retains its own corpus.
        return RAGQueryResult(
            query=query,
            corpus=CorpusType.VEDIC,
            retrieved_chunks=chunks,
            total_chunks_found=len(chunks),
            citations=citations[:8],
            formatted_prompt_context=context
        )

    def _search_one(
        self,
        query: str,
        corpus: CorpusType,
        preferred_books: List[str],
        required_tags: List[str]
    ) -> RAGQueryResult:
        result = self.rag_service.search_rag(
            query=query,
            corpus=corpus,
            top_k=5,
            max_total_chars=3500,
            preferred_books=preferred_books or None,
            required_tags=required_tags or None,
            excluded_books=[]
        )
        if result.total_chunks_found == 0 and required_tags:
            result = self.rag_service.search_rag(
                query=query,
                corpus=corpus,
                top_k=5,
                max_total_chars=3500,
                preferred_books=preferred_books or None,
                required_tags=None,
                excluded_books=[]
            )
        return result

    def retrieve_astrological_knowledge(
        self,
        query: str,
        decision: AstrologyMethodDecision
    ) -> RAGQueryResult:
        """Retrieves relevant book material based on methodology and topic intent."""

        # Determine corpus
        corpus = CorpusType.VEDIC
        if decision.primary_method == "KP" or "KP" in decision.supporting_methods:
            corpus = CorpusType.KP
        elif "palm" in query.lower() or "hand" in query.lower() or decision.primary_method == "PALMISTRY":
            corpus = CorpusType.PALMISTRY

        preferred_books = []
        excluded_books = []
        required_tags = []

        q_lower = query.lower()
        topic = decision.question_category

        # 0. PALMISTRY ROUTING
        if corpus == CorpusType.PALMISTRY:
            preferred_books = [
                "palm_benham_scientific_hand_reading",
                "palm_cheiro_language_of_hand",
                "palm_hasta_samudrika_vyas"
            ]
            if "life line" in q_lower or "जीवन रेखा" in q_lower:
                required_tags = ["life_line"]
            elif "head line" in q_lower or "मस्तिष्क रेखा" in q_lower:
                required_tags = ["head_line"]
            elif "heart line" in q_lower or "हृदय रेखा" in q_lower:
                required_tags = ["heart_line"]
            elif "fate line" in q_lower or "भाग्य रेखा" in q_lower:
                required_tags = ["fate_line"]
            elif "mount" in q_lower or "पर्वत" in q_lower:
                if "jupiter" in q_lower or "गुरु" in q_lower: required_tags = ["mount_jupiter"]
                elif "saturn" in q_lower or "शनि" in q_lower: required_tags = ["mount_saturn"]
                elif "sun" in q_lower or "apollo" in q_lower or "सूर्य" in q_lower: required_tags = ["mount_apollo_sun"]
                elif "mercury" in q_lower or "बुध" in q_lower: required_tags = ["mount_mercury"]
                elif "mars" in q_lower or "मंगल" in q_lower: required_tags = ["mount_mars"]
                elif "moon" in q_lower or "luna" in q_lower or "चन्द्र" in q_lower: required_tags = ["mount_moon"]
                elif "venus" in q_lower or "शुक्र" in q_lower: required_tags = ["mount_venus"]

        # 1. HARD CATEGORY PRIORITY FOR MUHURTA
        elif "muhurta" in q_lower or topic == "MUHURTA" or decision.primary_method == "MUHURTA":
            preferred_books = ["vedic_muhurta_chintamani"]
            required_tags = ["muhurta"]
            query += " Muhurta Electional"

        # 2. HARD CATEGORY PRIORITY FOR PRASHNA
        elif "prashna" in q_lower or topic == "PRASHNA" or decision.primary_method == "PRASHNA":
            preferred_books = ["vedic_prasna_marga", "vedic_prasna_tantra"]
            required_tags = ["prashna"]
            query += " Prasna Horary Query"

        # 3. KP Specific Routing
        elif decision.primary_method == AstrologyMethod.KP or topic == "KP":
            preferred_books = ["kp_reader_1", "kp_reader_2", "kp_reader_3", "kp_reader_4", "kp_reader_5", "kp_reader_6"]
            required_tags = ["kp"]
            query += " Krishnamurti Paddhati"

        # 4. Routing for Yogas
        elif "yoga" in q_lower or "combination" in q_lower:
            preferred_books = [
                "vedic_three_hundred_combinations",
                "vedic_bphs",
                "vedic_saravali",
                "vedic_phaladeepika",
                "vedic_brihat_jataka"
            ]
            required_tags = ["yoga"]

        # 5. Routing for Dasha
        elif "dasha" in q_lower:
            preferred_books = ["vedic_laghu_parashari", "vedic_bphs", "vedic_phaladeepika"]
            required_tags = ["dasha"]

        # 6. Domain specific routing
        elif topic == "CAREER" or topic == "GOVERNMENT_JOB" or topic == "JOB":
            required_tags = ["career"]
            preferred_books = ["vedic_bphs", "vedic_phaladeepika", "vedic_saravali", "kp_reader_3"]
            query += " Career Job Profession"
        elif topic == "BUSINESS":
            required_tags = ["career"]
            preferred_books = ["vedic_bphs", "vedic_saravali", "kp_reader_3"]
            query += " Business Trade Vyapar"
        elif topic == "WEALTH" or topic == "FINANCE":
            required_tags = ["finance"]
            preferred_books = ["vedic_bphs", "vedic_three_hundred_combinations", "kp_reader_2"]
            query += " Wealth Money Finance"
        elif topic == "MARRIAGE" or topic == "RELATIONSHIP" or topic == "BREAKUP" or topic == "RELATIONSHIP_TO_MARRIAGE":
            required_tags = ["marriage"]
            preferred_books = ["vedic_bphs", "vedic_phaladeepika", "vedic_jataka_parijata", "kp_reader_4"]
            if topic == "RELATIONSHIP_TO_MARRIAGE":
                query += " Love Marriage relationship conversion"
            else:
                query += " Marriage Relationship Spouse"
        elif topic == "CHILDREN":
            required_tags = ["children"]
            preferred_books = ["vedic_bphs", "vedic_phaladeepika"]
        elif topic == "HEALTH" or topic == "ACCIDENT":
            required_tags = ["health"]
            preferred_books = ["vedic_bphs", "vedic_saravali"]
        elif topic == "LEGAL":
            required_tags = ["legal"]
            preferred_books = ["kp_reader_6", "vedic_bphs"]
        elif topic == "EDUCATION":
            required_tags = ["education"]
            preferred_books = ["vedic_phaladeepika", "kp_reader_2"]
        elif topic == "TRAVEL" or topic == "FOREIGN_TRAVEL":
            required_tags = ["travel"]
            preferred_books = ["kp_reader_3", "vedic_phaladeepika"]
        elif topic == "PROPERTY" or topic == "HOME":
            required_tags = ["property"]
            preferred_books = ["vedic_bphs", "kp_reader_4"]
        elif topic == "FAMILY":
            required_tags = ["family"]
            preferred_books = ["vedic_bphs"]
        elif topic == "SPIRITUALITY":
            required_tags = ["spiritual"]
            preferred_books = ["vedic_saravali", "vedic_bphs"]

        # General Fallback for VEDIC
        if not preferred_books and corpus == CorpusType.VEDIC:
            preferred_books = ["vedic_bphs", "vedic_phaladeepika", "vedic_jataka_parijata"]
            if not required_tags:
                 required_tags = ["natal", "lagna", "planet"] # Broad but indexed tags

        # Search all methodologies selected by the router.
        # HYBRID questions must not silently lose Vedic evidence just because KP is a supporting method.
        corpora: List[CorpusType] = []
        if decision.primary_method == AstrologyMethod.KP:
            corpora = [CorpusType.KP, CorpusType.VEDIC]
        elif decision.primary_method == AstrologyMethod.HYBRID:
            corpora = [CorpusType.VEDIC, CorpusType.KP]
        elif corpus == CorpusType.PALMISTRY:
            corpora = [CorpusType.PALMISTRY]
        else:
            corpora = [CorpusType.VEDIC]
            if AstrologyMethod.KP in decision.supporting_methods:
                corpora.append(CorpusType.KP)

        results: List[RAGQueryResult] = []
        for selected_corpus in corpora:
            corpus_books = preferred_books
            corpus_tags = required_tags

            # When a hybrid topic's preferred list contains both traditions,
            # let source_id preference naturally boost matching books in each isolated corpus.
            result = self._search_one(
                query=query,
                corpus=selected_corpus,
                preferred_books=corpus_books,
                required_tags=corpus_tags
            )
            if result.total_chunks_found:
                results.append(result)

        if not results:
            return RAGQueryResult(
                query=query,
                corpus=corpora[0],
                formatted_prompt_context="[No relevant classical text evidence retrieved]"
            )
        if len(results) == 1:
            return results[0]
        return self._merge_results(query, results)
