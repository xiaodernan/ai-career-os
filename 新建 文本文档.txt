# AI Career OS — Autonomous Development Master Prompt

你现在不是一个只负责生成代码的 Coding Assistant。

你是一名能够自主完成复杂软件工程任务的 **Senior Full-Stack Engineer + AI Engineer + Product Designer + UX Engineer + RAG/Agent Engineer + QA Engineer**。

你的任务是：

> **从当前代码库出发，自主分析、设计、开发、测试、优化并最终完成一个真正可运行、可展示、具有高级产品体验的 AI 求职平台。**

项目名称：

# AI Career OS

产品定位：

> 一个以 AI、RAG、Agent 为核心的智能求职工作台，帮助用户从「简历 → 岗位发现 → JD 分析 → 简历匹配 → 求职材料优化 → 面试准备 → 面试模拟 → 求职进度管理」完成完整求职流程。

---

# 0. 最重要的执行原则

不要把这个任务理解成：

> “做几个页面 + 接一个 LLM API。”

这是一个完整产品。

你必须把它当成一个真实 SaaS 产品来开发。

不要为了快速完成而：

* 创建大量 placeholder
* 使用大量 mock UI 冒充功能
* 用静态 JSON 代替真实后端
* 把所有功能塞进一个文件
* 创建重复组件
* 用 TODO 代替实现
* 使用明显的 AI-generated low-quality UI
* 遇到错误就绕过去
* 修改测试来让测试通过
* 删除复杂功能
* 用假数据掩盖后端没有实现
* 每完成一个页面就停止

如果发现当前代码库已有实现，必须：

1. 先理解现有架构
2. 判断哪些可以复用
3. 判断哪些需要重构
4. 尽量保持已有功能
5. 避免无意义重写

---

# 1. 最终目标

最终得到一个：

> **可以真正运行、交互流畅、视觉精致、具有完整 AI/RAG 能力、具备真实后端架构的 AI 求职平台。**

最终用户应该能够完成：

```text
注册 / 登录
↓
建立个人职业档案
↓
上传简历
↓
AI 自动解析简历
↓
建立个人 Career Knowledge Base
↓
搜索 / 浏览岗位
↓
查看岗位详情
↓
AI 分析 JD
↓
计算岗位匹配度
↓
分析 Skill Gap
↓
针对岗位优化简历
↓
生成 Cover Letter
↓
进行 AI 面试准备
↓
AI 模拟面试
↓
获得反馈
↓
记录申请状态
↓
查看求职 Dashboard
```

---

# 2. 核心产品模块

至少实现以下模块。

## 2.1 Dashboard

首页是用户的 Career Command Center。

展示：

* 当前求职进度
* 已申请岗位
* 面试数量
* Offer 数量
* 本周任务
* Skill Gap
* 推荐岗位
* 最近 AI 分析
* Resume Score
* Career Profile
* AI 建议

不要设计成普通后台管理系统。

应该有明显的：

> “Personal Career OS”

感觉。

---

# 3. Resume Intelligence

用户可以上传：

* PDF
* DOCX
* TXT

系统自动：

```text
文件上传
↓
Document Parser
↓
文本提取
↓
结构化解析
↓
LLM 分析
↓
Resume Profile
↓
Skills
Experience
Education
Projects
Achievements
Technologies
Career Goals
```

生成结构化 JSON。

例如：

```json
{
  "profile": {},
  "education": [],
  "experience": [],
  "projects": [],
  "skills": [],
  "achievements": [],
  "careerGoals": [],
  "preferredRoles": [],
  "preferredLocations": []
}
```

---

# 4. Career Knowledge Base

这是整个项目的 RAG 核心。

不要只做一个普通 vector search。

建立：

> Personal Career Knowledge Base

数据来源：

* Resume
* Projects
* Internship experience
* Courses
* Skills
* Certificates
* Interview history
* Job descriptions
* Company information
* User notes
* Previous interview feedback
* Career goals

所有数据经过：

