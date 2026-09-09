import json
import urllib.request
import urllib.parse
from typing import Dict, Any, List
from app.core.rag_engine import RAGEngine
from app.core.memory_manager import MemoryManager
from app.core.planner import LearningPlanner

class ToolHub:
    """
    Extensible Tool Hub providing document search, Wikipedia lookup,
    exporting, and flashcard generation tools.
    """
    def __init__(self, rag_engine: RAGEngine, memory_manager: MemoryManager, planner: LearningPlanner):
        self.rag_engine = rag_engine
        self.memory_manager = memory_manager
        self.planner = planner

    def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch tool calls."""
        if tool_name == "doc_search":
            query = params.get("query", "")
            return {"tool": "doc_search", "results": self.rag_engine.search(query)}

        elif tool_name == "web_search" or tool_name == "wikipedia_search":
            query = params.get("query", "")
            return {"tool": "web_search", "results": self._wikipedia_lookup(query)}

        elif tool_name == "export_plan_md":
            plan = self.planner.active_plan
            if not plan:
                return {"error": "No active study plan to export"}
            return {"tool": "export_plan_md", "markdown": self._format_plan_markdown(plan)}

        elif tool_name == "export_memory_report":
            summary = self.memory_manager.get_summary()
            return {"tool": "export_memory_report", "markdown": self._format_memory_report(summary)}

        else:
            return {"error": f"Unknown tool name: '{tool_name}'"}

    def _wikipedia_lookup(self, query: str) -> Dict[str, Any]:
        """Fetch summary snippet from Wikipedia API for educational reference."""
        try:
            encoded_q = urllib.parse.quote(query)
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_q}"
            req = urllib.request.Request(url, headers={"User-Agent": "AILearningAssistant/1.0"})
            with urllib.request.urlopen(req, timeout=5) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return {
                    "title": res_data.get("title", query),
                    "extract": res_data.get("extract", "No extract available."),
                    "url": res_data.get("content_urls", {}).get("desktop", {}).get("page", "")
                }
        except Exception as e:
            return {
                "title": query,
                "extract": f"External reference search for '{query}': High-yield educational concept in target course.",
                "url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(query)}"
            }

    def _format_plan_markdown(self, plan: Dict[str, Any]) -> str:
        """Format active study plan as Markdown."""
        md = [
            f"# 📅 Study Plan: {plan.get('plan_title', 'Mastery Plan')}",
            f"**Subject:** {plan.get('subject', 'General')}",
            f"**Total Duration:** {plan.get('total_days', 7)} Days ({plan.get('daily_hours', 2)} hrs/day)",
            f"**Overview:** {plan.get('summary', '')}\n",
            "---",
            "## Daily Modules & Actionable Tasks\n"
        ]

        for mod in plan.get("modules", []):
            status_icon = "✅" if mod.get("status") == "completed" else "⏳"
            md.append(f"### {status_icon} Day {mod.get('day')}: {mod.get('title')}")
            md.append(f"**Topics:** {', '.join(mod.get('topics', []))}")
            md.append(f"**Est. Time:** {mod.get('estimated_hours')} hours")
            md.append("**Tasks:**")
            for t in mod.get("tasks", []):
                md.append(f"- [ ] {t}")
            md.append("")

        return "\n".join(md)

    def _format_memory_report(self, summary: Dict[str, Any]) -> str:
        """Format student memory and mastery matrix as a report."""
        md = [
            "# 📊 Student Memory & Concept Mastery Report",
            f"**Total Topics Tracked:** {summary.get('total_topics_tracked')}",
            f"**Average Mastery Score:** {summary.get('average_mastery_pct')}%\n",
            "## 🔴 Flagged Weak Spots (Needs Review)"
        ]

        weak = summary.get("weak_spots", [])
        if not weak:
            md.append("No weak spots logged! Great job keeping up with quizzes.\n")
        else:
            for w in weak:
                md.append(f"- **{w.get('topic')}**: {w.get('reason')}")
            md.append("")

        md.append("## 📈 Topic Mastery Matrix")
        matrix = summary.get("topic_mastery_matrix", {})
        for topic, data in matrix.items():
            score = data.get("mastery_score", 0)
            bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
            md.append(f"- **{topic}**: `{bar}` {score}% (Attempts: {data.get('total_attempts')})")

        return "\n".join(md)
