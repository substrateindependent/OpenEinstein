# Agent Architecture Best Practices: Design, Infrastructure, and Operations

**Research Date:** February 2026

**Author:** Glenn Clayton / Fieldcrest Ventures

**Purpose:** Inform agent architecture decisions for any AI-powered application, whether you're building a platform, an end-user product, or an internal tool.

> **Note on Currency:** This document reflects the state of the industry as of February 2026. The AI agent ecosystem is evolving rapidly — architectural patterns, tooling, and best practices may shift significantly within 6 months. Treat this as a point-in-time snapshot, not a permanent reference. Key areas likely to change fastest: model capabilities, context window sizes, framework maturity, and marketplace ecosystems.

---

## Key Takeaways 

1. **The industry is converging on skills-based architecture** as the default for most agentic workloads. Multi-agent systems are reserved for genuinely parallelizable, context-heavy tasks.

2. **Context engineering is what separates demo agents from production agents.** Getting the right information to the model at the right time matters more than model capability for most production failures. RAG, memory, embeddings, and long context windows are all components within this discipline.

3. **Skills + MCP is the right layered architecture** — MCP for data connectivity, skills for procedural expertise. They are complementary, not competing.

4. **Retrieval infrastructure is a foundational agent layer, not a separate system.** Agents use retrieval as a tool; memory is persistent state managed through MCP. Start with hybrid search, add agentic retrieval and memory incrementally.

5. **Most applications should use a hybrid** — skills-based agents for interactive workloads, orchestrator + subagents for autonomous pipelines that benefit from parallelization.

6. **User-facing features should default to single agent + skills** — simpler, cheaper, more maintainable, and easier to debug than multi-agent alternatives.

7. **Start simple, scale carefully** — OpenAI, Anthropic, LangChain, and Amazon all agree: begin with a single agent, add complexity only when genuinely needed. Forrester predicts 75% of firms attempting complex agentic architectures on their own will fail [5].

8. **The Agent Skills open standard is a strategic tailwind** — building on this standard means applications are portable, the skill ecosystem grows externally, and you aren't locked to a single AI provider.

---

## Table of Contents

**Part I: Strategic Overview**

