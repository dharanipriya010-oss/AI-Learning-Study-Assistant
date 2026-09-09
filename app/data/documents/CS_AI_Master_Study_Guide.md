# Computer Science & Artificial Intelligence Master Study Guide

## Chapter 1: Retrieval-Augmented Generation (RAG)
Retrieval-Augmented Generation (RAG) is an architectural framework that enhances Large Language Model (LLM) responses by querying external authoritative knowledge bases before generating text.

### Key Components of RAG:
1. **Document Ingestion**: Parsing source materials (PDFs, Markdown, raw text) into structured chunks.
2. **Text Chunking**: Dividing documents into overlapping sliding windows (e.g. 500 characters with 100 character overlap) to preserve contextual boundaries across split lines.
3. **Vector Embedding & Indexing**: Converting text chunks into high-dimensional vector representations using embedding models or TF-IDF term frequency metrics.
4. **Similarity Retrieval**: Using Cosine Similarity to find the Top-K most relevant text passages for a given user question.
5. **Prompt Augmentation & Generation**: Synthesizing answer text while providing exact source citations to eliminate hallucinations.

---

## Chapter 2: Memory Systems & Cognitive Science in AI
AI Study Assistants rely on multi-tier memory models to personalize education:

### 1. Epistemic / Conversation Memory
Stores short-term turn-by-turn chat history to sustain coherent context across multi-turn user dialogues.

### 2. Long-Term Topic Mastery Matrix
Tracks student performance on specific knowledge domains (0% to 100% mastery score). Whenever a student takes a quiz, correct answers boost mastery scores, while incorrect answers flag concepts as **Weak Spots Needing Review**.

### 3. Spaced Repetition Systems (SRS) & SuperMemo SM-2 Algorithm
Spaced Repetition is an evidence-based learning technique where review intervals expand exponentially as performance improves.
The **SuperMemo SM-2** algorithm computes card interval $I(n)$ and Ease Factor $EF$ using the formula:
$$EF' = EF + (0.1 - (5 - q) \times (0.08 + (5 - q) \times 0.02))$$
where $q$ represents the user response quality rating:
- **0 (Again)**: Complete blackout (reset interval to 1 day).
- **3 (Hard)**: Correct response with serious difficulty.
- **4 (Good)**: Correct response after hesitation.
- **5 (Easy)**: Perfect recall with zero hesitation.

---

## Chapter 3: Adaptive Study Planning & Assessment Studio
A study plan decomposes long-term academic goals into daily manageable modules:
- **Milestone Goals**: Daily targeted topics with estimated completion hours.
- **Adaptive Scheduling**: Automatically shifts uncompleted tasks forward and adjusts daily workloads based on weak spots recorded in the Memory Matrix.
- **Multi-Format Assessment**: Combines Multiple-Choice Questions (MCQs), True/False items, Short Answer prompts, and Flashcard decks.
