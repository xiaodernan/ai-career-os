"""Skill vocabulary + normalization.

Shared by ingestion (chunk skill tags), resume parsing, JD analysis and the matching
engine so skill comparison is exact, not vibes. Aliases map to canonical names.
"""

import re

CATEGORY: dict[str, str] = {
    # languages
    "Java": "language", "Python": "language", "Go": "language", "Rust": "language",
    "C++": "language", "C": "language", "JavaScript": "language", "TypeScript": "language",
    "Kotlin": "language", "Scala": "language", "SQL": "language", "R": "language",
    "Swift": "language", "PHP": "language", "Ruby": "language", "Shell": "language",
    "Bash": "language", "Dart": "language", "HTML": "other", "CSS": "other",
    # frameworks / libs
    "Spring Boot": "framework", "Spring": "framework", "MyBatis": "framework",
    "Django": "framework", "Flask": "framework", "FastAPI": "framework",
    "React": "framework", "Vue": "framework", "Next.js": "framework", "NestJS": "framework",
    "Node.js": "framework", "Express": "framework", "Gin": "framework",
    "Spring Cloud": "framework", "gRPC": "framework", "Dubbo": "framework",
    "Jackson": "library", "Netty": "library", "Pandera": "library",
    "NumPy": "library", "Pandas": "library", "Scikit-learn": "library",
    "PyTorch": "framework", "TensorFlow": "framework", "JAX": "framework",
    "LangChain": "framework", "LlamaIndex": "framework", "Spring AI": "framework",
    "Transformers": "library", "Diffusers": "library",
    # data / infra
    "MySQL": "data", "PostgreSQL": "data", "Redis": "data", "MongoDB": "data",
    "Elasticsearch": "data", "Kafka": "data", "RabbitMQ": "data", "RocketMQ": "data",
    "ClickHouse": "data", "Hive": "data", "Spark": "data", "Flink": "data",
    "Hadoop": "data", "pgvector": "data", "Milvus": "data", "Pinecone": "data",
    "Chroma": "data", "Qdrant": "data", "SQLite": "data", "Cassandra": "data",
    "Doris": "data", "TDengine": "data", "InfluxDB": "data",
    # cloud / devops
    "AWS": "cloud", "Azure": "cloud", "GCP": "cloud", "阿里云": "cloud",
    "Docker": "devops", "Kubernetes": "devops", "K8s": "devops", "Terraform": "devops",
    "Jenkins": "devops", "GitLab CI": "devops", "GitHub Actions": "devops",
    "Prometheus": "devops", "Grafana": "devops", "Nginx": "devops", "Linux": "devops",
    "Ansible": "devops", "Istio": "devops",
    # AI / methods
    "LLM": "ai", "RAG": "ai", "Agent": "ai", "AI Agents": "ai", "Prompt Engineering": "ai",
    "Fine-tuning": "ai", "LoRA": "ai", "NLP": "ai", "CV": "ai",
    "Machine Learning": "ai", "Deep Learning": "ai", "Reinforcement Learning": "ai",
    "MCP": "ai", "A2A": "ai", "Vector Search": "ai", "Embedding": "ai",
    "PyTorch Lightning": "ai", "ONNX": "ai", "TensorRT": "ai", "vLLM": "ai",
    "OpenAI API": "ai", "Anthropic API": "ai", "LangGraph": "ai",
    # tools / methods
    "Git": "tool", "Jira": "tool", "Confluence": "tool", "Figma": "tool",
    "Agile": "method", "Scrum": "method", "TDD": "method", "Microservices": "method",
    "System Design": "method", "Distributed Systems": "method",
    "REST API": "method", "GraphQL": "method", "WebSockets": "method",
    "OAuth": "method", "JWT": "method", "CI/CD": "devops",
    "Data Structures": "cs_fundamentals", "Algorithms": "cs_fundamentals",
    "OS": "cs_fundamentals", "Operating Systems": "cs_fundamentals",
    "Computer Networks": "cs_fundamentals", "Networking": "cs_fundamentals",
    "Concurrency": "cs_fundamentals", "Multithreading": "cs_fundamentals",
    # soft
    "Communication": "soft", "Leadership": "soft", "Teamwork": "soft",
    "Problem Solving": "soft", "Ownership": "soft", "Mentoring": "soft",
}

ALIASES: dict[str, str] = {
    "js": "JavaScript", "ts": "TypeScript", "react.js": "React", "reactjs": "React",
    "vue.js": "Vue", "vue3": "Vue", "springboot": "Spring Boot", "spring-boot": "Spring Boot",
    "postgres": "PostgreSQL", "psql": "PostgreSQL", "elastic": "Elasticsearch",
    "es": "Elasticsearch", "k8s": "Kubernetes", "ml": "Machine Learning",
    "dl": "Deep Learning", "nlp": "NLP", "computer vision": "CV",
    "大模型": "LLM", "向量数据库": "Vector Search", "微服务": "Microservices",
    "分布式": "Distributed Systems", "消息队列": "Kafka", "高并发": "Concurrency",
    "websocket": "WebSockets", "restful": "REST API", "rest": "REST API",
    "grpc": "gRPC", "nextjs": "Next.js", "fastapi": "FastAPI", "langchain": "LangChain",
    "langgraph": "LangGraph", "llamaindex": "LlamaIndex", "pytorch": "PyTorch",
    "tensorflow": "TensorFlow", "elasticsearch": "Elasticsearch",
    "spring cloud": "Spring Cloud", "springcloud": "Spring Cloud",
    "github actions": "GitHub Actions", "gitlab": "GitLab CI",
    "openai": "OpenAI API", "anthropic": "Anthropic API", "claude": "Anthropic API",
    "gpt": "LLM", "chatgpt": "LLM", "claude code": "AI Agents",
    "ai agent": "AI Agents", "ai agents": "AI Agents", "agent开发": "AI Agents",
    "rag": "RAG", "检索增强": "RAG", "prompt": "Prompt Engineering",
    "提示词": "Prompt Engineering", "调优": "Fine-tuning", "微调": "Fine-tuning",
}
CANONICAL = {k.lower(): k for k in CATEGORY}
for k in CATEGORY:
    CANONICAL[k.lower()] = k
for a, c in ALIASES.items():
    CANONICAL[a.lower()] = c

_CANON_PATTERNS: list[tuple[re.Pattern, str]] = []
for name in CATEGORY:
    esc = re.escape(name)
    _CANON_PATTERNS.append(
        (re.compile(rf"(?<![\w.+]){esc}(?![\w.+])", re.IGNORECASE), name))


def normalize(name: str) -> str:
    key = (name or "").strip().lower()
    return CANONICAL.get(key, (name or "").strip())


def extract_skills(text: str) -> list[str]:
    """Find canonical skills mentioned in free text."""
    found: set[str] = set()
    # sentence-final periods sit in the no-trailing-punctuation boundary; blank them
    probe = re.sub(r"\.(?=\s|$)", " ", text)
    low = probe.lower()
    for alias, canon in ALIASES.items():
        if alias in ("es", "ml", "dl", "ts", "js", "c", "r"):
            if re.search(rf"(?<![\w.]){re.escape(alias)}(?![\w.])", low):
                found.add(canon)
        elif alias in low:
            found.add(canon)
    for pat, name in _CANON_PATTERNS:
        if pat.search(probe):
            found.add(name)
    return sorted(found, key=str.lower)


def category(name: str) -> str:
    return CATEGORY.get(normalize(name), "other")
