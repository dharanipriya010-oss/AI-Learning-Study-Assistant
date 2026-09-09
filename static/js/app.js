/* AI Learning & Study Assistant - Main Frontend Script */

document.addEventListener("DOMContentLoaded", () => {
  // Navigation Tabs Logic
  const navBtns = document.querySelectorAll("#tab-nav button");
  const tabContents = document.querySelectorAll(".tab-content");

  navBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetTab = btn.getAttribute("data-tab");

      navBtns.forEach((b) => {
        b.classList.remove("active", "text-indigo-400", "bg-indigo-500/10", "border-indigo-500/20");
        b.classList.add("text-slate-400");
      });
      btn.classList.add("active", "text-indigo-400", "bg-indigo-500/10", "border-indigo-500/20");
      btn.classList.remove("text-slate-400");

      tabContents.forEach((content) => {
        content.classList.add("hidden");
        if (content.id === targetTab) {
          content.classList.remove("hidden");
        }
      });
    });
  });

  // Settings Modal Handlers
  const modalSettings = document.getElementById("modal-settings");
  const btnSettings = document.getElementById("btn-settings");
  const btnCloseSettings = document.getElementById("btn-close-settings");
  const btnSaveSettings = document.getElementById("btn-save-settings");
  const inputApiKey = document.getElementById("input-api-key");

  btnSettings.addEventListener("click", () => modalSettings.classList.remove("hidden"));
  btnCloseSettings.addEventListener("click", () => modalSettings.classList.add("hidden"));

  btnSaveSettings.addEventListener("click", async () => {
    const key = inputApiKey.value.strip ? inputApiKey.value.strip() : inputApiKey.value.trim();
    try {
      const res = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: key }),
      });
      const data = await res.json();
      alert(data.message || "Settings updated!");
      modalSettings.classList.add("hidden");
    } catch (err) {
      alert("Failed to update settings.");
    }
  });

  // 1. Document Upload (RAG Hub)
  const btnUploadDoc = document.getElementById("btn-upload-doc");
  const docFilename = document.getElementById("doc-filename");
  const docContent = document.getElementById("doc-content");
  const docsList = document.getElementById("docs-list");
  const docCountBadge = document.getElementById("doc-count-badge");
  const btnBrowseFile = document.getElementById("btn-browse-file");
  const filePicker = document.getElementById("file-picker");

  if (btnBrowseFile && filePicker) {
    btnBrowseFile.addEventListener("click", () => filePicker.click());
    filePicker.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (!file) return;
      docFilename.value = file.name;
      const reader = new FileReader();
      reader.onload = (event) => {
        docContent.value = event.target.result;
      };
      reader.readAsText(file);
    });
  }

  async function fetchDocuments() {
    try {
      const res = await fetch("/api/documents");
      const data = await res.json();
      const docs = data.documents || [];
      docCountBadge.innerText = `${docs.length} Documents (${data.total_chunks || 0} chunks)`;

      if (docs.length === 0) {
        docsList.innerHTML = `<p class="text-xs text-slate-500 italic">No documents uploaded yet. Add text notes above to enable RAG.</p>`;
        return;
      }

      docsList.innerHTML = docs
        .map(
          (d) => `
        <div class="p-3 bg-slate-900 border border-slate-800 rounded-xl flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <i data-lucide="file-text" class="w-4 h-4 text-indigo-400"></i>
            <div>
              <h4 class="text-xs font-semibold text-slate-200">${d.filename}</h4>
              <p class="text-[10px] text-slate-500">${d.char_count} characters • ${d.file_type}</p>
            </div>
          </div>
          <span class="text-[10px] bg-indigo-500/10 text-indigo-400 px-2 py-0.5 rounded-full border border-indigo-500/20">Indexed</span>
        </div>
      `
        )
        .join("");

      if (window.lucide) lucide.createIcons();
    } catch (e) {
      console.error("Error fetching documents:", e);
    }
  }

  btnUploadDoc.addEventListener("click", async () => {
    const filename = docFilename.value.trim() || "Course_Notes.txt";
    const content = docContent.value.trim();
    if (!content) {
      alert("Please paste text content before ingesting.");
      return;
    }

    try {
      const res = await fetch("/api/documents/upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename, content }),
      });
      const data = await res.json();
      if (data.status === "success") {
        alert(`Document ingested! ${data.chunks_added} vector chunks generated.`);
        docContent.value = "";
        fetchDocuments();
        refreshMemoryWidget();
      }
    } catch (e) {
      alert("Failed to ingest document.");
    }
  });

  // 2. AI Tutor Chat Logic
  const chatMessages = document.getElementById("chat-messages");
  const chatInput = document.getElementById("chat-input");
  const btnSendChat = document.getElementById("btn-send-chat");

  async function sendChatMessage() {
    const question = chatInput.value.trim();
    if (!question) return;

    // Append User Message
    chatMessages.innerHTML += `
      <div class="chat-bubble user flex items-start justify-end space-x-3">
        <div class="bg-indigo-600/20 border border-indigo-500/30 rounded-2xl rounded-tr-none p-3.5 text-xs text-slate-100 max-w-xl">
          <p>${escapeHtml(question)}</p>
        </div>
      </div>
    `;
    chatInput.value = "";
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Typing Indicator
    const typingId = `typing-${Date.now()}`;
    chatMessages.innerHTML += `
      <div id="${typingId}" class="chat-bubble assistant flex items-start space-x-3">
        <div class="w-8 h-8 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center flex-shrink-0">
          <i data-lucide="bot" class="w-4 h-4 text-indigo-400"></i>
        </div>
        <div class="bg-slate-900 border border-slate-800 rounded-2xl rounded-tl-none p-3.5 text-xs text-slate-400 animate-pulse">
          Searching course materials & generating response...
        </div>
      </div>
    `;
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const data = await res.json();
      document.getElementById(typingId)?.remove();

      let citationsHtml = "";
      if (data.citations && data.citations.length > 0) {
        citationsHtml = `<div class="pt-2 flex flex-wrap gap-1">` +
          data.citations.map((c) => `<span class="citation-tag" title="${escapeHtml(c.snippet)}">📖 ${c.filename} (p.${c.page})</span>`).join("") +
          `</div>`;
      }

      chatMessages.innerHTML += `
        <div class="chat-bubble assistant flex items-start space-x-3">
          <div class="w-8 h-8 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center flex-shrink-0">
            <i data-lucide="bot" class="w-4 h-4 text-indigo-400"></i>
          </div>
          <div class="bg-slate-900 border border-slate-800 rounded-2xl rounded-tl-none p-3.5 text-xs text-slate-200 max-w-2xl space-y-2">
            <div>${formatMarkdown(data.answer || "No response")}</div>
            ${citationsHtml}
          </div>
        </div>
      `;
      chatMessages.scrollTop = chatMessages.scrollHeight;

      if (window.renderMathInElement) {
        renderMathInElement(chatMessages, {
          delimiters: [
            { left: "$$", right: "$$", display: true },
            { left: "$", right: "$", display: false },
          ],
        });
      }
      if (window.lucide) lucide.createIcons();
    } catch (e) {
      document.getElementById(typingId)?.remove();
      alert("Failed to send question.");
    }
  }

  btnSendChat.addEventListener("click", sendChatMessage);
  chatInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendChatMessage();
  });

  // 3. Learning Plan Studio
  const btnGeneratePlan = document.getElementById("btn-generate-plan");
  const planSubject = document.getElementById("plan-subject");
  const planGoal = document.getElementById("plan-goal");
  const planDays = document.getElementById("plan-days");
  const planHours = document.getElementById("plan-hours");
  const planDisplayContainer = document.getElementById("plan-display-container");
  const btnExportPlanMd = document.getElementById("btn-export-plan-md");
  const btnExportPlanIcs = document.getElementById("btn-export-plan-ics");

  btnGeneratePlan.addEventListener("click", async () => {
    const subject = planSubject.value.trim() || "Data Structures & Algorithms";
    const goal = planGoal.value.trim() || "Master Core Concepts";
    const days = parseInt(planDays.value) || 7;
    const hours = parseFloat(planHours.value) || 2.0;

    planDisplayContainer.innerHTML = `<div class="text-center py-8 text-indigo-400 text-xs animate-pulse">Generating personalized learning plan with Gemini AI...</div>`;

    try {
      const res = await fetch("/api/planner/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subject, goal, total_days: days, daily_hours: hours }),
      });
      const plan = await res.json();
      renderPlanUI(plan);
    } catch (e) {
      alert("Failed to generate learning plan.");
    }
  });

  function renderPlanUI(plan) {
    if (!plan || !plan.modules) return;

    const modulesHtml = plan.modules
      .map(
        (m) => `
      <div class="bg-slate-950 border ${m.status === "completed" ? "border-emerald-500/40" : "border-slate-800"} rounded-xl p-4 space-y-2">
        <div class="flex items-center justify-between">
          <h4 class="text-xs font-bold text-slate-100 flex items-center space-x-2">
            <span class="w-6 h-6 rounded-full ${m.status === "completed" ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : "bg-indigo-500/20 text-indigo-400 border border-indigo-500/30"} flex items-center justify-center text-[10px]">
              ${m.day}
            </span>
            <span>${escapeHtml(m.title)}</span>
          </h4>
          <button data-day="${m.day}" data-completed="${m.status === "completed"}" class="btn-toggle-day text-[10px] px-2.5 py-1 rounded-lg ${m.status === "completed" ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : "bg-slate-800 text-slate-300 hover:bg-slate-700"} transition font-medium">
            ${m.status === "completed" ? "Completed ✓" : "Mark Done"}
          </button>
        </div>
        <p class="text-[11px] text-slate-400"><strong>Topics:</strong> ${(m.topics || []).join(", ")} • <strong>Est. Time:</strong> ${m.estimated_hours} hrs</p>
        <ul class="text-[11px] text-slate-300 space-y-1 pl-4 list-disc">
          ${(m.tasks || []).map((t) => `<li>${escapeHtml(t)}</li>`).join("")}
        </ul>
      </div>
    `
      )
      .join("");

    planDisplayContainer.innerHTML = `
      <div class="bg-indigo-950/40 border border-indigo-500/30 rounded-xl p-4 space-y-3">
        <div class="flex items-center justify-between">
          <div>
            <h3 class="text-sm font-bold text-white">${escapeHtml(plan.plan_title)}</h3>
            <p class="text-xs text-slate-300">${escapeHtml(plan.summary)}</p>
          </div>
          <span class="text-xs font-semibold text-indigo-300 bg-indigo-500/20 px-3 py-1 rounded-full border border-indigo-500/30">${plan.progress_pct || 0}% Complete</span>
        </div>
        <div class="w-full bg-slate-900 h-2 rounded-full overflow-hidden">
          <div class="bg-emerald-400 h-full transition-all duration-500" style="width: ${plan.progress_pct || 0}%"></div>
        </div>
      </div>
      <div class="space-y-3">${modulesHtml}</div>
    `;

    document.querySelectorAll(".btn-toggle-day").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const day = parseInt(btn.getAttribute("data-day"));
        const currentlyCompleted = btn.getAttribute("data-completed") === "true";
        try {
          const res = await fetch("/api/planner/toggle", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ day, completed: !currentlyCompleted }),
          });
          const updatedPlan = await res.json();
          renderPlanUI(updatedPlan);
        } catch (e) {
          console.error("Failed to toggle module completion.");
        }
      });
    });
  }

  btnExportPlanMd.addEventListener("click", async () => {
    try {
      const res = await fetch("/api/planner/export?format=md");
      const data = await res.json();
      if (data.markdown) {
        downloadBlob(data.markdown, "Study_Plan.md", "text/markdown");
      }
    } catch (e) {
      alert("Failed to export Markdown.");
    }
  });

  btnExportPlanIcs.addEventListener("click", () => {
    window.location.href = "/api/planner/export?format=ics";
  });

  // 4. Quiz & Flashcard Studio
  const subtabQuizBtn = document.getElementById("subtab-quiz-btn");
  const subtabSrsBtn = document.getElementById("subtab-srs-btn");
  const viewQuizContainer = document.getElementById("view-quiz-container");
  const viewSrsContainer = document.getElementById("view-srs-container");

  subtabQuizBtn.addEventListener("click", () => {
    subtabQuizBtn.className = "px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 text-white";
    subtabSrsBtn.className = "px-4 py-2 rounded-lg text-xs font-semibold bg-slate-800 text-slate-400 hover:text-slate-200";
    viewQuizContainer.classList.remove("hidden");
    viewSrsContainer.classList.add("hidden");
  });

  subtabSrsBtn.addEventListener("click", () => {
    subtabSrsBtn.className = "px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 text-white";
    subtabQuizBtn.className = "px-4 py-2 rounded-lg text-xs font-semibold bg-slate-800 text-slate-400 hover:text-slate-200";
    viewSrsContainer.classList.remove("hidden");
    viewQuizContainer.classList.add("hidden");
    loadFlashcardDeck();
  });

  const btnGenerateQuiz = document.getElementById("btn-generate-quiz");
  const quizTopic = document.getElementById("quiz-topic");
  const quizNum = document.getElementById("quiz-num");
  const quizDifficulty = document.getElementById("quiz-difficulty");
  const quizRunner = document.getElementById("quiz-runner");

  let currentActiveQuiz = null;

  btnGenerateQuiz.addEventListener("click", async () => {
    const topic = quizTopic.value.trim() || "General Course Material";
    const num_questions = parseInt(quizNum.value) || 5;
    const difficulty = quizDifficulty.value;

    quizRunner.classList.remove("hidden");
    quizRunner.innerHTML = `<div class="text-center py-6 text-indigo-400 text-xs animate-pulse">Generating ${difficulty} quiz on '${topic}' using course materials...</div>`;

    try {
      const res = await fetch("/api/quiz/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, num_questions, difficulty }),
      });
      currentActiveQuiz = await res.json();
      renderQuizRunner(currentActiveQuiz);
    } catch (e) {
      alert("Failed to generate quiz.");
    }
  });

  function renderQuizRunner(quiz) {
    if (!quiz || !quiz.questions) return;

    const questionsHtml = quiz.questions
      .map(
        (q, idx) => `
      <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
        <h4 class="text-xs font-semibold text-slate-100">${idx + 1}. ${escapeHtml(q.question)}</h4>
        <div class="space-y-2">
          ${(q.options || [])
            .map(
              (opt, oIdx) => `
            <label class="flex items-center space-x-3 p-2.5 bg-slate-950 rounded-lg border border-slate-800 hover:border-indigo-500/40 cursor-pointer text-xs text-slate-300 transition">
              <input type="radio" name="q_${q.id}" value="${escapeHtml(opt)}" class="text-indigo-600 focus:ring-0">
              <span>${escapeHtml(opt)}</span>
            </label>
          `
            )
            .join("")}
        </div>
      </div>
    `
      )
      .join("");

    quizRunner.innerHTML = `
      <div class="flex items-center justify-between border-b border-slate-800 pb-3">
        <h3 class="text-sm font-bold text-white">${escapeHtml(quiz.quiz_title || "Practice Assessment")}</h3>
        <span class="text-xs bg-indigo-500/20 text-indigo-300 px-2.5 py-0.5 rounded-full border border-indigo-500/30">${quiz.difficulty || "Medium"}</span>
      </div>
      <form id="form-submit-quiz" class="space-y-4">
        ${questionsHtml}
        <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs py-2.5 rounded-lg transition flex items-center justify-center space-x-2">
          <i data-lucide="check-circle" class="w-4 h-4"></i>
          <span>Submit Quiz for Grading</span>
        </button>
      </form>
      <div id="quiz-results-container"></div>
    `;

    document.getElementById("form-submit-quiz").addEventListener("submit", async (e) => {
      e.preventDefault();
      const answers = {};
      quiz.questions.forEach((q) => {
        const selected = document.querySelector(`input[name="q_${q.id}"]:checked`);
        if (selected) answers[q.id] = selected.value;
      });

      try {
        const res = await fetch("/api/quiz/grade", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ quiz_id: quiz.quiz_id, answers }),
        });
        const results = await res.json();
        renderQuizResults(results);
        refreshMemoryWidget();
      } catch (err) {
        alert("Failed to submit quiz.");
      }
    });

    if (window.lucide) lucide.createIcons();
  }

  function renderQuizResults(res) {
    const resultsContainer = document.getElementById("quiz-results-container");
    const feedbackHtml = (res.feedback || [])
      .map(
        (f) => `
      <div class="p-3 bg-slate-900 border ${f.is_correct ? "border-emerald-500/30" : "border-rose-500/30"} rounded-lg text-xs space-y-1">
        <div class="flex items-center justify-between font-semibold">
          <span class="${f.is_correct ? "text-emerald-400" : "text-rose-400"}">${f.is_correct ? "✓ Correct" : "✗ Incorrect"}</span>
          <span class="text-slate-500">${f.topic}</span>
        </div>
        <p class="text-slate-300"><strong>Q:</strong> ${escapeHtml(f.question)}</p>
        <p class="text-slate-400"><strong>Your Answer:</strong> ${escapeHtml(f.user_answer || "None")}</p>
        <p class="text-emerald-400"><strong>Correct Answer:</strong> ${escapeHtml(f.correct_answer)}</p>
        <p class="text-slate-400 italic"><strong>Rationale:</strong> ${escapeHtml(f.explanation)}</p>
      </div>
    `
      )
      .join("");

    resultsContainer.innerHTML = `
      <div class="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-4 mt-6">
        <div class="flex items-center justify-between">
          <h4 class="text-sm font-bold ${res.passed ? "text-emerald-400" : "text-amber-400"}">
            Score: ${res.score_pct}% (${res.correct_answers}/${res.total_questions})
          </h4>
          <span class="text-xs text-slate-400">${res.passed ? "Passed! Mastery logged." : "Weak topics auto-flagged in Memory!"}</span>
        </div>
        <div class="space-y-2">${feedbackHtml}</div>
      </div>
    `;
  }

  // Flashcards SRS Logic
  let flashcardDeck = [];
  let currentCardIndex = 0;
  let isFlipped = false;

  const flashcardBox = document.getElementById("flashcard-box");
  const flashcardInner = document.getElementById("flashcard-inner");
  const fcTopic = document.getElementById("fc-topic");
  const fcText = document.getElementById("fc-text");

  async function loadFlashcardDeck() {
    try {
      const res = await fetch("/api/flashcards");
      const data = await res.json();
      flashcardDeck = data.flashcards || [];

      if (flashcardDeck.length === 0) {
        fcTopic.innerText = "No Cards";
        fcText.innerText = "Generate a quiz first to automatically add SRS flashcards!";
        return;
      }
      currentCardIndex = 0;
      displayCurrentFlashcard();
    } catch (e) {
      console.error("Failed to load flashcards.");
    }
  }

  function displayCurrentFlashcard() {
    if (currentCardIndex >= flashcardDeck.length) {
      fcTopic.innerText = "Deck Complete";
      fcText.innerText = "You have reviewed all due flashcards!";
      return;
    }
    isFlipped = false;
    flashcardInner.classList.remove("flipped");
    const card = flashcardDeck[currentCardIndex];
    fcTopic.innerText = card.topic || "Study Concept";
    fcText.innerText = card.front;
  }

  flashcardBox.addEventListener("click", () => {
    if (!flashcardDeck[currentCardIndex]) return;
    isFlipped = !isFlipped;
    if (isFlipped) {
      flashcardInner.classList.add("flipped");
      fcText.innerText = flashcardDeck[currentCardIndex].back;
    } else {
      flashcardInner.classList.remove("flipped");
      fcText.innerText = flashcardDeck[currentCardIndex].front;
    }
  });

  document.querySelectorAll(".fc-rate-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!flashcardDeck[currentCardIndex]) return;
      const cardId = flashcardDeck[currentCardIndex].id;
      const rating = btn.getAttribute("data-rating");

      try {
        await fetch("/api/flashcard/srs", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ flashcard_id: cardId, rating }),
        });
        currentCardIndex++;
        displayCurrentFlashcard();
      } catch (e) {
        console.error("Failed to rate card.");
      }
    });
  });

  // 5. Memory & Analytics Dashboard
  let masteryChart = null;
  const weakSpotsList = document.getElementById("weak-spots-list");

  async function fetchMemoryAnalytics() {
    try {
      const res = await fetch("/api/memory");
      const summary = await res.json();

      // Render Weak Spots
      const weak = summary.weak_spots || [];
      if (weak.length === 0) {
        weakSpotsList.innerHTML = `<p class="text-xs text-slate-500 italic">No weak spots logged! Great job keeping up with quizzes.</p>`;
      } else {
        weakSpotsList.innerHTML = weak
          .map(
            (w) => `
          <div class="p-2.5 bg-slate-900 border border-slate-800 rounded-lg flex items-center justify-between text-xs">
            <div>
              <h5 class="font-semibold text-amber-400">${escapeHtml(w.topic)}</h5>
              <p class="text-[10px] text-slate-400">${escapeHtml(w.reason)}</p>
            </div>
            <span class="text-[10px] bg-amber-500/10 text-amber-300 px-2 py-0.5 rounded-full border border-amber-500/20">Needs Review</span>
          </div>
        `
          )
          .join("");
      }

      // Render Chart
      const matrix = summary.topic_mastery_matrix || {};
      const labels = Object.keys(matrix);
      const scores = labels.map((k) => matrix[k].mastery_score);

      const ctx = document.getElementById("mastery-chart")?.getContext("2d");
      if (ctx) {
        if (masteryChart) masteryChart.destroy();
        masteryChart = new Chart(ctx, {
          type: "bar",
          data: {
            labels: labels.length > 0 ? labels : ["Sample Topic"],
            datasets: [
              {
                label: "Mastery Score (%)",
                data: scores.length > 0 ? scores : [50],
                backgroundColor: "rgba(99, 102, 241, 0.6)",
                borderColor: "rgba(99, 102, 241, 1)",
                borderWidth: 1,
                borderRadius: 6,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              y: { beginAtZero: true, max: 100, ticks: { color: "#94a3b8" }, grid: { color: "#1e293b" } },
              x: { ticks: { color: "#94a3b8" }, grid: { color: "#1e293b" } },
            },
            plugins: { legend: { display: false } },
          },
        });
      }
    } catch (e) {
      console.error("Error fetching memory data:", e);
    }
  }

  async function refreshMemoryWidget() {
    try {
      const res = await fetch("/api/memory");
      const summary = await res.json();
      document.getElementById("widget-mastery-score").innerText = `${summary.average_mastery_pct || 0}%`;
      document.getElementById("widget-mastery-bar").style.width = `${summary.average_mastery_pct || 0}%`;
      document.getElementById("widget-weak-count").innerText = summary.weak_spots_count || 0;
      document.getElementById("widget-quiz-count").innerText = summary.quizzes_completed || 0;
    } catch (e) {}
  }

  document.querySelector('[data-tab="tab-memory"]').addEventListener("click", fetchMemoryAnalytics);

  // 6. Tools & Wiki Search
  const wikiQuery = document.getElementById("wiki-query");
  const btnWikiSearch = document.getElementById("btn-wiki-search");
  const wikiResult = document.getElementById("wiki-result");

  btnWikiSearch.addEventListener("click", async () => {
    const query = wikiQuery.value.trim();
    if (!query) return;
    wikiResult.classList.remove("hidden");
    wikiResult.innerHTML = `<span class="animate-pulse">Searching Wikipedia reference...</span>`;

    try {
      const res = await fetch("/api/tools/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tool_name: "web_search", params: { query } }),
      });
      const data = await res.json();
      const info = data.results || {};
      wikiResult.innerHTML = `
        <h4 class="font-bold text-indigo-400 text-sm">${escapeHtml(info.title)}</h4>
        <p>${escapeHtml(info.extract)}</p>
        ${info.url ? `<a href="${info.url}" target="_blank" class="text-xs text-indigo-300 underline">Read full Wikipedia entry →</a>` : ""}
      `;
    } catch (e) {
      alert("Failed to search Wikipedia.");
    }
  });

  // Helpers
  function escapeHtml(str) {
    return (str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function formatMarkdown(text) {
    return text
      .replace(/\n\n/g, "<br><br>")
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>")
      .replace(/`(.*?)`/g, "<code class='bg-slate-800 px-1 py-0.5 rounded text-indigo-300 font-mono text-[11px]'>$1</code>");
  }

  function downloadBlob(content, filename, contentType) {
    const blob = new Blob([content], { type: contentType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  // Initial Load
  fetchDocuments();
  refreshMemoryWidget();
});
