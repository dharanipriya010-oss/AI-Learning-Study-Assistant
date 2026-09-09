# 🎓 AI Learning & Study Assistant

An advanced, full-stack AI-powered study platform that creates personalized learning plans, answers questions from uploaded course materials with source citations, generates multi-format quizzes with automated grading, and tracks concept mastery using a long-term Memory system and Spaced Repetition System (SRS).

---
NAME: DHARANI PRIYA A      


REG NO: 920323104018

NM ID: 38b89559345cb62b3cb4c14cc2824e19

COLLEGE CODE: 9203

COLLEGE NAME: Christian College of Engineering and Technology 


---

## 🌟 Key Features

### 1. 📚 Course Materials & RAG Engine
- **Document Parsing & Ingestion**: Support for notes, Markdown, text, and course handouts.
- **Sliding Window Vector Indexing**: TF-IDF & Cosine Similarity vector search index.
- **Cited Answers**: Answers questions using uploaded course materials with exact page and section citations to eliminate hallucinations.

### 2. 💬 AI Tutor Chat
- Interactive Q&A over course context.
- Mathematical expression rendering via **KaTeX**.
- Source snippet inspection tooltips.

### 3. 📅 Smart Learning Plan Studio
- **Adaptive Day-by-Day Schedules**: Tailored study timeline based on goal, available daily hours, and current weak spots.
- **Progress Tracker**: Interactive completion checkboxes and dynamic percentage progress bars.
- **Calendar & Report Export**: Export schedules to **iCalendar (.ics)** format or **Markdown (.md)** files.

### 4. 🧠 Quiz & Flashcard Studio
- **Multi-Format Assessment**: Multiple-Choice Questions (MCQs), True/False, Short Answer.
- **Automated Grading Engine**: Detailed step-by-step rationale for correct and incorrect choices.
- **Spaced Repetition Flashcards (SRS)**: SuperMemo SM-2 algorithm rating controls (`Again`, `Hard`, `Good`, `Easy`) with 3D card flip animation.

### 5. 📊 Memory & Analytics Dashboard
- **Long-Term Memory Persistence**: Stores user profile, quiz performance history, and chat context.
- **Topic Mastery Matrix**: Visual chart tracking mastery percentage across all subject topics.
- **Weak Spots Auto-Flagging**: Automatically logs missed quiz concepts to prioritize in upcoming study plans.

### 6. 🛠️ Tools Hub
- **Wikipedia Concept Lookup**: External knowledge reference search.
- **Document Vector Search**: Raw vector similarity tester.
- **Report Exporters**: Export memory reports and active plans.

---

## 🚀 Quick Start & Installation

### Running the Application

Simply launch the `run.py` script using standard Python:

```bash
python run.py
```

This will:
1. Initialize the vector store index and pre-load sample course materials.
2. Start the HTTP server at `http://127.0.0.1:8000`.
3. Open the web interface automatically in your browser.

---

## ⚙️ Configuration & Gemini API Key

The application works 100% offline out of the box using a smart fallback engine. To enable real-time generative capabilities with Google's Gemini API:

1. Click on **Gemini API Key** in the top header.
2. Enter your API key (or set `export GEMINI_API_KEY="your_api_key"` in your terminal environment).
3. Click **Save Settings**.
