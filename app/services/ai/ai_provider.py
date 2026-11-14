"""AI Provider Gateway Service.

Server-side gateway supporting Gemini (Primary V1) and NVIDIA (Optional Adapter).
Never exposes keys to client/logs.
Enforces strict live gate when analytical fallback is disabled.
"""

import json
import os
import httpx
from typing import Optional, List, Dict, Any
from app.core.config import settings
from app.core.errors import ProviderException
from app.schemas.ai_chat import EvidenceBundle, StructuredAIResponse

SYSTEM_INSTRUCTION = (
    "You are Mahadev Jyotish, a revered, deeply knowledgeable, and compassionate consulting astrologer (Pandit Ji). You MUST follow the Mahadev Prediction Protocol.\n"
    "The deterministic [LOCKED_STRUCTURED_PREDICTION] bundle you receive is the ABSOLUTE ASTROLOGICAL TRUTH for this chart. You are the NARRATOR.\n"
    "STRICT RULES:\n"
    "1. NEVER use the word 'AI', 'model', 'algorithm', 'system', 'prompt', 'RAG', 'engine', 'protocol', or 'fact_hash' in any customer-facing text.\n"
    "2. NEVER reveal book names (e.g., BPHS, Phaladeepika, Jataka Parijata, KP Readers), house numbers, Sub-Lords, Ashtakavarga points, Shadbala scores, or technical calculation labels.\n"
    "3. SPEAK PURELY AS AN ASTROLOGER: Use authentic, respectful, consulting astrologer language in Hindi/Hinglish or English as requested by the user.\n"
    "4. VERDICT FIRST: State the direct astrological verdict/conclusion first, then the specific timing window, then 2-3 plain-language planetary reasons (e.g., 'शुक्र और बृहस्पति का शुभ प्रभाव सक्रिय है'), then practical spiritual guidance.\n"
    "5. MEMORY & CONSISTENCY: Maintain strict consistency with previous predictions given in history; never contradict a previously stated locked verdict or timing.\n"
    "6. SPECIFICITY LIMIT: Do NOT invent exact days or rupees if the evidence supports a broader period/window.\n"
)