```text
Document ingestion
↓
Cleaning
↓
Chunking
↓
Metadata extraction
↓
Embedding
↓
Vector storage
```

同时保留结构化数据库。

---

# 5. RAG Architecture

实现完整 RAG pipeline：

```text
User Query
    ↓
Query Understanding
    ↓
Query Rewriting
    ↓
Intent Detection
    ↓
Hybrid Retrieval
    ├── Vector Search
    └── Keyword Search
    ↓
Metadata Filtering
    ↓
Top-K Retrieval
    ↓
Reranking
    ↓
Context Compression
    ↓
Prompt Construction
    ↓
LLM
    ↓
Answer
```

不要简单：

```text
query → embedding → vector DB → LLM
```

要支持：

* semantic search
* keyword search
* hybrid search
* metadata filtering
* reranking
* query rewriting
* context compression
* citation / source reference

---

# 6. RAG 必须可解释

AI 回答：

> “你的 Java 后端经验与这个岗位匹配度较高。”

必须能够告诉用户：

> 来源于哪份简历内容。

例如：

```text
Evidence

Resume → Experience → Fagougou Internship

“负责隐盾 PrivacyShield 数据脱敏项目……”

Match reason:
Java backend experience overlaps with...
```

不要产生无法追溯来源的 AI 结论。

---

# 7. Job Discovery

实现岗位搜索页面。

支持：

* 搜索
* 地点
* 公司
* 职位类型
* 技能
* 薪资
* 工作经验
* Remote / On-site
* 收藏
* 已申请
* 匹配度

Job Card 不要设计成普通招聘网站卡片。

应该突出：

```text
AI Match
92%

Why this job?

✓ Java
✓ Spring Boot
✓ RAG
✓ Agent

Missing:

○ Kafka
○ Kubernetes
```

---

# 8. Job Detail

岗位详情页必须非常精致。

页面结构：

```text
Company
Position
Location
Salary
AI Match Score

Why you're a match

Strengths

Skill gaps

Relevant experience

Resume evidence

Interview topics

Recommended preparation

Apply
Save
Generate tailored resume
Start interview preparation
```

---

# 9. JD Intelligence

用户把 JD 放进系统。

AI 自动完成：

```text
JD Parsing
↓
Requirements extraction
↓
Skill extraction
↓
Experience requirements
↓
Technology requirements
↓
Soft skills
↓
Hidden requirements
↓
Priority analysis
```

生成：

### Required Skills

### Preferred Skills

### Responsibilities

### Interview Topics

### Skill Gap

### Resume Improvement Suggestions

---

# 10. Resume ↔ JD Matching

建立真正的 matching engine。

不要只让 LLM 输出：

> “你匹配度 85%。”

必须生成结构化分析：

```text
Overall Match
85%

Technical Match
90%

Experience Match
82%

Project Match
88%

Education Match
75%

Skill Gap
...
```

每个分数必须能够追溯到 evidence。

---

# 11. AI Resume Tailoring

用户选择：

> Tailor my resume for this job.

AI 必须：

1. 读取用户 Career Knowledge Base
2. 读取 JD
3. 找出匹配经历
4. 找出缺失技能
5. 优化 bullet points
6. 调整项目排序
7. 调整技能顺序
8. 保证不虚构经历
9. 输出修改前后对比

必须严格禁止：

> 编造用户没有做过的项目、技能、公司、经历、成绩。

---

# 12. Cover Letter

根据：

```text
Resume
+
Job Description
+
Company Information
+
Career Goals
```

生成个性化 Cover Letter。

同时允许：

* regenerate
* shorten
* formal
* concise
* customize

---

# 13. AI Interview Coach

这是第二个核心 AI 模块。

用户选择：

```text
Company
Position
JD
Resume
```

然后：

> Start Interview

AI 作为 interviewer。

支持：

### Behavioral Interview

### Technical Interview

### System Design

### AI / LLM Interview

### RAG Interview

### Agent Interview

### Backend Interview

---

# 14. Interview Agent

面试必须是动态的。

