import os
from groq import Groq
import json
import streamlit as st

class HealthClaimChecker:
    def __init__(self):
        api_key = st.secrets.get("GROQ_API_KEY") or os.getenv('GROQ_API_KEY')
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in secrets")
        
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"
    
    def analyze_claims(self, transcript, language="hindi"):
        lang_instruction = "Hindi" if language == "hindi" else "English"
        
        system_prompt = f"""You are a medical fact-checker. Analyze health claims in videos and provide response in {lang_instruction}.

Return ONLY valid JSON in this exact format:
{{
    "summary": "Overall analysis paragraph in {lang_instruction}",
    "claims": [
        {{
            "claim": "Specific health claim",
            "verdict": "TRUE/FALSE/PARTIALLY TRUE",
            "explanation": "Why this verdict",
            "sources": ["Source 1", "Source 2"]
        }}
    ],
    "rating": 75.5,
    "key_issues": ["Issue 1", "Issue 2"]
}}

Rules:
1. Provide detailed scientific analysis
2. Use medical sources (PubMed, WHO, CDC)
3. Rate accuracy 0-100%
4. Respond entirely in {lang_instruction}"""

        user_prompt = f"""Analyze this health video transcript and fact-check all claims:

{transcript}

Provide analysis in {lang_instruction} with scientific sources."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            
            # Extract JSON from response
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                return json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
                
        except Exception as e:
            # Fallback response
            return {
                "summary": f"Analysis completed. Transcript: {transcript[:200]}...",
                "claims": [{
                    "claim": "Unable to parse structured analysis",
                    "verdict": "ERROR",
                    "explanation": str(e),
                    "sources": []
                }],
                "rating": 50.0,
                "key_issues": ["Error in processing. Please try again."]
            }
    
    def chat_about_video(self, transcript, analysis, user_question, chat_history, language="hindi"):
        lang_instruction = "Hindi" if language == "hindi" else "English"
        
        messages = [
            {
                "role": "system", 
                "content": f"""You are a medical expert discussing a health video. Respond in {lang_instruction}.

Original transcript: {transcript}

Analysis: {json.dumps(analysis, ensure_ascii=False)}

Answer user questions conversationally and informatively in {lang_instruction}."""
            }
        ]
        
        # Add chat history
        for chat in chat_history[-5:]:  # Last 5 messages for context
            messages.append({"role": "user", "content": chat['user_message']})
            messages.append({"role": "assistant", "content": chat['assistant_response']})
        
        # Add current question
        messages.append({"role": "user", "content": user_question})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {str(e)}"