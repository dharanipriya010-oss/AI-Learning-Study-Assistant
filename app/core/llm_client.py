import os
import json
import re
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional, List

class LLMClient:
    """
    Unified LLM Client interfacing with Google Gemini API with smart fallback.
    """
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model = model

    def set_api_key(self, api_key: str):
        self.api_key = api_key

    def generate_text(self, prompt: str, system_instruction: str = "") -> str:
        """
        Generate text response from Gemini API or fallback heuristic engine.
        """
        if self.api_key:
            try:
                return self._call_gemini_api(prompt, system_instruction)
            except Exception as e:
                print(f"[LLMClient Warning] Gemini API call failed: {e}. Falling back to smart heuristic engine.")
        
        return self._smart_fallback_response(prompt, system_instruction)

    def generate_json(self, prompt: str, system_instruction: str = "") -> Dict[str, Any]:
        """
        Generate structured JSON response.
        """
        json_prompt = f"{prompt}\n\nIMPORTANT: Respond ONLY with valid JSON inside a ```json ``` block or raw JSON object. Do not include extra text outside the JSON."
        raw_response = self.generate_text(json_prompt, system_instruction)
        
        # Parse JSON
        try:
            # Extract json code block if present
            match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', raw_response)
            if match:
                clean_json = match.group(1).strip()
            else:
                clean_json = raw_response.strip()
            return json.loads(clean_json)
        except Exception as e:
            print(f"[LLMClient Warning] JSON parse error: {e}. Output was: {raw_response[:200]}")
            return {"raw_text": raw_response}

    def _call_gemini_api(self, prompt: str, system_instruction: str) -> str:
        """
        Direct REST call to Gemini API using supported models (gemini-1.5-flash, gemini-2.0-flash).
        """
        models_to_try = [self.model, "gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
        # Deduplicate list preserving order
        models_to_try = list(dict.fromkeys([m for m in models_to_try if m]))
        
        last_error = None
        for model_name in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
                
                payload = {
                    "contents": [{
                        "role": "user",
                        "parts": [{"text": prompt}]
                    }],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 2048
                    }
                }
                
                if system_instruction:
                    payload["system_instruction"] = {
                        "parts": [{"text": system_instruction}]
                    }

                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                
                with urllib.request.urlopen(req, timeout=25) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    candidates = res_data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
            except Exception as e:
                last_error = e
                print(f"[LLMClient Info] Model '{model_name}' failed: {e}. Trying fallback model...")
                
        raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")

    def _smart_fallback_response(self, prompt: str, system_instruction: str) -> str:
        """
        Offline fallback logic providing structured responses for Q&A, Quizzes, and Study Plans.
        """
        prompt_lower = prompt.lower()
        
        # Check if JSON was expected (quiz or learning plan request)
        if "quiz" in prompt_lower or "multiple-choice" in prompt_lower or "flashcard" in prompt_lower:
            return json.dumps({
                "quiz_title": "Generated Quiz (Demo Mode)",
                "questions": [
                    {
                        "id": 1,
                        "type": "mcq",
                        "question": "What is the primary objective of Retrieval-Augmented Generation (RAG)?",
                        "options": [
                            "A) Fine-tuning large language models on private codebases",
                            "B) Enhancing LLM outputs with retrieved ground-truth context from external documents",
                            "C) Reducing the memory footprint of vector databases",
                            "D) Replacing neural networks with traditional search engines"
                        ],
                        "correct_answer": "B) Enhancing LLM outputs with retrieved ground-truth context from external documents",
                        "explanation": "RAG retrieves relevant passages from authoritative course materials to augment prompt context, reducing hallucination and delivering accurate answers with exact citations.",
                        "topic": "RAG Systems"
                    },
                    {
                        "id": 2,
                        "type": "true_false",
                        "question": "Spaced Repetition Systems (SRS) increase review intervals for items answered correctly.",
                        "options": ["True", "False"],
                        "correct_answer": "True",
                        "explanation": "SRS algorithms (like SuperMemo SM-2) exponentially space out card reviews when you answer correctly, optimizing long-term retention.",
                        "topic": "Learning Strategies"
                    },
                    {
                        "id": 3,
                        "type": "short_answer",
                        "question": "Explain how long-term memory improves personal study plans.",
                        "options": [],
                        "correct_answer": "By logging weak concepts and past quiz scores, the memory system dynamically prioritizes struggling topics in upcoming study schedules.",
                        "explanation": "Tracking topic mastery allows the planner to allocate more review time to low-mastery concepts.",
                        "topic": "Memory & Personalization"
                    }
                ],
                "flashcards": [
                    {
                        "id": "fc1",
                        "front": "What is Cosine Similarity in vector search?",
                        "back": "A metric that measures the cosine of the angle between two multi-dimensional vectors, indicating their semantic similarity (range -1 to 1).",
                        "topic": "Vector Search"
                    },
                    {
                        "id": "fc2",
                        "front": "What is the SM-2 Ease Factor (EF)?",
                        "back": "A multiplier in Spaced Repetition that increases or decreases card intervals based on performance ratings (Easy, Good, Hard, Again).",
                        "topic": "Spaced Repetition"
                    }
                ]
            }, indent=2)
            
        if "plan" in prompt_lower or "schedule" in prompt_lower:
            return json.dumps({
                "plan_title": "Personalized Master Study Plan",
                "total_days": 7,
                "daily_hours": 2,
                "summary": "Structured 7-day learning schedule covering core topics, document review, RAG practice, and self-assessment quizzes.",
                "modules": [
                    {
                        "day": 1,
                        "title": "Foundations & Core Principles",
                        "topics": ["Overview of Course Materials", "Key Definitions & Terminology"],
                        "estimated_hours": 2.0,
                        "tasks": ["Read Chapter 1 notes", "Complete initial self-assessment flashcards"],
                        "status": "pending"
                    },
                    {
                        "day": 2,
                        "title": "Deep Dive & RAG Q&A",
                        "topics": ["Contextual Search", "Vector Embeddings & Retrieval"],
                        "estimated_hours": 2.0,
                        "tasks": ["Upload reference materials", "Query AI Tutor on key algorithms"],
                        "status": "pending"
                    },
                    {
                        "day": 3,
                        "title": "Practice & Quiz Assessment",
                        "topics": ["MCQ Assessment", "Weak-Spot Identification"],
                        "estimated_hours": 2.0,
                        "tasks": ["Take 10-question quiz", "Review missed concepts in Memory Dashboard"],
                        "status": "pending"
                    },
                    {
                        "day": 4,
                        "title": "Advanced Applications",
                        "topics": ["Complex Problem Solving", "Case Studies"],
                        "estimated_hours": 2.0,
                        "tasks": ["Solve practice exercises", "Generate flashcards for difficult terms"],
                        "status": "pending"
                    },
                    {
                        "day": 5,
                        "title": "Final Review & Exam Prep",
                        "topics": ["Comprehensive Review", "Mastery Check"],
                        "estimated_hours": 2.0,
                        "tasks": ["Review all flagged weak spots", "Complete final mastery quiz"],
                        "status": "pending"
                    }
                ]
            }, indent=2)

        # Standard Q&A Fallback: Extract actual text from retrieved context if available!
        if "retrieved course material context:" in prompt_lower:
            parts = prompt.split("Retrieved Course Material Context:\n")
            if len(parts) > 1 and parts[1].strip() and "No specific course materials found" not in parts[1]:
                retrieved_text = parts[1].strip()
                clean_snippets = []
                for block in retrieved_text.split("\n\n---\n\n"):
                    lines = block.strip().split("\n")
                    header = lines[0] if lines else ""
                    body = "\n".join(lines[1:]) if len(lines) > 1 else block
                    clean_snippets.append(f"• **From {header}**:\n{body}")
                
                return (
                    "Based on your uploaded course materials:\n\n" +
                    "\n\n".join(clean_snippets[:3])
                )

        return "I am your AI Learning & Study Assistant. Ask any question about your uploaded materials!"