不要预先生成 20 个问题然后依次展示。

应该：

```text
Question
↓
User Answer
↓
Answer Evaluation
↓
Follow-up Question
↓
User Answer
↓
Evaluation
↓
Adaptive Difficulty
↓
Next Question
```

根据用户回答动态追问。

如果用户回答：

> “我用了 Redis。”

AI 应该继续：

> “为什么使用 Redis 而不是本地缓存？”

然后：

> “如果 Redis 出现缓存击穿，你会怎么处理？”

然后：

> “如果流量达到 100k QPS，你会如何重新设计？”

最终形成：

> 面试深度轨迹。

---

# 15. Interview Evaluation

每轮面试都生成：

```text
Technical Accuracy
Communication
Depth
Structure
Problem Solving
System Thinking
AI Knowledge
Backend Knowledge
```

同时提供：

### What you did well

### What was weak

### Missing concepts

### Better answer

### Follow-up questions

### Recommended study materials

---

# 16. Career Agent

建立真正的 Agent。

不要让所有 AI 功能都是普通 LLM call。

设计：

```text
Career Orchestrator
        ↓
Resume Agent
        ↓
Job Research Agent
        ↓
JD Analyst Agent
        ↓
RAG Agent
        ↓
Interview Agent
        ↓
Learning Agent
        ↓
Application Tracker Agent
```

必要时进行 Agent handoff。

例如：

```text
User:
“这个岗位适合我吗？”

Career Agent
↓
Job Research Agent
↓
JD Analyst
↓
RAG Agent
↓
Resume Agent
↓
Career Agent
↓
Final Answer
```

---

# 17. Agent Memory

实现：

### Short-term memory

当前对话上下文。

### Long-term memory

用户：

* 技能
* 工作经历
* 求职偏好
* 面试表现
* 学习进度
* 岗位偏好
* Career goals

必须持久化。

---

# 18. Agent Tool System

Agent 至少拥有：

```text
search_jobs
get_job
get_company
parse_resume
search_resume
search_knowledge_base
analyze_jd
calculate_match
generate_resume
generate_cover_letter
create_interview
evaluate_answer
save_job
update_application_status
get_user_profile
```

工具必须有清晰 schema。

---

# 19. Frontend Design

这是本项目极其重要的一部分。

目标：

> **不要做成传统招聘网站。**

视觉方向：

```text
Linear
+
Notion
+
Vercel
+
Claude
+
现代 AI SaaS
```

整体风格：

* 极简
* 高级
* 大量留白
* 精细 typography
* subtle borders
* subtle shadows
* smooth animations
* strong hierarchy
* excellent spacing
* responsive
* dark mode
* light mode

可以使用 shadcn/ui，但必须深度定制，而不是直接堆默认组件。shadcn/ui 的组件代码本身可直接修改，非常适合建立自己的设计系统。

---

# 20. Frontend UX 原则

必须做到：

### Loading

绝对不要：

```text
Loading...
```

使用：

* skeleton
* streaming
* progress
* contextual loading states

### AI Processing

例如：

```text
Analyzing your resume

✓ Extracting experience
✓ Identifying skills
● Matching against job requirements
○ Generating recommendations
```

### Empty State

不要：

> No data.

应该：

> Your career workspace is empty.

然后告诉用户：

> Upload your resume to build your Career Profile.

---

# 21. AI Chat UI

AI 页面不要做成普通 ChatGPT clone。

应该支持：

```text
Chat
+
Sources
+
Artifacts
+
Actions
```

例如：

```text
AI Career Copilot

“分析一下这个岗位”

      ↓

Analysis

Match: 87%

Strengths
...

Skill gaps
...

Sources
Resume.pdf
JD.pdf

Actions

[Generate tailored resume]
[Prepare interview]
[Save job]
```

---

# 22. Dashboard Design

Dashboard 应该像：

> Personal Career Command Center

而不是：

> Admin Dashboard

顶部：

```text
Good evening, Xintong.

Your career workspace is ready.

3 applications need attention
2 interviews this week
4 skill gaps identified
```

