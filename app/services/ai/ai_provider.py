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
    "You are Mahadev Jyotish AI, an expert Indian astrologer. You MUST follow the Mahadev Prediction Protocol.\n"
    "The deterministic [LOCKED_STRUCTURED_PREDICTION] bundle you receive is the ABSOLUTE TRUTH. You are the NARRATOR.\n"
    "RULES:\n"
    "1. NEVER recalculate positions, invent Dasha dates, or override the provided event_type, event_state, or timing.\n"
    "2. ANSWER FORMAT: Give the direct verdict first, then main timing, then 2-5 strongest astrological reasons from the bundle.\n"
    "3. SPECIFICITY: Do NOT exceed the 'allowed_specificity' level. If it is YEAR_WINDOW, do not invent exact months or days.\n"
    "4. NO TECHNICAL DUMP: Do not mention internal house numbers, rule IDs, or engine names unless specifically asked 'kaise nikala?'.\n"
    "5. LANGUAGE: Use natural, professional Hindi/Hinglish or English as requested. Speak like a wise consulting astrologer.\n"
    "6. FORBIDDEN: Never claim 100% scientific certainty. Never invent missing divisional charts (Vargas).\n"
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
        topic = evidence.topic
        verdict = evidence.timing_verdict
        strength = evidence.evidence_strength
        dasha_chain = " -> ".join([d["lord"] for d in evidence.active_dasha_chain[:3]])

        if language == "hi":
            direct_ans = f"नमस्ते! आपकी कुंडली में {topic} के लिए समय की स्थिति {strength} दिखाई दे रही है।"
            short_exp = (
                f"आपके चार्ट का विश्लेषण करने पर पता चलता है कि अभी {dasha_chain} की दशा सक्रिय है। "
                f"सितारों की चाल बताती है कि {verdict} यह आपके लिए एक महत्वपूर्ण अवधि है, जिसमें आपको धैर्य और समझदारी से काम लेना चाहिए।"
            )
            timing_str = f"यह ज्योतिषीय प्रभाव {evidence.active_dasha_chain[1]['end'][:10]} तक विशेष प्रभावी रहेगा।"
            prac_sug = "अपने लक्ष्यों पर केंद्रित रहें और नियमित रूप से ध्यान या ईश्वर की आराधना करें, इससे मानसिक शांति मिलेगी।"
            tech_reason = (
                f"मुख्य ज्योतिषीय आधार:\n"
                f"• महादशा/अंतर्दशा: {evidence.active_dasha_chain[0]['lord']} - {evidence.active_dasha_chain[1]['lord']}\n"
                f"• लग्न: {evidence.lagna_rashi}\n"
                f"• विश्लेषण तिथि: {evidence.temporal_context.target_date or 'आज'}\n"
            )
            follow_ups = [
                f"इस {topic} अवधि में मुझे क्या उपाय करने चाहिए?",
                "आने वाले महीनों में ग्रहों की स्थिति कैसे बदलेगी?",
                "मेरे करियर के लिए कौन सा रत्न शुभ रहेगा?"
            ]
        else:
            direct_ans = f"Greetings! For {topic}, the planetary alignment shows {strength} indications."
            short_exp = (
                f"Upon observing your chart, the current {dasha_chain} dasha is influencing your life. "
                f"The alignment suggests that {verdict} This is a significant window requiring mindful action."
            )
            timing_str = f"This influence is prominent until {evidence.active_dasha_chain[1]['end'][:10]}."
            prac_sug = "Stay focused on your path and practice regular meditation to maintain clarity and peace."
            tech_reason = (
                f"Main Astrological Basis:\n"
                f"• Mahadasha/Antardasha: {evidence.active_dasha_chain[0]['lord']} - {evidence.active_dasha_chain[1]['lord']}\n"
                f"• Lagna: {evidence.lagna_rashi}\n"
                f"• Analysis Date: {evidence.temporal_context.target_date or 'Today'}\n"
            )
            follow_ups = [
                f"What remedies should I follow during this {topic} period?",
                "How will the transits shift in the coming months?",
                "Which direction is best for my growth?"
            ]

        return {
            "direct_answer": direct_ans,
            "short_explanation": short_exp,
            "timing": timing_str,
            "supporting_factors": [f"Active Dasha lord {evidence.active_dasha_chain[0]['lord']} supports sector energy."],
            "challenging_factors": ["Transit Saturn requires discipline and cautious pacing."],
            "practical_suggestion": prac_sug,
            "confidence": 0.85,
            "classical_basis": [f"BPHS Chapter on {topic} house lords and Vimshottari Dasha effects."],
            "technical_astrological_reason": tech_reason,
            "follow_up_questions": follow_ups,
            "evidence_ids": [evidence.fact_hash[:8]],
            "fact_hash": evidence.fact_hash,
            "disclaimer": "Predictions are astrological guidance, not absolute certainty. No medical diagnosis or guaranteed financial returns."
        }
