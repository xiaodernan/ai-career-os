"""RAG evaluation framework (PRD §32).

Golden set -> hybrid retrieval -> retrieval metrics (recall@k, precision@k, MRR)
+ generation metrics (context relevance, answer relevance, faithfulness) with
LLM-as-judge when a real provider is configured and deterministic lexical
proxies otherwise, so `python -m app.eval.run_eval` works offline too.
Compare experiments (chunking/top-k/rerank/retrieval strategy) via JSON reports
under evals/reports/.
"""