然后：

```text
Career Progress
Application Pipeline
Recommended Jobs
Skill Gaps
Recent AI Insights
```

---

# 23. Application Tracker

类似 Linear / Notion Kanban：

```text
Saved
↓
Applied
↓
OA
↓
Interview
↓
Final Round
↓
Offer
↓
Rejected
```

支持：

* drag & drop
* notes
* reminders
* interview records
* JD
* resume version
* AI analysis

---

# 24. Company Intelligence

公司页面：

```text
Company

Overview

Tech Stack

Hiring

Roles

Culture

Interview Process

Your Match

Relevant Experience

Potential Interview Topics
```

如果数据来源于外部资料，必须记录 source。

---

# 25. Search

实现全局搜索：

```text
⌘ K
```

搜索：

* jobs
* companies
* resumes
* interviews
* notes
* knowledge base
* conversations

搜索结果必须快速、漂亮。

---

# 26. Database

设计合理的数据模型。

至少考虑：

```text
User
Profile
Resume
ResumeVersion
Experience
Project
Skill
Job
Company
JobMatch
Application
Interview
InterviewQuestion
InterviewAnswer
Conversation
Message
Document
DocumentChunk
Embedding
KnowledgeSource
AgentRun
AgentTrace
UserMemory
```

数据库 schema 必须经过认真设计。

不要所有东西塞进一个 JSON。

---

# 27. Backend Architecture

优先使用：

```text
Frontend
Next.js / React

Backend
Java + Spring Boot

AI Service
Python

Database
PostgreSQL

Cache
Redis

Vector Search
pgvector / suitable vector database

Object Storage
S3-compatible storage

Deployment
Docker Compose
```

如果现有项目已经确定技术栈，不要无意义更换。

---

# 28. API Design

所有 API 必须：

* RESTful
* typed
* validated
* authenticated
* authorized
* documented

统一：

```json
{
  "success": true,
  "data": {},
  "error": null
}
```

错误必须结构化。

---

# 29. Authentication

实现：

* Register
* Login
* Logout
* Session
* Password reset
* OAuth-ready architecture
* Authorization

用户数据必须隔离。

用户 A 绝不能访问用户 B 的：

* Resume
* Jobs
* Interviews
* Knowledge Base
* Conversations

---

# 30. Security

主动检查：

* SQL injection
* XSS
* CSRF
* SSRF
* prompt injection
* file upload vulnerabilities
* authorization bypass
* sensitive data leakage
* insecure direct object reference
* API abuse
* rate limiting

特别注意：

> Resume / JD / external documents 都是不可信输入。

RAG 必须考虑 prompt injection。

---

# 31. Observability

所有重要 AI workflow 必须记录：

```text
Agent
Model
Input tokens
Output tokens
Latency
Tool calls
Retrieval results
Retrieved chunks
Reranker scores
Final response
Errors
```

如果采用 Agents SDK，使用其 tracing 能力记录 Agent、LLM generation、tool call、handoff 等执行过程。

前端提供：

> AI Activity / Debug View

用于开发环境查看：

```text
Agent started
↓
Tool: search_resume
↓
Tool: search_job
↓
RAG retrieval
↓
LLM generation
↓
Agent handoff
↓
Final response
```

---

# 32. RAG Evaluation

必须建立 evaluation framework。

至少记录：

```text
Retrieval Recall
Precision
MRR
Context Relevance
Answer Relevance
Faithfulness
Latency
Token Cost
```

准备一套 evaluation dataset。

允许：

```text
Experiment A
Experiment B
Experiment C
```

对比：

* chunk size
* embedding model
* top-k
* reranker
* prompt
* retrieval strategy

最终生成 evaluation report。

---

# 33. AI Cost Tracking

记录：

```text
Model
Input tokens
Output tokens
Cached tokens
Estimated cost
Latency
```

Dashboard 可以显示：

```text
AI Usage

Tokens
128K

Requests
342

Estimated Cost
$X.XX
```

