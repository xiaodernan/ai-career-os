#!/usr/bin/env bash
# Live full-stack smoke: backend(8080) + ai-service(8000) + DB career_os
set -u
B=http://127.0.0.1:8080/api/v1
EMAIL="smoke$(date +%s)@example.com"
PASS="Str0ngPassphrase!23"
step() { echo; echo "== $1"; }
jget() { PYEXPR="$1" python -c "import sys,json,os;d=json.load(sys.stdin);v=eval('d'+os.environ['PYEXPR']);print('' if v is None else v)"; }

step register
REG=$(curl -s -X POST $B/auth/register -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\",\"displayName\":\"Smoke Tester\"}")
T=$(echo "$REG" | jget "['data']['tokens']['accessToken']")
U=$(echo "$REG" | jget "['data']['user']['id']")
echo "user=$U token=${T:0:20}..."
AUTH="Authorization: Bearer $T"

step profile
curl -s -X PATCH $B/users/me -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"displayName":"Smoke Tester","headline":"Backend engineer","location":"Hangzhou"}' | head -c 200

step resume-create
RES=$(curl -s -X POST $B/resumes -H "$AUTH" -H "Content-Type: application/json" -d '{
 "title":"Main Resume",
 "plaintext":"Zhang San\nBackend Engineer\nEXPERIENCE\nTechCorp 2021-2024 Senior Backend Engineer\n- Built order services in Java with Spring Boot and MySQL, cut p99 latency by 40%\n- Introduced Redis cache and Kafka streaming for inventory events\n- Designed RAG pipeline over company docs using PostgreSQL and pgvector\nPROJECTS\nGateway platform in Spring Cloud and Redis rate limiting\nINTERNSHIPS\nAlibaba 2019 Summer Internship (实习): backend intern on the search service\nEDUCATION\nBachelor of Computer Science, Zhejiang University\nSKILLS\nJava Python Spring Boot MySQL Redis Kafka Elasticsearch RAG Docker Kubernetes"}')
RID=$(echo "$RES" | jget "['data']['id']")
echo "resume=$RID"

step resume-parse
curl -s -X POST $B/resumes/$RID/parse -H "$AUTH" | head -c 400

step knowledge-ingest
curl -s -X POST $B/knowledge/text -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"kind\":\"resume\",\"title\":\"Main Resume\",\"refId\":\"$RID\",\"text\":\"Senior backend engineer with five years building 分布式 微服务 order and payment platforms in Java, Spring Boot and Spring Cloud. Cut p99 latency by 40 per cent and served 高并发 并发 peaks of 12k QPS with Redis caching, 缓存穿透 caching-penetration guards and 消息队列 Kafka RabbitMQ event streaming. 数据库 MySQL 索引 优化: rewrote slow queries, added composite indexes and moved reporting to PostgreSQL. Deployed services on Kubernetes with Docker, autoscaling and Grafana alerts, and tuned scaling during campaigns. Spring Boot configuration security: JWT authentication, secret rotation, and the 数据脱敏 隐私 PrivacyShield project that masks PII before it reaches a log. Designed a RAG pipeline over company docs with PostgreSQL and pgvector. 教育背景: Zhejiang University, Bachelor of Engineering in Computer Science, 2019. 实习经历: an Internship on the payments team before joining full time. Java Python Elasticsearch Kafka RabbitMQ Kubernetes Docker RAG 分布式 微服务 并发 concurrency 索引 优化 缓存穿透 scaling messaging security.\"}" | head -c 300
echo

step knowledge-status
sleep 2
curl -s "$B/knowledge/sources" -H "$AUTH" | head -c 500

