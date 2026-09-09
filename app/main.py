import os
import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

from app.config import BASE_DIR, SERVER_HOST, SERVER_PORT, DOCS_DIR
from app.core.llm_client import LLMClient
from app.core.rag_engine import RAGEngine
from app.core.memory_manager import MemoryManager
from app.core.planner import LearningPlanner
from app.core.quiz_generator import QuizGenerator
from app.core.tools import ToolHub

# Initialize core instances
llm_client = LLMClient()
memory_manager = MemoryManager()
rag_engine = RAGEngine(llm_client)
planner = LearningPlanner(llm_client, memory_manager)
quiz_generator = QuizGenerator(llm_client, memory_manager, rag_engine)
tool_hub = ToolHub(rag_engine, memory_manager, planner)

STATIC_DIR = BASE_DIR / "static"

class AssistantRequestHandler(BaseHTTPRequestHandler):
    """
    Standard HTTP Request Handler for AI Learning & Study Assistant REST API and Web UI.
    """

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == "/" or path == "/index.html":
            self._serve_static("index.html", "text/html")
        elif path.startswith("/css/") or path.startswith("/js/"):
            file_rel = path.lstrip("/")
            mime = "text/css" if path.endswith(".css") else "application/javascript"
            self._serve_static(file_rel, mime)
        elif path == "/api/documents":
            self._send_json({"documents": rag_engine.documents, "total_chunks": len(rag_engine.chunks)})
        elif path == "/api/memory":
            self._send_json(memory_manager.get_summary())
        elif path == "/api/planner/export":
            query = urllib.parse.parse_qs(parsed_url.query)
            fmt = query.get("format", ["md"])[0]
            if fmt == "ics":
                ics_str = planner.export_icalendar()
                self._send_response_raw(ics_str.encode("utf-8"), "text/calendar", filename="study_plan.ics")
            else:
                md_res = tool_hub.execute_tool("export_plan_md", {})
                self._send_json(md_res)
        elif path == "/api/flashcards":
            self._send_json({"flashcards": quiz_generator.flashcards_deck})
        else:
            self._send_error(404, "Not Found")

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        body = self._read_body_json()

        if path == "/api/documents/upload":
            filename = body.get("filename", "course_material.txt")
            content = body.get("content", "")
            if not content:
                self._send_json({"error": "Document content cannot be empty"}, status=400)
                return
            res = rag_engine.add_document(filename, content)
            self._send_json(res)

        elif path == "/api/chat":
            question = body.get("question", "")
            if not question:
                self._send_json({"error": "Question parameter required"}, status=400)
                return
            res = rag_engine.answer_question(question)
            memory_manager.add_chat_turn("user", question)
            memory_manager.add_chat_turn("assistant", res.get("answer", ""))
            self._send_json(res)

        elif path == "/api/planner/generate":
            subject = body.get("subject", "General Course")
            goal = body.get("goal", "Master Core Topics")
            days = int(body.get("total_days", 7))
            hours = float(body.get("daily_hours", 2.0))
            topics = body.get("topics", [])
            plan = planner.create_plan(subject, goal, days, hours, topics)
            self._send_json(plan)

        elif path == "/api/planner/toggle":
            day = int(body.get("day", 1))
            completed = bool(body.get("completed", True))
            res = planner.toggle_day_completion(day, completed)
            self._send_json(res)

        elif path == "/api/quiz/generate":
            topic = body.get("topic", "General Course Material")
            num_q = int(body.get("num_questions", 5))
            difficulty = body.get("difficulty", "Medium")
            quiz = quiz_generator.generate_quiz(topic, num_q, difficulty)
            self._send_json(quiz)

        elif path == "/api/quiz/grade":
            quiz_id = body.get("quiz_id", "")
            answers = body.get("answers", {})
            result = quiz_generator.grade_quiz(quiz_id, answers)
            self._send_json(result)

        elif path == "/api/flashcard/srs":
            fc_id = body.get("flashcard_id", "")
            rating = body.get("rating", "good")
            res = quiz_generator.review_flashcard_srs(fc_id, rating)
            self._send_json(res)

        elif path == "/api/settings":
            api_key = body.get("api_key", "").strip()
            if api_key:
                llm_client.set_api_key(api_key)
                self._send_json({"status": "success", "message": "Gemini API key updated successfully!"})
            else:
                self._send_json({"status": "info", "message": "Cleared API key. Switched to smart fallback mode."})

        elif path == "/api/tools/execute":
            tool_name = body.get("tool_name", "")
            params = body.get("params", {})
            res = tool_hub.execute_tool(tool_name, params)
            self._send_json(res)

        else:
            self._send_error(404, "Endpoint Not Found")

    def _serve_static(self, rel_path: str, mime_type: str):
        file_path = STATIC_DIR / rel_path
        if file_path.exists() and file_path.is_file():
            with open(file_path, "rb") as f:
                content = f.read()
            self._send_response_raw(content, mime_type)
        else:
            self._send_error(404, f"File {rel_path} not found")

    def _read_body_json(self) -> dict:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        raw_body = self.rfile.read(content_length).decode("utf-8")
        try:
            return json.loads(raw_body)
        except Exception:
            return {}

    def _send_json(self, data: dict, status: int = 200):
        body_bytes = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body_bytes)

    def _send_response_raw(self, content_bytes: bytes, content_type: str, filename: str = ""):
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(content_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(content_bytes)

def run_server(host=SERVER_HOST, port=SERVER_PORT):
    server_address = (host, port)
    httpd = HTTPServer(server_address, AssistantRequestHandler)
    print(f"🚀 AI Learning & Study Assistant running at http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
