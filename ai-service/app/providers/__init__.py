"""LLM & embedding providers behind one interface.

- openai_compat: OpenAI or any OpenAI-compatible gateway (DeepSeek, Qwen, ...).
- anthropic:     api.anthropic.com Messages API.
- ollama:        local Ollama server.
- mock:          deterministic, TEST-ONLY provider. Never served when APP_ENV=prod.

All providers normalize tool calling to OpenAI-style specs and report usage tokens.
"""