step job-create
JOB=$(curl -s -X POST $B/jobs -H "$AUTH" -H "Content-Type: application/json" -d '{
 "title":"Backend Engineer, Payments",
 "company":{"name":"TechCorp","industry":"fintech"},
 "location":"Hangzhou","remoteType":"hybrid","salaryMin":30,"salaryMax":45,
 "description":"We are hiring a backend engineer for the payments platform.",
 "requirements":["Java","Spring Boot","MySQL","Redis","Kafka"],
 "skills":["Java","Spring Boot","MySQL","Redis","Kafka","Docker","Kubernetes"],
 "niceToHave":["RAG","LLM applications"]}')
echo "$JOB" | head -c 400
JID=$(echo "$JOB" | jget "['data']['id']")

step job-save
curl -s -X POST $B/jobs/$JID/save -H "$AUTH" -H "Content-Type: application/json" -d '{"note":"top choice"}' | head -c 200

step jd-analyze
curl -s -X POST $B/jds -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"jobId\":\"$JID\",\"rawText\":\"Backend role. Must have Java Spring Boot MySQL Redis. Nice to have Kafka, K8s, RAG experience.\"}" | head -c 400

step match
M=$(curl -s -X POST $B/jobs/$JID/match -H "$AUTH" -H "Content-Type: application/json" -d '{}')
echo "$M" | head -c 700
MVID=$(echo "$M" | jget "['data'].get('resumeVersionId','')")

step tailor
curl -s -X POST $B/jobs/$JID/tailor -H "$AUTH" -H "Content-Type: application/json" -d '{}' | head -c 500

step cover-letter
curl -s -X POST $B/jobs/$JID/cover-letter -H "$AUTH" -H "Content-Type: application/json" -d '{}' | head -c 400

step copilot-chat
CC=$(curl -s -X POST $B/copilot/chat -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"message":"Find backend jobs that match my resume and tell me my biggest skill gap"}')
echo "$CC" | head -c 900
CID=$(echo "$CC" | jget "['data']['conversationId']")

step copilot-followup
curl -s -X POST $B/copilot/chat -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"conversationId\":\"$CID\",\"message\":\"Great, now tailor my resume for the first one\"}" | head -c 500

# The same turn as an event stream - what the copilot page calls. --max-time bounds a turn that
# never closes; curl exits 18 when the connection ends without a terminating chunk (the relay does
# the same), so the frame counts below, not curl's exit, are the check.
step copilot-stream
STREAM=$(curl -sN --max-time 60 -X POST $B/copilot/chat/stream -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"message":"Which skill gap should I close first?"}')
echo "$STREAM" | head -c 400
echo
echo "frames=$(printf '%s' "$STREAM" | grep -c '^event:') tokens=$(printf '%s' "$STREAM" | grep -cE '^event: ?token') done=$(printf '%s' "$STREAM" | grep -cE '^event: ?done')"
printf '%s' "$STREAM" | grep -qE '^event: ?done' || echo "!! the stream closed without a done frame"

step interview-start
IS=$(curl -s -X POST $B/interview/sessions -H "$AUTH" -H "Content-Type: application/json" -d '{"mode":"backend"}')
echo "$IS" | head -c 400
IID=$(echo "$IS" | jget "['data']['id']")

step interview-opening
curl -s -X POST $B/interview/sessions/$IID/opening -H "$AUTH" | head -c 400

step interview-answer
curl -s -X POST $B/interview/sessions/$IID/answer -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"answer":"I would shard orders by user_id, use optimistic locking on inventory rows, publish stock events through Kafka with idempotent consumers, and fall back to Redis for hot reads."}' | head -c 400

step interview-finalize
curl -s -X POST $B/interview/sessions/$IID/finalize -H "$AUTH" | head -c 500

step application-create
curl -s -X POST $B/applications -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"jobId\":\"$JID\",\"title\":\"Backend Engineer, Payments\",\"status\":\"applied\"}" | head -c 400

step dashboard
curl -s $B/reports/dashboard -H "$AUTH" | head -c 700

step activity
curl -s "$B/activity/runs?size=5" -H "$AUTH" | head -c 600

step search
curl -s "$B/search?q=Redis" -H "$AUTH" | head -c 500

echo; echo "== DONE"
