import json
import time
from typing import Dict, Any, List, Optional
from app.config import MEMORY_FILE

class MemoryManager:
    """
    Manages long-term student memory, topic mastery matrix,
    weak-spot tracking, study session history, and user preferences.
    """
    def __init__(self):
        self.profile: Dict[str, Any] = {
            "name": "Student",
            "study_goal": "Master Course Materials & Pass Exam",
            "target_hours_per_day": 2.0,
            "streak_days": 1,
            "created_at": time.time()
        }
        self.topic_mastery: Dict[str, Dict[str, Any]] = {}
        self.weak_spots: List[Dict[str, Any]] = []
        self.quiz_history: List[Dict[str, Any]] = []
        self.study_logs: List[Dict[str, Any]] = []
        self.chat_history: List[Dict[str, str]] = []
        self.load_memory()

    def get_summary(self) -> Dict[str, Any]:
        """
        Return a high-level summary of student memory and progress analytics.
        """
        total_topics = len(self.topic_mastery)
        avg_mastery = (
            sum(t.get("mastery_score", 0) for t in self.topic_mastery.values()) / total_topics
            if total_topics > 0 else 0.0
        )
        
        return {
            "profile": self.profile,
            "total_topics_tracked": total_topics,
            "average_mastery_pct": round(avg_mastery, 1),
            "weak_spots_count": len(self.weak_spots),
            "weak_spots": self.weak_spots[-5:],  # latest 5 weak spots
            "quizzes_completed": len(self.quiz_history),
            "recent_quiz_scores": [q.get("score_pct", 0) for q in self.quiz_history[-5:]],
            "topic_mastery_matrix": self.topic_mastery
        }

    def update_topic_performance(self, topic: str, correct: bool, question_text: str = ""):
        """
        Update Topic Mastery Matrix and Weak Spot Queue based on quiz results.
        """
        if topic not in self.topic_mastery:
            self.topic_mastery[topic] = {
                "topic": topic,
                "total_attempts": 0,
                "correct_attempts": 0,
                "mastery_score": 50.0,  # baseline 50%
                "last_reviewed": time.time()
            }
            
        t_data = self.topic_mastery[topic]
        t_data["total_attempts"] += 1
        if correct:
            t_data["correct_attempts"] += 1
            # Increase mastery score
            t_data["mastery_score"] = min(100.0, t_data["mastery_score"] + 12.5)
        else:
            # Decrease mastery score
            t_data["mastery_score"] = max(0.0, t_data["mastery_score"] - 15.0)
            
            # Log as a weak spot if incorrect
            if not any(w["topic"].lower() == topic.lower() for w in self.weak_spots):
                self.weak_spots.append({
                    "topic": topic,
                    "flagged_at": time.time(),
                    "reason": f"Incorrect answer in quiz: '{question_text[:80]}...'" if question_text else "Quiz error",
                    "status": "needs_review"
                })

        t_data["last_reviewed"] = time.time()
        self.save_memory()

    def resolve_weak_spot(self, topic: str):
        """Mark a weak spot as resolved once user demonstrates mastery."""
        self.weak_spots = [w for w in self.weak_spots if w["topic"].lower() != topic.lower()]
        if topic in self.topic_mastery:
            self.topic_mastery[topic]["mastery_score"] = max(75.0, self.topic_mastery[topic]["mastery_score"])
        self.save_memory()

    def log_quiz_result(self, quiz_id: str, score_pct: float, total_questions: int, topic: str):
        """Record completed quiz in history."""
        self.quiz_history.append({
            "quiz_id": quiz_id,
            "score_pct": score_pct,
            "total_questions": total_questions,
            "topic": topic,
            "timestamp": time.time()
        })
        self.save_memory()

    def add_chat_turn(self, role: str, message: str):
        """Maintain recent chat turns for contextual memory."""
        self.chat_history.append({"role": role, "content": message})
        if len(self.chat_history) > 20:
            self.chat_history = self.chat_history[-20:]
        self.save_memory()

    def save_memory(self):
        """Persist memory data to JSON file."""
        data = {
            "profile": self.profile,
            "topic_mastery": self.topic_mastery,
            "weak_spots": self.weak_spots,
            "quiz_history": self.quiz_history,
            "study_logs": self.study_logs,
            "chat_history": self.chat_history
        }
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_memory(self):
        """Load memory data from JSON file if available."""
        if MEMORY_FILE.exists():
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.profile = data.get("profile", self.profile)
                    self.topic_mastery = data.get("topic_mastery", {})
                    self.weak_spots = data.get("weak_spots", [])
                    self.quiz_history = data.get("quiz_history", [])
                    self.study_logs = data.get("study_logs", [])
                    self.chat_history = data.get("chat_history", [])
            except Exception as e:
                print(f"[MemoryManager Warning] Failed to load memory file: {e}")