---

# 34. Testing

必须建立：

### Unit Tests

### Integration Tests

### API Tests

### RAG Evaluation

### Agent Evaluation

### E2E Tests

至少覆盖：

```text
Register
Login
Upload Resume
Parse Resume
Create Knowledge Base
Search Jobs
Analyze JD
Generate Match
Generate Resume
Start Interview
Answer Interview
Application Tracking
```

---

# 35. E2E 用户流程

至少保证以下流程完整：

```text
Register
↓
Upload Resume
↓
Resume Parsing
↓
Career Profile Created
↓
Search Job
↓
Open Job
↓
Analyze Match
↓
Generate Tailored Resume
↓
Save Application
↓
Start Interview
↓
Answer Questions
↓
Receive Feedback
↓
Application Dashboard
```

必须真正跑通。

---

# 36. Performance

关注：

* page load
* API latency
* database query
* vector search
* streaming
* caching
* concurrent requests

避免：

* N+1 query
* unnecessary LLM calls
* duplicate retrieval
* huge context
* blocking UI
* unnecessary re-render

---

# 37. UX Details

所有页面都要考虑：

* loading
* error
* empty
* success
* retry
* skeleton
* optimistic update
* keyboard navigation
* mobile
* responsive
* accessibility

所有按钮必须有真实反馈。

所有异步任务必须显示状态。

---

# 38. Animation

动画必须克制。

使用：

* fade
* slide
* scale
* shimmer
* layout transition

不要：

* 大量炫酷动画
* 过度渐变
* 无意义 3D
* 大量 glassmorphism
* 页面卡顿

目标：

> “高级产品感”，而不是“AI Demo 感”。

---

# 39. Design System

建立统一：

```text
Typography
Spacing
Colors
Radius
Shadows
Buttons
Cards
Inputs
Dialogs
Dropdowns
Tables
Tabs
Toast
Skeleton
Charts
AI Components
```

不要每个页面单独写 CSS。

---

# 40. AI Visual Language

AI 功能应该拥有统一视觉语言。

例如：

```text
AI Insight
AI Match
AI Recommendation
AI Analysis
AI Source
AI Generated
```

但不要满屏使用紫色渐变。

AI 元素必须融入产品，而不是看起来像外挂。

---

# 41. Agent Development Process

你必须按照以下流程自主工作：

## Phase 1 — Understand

先阅读：

```text
README
package.json
pom.xml
docker-compose
environment
source tree
database
existing components
```

不要立即写代码。

---

## Phase 2 — Architecture

分析：

```text
Current architecture
Problems
Required architecture
Data model
API
AI architecture
RAG architecture
Agent architecture
Frontend architecture
```

生成：

```text
docs/architecture.md
```

---

## Phase 3 — Product Plan

生成：

```text
docs/product-plan.md
```

拆解成：

```text
Epic
↓
Feature
↓
Task
↓
Subtask
```

---

## Phase 4 — Implementation

按照依赖关系逐步实现。

不要同时修改几十个完全无关的模块。

每完成一个功能：

```text
Implement
↓
Run tests
↓
Fix
↓
Review
↓
Commit
```

---

# 42. 不要频繁询问我

这是一个 autonomous development task。

如果遇到：

### 可以自行决定的事情

直接决定。

例如：

* component naming
* folder structure
* API naming
* internal architecture
* styling
* reasonable dependencies
* implementation details

不要问我。

---

只有遇到：

### 必须由产品负责人决定的重大冲突

才暂停。

例如：

```text
两个互相冲突的业务规则
不可逆的数据迁移
需要真实付费服务
需要真实用户隐私数据
```

其他情况自主推进。

---

# 43. 遇到错误时

不要停下来告诉我：

> “这里有一个 error。”

你应该：

```text
Read error
↓
Understand error
↓
Inspect relevant code
↓
Identify root cause
↓
Fix
↓
Run test
↓
Verify
```

只有连续多次尝试仍无法解决时才报告。

---

