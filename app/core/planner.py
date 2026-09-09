import json
import time
from typing import Dict, Any, List, Optional
from app.core.llm_client import LLMClient
from app.core.memory_manager import MemoryManager

class LearningPlanner:
    """
    Generates and manages structured, adaptive learning plans.
    Integrates memory weak spots to dynamically emphasize topics needing review.
    """
    def __init__(self, llm_client: LLMClient, memory_manager: MemoryManager):
        self.llm_client = llm_client
        self.memory_manager = memory_manager
        self.active_plan: Optional[Dict[str, Any]] = None

    def create_plan(
        self,
        subject: str,
        goal: str,
        total_days: int = 7,
        daily_hours: float = 2.0,
        topics_list: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate a personalized study plan using Gemini LLM and student memory.
        """
        memory_summary = self.memory_manager.get_summary()
        weak_spots = [w["topic"] for w in memory_summary.get("weak_spots", [])]

        system_instruction = (
            "You are an expert Educational Curriculum & Study Planner AI. "
            "Generate a highly structured, realistic, day-by-day study schedule tailored to the user's timeline and goals."
        )

        user_prompt = (
            f"Create a {total_days}-day study plan for the subject/course: '{subject}'.\n"
            f"Primary Goal: {goal}\n"
            f"Available Study Time: {daily_hours} hours per day.\n"
            f"Specific Topics to Cover: {', '.join(topics_list) if topics_list else 'Extract core topics from course materials'}.\n"
            f"Current Weak Spots to Emphasize: {', '.join(weak_spots) if weak_spots else 'None logged yet'}.\n\n"
            "Return valid JSON matching this exact structure:\n"
            "{\n"
            '  "plan_title": "Title of the Plan",\n'
            '  "subject": "Subject Name",\n'
            '  "total_days": 7,\n'
            '  "daily_hours": 2.0,\n'
            '  "summary": "Brief overview of what will be mastered",\n'
            '  "modules": [\n'
            '    {\n'
            '      "day": 1,\n'
            '      "title": "Module Title",\n'
            '      "topics": ["Topic 1", "Topic 2"],\n'
            '      "estimated_hours": 2.0,\n'
            '      "tasks": ["Task 1 description", "Task 2 description"],\n'
            '      "status": "pending"\n'
            '    }\n'
            '  ]\n'
            "}"
        )

        plan_data = self.llm_client.generate_json(user_prompt, system_instruction=system_instruction)
        
        # Ensure default fallback structure if keys are missing or generic
        if "modules" not in plan_data or plan_data.get("plan_title") == "Personalized Master Study Plan":
            sub_clean = subject if subject else "Course Subject"
            plan_data = {
                "plan_title": f"Mastery Plan: {sub_clean}",
                "subject": sub_clean,
                "total_days": total_days,
                "daily_hours": daily_hours,
                "summary": f"Structured {total_days}-day learning schedule for {sub_clean} ({goal}).",
                "modules": [
                    {
                        "day": 1,
                        "title": f"Foundations of {sub_clean}",
                        "topics": [f"Core Principles of {sub_clean}", "Key Terminology & Concepts"],
                        "estimated_hours": daily_hours,
                        "tasks": ["Read document notes", "Review lecture outlines", "Take initial concept flashcards"],
                        "status": "pending"
                    },
                    {
                        "day": 2,
                        "title": f"{sub_clean} Architecture & Deep Dive",
                        "topics": [f"Architectural Components of {sub_clean}", "System Models"],
                        "estimated_hours": daily_hours,
                        "tasks": ["Query AI Tutor on complex relationships", "Solve practice conceptual problems"],
                        "status": "pending"
                    },
                    {
                        "day": 3,
                        "title": f"{sub_clean} Assessment & Weak Spot Review",
                        "topics": ["Self-Assessment", "Review Flagged Weak Spots"],
                        "estimated_hours": daily_hours,
                        "tasks": ["Take 5-question practice quiz", "Check Memory Dashboard for low-mastery topics"],
                        "status": "pending"
                    },
                    {
                        "day": 4,
                        "title": f"Advanced {sub_clean} Applications",
                        "topics": ["Case Studies", "Real-World Systems"],
                        "estimated_hours": daily_hours,
                        "tasks": ["Review advanced exam questions", "Complete SRS flashcards deck"],
                        "status": "pending"
                    },
                    {
                        "day": 5,
                        "title": f"Final Exam Prep & Mastery Check",
                        "topics": ["Comprehensive Synthesis", "Mastery Evaluation"],
                        "estimated_hours": daily_hours,
                        "tasks": ["Complete final assessment quiz", "Verify 100% topic mastery matrix score"],
                        "status": "pending"
                    }
                ][:total_days]
            }

        plan_data["created_at"] = time.time()
        plan_data["completed_days"] = 0
        plan_data["progress_pct"] = 0.0

        self.active_plan = plan_data
        return plan_data

    def toggle_day_completion(self, day_number: int, completed: bool) -> Dict[str, Any]:
        """
        Mark a day's module as completed or pending and recalculate progress.
        """
        if not self.active_plan or "modules" not in self.active_plan:
            return {"error": "No active plan found"}

        modules = self.active_plan["modules"]
        for mod in modules:
            if mod.get("day") == day_number:
                mod["status"] = "completed" if completed else "pending"
                break

        completed_count = sum(1 for m in modules if m.get("status") == "completed")
        total_modules = max(1, len(modules))
        
        self.active_plan["completed_days"] = completed_count
        self.active_plan["progress_pct"] = round((completed_count / total_modules) * 100.0, 1)

        return self.active_plan

    def export_icalendar(self) -> str:
        """
        Export study plan schedule as iCalendar (.ics) format for calendar apps.
        """
        if not self.active_plan or "modules" not in self.active_plan:
            return ""

        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//AI Learning Assistant//Study Plan Scheduler//EN",
            f"X-WR-CALNAME:{self.active_plan.get('plan_title', 'Study Plan')}"
        ]

        for mod in self.active_plan.get("modules", []):
            day = mod.get("day", 1)
            title = mod.get("title", f"Study Day {day}")
            tasks = ", ".join(mod.get("tasks", []))
            
            lines.extend([
                "BEGIN:VEVENT",
                f"SUMMARY:Study: {title}",
                f"DESCRIPTION:Topics: {', '.join(mod.get('topics', []))}\\nTasks: {tasks}",
                f"DURATION:PT{int(mod.get('estimated_hours', 2))}H",
                "END:VEVENT"
            ])

        lines.append("END:VCALENDAR")
        return "\n".join(lines)
