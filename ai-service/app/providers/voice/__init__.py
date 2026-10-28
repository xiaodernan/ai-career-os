"""Speech providers behind one seam (19.6).

- openai_compat: OpenAI or any gateway that serves /audio/transcriptions and
  /audio/speech.
- mock: deterministic, TEST-ONLY. A fixed transcript and a short tone, refused
  when APP_ENV=prod.
- none: no provider -- the interview stays text-only and the page keeps the
  browser's own speech APIs.
"""