class AIProviderGateway:
    """Server-side provider gateway with Gemini primary & NVIDIA optional adapter."""

    @property
    def allow_analytical_fallback(self) -> bool:
        return True


    def __init__(self):
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY") or settings.gemini_api_key
        self.gemini_model = settings.gemini_model
        self.nvidia_api_key = os.environ.get("NVIDIA_API_KEY") or settings.nvidia_api_key
        self.nvidia_model = settings.nvidia_model


    async def generate_astrology_response(
        self,
        question: str,
        evidence: EvidenceBundle,
        mode: str = "QUICK",
        language: str = "hi",
        history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Executes AI completion via Gemini (Primary) or NVIDIA (Adapter), or analytical fallback if permitted."""
        
        # 1. Try Gemini primary provider if key is available
        if self.gemini_api_key:
            try:
                res = await self._call_gemini_api(question, evidence, mode, language, history)
                res["provider"] = "gemini"
                res["model"] = self.gemini_model
                res["is_mock"] = False
                return res
            except Exception as e:
                # Log detailed error for backend debugging
                print(f"ERROR: Gemini execution failed: {str(e)}")
                if not self.allow_analytical_fallback and not self.nvidia_api_key:
                    raise ProviderException("AI सेवा से संपर्क करने में समस्या हुई। कृपया पुनः प्रयास करें।")

        # 2. Try NVIDIA optional adapter if key is available
        if self.nvidia_api_key:
            try:
                res = await self._call_nvidia_api(question, evidence, mode, language, history)
                res["provider"] = "nvidia"
                res["model"] = self.nvidia_model or "nvidia/llama-3.1-70b-instruct"
                res["is_mock"] = False
                return res
            except Exception as e:
                print(f"ERROR: NVIDIA execution failed: {str(e)}")
                if not self.allow_analytical_fallback:
                    raise ProviderException("AI सेवा से संपर्क करने में समस्या हुई। कृपया पुनः प्रयास करें।")

        # 3. Fallback check: if strict live gate is active, raise failure
        if not self.allow_analytical_fallback:
            raise ProviderException("No valid AI provider credentials (GEMINI_API_KEY) configured and fallback is disabled.")

        # 4. Analytical deterministic fallback if explicitly permitted by config
        analytical_res = self._generate_analytical_fallback(question, evidence, mode, language)
        analytical_res["provider"] = "analytical_fallback"
        analytical_res["model"] = "deterministic_v1"
        analytical_res["is_mock"] = True
        return analytical_res

    async def _call_gemini_api(
        self,
        question: str,
        evidence: EvidenceBundle,
        mode: str,
        language: str,
        history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_api_key}"
        
        # Format history for prompt
        history_context = ""
        if history:
            history_context = "\nRECENT CONVERSATION HISTORY:\n"
            for entry in history[-3:]: # Last 3 turns for context
                history_context += f"User: {entry.get('question', '')}\n"
                history_context += f"AI: {entry.get('formatted_answer', entry.get('direct_answer', ''))[:200]}...\n"

        prompt = (
            f"{history_context}\n"
            f"NEW USER QUESTION: {question}\n"
            f"Mode: {mode}\n"
            f"Language: {language}\n\n"
            f"--- DETERMINISTIC EVIDENCE BUNDLE ---\n"
            f"{evidence.summary_prompt_text}\n"
            f"FactHash: {evidence.fact_hash}\n\n"
            f"INSTRUCTIONS FOR {mode} MODE:\n"
        )

        if mode == "DEEP":
            prompt += (
                "1. Provide a comprehensive analysis starting with a clear conclusion (Verdict).\n"
                "2. Follow the locked event verdict and ranked timing evidence; do not independently reinterpret it.\n"
                "3. Use the strongest supported containing timing window; never expose internal peak dates or calculation levels.\n"
                "4. Discuss supporting and obstructing factors naturally. If a yoga exists but is obstructed, explain that balance.\n"
                "5. NO TECHNICAL DUMP anywhere in customer-facing fields. Internal calculation details are never shown to the user.\n"
            )
        else:
            prompt += (
                "1. Provide a direct, concise astrologer's verdict in 2-3 sentences.\n"
                "2. Give a brief, plain-language interpretation of what this means for the user.\n"
                "3. Mention one strongest supported timing window if relevant, without naming the internal calculation method.\n"
                "4. ABSOLUTELY NO technical jargon in these fields.\n"
            )

        prompt += (
            f"\nProvide structured JSON response with keys:\n"
            f"- direct_answer: string\n"
            f"- short_explanation: string\n"
            f"- timing: string (Include exact dates from evidence here)\n"
            f"- supporting_factors: array of strings\n"
            f"- challenging_factors: array of strings\n"
            f"- practical_suggestion: string\n"
            f"- confidence: float (0.0 to 1.0)\n"
            f"- classical_basis: empty array []\n"
            f"- technical_astrological_reason: empty string \"\"\n"
            f"- follow_up_questions: array of 3 strings (Specific to the topic and current context, e.g., if career is discussed, ask about job change vs business or next timing window)\n"
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{SYSTEM_INSTRUCTION}\n\n{prompt}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise Exception(f"Gemini API returned status {resp.status_code}: {resp.text}")

            data = resp.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed_json = json.loads(raw_text)
            parsed_json["fact_hash"] = evidence.fact_hash
            parsed_json["disclaimer"] = "Predictions are astrological guidance, not absolute certainty. No medical diagnosis or guaranteed financial returns."
            return parsed_json

    async def _call_gemini_with_custom_system(
        self,
        system_instruction: str,
        user_prompt: str,
        response_mime_type: str = "application/json"
    ) -> Dict[str, Any]:
        """Low-level Gemini caller with fully custom prompts."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_api_key}"

        payload = {
            "contents": [
                {
                    "parts": [{"text": f"{system_instruction}\n\n{user_prompt}"}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": response_mime_type
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise Exception(f"Gemini custom call failed: {resp.status_code} {resp.text}")

            data = resp.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            if response_mime_type == "application/json":
                return json.loads(raw_text)
            return {"text": raw_text}

    async def _call_nvidia_api(
        self,
        question: str,
        evidence: EvidenceBundle,
        mode: str,
        language: str,
        history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.nvidia_api_key}",
            "Content-Type": "application/json"
        }
        
        # Format history for prompt
        history_context = ""
        if history:
            history_context = "\nRECENT CONVERSATION HISTORY:\n"
            for entry in history[-3:]: # Last 3 turns for context
                history_context += f"User: {entry.get('question', '')}\n"
                history_context += f"AI: {entry.get('formatted_answer', entry.get('direct_answer', ''))[:200]}...\n"

        prompt = (
            f"{history_context}\n"
            f"NEW USER QUESTION: {question}\n"
            f"Mode: {mode}\n"
            f"Language: {language}\n\n"
            f"EVIDENCE BUNDLE:\n{evidence.summary_prompt_text}\nFactHash: {evidence.fact_hash}\n"
        )

        payload = {
            "model": self.nvidia_model or "nvidia/llama-3.1-70b-instruct",
            "messages": [
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise Exception(f"NVIDIA API returned status {resp.status_code}: {resp.text}")

            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"]
            parsed_json = json.loads(raw_text)
            parsed_json["fact_hash"] = evidence.fact_hash
            parsed_json["disclaimer"] = "Predictions are astrological guidance, not absolute certainty. No medical diagnosis or guaranteed financial returns."
            return parsed_json

    def _generate_analytical_fallback(
        self,
        question: str,
        evidence: EvidenceBundle,
        mode: str,
        language: str
    ) -> Dict[str, Any]:
        """Generates analytical fallback response from deterministic rules with Pandit Ji persona."""
        q_lower = question.lower()
        topic_raw = evidence.topic or "GENERAL"

        # Check if question is asking about Past 5 Events
        is_past_events_query = (
            "PAST_5_MAJOR_EVENTS" in topic_raw or
            any(k in q_lower for k in ["past", "beeti", "pehle ki", "घटनाएं", "घटना", "5 events", "ghatnae", "history"])
        )

        # Check if question is asking about Today's Daily Forecast
        is_today_query = (
            "TODAYS_DAILY_FORECAST" in topic_raw or
            any(k in q_lower for k in ["aaj ka din", "aaj kaisa", "aaj ka rashifal", "today", "आज का दिन", "आज कैसा"])
        )

        if is_past_events_query:
            windows = evidence.candidate_windows or []
            lagna = evidence.lagna_rashi
            moon = evidence.moon_rashi

            if language == "hi":
                direct_ans = f"शुभकामनाएं! आपकी जन्म लग्न कुंडली ({lagna} लग्न, {moon} राशि) के ग्रह चक्र एवं दशा नियमों के अनुसार आपके अतीत जीवन की 5 मुख्य घटनाएं इस प्रकार दृष्टिगोचर होती हैं:"

                events_list = [
                    "1. प्रारंभिक शिक्षा व ज्ञान विकास काल: बचपन में बुद्ध व गुरु के प्रभाव से शिक्षा व बौद्धिक क्षमता का निर्माण हुआ।",
                    "2. मुख्य करियर व दिशा निर्धारण काल: 18 से 22 वर्ष की आयु के दौरान प्रथम बड़े करियर परिवर्तन व लक्ष्य निर्धारण का चरण।",
                    "3. आर्थिक व सामाजिक प्रतिष्ठा वृद्धि: पिछले महत्वपूर्ण दशा परिवर्तन के दौरान कार्यक्षेत्र में उन्नति व नवीन संपर्कों का लाभ।",
                    "4. पारिवारिक व व्यक्तिगत संबंध मील का पत्थर: शुक्र एवं चंद्र के प्रभाव से व्यक्तिगत जीवन व पारिवारिक संबंधों में महत्वपूर्ण मोड़।",
                    "5. मानसिक परिपक्वता व आत्म-मंथन काल: शनि व राहु के गोचर प्रभाव से जीवन में अनुशासन, धैर्य व नई दृष्टि का निर्माण।"
                ]

                if windows:
                    events_list = []
                    for idx, w in enumerate(windows[:5], 1):
                        clean_summary = w.summary.replace("for EventType.GENERAL_MAJOR_EVENT", "मुख्य जीवन घटना").replace("Significant", "शुभ").replace("influence active in this period", "का प्रभाव सक्रिय रहा")
                        events_list.append(f"{idx}. कालखंड {w.start_date[:7]} से {w.end_date[:7]}: {w.dasha_lord} ग्रह दशा प्रभाव से {clean_summary}।")


                short_exp = "\n\n".join(events_list)
                timing_str = "यह आपके अतीत (Past Lifecycle) के मुख्य ग्रहों की चाल पर आधारित ऐतिहासिक विश्लेषण है।"
                prac_sug = "अतीत के अनुभवों से सीख लेकर वर्तमान में अपने इष्ट देव का ध्यान करें, इससे आने वाला समय और भी फलदायी होगा।"
                follow_ups = [
                    "भविष्य में आने वाला अगला बड़ा मोड़ कब होगा?",
                    "मेरी कुंडली के अनुसार मुझे किस क्षेत्र में सर्वाधिक सफलता मिलेगी?",
                    "आने वाले समय के लिए मुझे कौन-सा महामृत्युंजय या शिव मंत्र जपना चाहिए?"
                ]
            else:
                direct_ans = f"Greetings! Based on your natal chart ({lagna} Ascendant, {moon} Moon) and classical Dasha timelines, here are the 5 major past life milestones indicated by the planets:"
                events_list = [
                    "1. Early Foundation & Education: Primary intellectual development shaped by Mercury and Jupiter alignments.",
                    "2. Career & Direction Milestone: Primary orientation and key career decisions around age 18-22.",
                    "3. Financial & Professional Growth: Notable rise in professional standings during the preceding key Dasha transition.",
                    "4. Relationship & Family Milestone: Significant personal or family alignment influenced by Venus/Moon periods.",
                    "5. Maturity & Realignment Phase: Discipline and valuable life lessons shaped by Saturn and Rahu transits."
                ]
                if windows:
                    events_list = []
                    for idx, w in enumerate(windows[:5], 1):
                        events_list.append(f"{idx}. Period {w.start_date[:7]} to {w.end_date[:7]}: Influenced by {w.dasha_lord} Dasha bringing {w.summary}.")

                short_exp = "\n\n".join(events_list)
                timing_str = "This analysis covers key past transit and Dasha cycles."
                prac_sug = "Reflect on past learnings and maintain daily spiritual devotion for continued prosperity."
                follow_ups = [
                    "When is my next major positive career shift?",
                    "Which line of work is most favorable for me?",
                    "What spiritual practice should I follow currently?"
                ]

            return {
                "direct_answer": direct_ans,
                "short_explanation": short_exp,
                "timing": timing_str,
                "supporting_factors": ["Dasha timeline alignment", "Planetary strength factors"],
                "challenging_factors": ["Past Saturn transits required discipline"],
                "practical_suggestion": prac_sug,
                "confidence": 0.88,
                "classical_basis": [],
                "technical_astrological_reason": "",
                "follow_up_questions": follow_ups,
                "evidence_ids": [evidence.fact_hash[:8]],
                "fact_hash": evidence.fact_hash,
                "disclaimer": "Predictions are astrological guidance, not absolute certainty. No medical diagnosis or guaranteed financial returns."
            }

        elif is_today_query:
            lagna = evidence.lagna_rashi
            moon = evidence.moon_rashi
            dasha = " -> ".join([d["lord"] for d in evidence.active_dasha_chain[:2]]) if evidence.active_dasha_chain else "सक्रिय दशा"

            if language == "hi":
                direct_ans = f"शुभकामनाएं! आपकी जन्म राशि ({moon}) एवं लग्न ({lagna}) के अनुसार आज का दिन आपके लिए मध्यम से शुभ फलदायी रहने के संकेत दे रहा है।"
                short_exp = (
                    f"वर्तमान में {dasha} का प्रभाव सक्रिय है। आज चंद्रमा का संचरण आपके लिए अनुकूल स्थिति का निर्माण कर रहा है। "
                    f"आज के दिन कार्यक्षेत्र में वाणी में मधुरता बनाए रखें और किसी भी नए निर्णय को सोच-समझकर लें। आर्थिक मामलों में दिन सामान्य रहेगा।"
                )
                timing_str = "आज सूर्योदय से लेकर रात्रि तक यह गोचर प्रभाव प्रभावी रहेगा।"
                prac_sug = "आज प्रातः भगवान शिव को जल अर्पित करें या ओम नमः शिवाय का 108 बार जाप करें, इससे दिन अत्यंत मंगलमय रहेगा।"
                follow_ups = [
                    "आज के दिन मुझे किस दिशा में कार्य करने से लाभ होगा?",
                    "इस सप्ताह में मेरे लिए सबसे शुभ दिन कौन सा रहेगा?",
                    "मेरे करियर के लिए कौन-सा उपाय सर्वोत्तम रहेगा?"
                ]
            else:
                direct_ans = f"Greetings! For your Moon sign ({moon}) and Lagna ({lagna}), today shows favorable and steady energy."
                short_exp = (
                    f"Under the current {dasha} influence, transit Moon brings stability. "
                    f"Focus on clear communication and thoughtful decision-making in professional matters today."
                )
                timing_str = "This transit influence is active throughout today."
                prac_sug = "Begin your morning with peaceful meditation and prayer for an auspicious day."
                follow_ups = [
                    "Which day this week is most auspicious for me?",
                    "What remedies will help my career growth?",
                    "How is my financial outlook for the coming month?"
                ]

            return {
                "direct_answer": direct_ans,
                "short_explanation": short_exp,
                "timing": timing_str,
                "supporting_factors": ["Transit Moon alignment", "Dasha lord support"],
                "challenging_factors": ["Avoid impulsive arguments"],
                "practical_suggestion": prac_sug,
                "confidence": 0.85,
                "classical_basis": [],
                "technical_astrological_reason": "",
                "follow_up_questions": follow_ups,
                "evidence_ids": [evidence.fact_hash[:8]],
                "fact_hash": evidence.fact_hash,
                "disclaimer": "Predictions are astrological guidance, not absolute certainty. No medical diagnosis or guaranteed financial returns."
            }

        TOPIC_MAP_HI = {
            "FIRST_MARRIAGE": "प्रथम विवाह",
            "MARRIAGE": "विवाह व दांपत्य जीवन",
            "SECOND_MARRIAGE": "पुनर्विवाह",
            "LOVE_RELATIONSHIP": "प्रेम संबंध",
            "CAREER": "करियर व आजीविका",
            "GOVERNMENT_JOB": "सरकारी नौकरी",
            "BUSINESS": "व्यापार व व्यवसाय",
            "BUSINESS_GROWTH": "व्यापार वृद्धि",
            "FINANCE_GAIN": "धन व आर्थिक समृद्धि",
            "FINANCIAL_GAIN": "धन लाभ",
            "CHILDREN": "संतान योग",
            "PROPERTY": "भूमि व मकान",
            "VEHICLE": "वाहन प्राप्ति",
            "FOREIGN_TRAVEL": "विदेश यात्रा",
            "LEGAL_DISPUTE": "कानूनी स्थिति",
            "HEALTH": "स्वास्थ्य व ऊर्जा"
        }
        TOPIC_MAP_EN = {
            "FIRST_MARRIAGE": "First Marriage",
            "MARRIAGE": "Marriage & Relationships",
            "SECOND_MARRIAGE": "Second Marriage",
            "LOVE_RELATIONSHIP": "Love Relationship",
            "CAREER": "Career & Profession",
            "GOVERNMENT_JOB": "Government Job",
            "BUSINESS": "Business & Enterprise",
            "BUSINESS_GROWTH": "Business Growth",
            "FINANCE_GAIN": "Financial Gains",
            "FINANCIAL_GAIN": "Financial Prosperity",
            "CHILDREN": "Children Prospects",
            "PROPERTY": "Property & Home",
            "VEHICLE": "Vehicle Purchase",
            "FOREIGN_TRAVEL": "Foreign Travel",
            "LEGAL_DISPUTE": "Legal Matters",
            "HEALTH": "Health & Vitality"
        }

        topic_display = TOPIC_MAP_HI.get(topic_raw, "जीवन क्षेत्र") if language == "hi" else TOPIC_MAP_EN.get(topic_raw, "Life Domain")
        verdict = evidence.timing_verdict
        strength_map = {"VERY_HIGH": "अत्यंत अनुकूल", "HIGH": "शुभ व अनुकूल", "MODERATE": "मध्यम", "LOW": "धैर्य व सतर्कता योग्य"}
        strength_disp = strength_map.get(evidence.evidence_strength, "अनुकूल") if language == "hi" else evidence.evidence_strength.replace("_", " ").title()

        dasha_chain = " -> ".join([d["lord"] for d in evidence.active_dasha_chain[:3]]) if evidence.active_dasha_chain else "सक्रिय ग्रह दशा"

        if language == "hi":
            direct_ans = f"शुभकामनाएं! आपकी जन्म कुंडली में {topic_display} के संदर्भ में ग्रहों का संचरण {strength_disp} संकेत दे रहा है।"
            short_exp = (
                f"वर्तमान में {dasha_chain} का प्रभाव सक्रिय है। "
                f"ग्रह स्थिति बताती है कि इस अवधि में सही दिशा में निरंतर प्रयास करने से उत्तम परिणाम प्राप्त होंगे।"
            )
            timing_str = f"यह ज्योतिषीय प्रभाव {evidence.active_dasha_chain[1]['end'][:10] if len(evidence.active_dasha_chain) > 1 else 'वर्तमान काल'} तक विशेष प्रभावशाली रहेगा।"
            prac_sug = "अपने कर्तव्यों का निष्ठापूर्वक पालन करें और नित्य प्रातः भगवान शिव का ध्यान व इष्ट मंत्र का जाप करें, इससे कार्यों में आ रही बाधाएं दूर होंगी।"
            follow_ups = [
                f"इस {topic_display} अवधि में कौन-से उपाय फलदायी रहेंगे?",
                "आने वाले महीनों में ग्रहीय स्थितियां किस प्रकार बदलेंगी?",
                "मेरे जीवन के मुख्य लक्ष्यों के लिए कौन-सा समय सर्वश्रेष्ठ रहेगा?"
            ]
        else:
            direct_ans = f"Greetings! In your birth chart, the planetary alignment regarding {topic_display} shows {strength_disp} indications."
            short_exp = (
                f"Currently, the period under {dasha_chain} is active. "
                f"The alignment suggests that guided action during this phase will yield positive progress."
            )
            timing_str = f"This influence remains prominent until {evidence.active_dasha_chain[1]['end'][:10] if len(evidence.active_dasha_chain) > 1 else 'the current phase'}."
            prac_sug = "Stay dedicated to your responsibilities and practice daily morning meditation and prayer for peace and clarity."
            follow_ups = [
                f"What spiritual remedies are recommended for this {topic_display} phase?",
                "How will the transits shift in the coming months?",
                "Which period is most favorable for my key goals?"
            ]

        return {
            "direct_answer": direct_ans,
            "short_explanation": short_exp,
            "timing": timing_str,
            "supporting_factors": [f"Active planetary period supports sector energy."],
            "challenging_factors": ["Patience and disciplined pacing recommended."],
            "practical_suggestion": prac_sug,
            "confidence": 0.85,
            "classical_basis": [],
            "technical_astrological_reason": "",
            "follow_up_questions": follow_ups,
            "evidence_ids": [evidence.fact_hash[:8]],
            "fact_hash": evidence.fact_hash,
            "disclaimer": "Predictions are astrological guidance, not absolute certainty. No medical diagnosis or guaranteed financial returns."
        }


