# Voice AI Agent (Sales)

### Production-Grade Voice AI for Customer Conversations, Sales Intelligence & Autonomous Business Actions

> **A voice agent that doesn't just talk to customers — it understands intent, remembers the conversation, makes decisions, takes business actions, and safely completes the workflow after the call.**

---

## ⚡ The 30-Second Pitch

Picture a customer calling a business. Instead of a robotic IVR menu, they have a real, natural conversation with an AI representative — one that actually **listens, understands, and knows what to do next.**

As the conversation unfolds, the agent silently tracks something most systems never bother to measure: **is this customer actually interested, and is that interest growing?** The moment a customer clearly says "yes, send me the brochure," the agent doesn't wait for a human to notice — it **sends a WhatsApp brochure in real time, mid-call.** If the customer isn't ready yet, the agent is smart enough to hold off and follow up later instead of spamming them.

That's the visible part. The invisible part is what makes this a *business system* rather than a demo: every action is tracked so it can never fire twice, every external failure (a dropped API call, a timeout) is caught and retried safely, and if the system crashes mid-call, **no conversation and no customer intent is ever silently lost.** The call transcript, the business action, and the outcome are all durably recorded — so a founder can trust this system with real customers and real revenue, not just a sandbox demo.

**In short: this is what it looks like when someone builds the boring, unglamorous infrastructure that separates a cool AI chatbot from a system a business can actually run on.**

---

## 💡 Why This Matters for Founders

If you're evaluating this as a founder or technical hiring manager, here's the honest value proposition:

- **It solves a real, expensive problem** — missed buying signals and slow follow-up cost sales teams revenue every day. This agent catches intent *while the customer is still on the phone.*
- **It's engineered to survive contact with reality** — external APIs go down, networks time out, processes crash. This system assumes all of that will happen and is designed not to break when it does.
- **It respects the difference between "real-time" and "durable."** The voice call has to feel instant; the business workflow behind it has to be bulletproof. Most prototypes conflate the two — this one doesn't.
- **It's observable, not a black box.** You can see exactly what the agent decided and why, in production, not just in a Jupyter notebook.

This isn't a weekend hackathon project. It's a demonstration of the engineering judgment required to take an LLM from "cool demo" to "system I'd trust with paying customers."

---

## 🏗️ System Architecture

```text
                    ┌─────────────────────┐
                    │      Customer       │
                    └──────────┬──────────┘
                               ▼
                    ┌─────────────────────┐
                    │  Twilio Voice /      │
                    │  Media Stream        │
                    └──────────┬──────────┘
                               ▼
                    ┌─────────────────────┐
                    │      Sarvam STT     │
                    └──────────┬──────────┘
                               ▼
              ┌────────────────────────────────┐
              │        LangGraph Agent          │
              │  Conversation Memory            │
              │  Intent & Interest Detection     │
              │  Decision Making                │
              │  Business Action Policy         │
              └───────────────┬────────────────┘
                    ┌─────────┴─────────┐
                    ▼                   ▼
             Continue Call       Business Action
                    ▼                   ▼
              Sarvam LLM         WhatsApp / Email /
                    ▼               Follow-up
               Murf TTS
                    ▼
                 Customer
                             │
                        CALL ENDS
                             ▼
                    ┌─────────────────────┐
                    │   Post-Call Engine   │
                    │  Call Finalization    │
                    │  Insight Generation   │
                    │  Deferred Actions     │
                    │  Durable Persistence  │
                    └──────────┬──────────┘
                               ▼
                        Redis Cleanup
```

---

## 🚀 Core Capabilities

**Real-Time Voice Conversation**
Twilio Media Streams · streaming STT/LLM/TTS · barge-in / interruption handling · fully asynchronous pipeline.

**Stateful Agent, Not Stateless Q&A**
The agent tracks purchase probability, interest score, confidence, explicit positive signals, and prior decisions across the *entire* conversation — reasoning about trajectory, not just the last sentence.

**Business-Aware Decision Making**
The system cleanly separates *what the customer said* from *what the business should do about it* — turning conversation into a real decision pipeline:

```
Conversation → Understanding → Decision → Action
```