- [1. Executive Summary](#1-executive-summary)
- [2. The Two Architectural Paradigms](#2-the-two-architectural-paradigms)
- [3. The Emerging Consensus: Skills-First, Subagents When Needed](#3-the-emerging-consensus-skills-first-subagents-when-needed)

**Part II: Foundational Layers**

- [4. Context Engineering: The Core Discipline](#4-context-engineering-the-core-discipline)
- [5. Skills + MCP: Expertise and Connectivity](#5-skills--mcp-expertise-and-connectivity)
- [6. Agent Memory and Retrieval Infrastructure](#6-agent-memory-and-retrieval-infrastructure)

**Part III: Agent Design Patterns**

- [7. State Machines and Structured State Management](#7-state-machines-and-structured-state-management)
- [8. Orchestration Patterns](#8-orchestration-patterns)

**Part IV: Infrastructure and Operations**

- [9. Model Routing Layer](#9-model-routing-layer)
- [10. Security](#10-security)
- [11. Production Deployment Lessons](#11-production-deployment-lessons)

**Part V: Ecosystem**

- [12. Skill Marketplaces and Distribution](#12-skill-marketplaces-and-distribution)

**Appendix**

- [Citations](#citations)

---

# Part I: Strategic Overview

---

## 1. Executive Summary

The AI agent ecosystem underwent a fundamental architectural shift between October 2025 and February 2026. Two core insights define the current state of the art:

**First, the general-purpose agent with composable skills and MCP integrations is the emerging dominant pattern**, with subagents reserved for parallelizable workloads that exceed a single context window. The industry has converged on a clear answer to the question of "many specialized agents vs. one general-purpose agent equipped with modular capabilities."

**Second, context engineering — the discipline of ensuring the right information reaches the model at the right time — is what separates agents that work in demos from those that work in production.** Retrieval (RAG), memory, embeddings, and long context windows are all components within this discipline, and they form the foundational infrastructure layer that makes agents reliable.

This document synthesizes findings from Anthropic, OpenAI, LangChain, Amazon, Google Cloud, and independent researchers to inform agent architecture decisions. The recommendation is a **hybrid approach** — a skills-first architecture for most workloads, with strategic subagent orchestration reserved for parallelizable tasks that exceed a single context window — built on a solid context engineering foundation.

---

## 2. The Two Architectural Paradigms

### 2.1 Specialized Agents (One Agent Per Task)

In this model, each AI task gets its own dedicated agent with a custom system prompt, tailored tool access, and narrow scope. OpenAI's "A Practical Guide to Building Agents" (January 2025) describes this as the foundation — an agent is a model configured with instructions and tools, running in a loop until a task is complete [1].

**How it works:**

- Each agent has a hyper-specific system prompt encoding domain expertise
- Tool access is scoped narrowly to only what the agent needs
- The agent runs in a tight loop: reason → act → observe → repeat
- Multiple agents coordinate via orchestration patterns (manager/orchestrator or decentralized handoffs)

**OpenAI's orchestration patterns fall into two categories** [1]:

- **Manager pattern**: A central LLM orchestrates a network of specialized agents through tool calls, maintaining context and synthesizing results
- **Decentralized/handoff pattern**: Peer agents hand off tasks to one another based on specialization, with conversation history transferred at each handoff

**Strengths:**

- Maximum control over each agent's behavior
- Clear separation of concerns
- Easier to evaluate and debug individual agents in isolation
- Each agent's prompt can be optimized independently
- Narrow tool access reduces attack surface per agent

**Weaknesses:**

- Proliferation of agents to maintain as the system grows
- Coordination complexity grows rapidly — Anthropic's research system found early prototypes spawning 50 subagents for simple queries and distracting each other with excessive updates [3]
- Context transfer between agents is where most failures occur [5]
- Duplicated infrastructure and boilerplate across agents
- Harder to share improvements — a better prompting technique must be manually propagated to every agent
- Cost scales with agent count — multi-agent systems use approximately 15x more tokens than single-agent chat interactions [3]

### 2.2 General-Purpose Agent + Skills + MCP (Dynamic Capability Loading)

In this model, a single general-purpose agent runtime dynamically loads domain-specific expertise (skills) and external connectivity (MCP servers) on demand. Anthropic formalized this with Agent Skills in October 2025 and released it as an open standard in December 2025 [2][4].

**How it works:**

- A single agent runtime has access to a registry of skills and MCP servers
- Skills are folders containing instructions, scripts, and reference materials
- At startup, only skill metadata (~100 tokens each) is loaded into context
- When a user's request matches a skill's domain, the full skill instructions are loaded on demand ("progressive disclosure")
- MCP servers provide standardized connectivity to external systems (databases, APIs, tools)
- Skills provide the procedural knowledge; MCP provides the data connectivity [2][4]

**The PC analogy** (from Anthropic's engineering blog) [2]:

- **Models** = Processors (raw computational engine)
- **Agent runtimes** = Operating system (orchestrating resources and processes)
- **Skills** = Applications (modular, task-specific programs anyone can build and run)

**Strengths:**

- One agent to maintain, not dozens
- Skills are composable — combine multiple skills for complex workflows
- Progressive disclosure keeps context efficient (only load what's needed)
- Skills are portable across platforms — the open standard means skills work on Claude, OpenAI, Cursor, and other compliant platforms [7]
- Organizational knowledge is captured once and reused everywhere
- Easier to version, test, and distribute expertise
- Lower token cost than multi-agent systems for most tasks

**Weaknesses:**

- Single context window limits parallelization
- Very large skill libraries can still cause context pressure if many skills trigger simultaneously
- Less isolation — a misbehaving skill can pollute the context for other tasks
- Security surface is different — skills with executable code require trust and auditing [2]
- Not ideal for tasks that genuinely require parallel independent reasoning across separate context windows

---

## 3. The Emerging Consensus: Skills-First, Subagents When Needed

### 3.1 LangChain's Four-Pattern Framework

LangChain identifies four architectural patterns that form the foundation of most multi-agent applications: subagents, skills, handoffs, and routers [8][9].

Critically, LangChain considers the **skills pattern a "quasi-multi-agent architecture"** — it technically uses a single agent but provides similar benefits to multi-agent patterns (distributed development, fine-grained context control) through a lighter-weight, prompt-driven method [8].

LangChain's benchmarking found significant performance degradation in single agents as context size increases, even with irrelevant context. This is a key motivation for both the skills pattern (load only relevant context) and multi-agent patterns (isolate context per agent) [9].

**Their guidance**: Start with a single agent with well-designed tools. Graduate to skills for context management. Use subagents only when you genuinely need parallel independent reasoning or context isolation [8].

### 3.2 Anthropic's Production Experience

Anthropic's multi-agent research system provides the most detailed public account of both approaches in production [3]:

**The architecture**: An orchestrator-worker pattern where a lead agent (Claude Opus 4) coordinates subagents (Claude Sonnet 4) that work in parallel. The lead agent analyzes queries, develops strategy, spawns subagents, and synthesizes results.

**Performance**: The multi-agent setup outperformed single-agent Claude Opus 4 by 90.2% on complex research evaluations — but at a significant cost premium (4x tokens for agents, 15x for multi-agent vs. chat) [3].

**Key lessons** [3]:

1. **Detailed task delegation is critical** — vague instructions like "research the semiconductor shortage" led to duplicated work and gaps
2. **Scale effort to query complexity** — simple fact checks need 1 agent with 3-10 tool calls; complex research needs 10+ subagents with divided responsibilities
3. **Early prototypes failed spectacularly** — spawning too many agents, endless web searches, agents distracting each other
4. **Tool reliability matters** — a tool-testing agent that rewrote tool descriptions decreased task completion time by 40%
5. **Multi-agent is not universal** — domains requiring shared context among all agents or with many inter-agent dependencies are poor fits

### 3.3 The Hybrid Consensus

The industry consensus as of early 2026 [5][6][10]:

| Pattern | Best For | Token Cost | Complexity |
|---------|----------|------------|------------|
| Single agent + tools | Focused, well-defined tasks | Low | Low |
| Single agent + skills | Repeatable domain expertise across conversations | Low-Medium | Low-Medium |
| Orchestrator + subagents | Parallelizable workloads exceeding one context window | High | High |
| Multi-agent handoffs | Sequential workflows with clear domain boundaries | Medium-High | Medium-High |

**Start with skills. Add subagents only when the task genuinely requires parallel reasoning across independent context windows or when a single context window cannot hold the necessary information.**

---

# Part II: Foundational Layers

---

## 4. Context Engineering: The Core Discipline

### 4.1 What Context Engineering Is

Context engineering is the practice of designing the environment in which an agent operates before it generates anything. If a prompt tells an agent *what to do*, the context tells it *how to think*. A context engineer designs how information flows into the model — structuring knowledge, building retrieval pipelines, creating tool schemas, defining memory strategies, enforcing rules, and refining context at runtime [36][37][38].

The term emerged in 2025-2026 as the industry recognized that **the #1 reason AI systems fail in production isn't the model's capability — it's that the model doesn't have the right information when it needs it.** LangChain's 2025 State of Agent Engineering report found 57% of organizations now have AI agents in production, yet 32% cite quality as the top barrier — with most failures traced not to LLM capabilities but to poor context management [36].

### 4.2 Why It Replaced Prompt Engineering as the Focus

Prompt engineering — crafting the right instructions for an LLM — is still useful but is no longer the center of AI development. The shift reflects a larger trend: reliable AI comes from architecture, not clever phrasing. Even the co-author of the original 2020 RAG paper acknowledges the rebranding: "People have rebranded it now as context engineering, which includes MCP and RAG" [39].

### 4.3 The Six Techniques

Six techniques define effective context engineering in 2026 [36]:

1. **Dynamic context selection** — Load only what's relevant (aligned with Agent Skills progressive disclosure — see Section 5.3)
2. **Context compression** — Reduce token usage while preserving meaning
3. **Hierarchical context layouts** — Signal importance through structure (system prompt > retrieved data > conversation history)
4. **Just-in-time retrieval** — Agents discover and dynamically load data at runtime using tools (see Section 6)
5. **Memory management** — Persistent state across sessions (see Section 6.6)
6. **Tool schema design** — Structured interfaces for agent-data interaction (aligned with MCP — see Section 5)

### 4.4 How Context Engineering Connects to the Rest of This Document

Context engineering is not a separate architectural layer — it is the unifying discipline that explains *why* the foundational layers in Part II matter:

- **Skills** (Section 5) implement dynamic context selection through progressive disclosure
- **MCP** (Section 5) provides standardized tool schemas for data access
- **Retrieval infrastructure** (Section 6) implements just-in-time retrieval
- **Agent memory** (Section 6.6) implements persistent memory management
- **State machines** (Section 7) provide structured context flow between agent steps

Every architectural decision in this document can be evaluated through the lens of: *does this get the right information to the model at the right time, in the right format, at an acceptable cost?*

---

## 5. Skills + MCP: Expertise and Connectivity

### 5.1 How Skills and MCP Work Together

Skills and MCP are complementary, not competing [2][4][7]:

- **MCP (Model Context Protocol)**: Universal connectivity layer. An MCP server built for Postgres works for any user, any company, any MCP-compliant AI client. "Write once, run everywhere" for data access. MCP servers also provide the standard interface for retrieval infrastructure (vector stores, knowledge graphs) and agent memory (see Section 6).
- **Skills**: Highly contextual procedural knowledge. A skill named "Write Blog Post" is specific to a user's voice, brand guidelines, and formatting rules. Skills teach the agent *how* to use MCP-provided data.

**Example**: An MCP server connects to a database. A skill teaches the agent your company's specific data validation rules, query patterns, and reporting format. The MCP provides the data; the skill provides the expertise.

### 5.2 Skills vs. Subagents — When to Use Each

From Anthropic's official guidance [4][11]:

- **Use Skills** when you need capabilities that any agent instance can load and use — like training materials that make the agent better at specific tasks across all conversations
- **Use Subagents** for task specialization requiring independent execution with specific tool restrictions — e.g., a code-reviewer subagent with read-only permissions

**Key distinction**: If multiple agents or conversations need the same expertise (security review procedures, data analysis methods), create a skill rather than building that knowledge into a subagent [11].

### 5.3 Progressive Disclosure Architecture

The three-level loading model is central to why skills scale [2]:

| Level | When Loaded | Token Cost | Content |
|-------|-------------|------------|---------|
| Level 1: Metadata | Always (at startup) | ~100 tokens per skill | Name and description from YAML frontmatter |
| Level 2: Instructions | When skill is triggered | Under 5K tokens | SKILL.md body with instructions and guidance |
| Level 3+: Resources | As needed | Effectively unlimited | Bundled files, scripts executed via bash |

This means you can install dozens of skills with near-zero context overhead until they're actually needed. Scripts execute without their code entering the context window — only output flows back.

Progressive disclosure is a direct implementation of the context engineering principle of "dynamic context selection" (Section 4.3) — loading only what's relevant at the moment it's needed.

---

## 6. Agent Memory and Retrieval Infrastructure

### 6.1 The Role of Retrieval in Agent Architecture

Retrieval infrastructure provides agents with access to knowledge that doesn't fit in (or shouldn't be loaded into) the context window. It is the data foundation layer that grounds agent outputs in accurate, traceable information. Without it, agents hallucinate. With it, agents can answer questions grounded in your actual data, cite their sources, and stay current as information changes.

As of 2026, Gartner projects that over 70% of enterprise generative AI initiatives will require structured retrieval pipelines to mitigate hallucination and compliance risk [40][41].

### 6.2 Agentic RAG: From Static Pipelines to Agent-Directed Retrieval

**Traditional RAG** (2023-2024) was a rigid pipeline: query → retrieve → generate. The search happened once, in one way, and the model got whatever came back.

**Agentic RAG** (2025-2026) embeds retrieval inside the agent's reasoning loop. Instead of a fixed pipeline, the agent decides *what* to fetch, *which tools* to call, *when to reflect*, and *how to verify answers* — looping until a grounded result is achieved [42][43][44].

**How agentic RAG works:**

1. **Query understanding** — Interpret intent and classify complexity
2. **Planning/routing** — Decide whether to retrieve, use tools, or answer directly
3. **Retrieval execution** — Search across one or more data sources
4. **Quality grading** — Evaluate whether retrieved documents are sufficient
5. **Query rewriting** — If results are poor, decompose or rephrase the query
6. **Citation and verification** — Ground the answer and provide provenance

**Three agent types in agentic RAG** [42][44]:

- **Routing agents**: Use LLM reasoning to select the most appropriate retrieval pipeline (e.g., summarization vs. QA) for a given query
- **One-shot query planning agents**: Decompose complex queries into subqueries, execute across different data sources, and combine results
- **ReAct agents**: Integrate reasoning and action for multi-part queries, maintaining in-memory state and iteratively invoking tools until fully resolved

**When pipeline RAG still wins** [42][43]: Single-hop questions (simple factual lookups), tight latency and cost budgets, and document-shaped corpora (manuals, FAQs, SOPs) where the answer is typically in a single coherent section.

**Production best practices for agentic RAG** [40][41][44]:

1. **Start with hybrid RAG, add agentic layers incrementally** — Agentic RAG is only necessary for complex, multi-step workflows. Most enterprise search use cases perform well with hybrid RAG.
2. **Hybrid retrieval + reranking as default** — Combine BM25 (keyword) with vector search; add cross-encoder reranking. This improved accuracy by 33-47% depending on query complexity.
3. **Intelligent query routing** — Saves 40% on costs by skipping unnecessary retrievals and reduces latency by 35%.
4. **Enforce document-level access control** — At query time, not just at ingestion. Users should only see what they're entitled to.
5. **Read + write capabilities** — Production RAG needs continuous data syncing, granular permissions mirroring source systems, and a secure action layer.
6. **Evaluation is non-negotiable** — Use BEIR metrics (nDCG, MRR, Recall@K) for retrieval and RAGAS for answer faithfulness and relevance.

### 6.3 Long Context Windows vs. RAG

Context windows have grown dramatically — Google Gemini 3 Pro now supports 10M tokens (~15,000 pages). This has fueled "RAG is dead" claims, but the data tells a more nuanced story [45][46][47].

**Where long context wins:**

- Small document sets (under 100 docs, under 100K tokens total)
- Static data that never updates
- Rapid prototyping (faster than building a retrieval pipeline)
- Cross-document reasoning where the model needs to see everything simultaneously

**Where RAG wins:**

- **Cost**: RAG averages ~$0.00008 per query vs. ~$0.10 for long context (1,250x cheaper) [45]
- **Accuracy at scale**: Models degrade at full context load — Gemini 3 Pro maintains only 77% accuracy at 1M tokens [45]
- **The "lost in the middle" problem**: Stanford research showed 30%+ performance degradation when relevant information sits in the middle of long contexts [45][46]
- **Dynamic data**: Incremental indexing beats reloading everything on every query
- **Multi-tenant access control**: RAG filters results by user permissions at query time
- **Auditability**: Traceable retrieval provenance for regulated industries [47]

**The hybrid approach (emerging best practice)**: Use lightweight retrieval to select relevant documents, then inject *complete documents* (not chunks) as full context. This avoids information loss from chunk boundaries while keeping input size manageable [45][46].

**Decision framework:**

| Factor | Favors RAG | Favors Long Context |
|--------|-----------|-------------------|
| Corpus size | > 1M tokens | < 100K tokens |
| Query volume | High (1000s/day) | Low (analytical) |
| Data freshness | Dynamic, frequently updated | Static or batch |
| Latency requirement | Real-time (< 2s) | Batch-tolerant (30-60s) |
| Budget | Cost-sensitive | Simplicity-sensitive |
| Compliance | Audit trail required | N/A |

### 6.4 Retrieval Infrastructure: Vector Databases, Knowledge Graphs, and Hybrid Search

**Vector databases** store mathematical representations (embeddings) of text and find semantically similar content. The 2026 landscape shows consolidation [48][49]:

- **PostgreSQL + pgvector** is absorbing vector capabilities for most workloads. OpenAI's ChatGPT and API run on PostgreSQL. Benefits: ACID compliance, familiar tooling, JOINs with relational data. Adequate for small-to-medium workloads (< 50M vectors).
- **Purpose-built vector DBs** remain dominant at scale: Pinecone (managed, zero-ops), Qdrant (cost-sensitive, self-hosted — 60-80% cheaper than Pinecone at equivalent scale), Weaviate (hybrid search), Milvus (billion-scale performance).

**Knowledge graphs** preserve explicit relationships between entities, enabling multi-hop reasoning that vector search cannot do [50][51]:

| Dimension | Vector RAG | Graph RAG |
|-----------|-----------|-----------|
| Data type | Unstructured text | Structured entities with explicit relationships |
| Retrieval | Similarity search | Graph traversal + relationship reasoning |
| Strength | Fast, scalable | Multi-hop reasoning, causal chains |
| Weakness | Doesn't understand relationships | Requires upfront effort to build the graph |
| Best for | "Find the vacation policy" | "What decisions led to this outcome?" |

Benchmark data: GraphRAG outperforms vector RAG by 3.4x on multi-entity queries. Vector RAG accuracy drops to near 0% as the number of entities per query exceeds 5, while GraphRAG sustains stable performance even with 10+ entities [50].

**Hybrid search as the production default**: Combine BM25 (keyword/lexical matching) with vector similarity search, then apply a cross-encoder reranker. This improved accuracy by 33-47% versus either method alone [40][41].

### 6.5 Embedding Models and Chunking

**Embedding models** convert text into mathematical vectors that encode meaning. The quality of embeddings determines everything downstream — a mediocre embedding model with a great database will underperform a great embedding model with a mediocre database [48][52][53].

Key guidance for embedding models:

- **Open-source models have caught up** to proprietary alternatives, especially when fine-tuned on domain-specific data (BGE-M3, NV-Embed-v2, E5-Mistral)
- **Fine-tuning is the biggest lever**: A smaller, fine-tuned model can outperform a larger general-purpose model on domain-specific tasks. Start with 1,000-5,000 high-quality training samples; plan for 10,000+ for complex specialized terminology
- **LoRA/adapter fine-tuning** lets you update a few million parameters instead of billions — fast and cheap, ideal for domain adaptation
- Pre-trained models are trained on general-purpose data (books, Wikipedia, web crawl) and often underperform on specialized domains (legal, medical, financial) without fine-tuning [52][53]

**Chunking** — splitting documents into smaller pieces for embedding and retrieval — is the most underestimated lever for RAG performance. Poor chunking is the #1 silent failure mode [54][55]:

| Strategy | How It Works | Best For |
|----------|-------------|----------|
| **Recursive** (start here) | Split at hierarchical boundaries (sections → paragraphs → sentences) | Best starting point for most teams |
| **Semantic** | Use embeddings to detect topic shifts | Complex documents with topic changes |
| **Hierarchical** | Multiple chunk layers (summary + detail) | Systems serving both high-level and specific queries |
| **Late chunking** | Embed full document first, then split | Preserving cross-chunk context |

2026 benchmarks: ClusterSemanticChunker achieved 92% retrieval accuracy vs. 78% for RecursiveCharacterTextSplitter. Hierarchical chunking improved retrieval quality by 18-25% across multiple datasets [54][55].

### 6.6 Agent Memory: Persistent State Across Sessions

Without persistent memory, agents don't remember past decisions, user preferences, or conversation context across sessions. Agent memory solves this by providing tools like `remember()` and `recall()` that agents invoke through MCP [56][57][58].

**Vector memory vs. graph memory:**

- **Vector memory**: Retrieves similar past exchanges but treats each memory independently. Good for "What did we discuss about X?"
- **Graph memory**: Preserves how information connects across time, enabling reasoning about relationships and tracking changes. Good for "What decisions led to this outcome?"

**Key memory solutions (2026):**

| Solution | Approach | Key Feature |
|----------|----------|-------------|
| **MCP Memory Service** | BM25 + vector similarity | 5ms speed, 13+ AI app support |
| **Mem0** | Vector + optional graph layer | Dual self-host/managed deployment |
| **Zep** | Temporal knowledge graph | Temporal invalidation of old facts |
| **Graphiti + FalkorDB** | Persistent knowledge graphs | Multi-tenancy, low-latency retrieval |

**Recommended implementation path** [57][58]:

1. Start with stateless RAG using a vector store and a search tool
2. Once retrieval is reliable, add episodic memory tools (`remember()` and `recall()`)
3. Extend to structured memory (user profiles, task state)
4. Layer in fallback handling and tool chaining logic
5. Secure, log, and monitor all memory interactions

### 6.7 RAG Evaluation

RAGAS is the open-source standard for evaluating RAG pipelines [59][60]:

| Metric | What It Measures |
|--------|-----------------|
| **Context Precision** | Are the retrieved documents relevant? |
| **Context Recall** | Did we find all the relevant documents? |
| **Faithfulness** | Is the answer supported by retrieved context? (Low = hallucination) |
| **Answer Relevancy** | Does the answer address the user's question? |

Best practices: Use golden datasets (frozen for each evaluation cycle), add at least one custom metric tailored to your use case, and integrate evaluation into production monitoring from day one. Leading platforms include Langfuse + RAGAS, Datadog + RAGAS, and Arize Phoenix [59][60].

---

# Part III: Agent Design Patterns

---

## 7. State Machines and Structured State Management

### 7.1 State Machines as Agent Architecture

A growing body of research — including the StateFlow framework and MetaAgent (accepted at ICML 2025) — formalizes modeling agent workflows as finite state machines. Each state represents a phase of work, and transitions happen when specific conditions are met [20][21].

LangGraph is the most production-ready implementation. It models agents as graph-based state machines where each node is a reasoning or tool-use step, edges define data flow, and conditional edges allow dynamic routing based on current state. A centralized state object flows through every node, getting updated as it goes [20].

**Key LangGraph concepts:**

- **State Schema**: Defined upfront as a TypedDict or Pydantic model — forms the contract for what data flows through the workflow
- **Reducer Logic**: When a node emits an update, LangGraph merges it using reducer logic (append vs. replace) rather than overwriting
- **Super-Steps**: Batches of concurrent node executions — after each step, reducers merge updates and state is checkpointed
- **Persistence**: State can be stored in external storage (SQLite, Redis, Postgres), enabling workflows to pause and resume — even across different computing environments
- **Agent Communication via State**: Instead of direct peer-to-peer messaging, agents communicate through the centralized state object. Each agent processes the current state as input and returns an updated version

**Production best practices for LangGraph state** [20]:

- Define a clear state schema upfront
- Use reducers intentionally (append vs. replace)
- Keep state lightweight and serializable
- Apply state versioning for schema changes
- Ensure idempotency for retries
- Use persistent checkpointers (Postgres/Redis) in production, not in-memory
- Enable monitoring for debugging and observability

### 7.2 To-Do Lists as Structured Agent State

Research and production implementations demonstrate using structured to-do lists as a first-class state object within the agent loop. Coding agents like Claude Code, Codex, and Cline use this pattern with tools like `write_todos` [21].

**What the to-do list solves:**

- **Planning visibility**: Users can see what the agent intends to do before it does it
- **Context persistence**: In long sessions, the structured plan persists even when detailed reasoning is pushed out of the context window
- **Progress tracking**: For autonomous workflows, the to-do list gives the orchestrator a concrete artifact to check — which steps are done, in progress, or pending
- **Failure recovery**: A persisted to-do list with status markers lets the next session pick up where the previous one left off without re-deriving the plan

### 7.3 Subagent Spawning: Programmatic vs. Agent-Directed

Research confirms three approaches to subagent spawning [22][23][24]:

**Approach 1: Programmatic / developer-defined.** You pre-define subagent configurations (tools, model, permissions) and the infrastructure decides when to invoke them based on triggers (cron, events). Most predictable, easiest to monitor.

**Approach 2: Agent-directed.** The main agent autonomously decides when to spawn subagents based on task analysis and subagent descriptions. More flexible, but less predictable.

**Approach 3: Hybrid (emerging best practice).** Developers pre-define available subagent configurations. The infrastructure handles *when to trigger the workflow* (cron, event, user request). The agent handles *how to execute it* (which subagents to spawn, in what order, whether to parallelize). This separates scheduling from execution strategy [22][23].

**Key constraints** [22][24]:

- Subagents cannot spawn their own subagents (prevents infinite nesting)
- Subagents are synchronous — the main agent waits for results before continuing
- Subagents start with clean context windows — they don't inherit the main agent's conversation history
- Model selection for subagents is currently static in most frameworks (active area of feature requests)

---

## 8. Orchestration Patterns

### 8.1 The Three Orchestration Approaches

The core distinction in modern agent orchestration is between programmatic control (developer defines the flow), LLM-directed orchestration (the LLM decides what to do next), and managed platforms (infrastructure-level deployment and scaling) [25][26][27].

**Programmatic / Graph-Based (e.g., LangGraph):**
LangGraph models workflows as directed acyclic graphs (DAGs) where nodes represent reasoning or tool-use steps, edges define flow, and conditional edges allow branching. Tool usage follows the predefined graph structure — the LLM only intervenes at ambiguous decision points. This minimizes LLM invocations, reduces token usage, and simplifies debugging [25][26].

**LLM-Directed / Role-Based (e.g., CrewAI):**
CrewAI models crews of specialized agents with roles, tasks, and collaboration protocols. Agents deliberate autonomously before each tool call, passing full prior-agent context forward. This preserves maximum context but introduces deliberation latency (~5 seconds per decision) and higher token consumption [25][26].

**Managed Deployment Platforms (e.g., Amazon Bedrock AgentCore):**
AgentCore provides the infrastructure layer — VM-level session isolation, managed memory, secure MCP tool integration, and monitoring via CloudWatch/OpenTelemetry. It is framework-agnostic and model-agnostic. CloudZero reported 5x faster response times after migrating to AgentCore [27].

### 8.2 Performance Comparison

LangGraph executes fastest with the most efficient state management. CrewAI experiences the longest delays due to autonomous deliberation before tool calls. LangChain consumes more tokens due to heavier memory handling. AutoGen performs moderately with consistent coordination behavior [25].

Key finding: LangGraph passes only necessary state deltas between nodes rather than full conversation histories, resulting in minimal token usage and reduced latency [25].

### 8.3 Durable Execution: Temporal

For long-running agent workflows (multi-step builds, multi-day processes), durable execution is becoming foundational [28].

Temporal wraps agent interactions — LLM calls, tool executions, API requests — as discrete workflow steps with deterministic replay. If a process crashes mid-execution, Temporal automatically restores the agent's exact state from its event history log, eliminating the need for complete restarts [28].

Temporal raised $300M at a $5B valuation in early 2026, with customers including OpenAI, Netflix, and JPMorgan Chase. Competitors include Inngest (event-driven durable workflows) and Restate (lightweight workflows-as-code) [28].

### 8.4 The Layered Production Stack

The 2026 production AI stack increasingly consists of complementary layers, not a single winner [26][27][28]:

| Layer | Purpose | Examples |
|-------|---------|----------|
| Orchestration framework | Agent logic, workflow design | LangGraph, CrewAI, OpenAI Agents SDK |
| Durable execution | Fault tolerance, crash recovery, state replay | Temporal, Inngest, Restate |
| Managed infrastructure | Deployment, scaling, monitoring, security | Amazon Bedrock AgentCore |
| Tool integration | Standardized external connectivity | MCP |
| Retrieval & memory | Data grounding and persistent state | Vector DBs, knowledge graphs, MCP memory |
| Job queuing | Background task distribution, scheduling | BullMQ, Celery |

**Decision guidance** [25][26]:

- For custom orchestration with explicit state control → LangGraph, GenServ AI
- For role-based multi-agent collaboration → CrewAI
- For rapid prototyping on OpenAI stack → OpenAI Agents SDK
- For managed deployment with enterprise governance → AgentCore
- For workflows that must survive failures and run for extended periods → Temporal
- For scheduled background tasks and event-driven triggers → BullMQ or equivalent job queue

---

# Part IV: Infrastructure and Operations

---

## 9. Model Routing Layer

### 9.1 Why Model Routing Matters

IDC recognizes model routing as a key architectural trend: the future of AI is model routing — one model no longer fits all, and production systems need to navigate multiple providers, model versions, and parameter configurations without hard-coding these choices into application code [29][30].

OpenRouter's large-scale data (100T+ tokens routed) confirms a foundational shift from single-turn text completion toward multi-step, tool-integrated, and reasoning-intensive workflows. The share of tokens routed through reasoning-optimized models has risen steadily since early 2025 [30].

### 9.2 LLM Gateways: The Abstraction Layer

LLM gateways sit between your application and multiple LLM providers, acting as a lightweight abstraction layer. Instead of calling OpenAI, Anthropic, or other APIs directly, requests go through the gateway, which forwards them to the selected provider using a consistent API format [29][31].

**Key capabilities of production LLM gateways:**

- **Unified API format**: Write your application once, swap LLMs behind the scenes
- **Routing strategies**: Latency-based, cost-based, usage-based routing with customizable algorithms
- **Fallback and reliability**: Automatic failover if a provider's API is down, cooldowns for failed deployments
- **Cost management**: Team-based budget controls, virtual keys, spend tracking
- **Observability**: Integration with Prometheus, OpenTelemetry, Langfuse, Datadog for LLM-specific metrics

**Leading solutions (2026):**

- **LiteLLM**: Open-source, 33,000+ GitHub stars, supports 100+ LLMs via OpenAI-compatible API. Available as Python SDK or proxy server. YAML-based configuration for declarative routing policies. AWS has published a reference architecture using LiteLLM. Known limitation: introduces measurable latency as a proxy, which can be a bottleneck for real-time applications [29][31].
- **OpenRouter**: Specializes in cross-provider parameter normalization, particularly for reasoning tokens. Normalizes extended thinking/reasoning parameters across providers into a unified `reasoning` config object [30].
- **Bifrost, Helicone, Kong AI Gateway, Cloudflare AI Gateway**: Commercial alternatives with varying strengths in enterprise governance, analytics, and edge deployment [29].

### 9.3 Cross-Provider Parameter Normalization

A critical challenge in multi-provider architectures is that equivalent features have different API structures across providers [30]:

- **OpenAI**: "reasoning_effort" parameter (low/medium/high) for o-series models
- **Anthropic**: "extended_thinking" with budget_tokens for Claude models
- **Alibaba/Qwen**: "thinking_budget" for Qwen reasoning models

OpenRouter normalizes these into a unified `reasoning` config object, so switching between providers requires no code changes. LiteLLM achieves similar normalization through its OpenAI-compatible API format [30][31].

**Best practices for reasoning token management** [30]:

- Use a unified reasoning parameter via the routing layer rather than provider-specific parameters
- Preserve reasoning blocks during tool-calling workflows to maintain thinking chain continuity
- Control reasoning budget explicitly to manage cost vs. depth tradeoffs
- Guard against overthinking — extended reasoning doesn't always improve solutions; monitor token output length
- Design for model switching from the start — abstract provider-specific details behind logical roles

### 9.4 Architecture Pattern: Logical Roles → Concrete Configuration

The recommended pattern for production systems:

1. **Define logical model roles** in your application: "big-reasoning", "mid-generation", "fast-classification", "audit-model"
2. **Map each role to a concrete configuration** in a central YAML/config file: provider, model ID, parameters (temperature, max_tokens, reasoning effort), fallback chain
3. **Application code references only the logical role** — never a specific model or provider
4. **The routing layer resolves** the logical role to the actual API call with the right parameters

This enables A/B testing models, automatic fallback, gradual migration to new model versions, and cross-provider audit (using a different provider for execution vs. security review) without touching application code.

---

## 10. Security

### 10.1 Skills Attack Surface

Research from October 2025 through February 2026 identified that Agent Skills enable a novel attack surface [2][13]:

- Skills combine natural-language instructions with executable code in a format agents trust implicitly
- Malicious instructions can be embedded within long SKILL.md files
- Once loaded, a skill's instructions are treated as authoritative context
- System-level guardrails can potentially be bypassed

**Mitigation**: Only use skills from trusted sources (self-created or from Anthropic). Audit all bundled files. Treat skill installation like software installation. Establish skill registries and policy engines for governance [2][7].

### 10.2 Subagent Security

The Claude Agent SDK enforces several security patterns [12]:

- Subagents cannot spawn their own subagents (prevents infinite nesting)
- Tool access should follow deny-all default with allowlisting per subagent
- Pre-tool hooks can intercept risky actions
- Every tool invocation should be logged with inputs, outputs, timestamps, and calling agent

### 10.3 Retrieval and Memory Security

Retrieval and memory infrastructure introduces additional security considerations:

- **Document-level access control**: Enforce at query time so users see only what they're entitled to — avoid "one big bucket" indices [40][41]
- **Memory poisoning**: Persistent agent memory can be corrupted by adversarial inputs; validate and sanitize all memory writes
- **Data freshness and provenance**: Track the source and timestamp of all retrieved data; stale or unattributed data in regulated industries creates compliance risk
- **Tenant isolation**: In multi-tenant systems, enforce strict isolation in vector stores and knowledge graphs to prevent cross-tenant data leakage

---

## 11. Production Deployment Lessons

### 11.1 Amazon's Evaluation Framework

Amazon's experience with thousands of agents established that evaluation must be holistic [5]: quality (reasoning coherence, tool selection accuracy, task completion), performance (latency, throughput, resource utilization), responsibility (safety, bias, hallucination detection), and cost (token economics at scale).

### 11.2 Cost-Performance Trade-offs

Production systems increasingly use heterogeneous model routing [5][6]:

- **Expensive frontier models** (Opus) for complex reasoning and orchestration
- **Mid-tier models** (Sonnet) for standard tasks and subagent work
- **Small/fast models** (Haiku) for high-frequency execution, classification, and routing

This aligns with the common design pattern of a model routing layer (Section 9) — using frontier models for reasoning and mid-tier models for execution.

### 11.3 The 45% Rule

Research establishes an empirical threshold: once single-agent accuracy exceeds approximately 45% on a task, adding more agents typically yields diminishing returns [5]. In parallel setups without communication, errors are actually amplified.

### 11.4 Observability is Non-Negotiable

Every production agent system that failed at scale had insufficient observability [5]. You need to see every tool call, every handoff, every LLM invocation, and the full state at each step. OpenTelemetry traces with correlation IDs across subagents is the emerging standard [12].

### 11.5 "Use LLMs Only Where Needed"

The agents that reach production fastest use LLM reasoning for genuinely ambiguous decisions and deterministic code for everything else [6]. Input validation, output formatting, API call construction, error handling — these don't benefit from LLM flexibility and actively suffer from LLM non-determinism.

Most common production architecture: deterministic routing decides which agent handles a request → agent uses LLM reasoning for its core task → deterministic post-processing validates and formats the output [6].

---

# Part V: Ecosystem

---

## 12. Skill Marketplaces and Distribution

### 12.1 The Emerging Skill Marketplace Landscape

The Agent Skills open standard (Section 5) has catalyzed rapid growth in skill distribution infrastructure. As of February 2026, multiple marketplaces and registries serve different parts of the ecosystem [32][33][34]:

**Community-driven skill marketplaces:**
- **SkillsMP** (skillsmp.com): 60,000+ indexed agent skills compatible with Claude Code, Codex CLI, and ChatGPT. Skills organized by SDLC phase. The first major marketplace to reach meaningful scale.
- **SkillHub** (skillhub.club): 7,000+ AI-evaluated skills for Claude, Gemini, and OpenCode. Focuses on curated recommendations.
- **Anthropic's public skills repo** (github.com/anthropics/skills): Official repository maintained by Anthropic.

**MCP server registries:**
- **Official MCP Registry** (registry.modelcontextprotocol.io): The authoritative source for publicly-available MCP servers, maintained by the MCP project.
- **Smithery.ai**: 2,000+ MCP servers with centralized hosting, authentication (OAuth), and standardized interfaces. Acts as both registry and hosting platform.
- **Composio** (mcp.composio.dev): 300+ app integrations with MCP servers, including Gmail, GitHub, Google Calendar, Notion, and Slack. Note: migrating to updated MCP implementation.

**Platform-level marketplaces:**
- **Cursor Plugin Marketplace** (launched February 2026): Official marketplace with launch partners including Amplitude, AWS, Figma, Linear, Stripe, and Vercel.
- **Anthropic Cowork Plugin Marketplace**: 11 open-source plugins for enterprise functions.
- **Microsoft Magentic Marketplace**: Agent marketplace as part of Microsoft's broader agent infrastructure.

### 12.2 Security: The ClawHavoc Incident

In January 2026, the "ClawHavoc" incident demonstrated the risks of unvetted community skills. 341 malicious skills were distributed through community-driven marketplaces, compromising approximately 9,000 installations [35]. This affected all community-driven AI plugin ecosystems and underscored that marketplace presence does not equal security vetting.

**Implications for any system consuming marketplace skills:**
- Community-curated ≠ security-audited
- Any skill sourced from a marketplace must pass through your own audit pipeline before deployment
- The security measures outlined in Section 10 apply regardless of skill source
- Pre-vetted marketplace tiers are emerging but not yet mature enough for blind trust

### 12.3 Integration Strategy

For any system that incorporates agent skills, the recommended approach is a tiered skill sourcing model:

1. **First-party skills** (highest trust): Built and maintained in-house, full internal security review. These cover common integration needs and core functionality.
2. **Marketplace-sourced skills** (moderate trust): Pulled from established registries (Smithery, official MCP registry, SkillsMP). Must pass automated audit gate (static analysis, sandboxed testing) before deployment to any production environment.
3. **User-uploaded skills** (lowest initial trust): Custom skills provided by end users. Full security pipeline applies, starting with restricted capability set.

The key principle: marketplace integration reduces the volume of skills you need to build from scratch, but does NOT eliminate the need for independent auditing. You own the trust boundary, not the marketplace.

---

# Appendix

---

## Citations

### Part I: Strategic Overview

[1] OpenAI. "A Practical Guide to Building Agents." January 2025. https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/

[2] Anthropic (Barry Zhang, Keith Lazuka, Mahesh Murag). "Equipping Agents for the Real World with Agent Skills." October 2025. https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills

[3] Anthropic. "How We Built Our Multi-Agent Research System." June 2025. https://www.anthropic.com/engineering/multi-agent-research-system

[4] Anthropic. "Agent Skills Overview — Claude API Docs." 2025. https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview

[5] AWS. "Evaluating AI Agents: Real-World Lessons from Building Agentic Systems at Amazon." 2025. https://aws.amazon.com/blogs/machine-learning/evaluating-ai-agents-real-world-lessons-from-building-agentic-systems-at-amazon/

[6] Zircon Tech. "Agentic Frameworks in 2026: What Actually Works in Production." 2026. https://zircon.tech/blog/agentic-frameworks-in-2026-what-actually-works-in-production/

[7] Various sources on Agent Skills open standard adoption (December 2025):
- Unite.AI: https://www.unite.ai/anthropic-opens-agent-skills-standard-continuing-its-pattern-of-building-industry-infrastructure/
- VentureBeat: https://venturebeat.com/ai/anthropic-launches-enterprise-agent-skills-and-opens-the-standard
- SiliconANGLE: https://siliconangle.com/2025/12/18/anthropic-makes-agent-skills-open-standard/
- ByteIota: https://byteiota.com/agent-skills-standard-microsoft-openai-adopt-in-48-hours/

[8] LangChain. "Choosing the Right Multi-Agent Architecture." January 2025. https://blog.langchain.com/choosing-the-right-multi-agent-architecture/

[9] LangChain. "Benchmarking Multi-Agent Architectures." June 2025. https://blog.langchain.com/benchmarking-multi-agent-architectures/

[10] Neomanex. "Multi-Agent AI Systems: The Complete Enterprise Guide for 2026." 2026. https://neomanex.com/posts/multi-agent-ai-systems-orchestration

[11] Anthropic. "Skills Explained: How Skills Compares to Prompts, Projects, MCP, and Subagents." 2025. https://claude.com/blog/skills-explained

[12] Various sources on Claude Agent SDK best practices:
- Anthropic: https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk
- Anthropic SDK Docs: https://platform.claude.com/docs/en/agent-sdk/overview
- Claude Code Docs: https://code.claude.com/docs/en/sub-agents

[13] Arxiv. "Agent Skills for Large Language Models: Architecture, Acquisition, Security, and the Path Forward." February 2026. https://arxiv.org/html/2602.12430

### Part II: Foundational Layers — General

[14] Subramanya N. "Agent Skills: The Missing Piece of the Enterprise AI Puzzle." December 2025. https://subramanya.ai/2025/12/18/agent-skills-the-missing-piece-of-the-enterprise-ai-puzzle/

[15] CometAPI. "Claude Skills vs MCP: The 2026 Guide to Agentic Architecture." 2026. https://www.cometapi.com/claude-skills-vs-mcp-the-2026-guide-to-agentic-architecture/

[16] Google Cloud. "Lessons from 2025 on Agents and Trust." 2025. https://cloud.google.com/transform/ai-grew-up-and-got-a-job-lessons-from-2025-on-agents-and-trust

[17] LangChain. "How and When to Build Multi-Agent Systems." June 2025. https://blog.langchain.com/how-and-when-to-build-multi-agent-systems/

[18] O'Reilly. "Designing Effective Multi-Agent Architectures." 2025. https://www.oreilly.com/radar/designing-effective-multi-agent-architectures/

[19] Speakeasy. "A Practical Guide to the Architectures of Agentic Applications." 2025. https://www.speakeasy.com/mcp/using-mcp/ai-agents/architecture-patterns

### Part III: Agent Design Patterns

[20] Various sources on LangGraph state management:
- LangChain. "LangGraph: Agent Orchestration Framework." https://www.langchain.com/langgraph
- Latenode. "LangGraph AI Framework 2025: Complete Architecture Guide." https://latenode.com/blog/ai-frameworks-technical-infrastructure/langgraph-multi-agent-orchestration/langgraph-ai-framework-2025-complete-architecture-guide-multi-agent-orchestration-analysis
- Bharatsinh Raj. "LangGraph State Management — Part 1." Medium, 2025. https://medium.com/@bharatraj1918/langgraph-state-management-part-1-how-langgraph-manages-state-for-multi-agent-workflows-da64d352c43b

[21] Various sources on to-do lists and structured state in agents:
- LangChain. "Deep Agents." GitHub. https://github.com/langchain-ai/deepagents
- Block/Goose. "Agents, Subagents, and Multi Agents: When to Use Them." August 2025. https://block.github.io/goose/blog/2025/08/14/agent-coordination-patterns/

[22] Colin McNamara. "Understanding Skills, Agents, Subagents, and MCP in Claude Code: When to Use What." 2025. https://colinmcnamara.com/blog/understanding-skills-agents-and-mcp-in-claude-code

[23] Eesel AI. "Subagent Orchestration: The Complete 2025 Guide for AI Workflows." 2025. https://www.eesel.ai/blog/subagent-orchestration

[24] Various sources on subagent spawning patterns:
- Claude Code Docs. "Create Custom Subagents." https://code.claude.com/docs/en/sub-agents
- Claude API Docs. "Subagents in the SDK." https://platform.claude.com/docs/en/agent-sdk/subagents
- VS Code. "Subagents in Visual Studio Code." https://code.visualstudio.com/docs/copilot/agents/subagents

### Part III: Orchestration Patterns

[25] Various sources on orchestration framework comparison:
- AIMultiple. "Top 10+ Agentic Orchestration Frameworks & Tools in 2026." https://aimultiple.com/agentic-orchestration
- n8n Blog. "AI Agent Orchestration Frameworks: Which One Works Best?" https://blog.n8n.io/ai-agent-orchestration-frameworks/
- Langfuse. "Comparing Open-Source AI Agent Frameworks." 2025. https://langfuse.com/blog/2025-03-19-ai-agent-comparison
- Turing. "A Detailed Comparison of Top 6 AI Agent Frameworks in 2026." https://www.turing.com/resources/ai-agent-frameworks

[26] Zircon Tech. "Agentic Frameworks in 2026: What Actually Works in Production." 2026. https://zircon.tech/blog/agentic-frameworks-in-2026-what-actually-works-in-production/

[27] Various sources on Amazon Bedrock AgentCore:
- AWS. "Amazon Bedrock AgentCore." https://aws.amazon.com/bedrock/agentcore/
- AWS Blog. "Build and Deploy Scalable AI Agents with AgentCore." https://aws.amazon.com/blogs/machine-learning/build-and-deploy-scalable-ai-agents-with-nvidia-nemo-amazon-bedrock-agentcore-and-strands-agents/
- MyTechMantra. "Scaling Multi-Agent Systems: Amazon Bedrock AgentCore 2026 Guide." https://www.mytechmantra.com/sql-server/scaling-multi-agent-systems-amazon-bedrock-agentcore/

[28] Various sources on Temporal and durable execution:
- InfoQ. "Temporal and OpenAI Launch AI Agent Durability." September 2025. https://www.infoq.com/news/2025/09/temporal-aiagent/
- VentureBurn. "Temporal Raises $300 Million To Scale Durable Execution For AI Systems." 2026. https://ventureburn.com/temporal-raises-300m/
- ActiveWizards. "Indestructible AI Agents: A Guide to Using Temporal." https://activewizards.com/blog/indestructible-ai-agents-a-guide-to-using-temporal
- Kinde. "Orchestrating Multi-Step Agents: Temporal/Dagster/LangGraph Patterns." https://www.kinde.com/learn/ai-for-software-engineering/ai-devops/orchestrating-multi-step-agents-temporal-dagster-langgraph-patterns-for-long-running-work/
- IntuitionLabs. "Agentic AI Workflows: Why Orchestration with Temporal is Key." https://intuitionlabs.ai/articles/agentic-ai-temporal-orchestration

### Part IV: Infrastructure and Operations

[29] Various sources on LLM gateways and model routing:
- GetMaxim. "Top 5 LLM Gateways in 2025: The Definitive Guide." https://www.getmaxim.ai/articles/top-5-llm-gateways-in-2025-the-definitive-guide-for-production-ai-applications/
- GetMaxim. "Top 5 LLM Gateways for 2026." https://www.getmaxim.ai/articles/top-5-llm-gateways-for-2026-a-comprehensive-comparison/
- Helicone. "Top 5 LLM Gateways Comparison 2025." https://www.helicone.ai/blog/top-llm-gateways-comparison-2025
- Kamya Shah. "The Complete Guide to LLM Routing." Medium, February 2026. https://medium.com/@kamyashah2018/the-complete-guide-to-llm-routing-5-ai-gateways-transforming-production-ai-infrastructure-b5c68ee6d641

[30] Various sources on OpenRouter and cross-provider reasoning normalization:
- OpenRouter. "Reasoning Tokens." https://openrouter.ai/docs/guides/best-practices/reasoning-tokens
- OpenRouter. "State of AI 2025: 100T Token Usage Study." https://openrouter.ai/state-of-ai
- IDC. "The Future of AI is Model Routing." https://www.idc.com/resource-center/blog/the-future-of-ai-is-model-routing/

[31] Various sources on LiteLLM:
- LiteLLM. https://www.litellm.ai/
- Infralovers. "LiteLLM: Flexible and Secure LLM Access for Organizations." Medium. https://medium.com/@infralovers/litellm-flexible-and-secure-llm-access-for-organizations-4dd19720f04b
- AWS. "Streamline AI Operations with Multi-Provider Generative AI Gateway Reference Architecture." https://aws.amazon.com/blogs/machine-learning/streamline-ai-operations-with-the-multi-provider-generative-ai-gateway-reference-architecture/
- TrueFoundry. "Top 5 LiteLLM Alternatives in 2026." https://www.truefoundry.com/blog/litellm-alternatives

### Part V: Ecosystem

[32] Various sources on agent skill marketplaces:
- SkillsMP. https://skillsmp.com
- Medium (Mark Chen). "Claude Code Has a Skills Marketplace Now." January 2026. https://medium.com/@markchen69/claude-code-has-a-skills-marketplace-now-a-beginner-friendly-walkthrough-8adeb67cdc89
- Medium (The Context Layer). "The First Real Marketplace for Agent Skills Is Already Live." December 2025. https://medium.com/the-context-layer/the-first-real-marketplace-for-agent-skills-is-already-live-aa2265bf8769

[33] Various sources on MCP registries and directories:
- Official MCP Registry. https://registry.modelcontextprotocol.io/
- GitHub. "modelcontextprotocol/registry." https://github.com/modelcontextprotocol/registry
- Smithery.ai. https://smithery.ai/
- WorkOS Blog. "Smithery AI: A central hub for MCP servers." https://workos.com/blog/smithery-ai
- Medium (DemoHub). "17+ Top MCP Registries, Directories & Marketplaces." 2025. https://medium.com/demohub-tutorials/17-top-mcp-registries-and-directories-explore-the-best-sources-for-server-discovery-integration-0f748c72c34a

[34] Various sources on platform-level marketplaces:
- Microsoft. "Magentic Marketplace for AI Agents." The New Stack, 2026. https://thenewstack.io/microsoft-launches-magentic-marketplace-for-ai-agents/
- Anthropic. "Agent Skills Open Standard." The New Stack. https://thenewstack.io/agent-skills-anthropic-next-bid-to-define-ai-standards/
- GitHub. "anthropics/skills." https://github.com/anthropics/skills

[35] Digital Applied. "AI Agent Plugin Security: Lessons from ClawHavoc 2026." 2026. https://www.digitalapplied.com/blog/ai-agent-plugin-security-lessons-clawhavoc-2026

### Part II: Context Engineering

[36] Towards AI. "Context Engineering: The 6 Techniques That Actually Matter in 2026." 2026. https://towardsai.net/p/machine-learning/context-engineering-the-6-techniques-that-actually-matter-in-2026-a-comprehensive-guide

[37] Elastic Search Labs. "Context Engineering vs. Prompt Engineering." 2026. https://www.elastic.co/search-labs/blog/context-engineering-vs-prompt-engineering

[38] Neo4j. "Why AI Teams Are Moving From Prompt Engineering to Context Engineering." 2026. https://neo4j.com/blog/agentic-ai/context-engineering-vs-prompt-engineering/

[39] The New Stack. "RAG Isn't Dead, But Context Engineering Is the New Hotness." 2026. https://thenewstack.io/rag-isnt-dead-but-context-engineering-is-the-new-hotness/

### Part II: Agent Memory and Retrieval Infrastructure

[40] Techment. "10 RAG Architectures in 2026: Enterprise Use Cases & Strategy." 2026. https://www.techment.com/blogs/rag-architectures-enterprise-use-cases-2026/

[41] Data Nucleus. "Agentic RAG in 2026: The UK/EU Enterprise Guide to Grounded GenAI." 2026. https://datanucleus.dev/rag-and-agentic-ai/agentic-rag-enterprise-guide-2026

[42] arXiv. "Agentic Retrieval-Augmented Generation: A Survey on Agentic RAG." January 2025. https://arxiv.org/abs/2501.09136

[43] Rod Johnson. "Rethinking RAG: Pipelines Are the Past, Agentic Is the Future." Medium, January 2026. https://medium.com/@springrod/rethinking-rag-pipelines-are-the-past-agentic-is-the-future-77c887414621

[44] Adaline Labs. "Building Production-Ready Agentic RAG Systems." 2026. https://labs.adaline.ai/p/building-production-ready-agentic

[45] SitePoint. "Long Context vs RAG: When 1M Token Windows Replace RAG." 2026. https://www.sitepoint.com/long-context-vs-rag-1m-token-windows/

[46] Jason Willems. "Long Context Windows: Capabilities, Costs, and Tradeoffs." January 2026. https://www.jasonwillems.com/technology/2026/01/26/Long-Context-Windows/

[47] Redis. "RAG vs Large Context Window: Real Trade-offs for AI Apps." 2026. https://redis.io/blog/rag-vs-large-context-window-ai-apps/

[48] Firecrawl. "Best Vector Databases in 2026: A Complete Comparison Guide." 2026. https://www.firecrawl.dev/blog/best-vector-databases

[49] Instaclustr. "pgvector: Key Features, Tutorial, and Pros and Cons [2026 Guide]." 2026. https://www.instaclustr.com/education/vector-database/pgvector-key-features-tutorial-and-pros-and-cons-2026-guide/

[50] Neo4j. "Knowledge Graph vs. Vector RAG: Benchmarking, Optimization Levers, and a Financial Analysis Example." 2026. https://neo4j.com/blog/developer/knowledge-graph-vs-vector-rag/

[51] Meilisearch. "GraphRAG vs. Vector RAG: Side-by-side Comparison Guide." 2026. https://www.meilisearch.com/blog/graph-rag-vs-vector-rag

[52] Supermemory. "Best Open-Source Embedding Models Benchmarked and Ranked." 2026. https://supermemory.ai/blog/best-open-source-embedding-models-benchmarked-and-ranked/

[53] Weaviate. "Why, When and How to Fine-Tune a Custom Embedding Model." 2026. https://weaviate.io/blog/fine-tune-embedding-model

[54] DasRoot. "Chunking Strategies: The Hidden Lever in RAG Performance." February 2026. https://dasroot.net/posts/2026/02/chunking-strategies-rag-performance/

[55] Weaviate. "Chunking Strategies to Improve LLM RAG Pipeline Performance." 2026. https://weaviate.io/blog/chunking-strategies-for-rag

[56] GitHub (Shichun-Liu). "Agent-Memory-Paper-List: Memory in the Age of AI Agents: A Survey." 2026. https://github.com/Shichun-Liu/Agent-Memory-Paper-List

[57] Mem0. "Graph Memory for AI Agents." January 2026. https://mem0.ai/blog/graph-memory-solutions-ai-agents

[58] Knit. "Powering RAG and Agent Memory with MCP." 2026. https://www.getknit.dev/blog/powering-rag-and-agent-memory-with-mcp

[59] GetMaxim. "Top 5 Platforms to Evaluate and Observe RAG Applications in 2026." 2026. https://www.getmaxim.ai/articles/top-5-platforms-to-evaluate-and-observe-rag-applications-in-2026/

[60] Label Your Data. "RAG Evaluation: 2026 Metrics and Benchmarks for Enterprise AI Systems." 2026. https://labelyourdata.com/articles/llm-fine-tuning/rag-evaluation
