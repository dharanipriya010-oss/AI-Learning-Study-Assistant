import json
import time
import math
from typing import Dict, Any, List, Optional
from app.core.llm_client import LLMClient
from app.core.memory_manager import MemoryManager
from app.core.rag_engine import RAGEngine

class QuizGenerator:
    """
    Generates multi-format quizzes & flashcards, performs automated grading,
    updates weak spots in student memory, and powers SRS Leitner/SM-2 spacing.
    """
    def __init__(self, llm_client: LLMClient, memory_manager: MemoryManager, rag_engine: RAGEngine):
        self.llm_client = llm_client
        self.memory_manager = memory_manager
        self.rag_engine = rag_engine
        self.active_quizzes: Dict[str, Dict[str, Any]] = {}
        self.flashcards_deck: List[Dict[str, Any]] = []

    def generate_quiz(
        self,
        topic: str = "General Course Material",
        num_questions: int = 5,
        difficulty: str = "Medium",
        include_flashcards: bool = True
    ) -> Dict[str, Any]:
        """
        Generate a quiz with MCQs, True/False, Short Answer questions, and Flashcards.
        Contextualized using RAG search on course documents if available.
        """
        # Retrieve relevant text context for the topic
        retrieved = self.rag_engine.search(topic, top_k=3)
        context_str = "\n".join([c["text"] for c in retrieved]) if retrieved else "Use standard domain knowledge."

        system_instruction = (
            "You are an expert Educational Assessment AI. "
            "Generate engaging, high-yield study quizzes and flashcards derived from course materials."
        )

        user_prompt = (
            f"Generate a {difficulty}-difficulty quiz on topic: '{topic}'.\n"
            f"Number of Questions: {num_questions}.\n"
            f"Course Context Excerpts:\n{context_str[:1500]}\n\n"
            "Return valid JSON adhering to this exact format:\n"
            "{\n"
            '  "quiz_id": "quiz_101",\n'
            '  "quiz_title": "Quiz Title",\n'
            '  "topic": "Topic Name",\n'
            '  "difficulty": "Medium",\n'
            '  "questions": [\n'
            '    {\n'
            '      "id": 1,\n'
            '      "type": "mcq",\n'
            '      "question": "Question text?",\n'
            '      "options": ["A) option 1", "B) option 2", "C) option 3", "D) option 4"],\n'
            '      "correct_answer": "B) option 2",\n'
            '      "explanation": "Detailed rationale...",\n'
            '      "topic": "Topic Name"\n'
            '    }\n'
            '  ],\n'
            '  "flashcards": [\n'
            '    {\n'
            '      "id": "fc_1",\n'
            '      "front": "Term or Question",\n'
            '      "back": "Definition or Explanation",\n'
            '      "topic": "Topic Name"\n'
            '    }\n'
            '  ]\n'
            "}"
        )

        quiz_data = self.llm_client.generate_json(user_prompt, system_instruction=system_instruction)

        # Check if LLM returned demo fallback and we have custom document context available
        if (quiz_data.get("quiz_title") == "Generated Quiz (Demo Mode)" or "questions" not in quiz_data) and retrieved:
            quiz_data = self._generate_dynamic_document_quiz(topic, retrieved, num_questions, difficulty)

        # Ensure ID and timestamps
        quiz_id = f"quiz_{int(time.time())}"
        quiz_data["quiz_id"] = quiz_id
        quiz_data["created_at"] = time.time()

        # Cache active quiz
        self.active_quizzes[quiz_id] = quiz_data
        
        # Add generated flashcards to deck
        if "flashcards" in quiz_data and isinstance(quiz_data["flashcards"], list):
            for fc in quiz_data["flashcards"]:
                fc["ease_factor"] = 2.5
                fc["interval"] = 1
                fc["repetitions"] = 0
                fc["next_review"] = time.time()
                self.flashcards_deck.append(fc)

        return quiz_data

    def _generate_dynamic_document_quiz(self, topic: str, chunks: List[Dict[str, Any]], num_q: int, difficulty: str) -> Dict[str, Any]:
        """
        Dynamically synthesize a quiz based on extracted course text when offline.
        """
        context_text = " ".join([c["text"] for c in chunks])
        source_file = chunks[0]["filename"] if chunks else "Course Materials"
        
        # Extract keywords and sentences
        sentences = [s.strip() for s in context_text.replace("\n", " ").split(".") if len(s.strip()) > 20]
        
        questions = []
        flashcards = []

        # Question 1: Fundamental concept
        q1_text = f"Based on {source_file}, what is the primary role or definition associated with '{topic}'?"
        q1_ans = f"A core concept from {source_file} detailing {topic} principles."
        if sentences:
            q1_ans = sentences[0] + "."

        questions.append({
            "id": 1,
            "type": "mcq",
            "question": f"According to your uploaded document ({source_file}), what is key regarding '{topic}'?",
            "options": [
                f"A) {q1_ans[:100]}",
                "B) It is a legacy protocol that has been completely deprecated.",
                "C) It only applies to non-networked standalone hardware.",
                "D) It increases system overhead without providing functional benefits."
            ],
            "correct_answer": f"A) {q1_ans[:100]}",
            "explanation": f"Source passage from {source_file}: '{q1_ans}'",
            "topic": topic
        })

        # Question 2: Key advantages / properties
        questions.append({
            "id": 2,
            "type": "mcq",
            "question": f"Which of the following advantages or concepts is highlighted in the study material for {topic}?",
            "options": [
                "A) Increased data redundancy and manual synchronization",
                "B) Improved security, reduced redundancy, and structured management",
                "C) Hardware-level memory distortion",
                "D) Random data deletion"
            ],
            "correct_answer": "B) Improved security, reduced redundancy, and structured management",
            "explanation": f"Study notes for {topic} emphasize structured management, security, and integrity controls.",
            "topic": topic
        })

        # Question 3: True / False assessment
        q3_sent = sentences[min(1, len(sentences)-1)] if sentences else f"{topic} optimizes data access."
        questions.append({
            "id": 3,
            "type": "true_false",
            "question": f"True or False: The uploaded course notes state that '{q3_sent[:120]}'.",
            "options": ["True", "False"],
            "correct_answer": "True",
            "explanation": f"Verified directly from course material passage in {source_file}.",
            "topic": topic
        })

        # Flashcards
        flashcards.append({
            "id": f"fc_{int(time.time())}_1",
            "front": f"What is the key takeaway for '{topic}'?",
            "back": sentences[0] if sentences else f"Core principle of {topic} from course materials.",
            "topic": topic
        })
        flashcards.append({
            "id": f"fc_{int(time.time())}_2",
            "front": f"Why is '{topic}' important in your course?",
            "back": sentences[min(1, len(sentences)-1)] if sentences else f"Provides essential foundation for {source_file}.",
            "topic": topic
        })

        return {
            "quiz_title": f"{topic} Mastery Quiz ({source_file})",
            "topic": topic,
            "difficulty": difficulty,
            "questions": questions[:num_q],
            "flashcards": flashcards
        }

    def grade_quiz(self, quiz_id: str, user_answers: Dict[str, str]) -> Dict[str, Any]:
        """
        Grade submitted answers, return detailed feedback, and update memory mastery.
        """
        quiz = self.active_quizzes.get(quiz_id)
        if not quiz or "questions" not in quiz:
            # Fallback if quiz object expired
            quiz = next(iter(self.active_quizzes.values()), None)
            if not quiz:
                return {"error": "Quiz session not found"}

        questions = quiz.get("questions", [])
        total = len(questions)
        correct_count = 0
        feedback_items = []

        for q in questions:
            q_id = str(q.get("id"))
            u_ans = user_answers.get(q_id, "").strip()
            c_ans = str(q.get("correct_answer", "")).strip()
            topic = q.get("topic", quiz.get("topic", "General"))

            # Clean option prefixes for comparison
            is_correct = False
            if q.get("type") == "mcq":
                is_correct = (u_ans.lower() in c_ans.lower()) or (c_ans.lower() in u_ans.lower())
            elif q.get("type") == "true_false":
                is_correct = u_ans.lower() == c_ans.lower()
            else: # short answer
                is_correct = any(word.lower() in u_ans.lower() for word in c_ans.split()[:3]) if u_ans else False

            if is_correct:
                correct_count += 1
                
            # Log to Memory Manager
            self.memory_manager.update_topic_performance(topic, is_correct, question_text=q.get("question", ""))

            feedback_items.append({
                "question_id": q.get("id"),
                "question": q.get("question"),
                "user_answer": u_ans,
                "correct_answer": c_ans,
                "is_correct": is_correct,
                "explanation": q.get("explanation", ""),
                "topic": topic
            })

        score_pct = round((correct_count / max(1, total)) * 100.0, 1)

        # Log quiz result in long-term memory
        self.memory_manager.log_quiz_result(
            quiz_id=quiz_id,
            score_pct=score_pct,
            total_questions=total,
            topic=quiz.get("topic", "General")
        )

        return {
            "quiz_id": quiz_id,
            "total_questions": total,
            "correct_answers": correct_count,
            "score_pct": score_pct,
            "passed": score_pct >= 70.0,
            "feedback": feedback_items
        }

    def review_flashcard_srs(self, flashcard_id: str, rating: str) -> Dict[str, Any]:
        """
        SuperMemo SM-2 Spaced Repetition System calculation.
        Ratings: 'again' (q=0), 'hard' (q=3), 'good' (q=4), 'easy' (q=5).
        """
        rating_map = {"again": 0, "hard": 3, "good": 4, "easy": 5}
        q = rating_map.get(rating.lower(), 4)

        card = next((fc for fc in self.flashcards_deck if str(fc.get("id")) == str(flashcard_id)), None)
        if not card:
            return {"error": "Flashcard not found"}

        ef = card.get("ease_factor", 2.5)
        interval = card.get("interval", 1)
        reps = card.get("repetitions", 0)

        if q >= 3:
            if reps == 0:
                interval = 1
            elif reps == 1:
                interval = 6
            else:
                interval = math.ceil(interval * ef)
            reps += 1
        else:
            reps = 0
            interval = 1

        # Calculate new Ease Factor (EF)
        ef = ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        ef = max(1.3, ef)

        # Next review timestamp (interval in days converted to seconds)
        next_review_ts = time.time() + (interval * 86400)

        card["ease_factor"] = round(ef, 2)
        card["interval"] = interval
        card["repetitions"] = reps
        card["next_review"] = next_review_ts

        return {
            "flashcard_id": flashcard_id,
            "rating": rating,
            "new_interval_days": interval,
            "new_ease_factor": round(ef, 2),
            "repetitions": reps,
            "next_review_ts": next_review_ts
        }
