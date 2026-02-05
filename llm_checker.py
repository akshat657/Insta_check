import os
from groq import Groq
import json
import streamlit as st
import time

class HealthClaimChecker:
    def __init__(self):
        # Load all 3 API keys for fallback
        self.api_keys = [
            st.secrets.get("GROQ_API_KEY_1") or os.getenv('GROQ_API_KEY_1'),
            st.secrets.get("GROQ_API_KEY_2") or os.getenv('GROQ_API_KEY_2'),
            st.secrets.get("GROQ_API_KEY_3") or os.getenv('GROQ_API_KEY_3')
        ]
        
        self.api_keys = [key for key in self.api_keys if key]
        
        if not self.api_keys:
            raise ValueError("No GROQ_API_KEY found in secrets")
        
        self.current_key_index = 0
        self.model = "llama-3.3-70b-versatile"
        print(f"[✓] Loaded {len(self.api_keys)} Groq API key(s)")
    
    def _get_client(self):
        return Groq(api_key=self.api_keys[self.current_key_index])
    
    def _call_with_fallback(self, messages, temperature=0.3, max_tokens=2000):
        """Call Groq API with automatic fallback"""
        attempts = 0
        max_attempts = len(self.api_keys) * 2
        
        while attempts < max_attempts:
            try:
                client = self._get_client()
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content
                
            except Exception as e:
                error_msg = str(e)
                
                if "rate_limit" in error_msg.lower() or "429" in error_msg:
                    print(f"[!] Rate limit on key {self.current_key_index + 1}, switching...")
                    self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
                    attempts += 1
                    time.sleep(1)
                    continue
                else:
                    raise e
        
        raise Exception("All API keys exhausted. Please try again later.")
    
    def correct_transcript(self, raw_transcript, language="hindi"):
        """Correct medical terms in transcript"""
        print(f"[*] Correcting transcript...")
        
        lang_name = "हिंदी (देवनागरी)" if language == "hindi" else "English"
        
        system_prompt = f"""You are a medical transcript editor. Correct this transcript:

1. Fix medical terminology (diseases, anatomy, drugs)
2. Correct grammar
3. Keep original meaning
4. Output ONLY in {lang_name} script

For Hindi: Use ONLY Devanagari (देवनागरी), NOT Urdu (اردو).

Return corrected transcript as plain text."""

        user_prompt = f"""Correct this medical transcript in {lang_name}:

{raw_transcript}

Return ONLY corrected transcript."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            corrected = self._call_with_fallback(messages, temperature=0.2, max_tokens=1500)
            print(f"[✓] Transcript corrected")
            return corrected.strip()
        except Exception as e:
            print(f"[!] Correction failed: {e}")
            return raw_transcript
    
    def analyze_claims(self, transcript, language="hindi"):
        """Analyze health claims"""
        print(f"[*] Analyzing health claims...")
        
        if language == "hindi":
            lang_instruction = "हिंदी (देवनागरी लिपि में)"
            lang_note = "CRITICAL: Use ONLY Devanagari script (देवनागरी), NOT Urdu/Arabic (اردو)."
        else:
            lang_instruction = "English"
            lang_note = ""
        
        system_prompt = f"""You are a medical fact-checker. Analyze health claims in {lang_instruction}.

{lang_note}

Return ONLY valid JSON:
{{
    "summary": "Overall analysis in {lang_instruction}",
    "claims": [
        {{
            "claim": "Specific claim in {lang_instruction}",
            "verdict": "TRUE/FALSE/PARTIALLY TRUE",
            "explanation": "Why in {lang_instruction}",
            "sources": ["PubMed PMID:12345", "WHO 2024"]
        }}
    ],
    "rating": 75.5,
    "key_issues": ["Issue 1 in {lang_instruction}"]
}}

Rules:
- Detailed scientific analysis
- Cite sources (PubMed, WHO, CDC)
- Rate 0-100%
- All text in {lang_instruction}"""

        user_prompt = f"""Analyze this medical transcript:

{transcript}

Provide analysis in {lang_instruction} with sources."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            content = self._call_with_fallback(messages, temperature=0.3, max_tokens=2500)
            
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                result = json.loads(json_str)
                print(f"[✓] Analysis complete (Rating: {result.get('rating', 0)}%)")
                return result
            else:
                raise ValueError("No JSON in response")
                
        except Exception as e:
            print(f"[!] Analysis failed: {e}")
            return {
                "summary": f"विश्लेषण त्रुटि: {str(e)}" if language == "hindi" else f"Analysis error: {str(e)}",
                "claims": [],
                "rating": 50.0,
                "key_issues": ["कृपया पुनः प्रयास करें" if language == "hindi" else "Please try again"]
            }
    
    def chat_about_video(self, transcript, corrected_transcript, analysis, user_question, chat_history, language="hindi"):
        """Chat with FULL CONTEXT"""
        
        if language == "hindi":
            lang_instruction = "हिंदी (देवनागरी लिपि में)"
            lang_note = "RESPOND ONLY in Devanagari (देवनागरी), NOT Urdu."
        else:
            lang_instruction = "English"
            lang_note = ""
        
        # FULL CONTEXT in system prompt
        system_prompt = f"""You are a medical expert. Respond in {lang_instruction}.

{lang_note}

=== VIDEO INFORMATION ===
Original Transcript: {transcript}

Corrected Transcript: {corrected_transcript}

Complete Analysis:
{json.dumps(analysis, ensure_ascii=False, indent=2)}

Summary: {analysis.get('summary', '')}

Rating: {analysis.get('rating', 0)}%

All Claims:
{json.dumps(analysis.get('claims', []), ensure_ascii=False, indent=2)}

Key Issues:
{json.dumps(analysis.get('key_issues', []), ensure_ascii=False, indent=2)}

=== YOUR ROLE ===
Answer questions about this video conversationally and accurately using the above information.
Always respond in {lang_instruction}."""

        messages = [{"role": "system", "content": system_prompt}]
        
        # Add recent chat history
        for chat in chat_history[-5:]:
            messages.append({"role": "user", "content": chat['user_message']})
            messages.append({"role": "assistant", "content": chat['assistant_response']})
        
        # Add current question
        messages.append({"role": "user", "content": user_question})
        
        try:
            response = self._call_with_fallback(messages, temperature=0.7, max_tokens=1000)
            print(f"[✓] Chat response generated")
            return response
        except Exception as e:
            print(f"[!] Chat failed: {e}")
            return f"त्रुटि: {str(e)}" if language == "hindi" else f"Error: {str(e)}"