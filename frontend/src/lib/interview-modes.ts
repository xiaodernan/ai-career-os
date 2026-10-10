/**
 * The modes a candidate can pick, as one client declaration instead of one per screen.
 *
 * The `/interviews` page already read this list; the job detail page's "start a mock interview"
 * menu spelled its own copy of it instead, so adding a mode meant editing two menus that send the
 * same field, and the copy had already lost the hints the first one prints. The authority for what
 * a mode MEANS is the ai-service persona table (`app/features/interview.py`): every value here must
 * be a key of that table, and the table's own fallback mode -- the one a session carries when
 * nobody picks -- deliberately stays out of this list, because a picker offering it would ask the
 * candidate to choose the default.
 * `ai-service/tests/test_the_interview_mode_vocabulary_has_one_author.py` pins both halves.
 */
export const INTERVIEW_MODES = [
  { value: "behavioral", label: "Behavioral", hint: "STAR stories from your real experience" },
  { value: "technical", label: "Technical", hint: "coding & fundamentals, deepening by answer" },
  { value: "system_design", label: "System design", hint: "scaling trade-offs for your target role" },
  { value: "ai_llm", label: "AI / LLM", hint: "models, fine-tuning, evaluation" },
  { value: "rag", label: "RAG", hint: "retrieval, chunking, reranking, citations" },
  { value: "agent", label: "Agent", hint: "planning, tools, orchestration" },
  { value: "backend", label: "Backend", hint: "APIs, storage, concurrency" },
];