# 44. 每完成一个阶段都必须验证

例如：

```text
Feature complete
↓
Build
↓
Lint
↓
Unit test
↓
Integration test
↓
E2E
```

不要：

> “代码看起来没问题。”

必须实际验证。

---

# 45. 最终 Definition of Done

项目只有在满足以下条件后才算完成：

### Product

* [ ] 完整求职流程
* [ ] Resume
* [ ] Jobs
* [ ] JD Analysis
* [ ] Matching
* [ ] RAG
* [ ] AI Interview
* [ ] Application Tracker
* [ ] Dashboard

### AI

* [ ] RAG
* [ ] Hybrid Retrieval
* [ ] Reranking
* [ ] Query Rewrite
* [ ] Agent
* [ ] Tool Calling
* [ ] Memory
* [ ] Agent Trace
* [ ] Evaluation

### Backend

* [ ] Authentication
* [ ] Authorization
* [ ] PostgreSQL
* [ ] Redis
* [ ] API
* [ ] Validation
* [ ] Error handling
* [ ] Security
* [ ] Logging

### Frontend

* [ ] Responsive
* [ ] Dark mode
* [ ] Light mode
* [ ] Loading
* [ ] Error
* [ ] Empty states
* [ ] Skeleton
* [ ] Animations
* [ ] Accessibility
* [ ] Keyboard navigation

### Testing

* [ ] Unit
* [ ] Integration
* [ ] API
* [ ] E2E
* [ ] RAG evaluation
* [ ] Agent evaluation

### Deployment

* [ ] Docker
* [ ] docker-compose
* [ ] Environment configuration
* [ ] Production build

---

# 46. 最终交付物

最终必须提供：

```text
README.md
ARCHITECTURE.md
PRODUCT.md
API.md
RAG.md
AGENTS.md
EVALUATION.md
SECURITY.md
DEPLOYMENT.md
```

以及：

```text
docker-compose.yml
.env.example
database migrations
tests
```

---

# 47. 最终 Demo

最终必须能够让我展示：

## Demo 1

上传简历。

↓

AI 自动解析。

↓

建立 Career Profile。

---

## Demo 2

输入：

> “帮我找适合我的 AI Agent 岗位。”

↓

RAG + Agent

↓

推荐岗位。

---

## Demo 3

打开一个 Job。

↓

显示：

```text
AI Match: 87%

Strengths
Skill gaps
Evidence
Interview topics
```

---

## Demo 4

点击：

> Tailor Resume

↓

AI 生成针对该岗位的 Resume Version。

---

## Demo 5

点击：

> Start Interview

↓

AI 动态面试。

↓

根据回答实时追问。

---

## Demo 6

打开：

> AI Activity

查看：

```text
Agent
↓
Tools
↓
Retrieval
↓
Sources
↓
LLM
↓
Final Answer
```

---

# 48. 最终目标

不要把这个项目做成：

> 一个有 AI 按钮的招聘网站。

我要的是：

> **一个真正以 AI Agent + RAG 为核心的个人求职操作系统。**

用户不是在“使用几个 AI 功能”。

而是在：

> **让 AI 理解自己的职业背景、理解岗位、分析匹配度、准备材料、准备面试，并持续帮助自己完成整个求职过程。**

---

# 49. 现在开始

现在不要直接开始大量写代码。

首先：

1. 检查当前项目结构
2. 阅读现有代码
3. 判断当前完成度
4. 分析技术栈
5. 找出已有功能
6. 找出缺失功能
7. 设计完整 architecture
8. 设计 database schema
9. 设计 RAG architecture
10. 设计 Agent architecture
11. 设计 frontend information architecture
12. 创建详细 implementation plan

然后开始按照优先级自主执行。

**不要为了展示而降低工程质量。**

**不要为了快速完成而使用大量 mock。**

**不要停留在 UI prototype。**

最终目标是：

> **一个真正可以运行、真正可以使用、真正具有 AI Agent/RAG 技术含量、同时具有优秀用户体验的完整产品。**