rather than stopping at `Conversation → Response`.

---

## 🛡️ Production-Oriented Engineering

| Concern | How It's Handled |
|---|---|
| **Duplicate actions** | Business actions are persisted with unique constraints — a WhatsApp brochure can never send twice for the same call. |
| **Flaky external providers** | Transient failures (timeouts, 5xx) retry with bounded exponential backoff; permanent failures (bad credentials, bad data) fail fast instead of looping. |
| **Crash recovery** | Redis conversation memory is only deleted *after* post-call processing durably succeeds — a mid-process crash never loses the conversation. |
| **Graceful shutdown** | In-flight agent work finishes within a bounded timeout on call termination, then is safely cancelled — no hung calls, no dropped work. |

---

## 📊 Observability

Because "what actually happened on that call?" is a question a real business will ask.

- **Prometheus** — active calls, call duration, agent turn latency, STT/TTS/business-action/post-call latency and error rates, provider retries and timeouts, exposed via `/metrics`. Deliberately excludes high-cardinality data like phone numbers or transcripts.
- **LangSmith** — full tracing of the LangGraph execution path (state → reasoning → decision → action), so agent behavior is inspectable in production, not just in dev.

---

## 🧰 Technology Stack

| Layer | Technology |
|---|---|
| API | FastAPI |
| Voice Transport | Twilio Media Streams |
| Agent Orchestration | LangGraph |
| LLM | Sarvam |
| Speech-to-Text | Sarvam Saaras |
| Text-to-Speech | Murf |
| Business Messaging | Meta WhatsApp Cloud API |
| Conversation Memory | Redis |
| Durable Database | PostgreSQL (SQLAlchemy + Alembic) |
| Observability | Prometheus |
| Agent Tracing | LangSmith |
| Async Runtime | Python `asyncio`, HTTPX, WebSockets |

---

## 📁 Project Structure

```text
CustomerCare_Agent/
├── app/
│   ├── agent/          # state.py, graph.py, action.py
│   ├── voice/           # engine, Sarvam LLM/STT, Murf TTS
│   ├── services/        # call memory, post-call, business actions, WhatsApp
│   ├── repositories/
│   ├── models/
│   ├── observability/   # metrics.py
│   ├── core/
│   └── main.py
├── alembic/
├── .env
├── requirements.txt
└── README.md
```

---

## 🧩 Architecture Principles

1. **Separation of concerns** — providers, agent logic, persistence, actions, and observability live in distinct layers.
2. **Explicit agent state** — decisions live in structured state, not buried in prompt text.
3. **Business actions are durable** — external side effects are first-class, tracked operations, not fire-and-forget calls.
4. **Observability never blocks the customer** — metrics and tracing can never be the reason a call fails.
5. **Failure is expected, not exceptional** — timeouts, downtime, and malformed responses are treated as normal conditions to design around.
6. **Two lifecycles, one system** — the voice call is real-time; the business workflow behind it is durable. Conflating the two is where most prototypes break.

---

## 🧪 Current Development Stage

The system has moved past the basic voice-agent prototype and is being hardened toward real external-service operation:

- Real-time voice pipeline ✅
- Stateful LangGraph execution ✅
- Redis conversation memory + durable PostgreSQL state ✅
- Business-action idempotency ✅
- Meta WhatsApp integration ✅
- Post-call processing ✅
- Provider resilience, Prometheus metrics, LangSmith tracing ✅

Final validation is intended to run against **real provider credentials and an actual end-to-end voice call**, not mocked integrations alone.

---

## ⭐ Final Takeaway

This project isn't an attempt to prove an LLM can hold a conversation — that part is table stakes in 2026. It's an attempt to prove something harder: that conversational AI can be wired into a **real, durable, observable business workflow** that a company could actually run in production.

**It doesn't just listen. It doesn't just generate. It doesn't just talk.**
**It understands → decides → acts → persists → observes → recovers.**

That's the engineering bar for AI agents that operate as real members of a business — and it's the bar this project was built to meet.

---

### Built with a focus on
**AI Agents · Voice AI · LangGraph · Distributed Systems · Production Engineering · Observability · Autonomous Business Workflows**