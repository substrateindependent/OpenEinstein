# OpenEinstein: Implementation Plan
## An Open-Source AI Physicist Agent Platform

**Version:** 3.0 — March 2026
**Purpose:** A detailed, sequentially-ordered implementation plan for building OpenEinstein — an open-source, model-agnostic, domain-agnostic AI research platform that any physicist can download and use with their own LLM API keys and computational tools to conduct systematic theoretical physics research.

**Design constraint:** This plan is written to be handed to an AI coding agent (Claude Code, Codex, or similar) for autonomous execution. Tasks are ordered by dependency, not calendar duration. Each task includes acceptance criteria that an AI agent can verify.

---

## Table of Contents

1. [Vision and Design Philosophy](#1-vision-and-design-philosophy)
2. [Architecture Overview](#2-architecture-overview)
3. [Agent Framework and Model Routing](#3-agent-framework-and-model-routing)
4. [Multi-Agent Architecture](#4-multi-agent-architecture)
5. [Gateway Control Plane](#5-gateway-control-plane)
6. [Hooks and Extension System](#6-hooks-and-extension-system)
7. [MCP Integration Layer](#7-mcp-integration-layer)
8. [Computer Algebra System Integration](#8-computer-algebra-system-integration)
9. [Numerical Compute Workbench](#9-numerical-compute-workbench)
10. [Literature, Citations, and Knowledge Infrastructure](#10-literature-citations-and-knowledge-infrastructure)
11. [LaTeX Publishing Toolchain](#11-latex-publishing-toolchain)
12. [Campaign Engine and State Management](#12-campaign-engine-and-state-management)
13. [Campaign Packs: The Extension Mechanism](#13-campaign-packs-the-extension-mechanism)
14. [Personality and Persona System](#14-personality-and-persona-system)
15. [Observability: Tracing and Evals](#15-observability-tracing-and-evals)
16. [Long-Running Agent Infrastructure](#16-long-running-agent-infrastructure)
17. [AI Coding Best Practices Integration](#17-ai-coding-best-practices-integration)
18. [Security and Safety Model](#18-security-and-safety-model)
19. [Sequential Build Order](#19-sequential-build-order)
20. [Example Campaign Packs](#20-example-campaign-packs)
21. [Risk Assessment](#21-risk-assessment)
22. [Cost Estimates](#22-cost-estimates)
23. [Success Criteria](#23-success-criteria)
24. [PM Decision Register](#24-pm-decision-register)

---

## 1. Vision and Design Philosophy

### 1.1 What OpenEinstein Is

OpenEinstein is an open-source AI research platform for theoretical physics. It is analogous to what OpenClaw is for personal AI assistance — a system that runs on the researcher's own infrastructure, uses their own API keys, and connects to their own tools. It is not a SaaS product; it is a tool a physicist downloads and runs.

The name reflects the aspiration: just as OpenClaw democratized personal AI agents, OpenEinstein democratizes AI-assisted physics research. Any physicist — from a grad student to a senior researcher — can configure a research campaign, point it at their problem, and let it systematically explore a search space, run computations, cross-reference literature, and produce a curated shortlist for human evaluation.

### 1.2 Design Principles

**Model-agnostic.** OpenEinstein does not depend on any single LLM provider. Researchers choose their own models — Anthropic, OpenAI, Google, open-source via Ollama — and route different task types to different models based on their own cost/quality preferences. The platform abstracts all LLM calls behind a model routing layer with logical roles.

**Domain-agnostic core, physics-specific Campaign Packs.** The core platform — gateway, agent orchestration, model routing, MCP integration, campaign engine, tracing, evals, security — contains zero physics-subfield-specific logic. Specialization lives in **Campaign Packs**: versioned, modular content bundles containing campaign configs, skills, compute templates, eval suites, and documentation. The first Campaign Pack targets covariant action searches in modified gravity, but the platform is equally suited to lattice QCD parameter scans, dark matter model space exploration, EFT matching, or condensed matter phase classification.

**Open-source, gateway-inspired architecture.** Following OpenClaw's design, OpenEinstein runs as a local gateway process on the researcher's machine. It manages agent sessions, MCP server connections, CAS kernels, and campaign state. The researcher interacts through a CLI (day 1) and optionally a web dashboard (later).

**Evals-first, trace-first.** Observability and evaluation harnesses are built in Phase 1, not bolted on at the end. Every skill, every campaign, and even the persona are testable through eval suites. OpenTelemetry-style tracing is wired in from the first runnable agent.

**Built by AI, for physicists.** The platform is designed to be constructed autonomously by AI coding agents following the AI Coding Best Practices methodology. The build plan is structured as sequentially-ordered tasks with acceptance criteria, integration contracts, and verification steps at every stage.

### 1.3 What OpenEinstein Is Not

It is not a replacement for physical intuition or peer review. It is a research accelerator — it handles the systematic, computational grunt work of exploring large theoretical search spaces so the physicist can focus on evaluation, motivation, and interpretation. Every output includes complete derivations for independent verification.

---

## 2. Architecture Overview

### 2.1 High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        OpenEinstein Gateway                          │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                  Control Plane                                │    │
│  │  runId issuance · event stream (JSONL) · pause/resume/stop   │    │
│  │  hook dispatch · approvals enforcement · policy engine        │    │
│  └──────────────┬───────────────────────────┬───────────────────┘    │
│                  │                           │                        │
│  ┌───────────────▼──────────┐  ┌────────────▼────────────────────┐  │
│  │    Campaign Engine        │  │      Tracing + Evals             │  │
│  │  (State machine, config,  │  │  OpenTelemetry spans, skill      │  │
│  │   progress, checkpoints)  │  │  evals, campaign evals, persona  │  │
│  └──────────┬───────────────┘  │  evals, cost tracking             │  │
│             │                  └──────────────────────────────────┘  │
│  ┌──────────▼────────────────────────────────────────────────────┐   │
│  │               Multi-Agent Orchestration                        │   │
│  │  Orchestrator (reasoning) → Computation · Literature ·         │   │
│  │  Verification agents, configurable single/multi mode           │   │
│  └──────────┬────────────────────────────────────────────────────┘   │
│             │                                                        │
│  ┌──────────▼────────────────────────────────────────────────────┐   │
│  │                    Model Routing Layer                          │   │
│  │  LiteLLM gateway: logical roles → provider/model/params        │   │
│  │  Supports: Anthropic, OpenAI, Google, Ollama, etc.             │   │
│  └──────────┬───────────────────────────┬────────────────────────┘   │
│             │                           │                             │
│  ┌──────────▼──────────┐  ┌────────────▼────────────────────────┐   │
│  │    Tool Bus           │  │     Campaign Pack (loaded)          │   │
│  │  MCP + CLI+JSON       │  │                                    │   │
│  │                        │  │  • Skills (SKILL.md bundles)       │   │
│  │  • Mathematica CAS     │  │  • Compute templates              │   │
│  │  • Python/SymPy CAS    │  │  • Eval suites (golden tasks)     │   │
│  │  • Cadabra CAS         │  │  • campaign.yaml                  │   │
│  │  • arXiv retrieval     │  │  • docs + provenance              │   │
│  │  • Semantic Scholar     │  │                                    │   │
│  │  • INSPIRE-HEP         │  └────────────────────────────────────┘  │
│  │  • NASA ADS            │                                          │
│  │  • CrossRef / Zotero   │                                          │
│  │  • GROBID PDF ingest   │                                          │
│  │  • Parameter scanner   │                                          │
│  │  • Python sandbox      │                                          │
│  │  • LaTeX builder       │                                          │
│  │  • Campaign registry   │                                          │
│  └────────────────────────┘                                          │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │                  Bootstrap Context (bounded, token-aware)        ││
│  │  OPEN_EINSTEIN.md · PERSONALITY.md · TOOLS.md · POLICY.json     ││
│  │  Per-file max chars · Total bootstrap cap · `context report`    ││
│  └──────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │                  Persistence Layer                                ││
│  │  SQLite: campaign state, candidate registry, failure log,        ││
│  │          trace spans, eval results, approval log                 ││
│  │  pgvector (optional): literature embeddings                      ││
│  │  File system: CAS notebooks, derivations, reports, artifacts     ││
│  └──────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 Technology Stack Summary

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Language | Python 3.12+ | Ecosystem breadth, agent framework support, scientific computing |
| Agent framework | PydanticAI | 25+ model providers, native MCP, durable execution, model routing, type-safe |
| Model routing | LiteLLM (via PydanticAI) | 100+ LLM support, unified API, YAML config, provider-agnostic |
| Orchestration | LangGraph (optional layer) | State machine workflows, checkpointing, conditional routing |
| MCP SDK | Python MCP SDK (modelcontextprotocol/python-sdk) | Official protocol implementation |
| CAS primary | Mathematica/Wolfram Engine + xAct | Gold standard for tensor algebra in GR/teleparallel |
| CAS secondary | Python/SymPy | Ubiquitous, lightweight, integrates with numerical tools |
| CAS optional | Cadabra | Field-theory/tensor algebra specialist; complements Mathematica |
| Numerical sandbox | Python (SciPy, NumPy, optionally JAX) | Parameter scans, optimization, Monte Carlo, autodiff |
| Literature MCP | arXiv, Semantic Scholar, INSPIRE-HEP, NASA ADS, CrossRef | Physics-native literature coverage |
| Reference mgmt | Zotero integration | Library sync, BibTeX export |
| PDF ingestion | GROBID | Metadata, references, clean text extraction |
| LaTeX | latexmk + BibLaTeX | First-class publishing output |
| Tracing | OpenTelemetry-compatible spans (lightweight) | Observability from Phase 1 |
| Evals | Built-in eval runner (`openeinstein eval`) | Skill, campaign, and persona evals |
| Embeddings | PhysBERT (or fine-tuned BGE-M3) | Domain-specific physics embeddings |
| Vector store | SQLite + sqlite-vss (default), pgvector (optional) | Zero-dependency default, scale-up path |
| Persistence | SQLite | Zero-config, portable, sufficient for single-researcher use |
| CLI | Typer | Modern Python CLI with auto-completion |
| Config | YAML + Pydantic models | Type-safe configuration with validation |
| Package distribution | PyPI | `pip install openeinstein` |

---

## 3. Agent Framework and Model Routing

### 3.1 Why PydanticAI

The framework must be model-agnostic. PydanticAI was selected for:

- **25+ model providers** including Anthropic, OpenAI, Google Gemini, DeepSeek, Mistral, Cohere, Ollama, Azure, Bedrock, and Vertex AI — all through a unified interface.
- **Native MCP support** via FastMCP client, MCPServerStdio, and MCPServerStreamableHttp — critical for the tool-heavy architecture.
- **Durable execution** for long-running research campaigns that may span hours or days.
- **Model routing** across providers at the framework level, supporting the logical-roles pattern.
- **Type safety** via Pydantic models for all agent inputs, outputs, and state — reducing the surface area for LLM-generated bugs.
- **A2A (Agent2Agent) interoperability** for potential future multi-platform collaboration.

PydanticAI is not the only option. The architecture should abstract the framework choice behind interfaces so that LangGraph, CrewAI, or the OpenAI Agents SDK could substitute without rewriting campaign logic. The key abstraction is: `Agent`, `Tool`, `Skill`, `MCPConnection`, and `ModelRole`.

### 3.2 Model Routing: Logical Roles

All LLM calls in OpenEinstein use logical roles, never specific models. The researcher configures which provider/model fills each role in a YAML config file.

```yaml
# openeinstein.yaml — model routing configuration
model_routing:
  roles:
    reasoning:
      description: "Complex reasoning, planning, physics judgment, synthesis"
      default:
        provider: anthropic
        model: claude-opus-4-6
        params:
          extended_thinking: true
          budget_tokens: 32000
      fallback:
        provider: openai
        model: o3

    generation:
      description: "Code generation, template filling, routine orchestration"
      default:
        provider: anthropic
        model: claude-sonnet-4-5
      fallback:
        provider: openai
        model: gpt-4.1

    fast:
      description: "Classification, routing, simple extraction, failure coding"
      default:
        provider: anthropic
        model: claude-haiku-4-5
      fallback:
        provider: openai
        model: gpt-4.1-mini

    embeddings:
      description: "Text embedding for literature retrieval"
      default:
        provider: local
        model: physbert-base  # or bge-m3 fine-tuned
      fallback:
        provider: openai
        model: text-embedding-3-large
```

**Application code references only the role:**

```python
# In campaign code — never references a specific model
result = await agent.run(
    prompt=analysis_prompt,
    model_role="reasoning"  # resolved by routing layer
)
```

This means a researcher can switch from Anthropic to OpenAI to a local Ollama model by editing one config file, with no code changes.

### 3.3 The Deterministic Sandwich

Following AI Coding Best Practices, every agent operation follows the pattern:

```
Deterministic pre-processing → LLM reasoning → Deterministic post-processing
```

Examples:
- **Pre**: Validate CAS template slots are filled, check kernel is running → **LLM**: Decide which template to use for this candidate → **Post**: Parse CAS output, validate JSON schema
- **Pre**: Load candidate from registry, check it hasn't already been processed → **LLM**: Analyze failure mode and classify → **Post**: Write classification to SQLite, update campaign state
- **Pre**: Validate embedding dimensions match → **LLM**: Generate literature query from candidate properties → **Post**: Deduplicate results, validate DOIs

---

## 4. Multi-Agent Architecture

### 4.1 Why Multi-Agent for OpenEinstein

The architecture supports both single-agent and multi-agent modes. For a single campaign step, single-agent + skills is sufficient — the problem is sequential and context is coherent. However, the full research workflow has genuinely parallelizable concerns:

1. **Literature retrieval** can run concurrently with CAS computations.
2. **Multiple candidates** within the same action class can be evaluated in parallel (each is independent).
3. **Synthesis and reporting** benefit from a fresh context that reviews outputs without the accumulated reasoning of the computation agents.

The Anthropic multi-agent research system's 90.2% improvement over single-agent on complex research tasks supports this. Their key finding: multi-agent works when tasks can be parallelized and context isolated; it degrades on sequential workflows with shared dependencies.

### 4.2 Architecture: Orchestrator + Specialized Subagents

```
                    ┌─────────────────────────┐
                    │   Campaign Orchestrator   │
                    │   (reasoning model)       │
                    │                           │
                    │   Responsibilities:        │
                    │   • Campaign strategy      │
                    │   • Task delegation         │
                    │   • Result synthesis        │
                    │   • Adaptive sampling       │
                    │   • Human communication     │
                    └──────────┬────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
    ┌─────────▼──────┐ ┌──────▼────────┐ ┌─────▼───────────┐
    │  Computation    │ │  Literature   │ │  Verification   │
    │  Agent(s)       │ │  Agent        │ │  Agent          │
    │  (generation)   │ │  (generation) │ │  (reasoning)    │
    │                 │ │               │ │                  │
    │ • CAS execution │ │ • arXiv MCP   │ │ • Fresh context  │
    │ • Template fill │ │ • Semantic    │ │ • Cross-check    │
    │ • Gate checks   │ │   Scholar MCP │ │   derivations    │
    │ • Param scanning│ │ • INSPIRE-HEP │ │ • Audit results  │
    │                 │ │ • NASA ADS    │ │ • Flag issues    │
    │ MCP: CAS backends│ │ • CrossRef   │ │                  │
    │      Scanner    │ │ • Zotero      │ │ No CAS access    │
    │      Python box │ │ • GROBID      │ │ (read-only)      │
    └─────────────────┘ └───────────────┘ └──────────────────┘
```

**Agent specifications:**

| Agent | Model Role | Tool Access | Spawning |
|-------|-----------|------------|----------|
| **Orchestrator** | `reasoning` | Campaign registry (read/write), hooks | Spawns all subagents. Cannot be spawned. Bootstrap context is full. |
| **Computation Agent** | `generation` | CAS MCPs, Parameter Scanner, Python sandbox, Registry (write) | Spawned by orchestrator. Can be parallelized (1 per candidate batch). Bootstrap context is minimal (no PERSONALITY.md). |
| **Literature Agent** | `generation` | arXiv, S2, INSPIRE, ADS, CrossRef, Zotero, GROBID, Vector store | Spawned by orchestrator. Runs in parallel with computation. Minimal bootstrap. |
| **Verification Agent** | `reasoning` | Registry (read-only), File system (read-only) | Spawned by orchestrator. Uses fresh context (no shared history with computation agents). Full bootstrap. |

### 4.3 When to Use Single vs. Multi-Agent

Campaign configuration determines which mode:

```yaml
# Campaign config
campaign:
  agent_mode: multi  # or "single"

  multi_agent:
    max_parallel_computation_agents: 3
    enable_literature_agent: true
    enable_verification_agent: true
    verification_frequency: every_batch  # or "every_candidate", "end_only"
```

For simple campaigns or resource-constrained environments, `agent_mode: single` runs everything in a single agent with skills. For complex campaigns with large search spaces, `agent_mode: multi` activates the orchestrator pattern.

---

## 5. Gateway Control Plane

*Inspired by OpenClaw's operational primitives that survived real-world deployment.*

### 5.1 Why a Control Plane

Long-running campaigns need safe control primitives: pause/resume/stop, streaming progress, reliable retries, and a stable ID for traces and artifacts. Even though day-1 interaction is CLI-only, the control plane abstraction makes the gateway a proper runtime.

### 5.2 Control Plane Interface

```python
class ControlPlane(Protocol):
    def issue_run_id(self) -> RunId: ...
    def get_status(self, run_id: RunId) -> RunStatus: ...
    def stream_events(self, run_id: RunId) -> AsyncIterator[Event]: ...
    def pause(self, run_id: RunId) -> None: ...
    def resume(self, run_id: RunId) -> None: ...
    def stop(self, run_id: RunId) -> None: ...
```

**Event stream:** JSONL events at minimum. Every event includes `run_id`, `timestamp`, `event_type`, and `payload`. Event types include `state_transition`, `tool_call`, `tool_result`, `agent_spawn`, `agent_complete`, `error`, `checkpoint`, `hook_fired`.

**Artifact attachment:** Every artifact (CAS notebook, derivation, plot, report) is attached to a `run_id`. This enables full provenance: "which run produced this notebook?"

### 5.3 CLI Commands

```
openeinstein run <campaign.yaml>    # Start campaign, get run_id
openeinstein run status [run_id]    # Show status
openeinstein run wait [run_id]      # Block until completion
openeinstein run stop [run_id]      # Graceful stop
openeinstein run resume [run_id]    # Resume from last checkpoint
openeinstein run events [run_id]    # Stream events (tail -f style)
```

---

## 6. Hooks and Extension System

*Adopted from OpenClaw's hooks pattern — event-driven extension without patching core.*

### 6.1 Hook Points

```python
# Hook interface
class Hook(Protocol):
    async def __call__(self, event: HookEvent) -> HookResult: ...

# Available hook points
HOOK_POINTS = [
    "before_tool_call",       # Inspect/modify/block tool calls
    "after_tool_call",        # Inspect/log tool results
    "campaign_state_transition",  # Campaign state changes
    "before_compaction",      # Context compaction events
    "after_compaction",       # Verify invariants survived compaction
    "on_run_start",           # Campaign starts
    "on_run_end",             # Campaign completes/fails
    "on_agent_spawn",         # Subagent created
    "on_approval_required",   # Tool needs approval
]
```

### 6.2 What Hooks Absorb

Hooks are the extension mechanism for behaviors that don't belong in core:
- **Policy enforcement**: block unapproved tool calls
- **Audit logging**: record all tool calls for compliance
- **Artifact indexing**: register outputs in external systems
- **Custom lab integration**: HPC job submission, Slack notifications, email alerts
- **Persona enforcement**: validate outputs against persona constraints

### 6.3 Hook Registration

```yaml
# openeinstein.yaml
hooks:
  - name: "audit_logger"
    event: "after_tool_call"
    handler: "openeinstein.hooks.audit:log_tool_call"

  - name: "approval_gate"
    event: "before_tool_call"
    handler: "openeinstein.hooks.security:check_approval"
    config:
      require_approval_for: ["shell_exec", "network_fetch", "file_write_outside_workspace"]

  - name: "slack_notify"
    event: "campaign_state_transition"
    handler: "openeinstein.hooks.notify:slack_webhook"
    config:
      webhook_url: "${SLACK_WEBHOOK_URL}"
      notify_on: ["COMPLETE", "ERROR", "PAUSED"]
```

---

## 7. MCP Integration Layer

### 7.1 Capability-First Tool Integration

*Lesson from OpenClaw: use MCP where it pays rent; avoid low-quality MCP servers that pollute context.*

**Use MCP for:**
- CAS sessions (Mathematica, SymPy, Cadabra) — stateful, complex interaction
- Campaign registry/state server — session-scoped state
- Literature caches that benefit from session state

**Allow CLI+JSON tools for simpler integrations:**
- LaTeX builder (latexmk — fire and forget)
- GROBID PDF ingestion (request/response)
- File operations

Both are wrapped in a unified `ToolBus` interface so agent code doesn't care about the transport.

### 7.2 Tool Registry

**Literature + Citations (physics-native):**

| Tool | Type | Source | Purpose |
|------|------|--------|---------|
| arXiv | MCP | `blazickjp/arxiv-mcp-server` | Search, download, analyze physics preprints |
| Semantic Scholar | MCP | `FujishigeTemma/semantic-scholar-mcp` | 226M+ papers, citation graphs, author info |
| INSPIRE-HEP | MCP/CLI | Custom (REST API wrapper) | HEP-specific literature, author profiles |
| NASA ADS | MCP/CLI | Custom (REST API wrapper) | Astrophysics literature, citation metrics |
| CrossRef | MCP | `botanicastudios/crossref-mcp` | DOI resolution, metadata normalization |
| Zotero | CLI+JSON | Custom (Web API v3 wrapper) | Library sync, BibTeX export |
| GROBID | CLI+JSON | Custom (REST client) | PDF → metadata + references + clean text |

**Computation:**

| Tool | Type | Source | Purpose |
|------|------|--------|---------|
| Mathematica | MCP | Custom (extend `paraporoco/Wolfram-MCP`) | Symbolic tensor algebra via xAct |
| Python/SymPy | MCP | Custom | General symbolic + numeric glue |
| Cadabra | MCP | Custom | Field-theory/tensor algebra (optional first-class) |
| Parameter Scanner | MCP | Custom | Numerical parameter space exploration |
| Python Sandbox | MCP | Custom | SciPy, optimization, Monte Carlo, plotting |

**State + Infrastructure:**

| Tool | Type | Source | Purpose |
|------|------|--------|---------|
| Campaign Registry | MCP | Custom | CRUD on candidate registry and failure log |
| Knowledge Graph | MCP | Custom | Entity-relationship queries |
| LaTeX Builder | CLI+JSON | `latexmk` wrapper | Compile .tex → PDF |
| BibTeX Generator | CLI+JSON | Custom | Generate .bib from sources |

### 7.3 CAS Backend Capability Declaration

Instead of hardcoding backends, CAS backends declare capabilities:

```python
class CASCapability(str, Enum):
    SYMBOLIC_SIMPLIFY = "symbolic_simplify"
    TENSOR_SIMPLIFY = "tensor_simplify"
    VARY_ACTION = "vary_action"
    EXPORT_LATEX = "export_latex"
    EXPORT_NOTEBOOK = "export_notebook"
    PERTURBATION_EXPANSION = "perturbation_expansion"
    STABILITY_ANALYSIS = "stability_analysis"

class CASBackend(Protocol):
    name: str
    capabilities: set[CASCapability]

    async def evaluate(self, expr: str, session_id: str) -> CASResult: ...
    async def define_metric(self, name: str, components: dict) -> str: ...
    async def vary_action(self, action: str, field: str) -> str: ...
    async def restrict_to_cosmology(self, expr: str, ansatz: str) -> str: ...
    async def perturb(self, expr: str, order: int) -> str: ...
    async def check_stability(self, kinetic: str, gradient: str) -> StabilityResult: ...
    async def solve_system(self, equations: list, variables: list) -> list: ...
    async def export_session(self, session_id: str, path: str) -> str: ...
```

Campaign configs declare required capabilities; the platform selects the available backend automatically:

```yaml
campaign:
  cas_requirements:
    - tensor_simplify
    - vary_action
    - perturbation_expansion
  cas_preferred: mathematica  # fallback to any backend with required capabilities
```

### 7.4 MCP Server Configuration

```yaml
# openeinstein.yaml — MCP configuration
mcp_servers:
  mathematica:
    type: stdio
    command: "openeinstein-mcp-mathematica"
    args: ["--kernel-path", "/usr/local/bin/wolframscript"]
    sandbox:
      network: none
      workspace_access: rw
    required: false

  sympy:
    type: stdio
    command: "openeinstein-mcp-sympy"
    sandbox:
      network: none
      workspace_access: rw
    required: true  # always available (pure Python)

  cadabra:
    type: stdio
    command: "openeinstein-mcp-cadabra"
    sandbox:
      network: none
      workspace_access: rw
    required: false

  arxiv:
    type: stdio
    command: "npx"
    args: ["-y", "@blazickjp/arxiv-mcp-server"]
    sandbox:
      network: allow
      workspace_access: none
    required: true

  semantic_scholar:
    type: stdio
    command: "semantic-scholar-mcp"
    env:
      S2_API_KEY: "${S2_API_KEY}"
    sandbox:
      network: allow
      workspace_access: none
    required: false

  campaign_registry:
    type: stdio
    command: "openeinstein-mcp-registry"
    args: ["--db-path", "./campaign.db"]
    sandbox:
      network: none
      workspace_access: rw
    required: true
```

---

## 8. Computer Algebra System Integration

### 8.1 Mathematica MCP Server (Primary)

The Mathematica MCP server wraps the Wolfram Kernel and exposes symbolic computation tools via MCP.

**Tools to expose:**

| Tool | Description | Input | Output |
|------|-------------|-------|--------|
| `evaluate` | Execute arbitrary Mathematica expression | Expression string, session ID | Result, timing, warnings |
| `define_metric` | Define a spacetime metric tensor | Name, components dict | Confirmation, metric object ID |
| `vary_action` | Compute variational derivative of action | Action expression, field to vary | Field equations |
| `restrict_to_cosmology` | Substitute cosmological ansatz and simplify | Expression, ansatz type | Reduced expression |
| `perturb` | Expand to given perturbation order (via xPert) | Expression, order, gauge | Perturbed action |
| `compute_kinetic_matrix` | Extract kinetic matrix from second-order action | Second-order action, DOF list | Matrix expression |
| `check_stability` | Run full stability check suite | Kinetic matrix, gradient matrix | Ghost/gradient/tachyon verdicts |
| `solve_system` | Solve system of equations symbolically | Equations, variables | Solutions |
| `simplify` | Apply simplification rules | Expression, rule set | Simplified expression |
| `export_notebook` | Save computation session as .nb file | Session ID, path | File path |
| `export_latex` | Export expression as LaTeX | Expression | LaTeX string |

**Crash recovery:** The server maintains a session journal. If the Wolfram Kernel crashes (common with complex xAct computations), the server detects the crash, restarts the kernel, replays the session journal, and retries with a simplified fallback strategy.

**Template system:** The agent does not generate raw Mathematica code. Instead, it fills parameterized templates stored as `.wl` files with clearly marked `{{PLACEHOLDER}}` slots.

### 8.2 Python/SymPy MCP Server (Secondary — Always Available)

SymPy is the ubiquitous free alternative. It integrates naturally with NumPy/SciPy for numerical work and is always installed (pure Python dependency).

**Capabilities:** `symbolic_simplify`, `vary_action`, `solve_system`, `export_latex`. Tensor algebra is limited compared to Mathematica/xAct but sufficient for many campaigns.

### 8.3 Cadabra MCP Server (Optional First-Class)

Cadabra is purpose-built for field theory and tensor algebra. It complements Mathematica — particularly strong for QFT-oriented computations, index manipulation, and component calculations.

**Capabilities:** `tensor_simplify`, `vary_action`, `perturbation_expansion`, `export_latex`.

**Status:** First-class optional. Installed via `pip install openeinstein[cadabra]`. Not required for the core platform to function.

### 8.4 CAS Backend Abstraction

Campaign skills call the abstract `CASBackend` interface. The routing layer resolves to the available CAS backend that supports the required capabilities.

---

## 9. Numerical Compute Workbench

### 9.1 Sandboxed Python Runner

Beyond symbolic CAS, physics campaigns need general numerical computation: parameter scanning, optimization, Monte Carlo sampling, and plotting.

**MCP Server: `python_sandbox`**

| Tool | Description |
|------|-------------|
| `run_script` | Execute a Python script in sandbox (SciPy, NumPy, matplotlib available) |
| `scan_grid` | Grid scan over parameter space |
| `scan_adaptive` | Adaptive scan with refinement near boundaries |
| `optimize` | Minimize/maximize objective using scipy.optimize |
| `monte_carlo` | Random sampling with configurable distributions |
| `plot` | Generate matplotlib plots, save to workspace |

**Sandboxing:** The Python runner executes in a restricted subprocess with `network: none` and workspace-scoped filesystem access. No `subprocess`, `os.system`, or `importlib` from untrusted input.

### 9.2 Optional JAX Integration

For autodiff-heavy workflows (e.g., gradient-based optimization of action parameters), JAX can be installed as an optional dependency: `pip install openeinstein[jax]`.

---

## 10. Literature, Citations, and Knowledge Infrastructure

### 10.1 MCP-First Literature Access

The primary literature access path is through MCP servers and CLI+JSON tools. The agent makes tool calls like:

```
arxiv.search("scalar field coupling stability modified gravity")
semantic_scholar.search("teleparallel gravity perturbation theory", fields=["title","abstract","citationCount"])
inspire.search("find a gravitational wave speed constraints scalar-tensor")
ads.search("dark energy equation of state observational constraints")
crossref.search_by_doi("10.1103/PhysRevD.98.044048")
zotero.export_bibtex(collection="modified-gravity")
```

### 10.2 PDF Ingestion via GROBID

For local papers not in online databases, or for extracting structured data from PDFs:

```
grobid.parse_pdf("/path/to/paper.pdf")
→ { title, authors, abstract, sections, references[], equations[] }
```

GROBID runs as a local Docker container or service. The CLI+JSON wrapper sends the PDF and returns structured JSON.

### 10.3 Local Knowledge Base (Optional Enhancement)

For repeated-access papers and domain-specific retrieval:

**Embedding model:** PhysBERT (pre-trained on 1.2M arXiv physics papers) is the default. For researchers in specific subfields, fine-tuning BGE-M3 on their corpus is recommended.

**Vector store:** SQLite + sqlite-vss as the zero-dependency default. pgvector for larger corpora.

**Knowledge graph:** Lightweight graph in SQLite (nodes + edges tables) mapping: action structures → known pathologies, papers → results they establish, stability conditions → which theories they constrain, failure modes → which structural features cause them.

### 10.4 Building the Knowledge Base

The knowledge base is built incrementally:
1. **Seed corpus**: Campaign Pack lists key papers by arXiv ID. At campaign start, these are fetched via arXiv MCP, embedded, and stored locally.
2. **Runtime enrichment**: When the literature agent finds relevant papers during a campaign, they are automatically added.
3. **Cross-campaign persistence**: The knowledge base persists and grows across campaigns.

---

## 11. LaTeX Publishing Toolchain

*Publishing output is a first-class artifact in physics.*

### 11.1 LaTeX Build Tool

```
openeinstein latex build <file.tex>    # Compile via latexmk
openeinstein latex clean               # Remove build artifacts
```

The LaTeX builder wraps `latexmk` and handles:
- Multiple compilation passes (for references, cross-references)
- BibTeX/BibLaTeX compilation
- Error reporting with line numbers

### 11.2 BibTeX/BibLaTeX Generation

The literature agent can produce `.bib` files from any combination of sources:
- arXiv IDs → BibTeX entries (via arXiv MCP)
- DOIs → BibTeX entries (via CrossRef MCP)
- INSPIRE-HEP IDs → BibTeX entries (via INSPIRE API)
- Zotero collections → BibTeX export

### 11.3 Preprint Skeleton Generator

A skill that generates a complete LaTeX project structure for a physics preprint:

```
openeinstein latex skeleton --template "phys-rev-d" --title "..." --authors "..."
→ paper/
  ├── main.tex        # With standard sections
  ├── references.bib  # Populated from campaign citations
  ├── figures/         # Plots from campaign
  └── Makefile
```

---

## 12. Campaign Engine and State Management

### 12.1 What a Campaign Is

A campaign is a configured research task. It defines the search problem, search space, gate pipeline, success criteria, and resource constraints. The campaign engine runs any campaign defined in the standard format.

### 12.2 Campaign Configuration Schema

```yaml
# campaigns/example-action-search/campaign.yaml
campaign:
  name: "Action Search"
  version: "1.0"
  description: >
    Systematically explore candidate actions in a given
    gravitational theory, filtering through reduction,
    perturbation analysis, and stability gates.

  search_space:
    generator_skill: "action-taxonomy"
    # Campaign Pack defines classes and tiers
    estimated_candidates: 200-500

  gate_pipeline:
    - name: "Cosmological Reduction"
      skill: "cosmology-reduction"
      cas_requirements: [tensor_simplify, vary_action]
      timeout_minutes: 30

    - name: "Perturbation Expansion"
      skill: "perturbation-analysis"
      cas_requirements: [perturbation_expansion]
      timeout_minutes: 60

    - name: "Stability Analysis"
      skill: "stability-analysis"
      cas_requirements: [stability_analysis]
      timeout_minutes: 30

    - name: "Literature Cross-Reference"
      skill: "literature-xref"

  adaptive_sampling:
    enabled: true
    batch_size: 10
    prioritization:
      - "distance_from_successes"
      - "absence_of_shared_failures"
      - "simplicity"

  success_criteria:
    min_viable_candidates: 1
    require_failure_map: true
    require_notebooks: true
    require_next_steps_doc: true

  resources:
    agent_mode: multi
    max_parallel_computation: 3
    model_budget_usd: 200
    cas_timeout_per_candidate_min: 30
```

### 12.3 Campaign State Machine

```
INITIALIZED → GENERATING → EVALUATING → SYNTHESIZING → COMPLETE
     │              │            │              │           │
     │              │            │              │           └→ ARCHIVED
     │              │            ├→ ADAPTING ───┘
     │              │            │  (refine search based on failures)
     │              │            └→ PAUSED (human review requested)
     │              └→ ERROR (recoverable) → resume from last checkpoint
     └→ CONFIGURING (validating campaign config)
```

**State persistence:** Campaign state is stored in SQLite with WAL mode for crash safety. Every state transition is logged with timestamp, trigger, metadata, and `run_id`. If the process crashes, it resumes from the last committed state.

### 12.4 Concurrency and Idempotency

*Long-running systems with retries need to be safe under partial failure.*

- **Serialize by default:** campaign state transitions, per-candidate updates, per-CAS-session tool calls
- **Allow parallelism only when isolation is guaranteed:** independent candidates, literature queries
- **Idempotency keys:** every side-effecting action (write artifact, mutate state) carries an idempotency key so retries are safe

---

## 13. Campaign Packs: The Extension Mechanism

### 13.1 What a Campaign Pack Is

A Campaign Pack is a versioned, modular content bundle that turns the domain-agnostic core into a specialized research tool. It is analogous to a plugin or content pack.

**Core Platform** (domain-agnostic):
- Gateway + control plane
- Agent orchestration + model routing
- Tool bus (MCP + CLI+JSON)
- Campaign engine + state machine
- Security + sandboxing + approvals
- Tracing + evals
- Packaging + docs

**Campaign Pack** (physics-domain-specific):
```
campaign-packs/
  modified-gravity-action-search/
  ├── campaign.yaml           # Schema-validated campaign config
  ├── skills/                 # SKILL.md bundles + resources
  │   ├── action-taxonomy/
  │   ├── cosmology-reduction/
  │   ├── perturbation-analysis/
  │   ├── stability-analysis/
  │   └── literature-xref/
  ├── templates/              # CAS compute templates
  │   ├── mathematica/
  │   ├── sympy/
  │   └── cadabra/
  ├── evals/                  # Golden tasks + regression tests
  │   ├── known-models.yaml
  │   └── expected-results/
  ├── docs/
  │   ├── README.md
  │   └── provenance.md       # Which papers/methods this pack implements
  └── literature-seed.yaml    # arXiv IDs for corpus seeding
```

### 13.2 Installing and Running a Campaign Pack

```
openeinstein pack install ./campaign-packs/modified-gravity-action-search/
openeinstein run modified-gravity-action-search
```

Or from a git repository:
```
openeinstein pack install https://github.com/user/openeinstein-pack-modified-gravity.git
```

### 13.3 Example Campaign Packs (Generic, No Subfield Lock-In)

**Action → EOM Pipeline:**
Symbolic derivation of equations of motion from an action functional, with LaTeX export and citation bundle. Applicable to any gravitational theory, field theory, or classical mechanics problem.

**Stability & Parameter Scan:**
Scan a parameter space, classify stability regions (ghost-free, gradient-stable, tachyon-free), produce phase diagrams and summary. Applicable to any theory with tunable parameters.

**Literature Mapping:**
Build a taxonomy of papers on a topic, identify key results, open problems, and generate a structured BibTeX library. Applicable to any physics subfield.

---

## 14. Personality and Persona System

*Inspired by OpenClaw's SOUL.md — but fixed and testable.*

### 14.1 Why Personality Matters for OpenEinstein

A good "AI physicist" should reliably exhibit: epistemic humility (flag uncertainty), strong preference for derivations and explicit assumptions, disciplined citation behavior, low tolerance for confident nonsense, and helpful skepticism (push back on ill-posed questions). That's not just tone — it's **operational behavior** that affects research quality.

### 14.2 Canonical, Versioned Persona

**Design:** A single canonical persona file shipped with the system, not user-customizable by default.

**File:** `core/PERSONALITY.md` (shipped as a package resource)

The gateway injects this into the orchestrator's system prompt. The run manifest stores:
- persona hash + version
- policy state hash
- toolchain versions

**Override:** Only behind a `--dev` flag, explicitly marked as unsupported for production reproducibility.

### 14.3 What Goes into PERSONALITY.md

Following OpenClaw's structure (Core truths / Boundaries / Vibe):

**Core truths:**
- Be rigorous; show assumptions explicitly
- Prefer derivations over authority
- Admit uncertainty; propose verification steps
- Use standard notation; define non-standard symbols
- Cite sources for non-trivial claims

**Boundaries:**
- Never fabricate citations or results
- Never run destructive tools without approval
- Treat tool outputs as untrusted unless verified
- Flag when a computation exceeds confidence bounds
- Clearly separate established results from speculative reasoning

**Vibe:**
- Pragmatic, direct, slightly nerdy, not sycophantic
- Communicate like a careful postdoc, not a marketing page
- Use equations where they clarify, prose where they don't

### 14.4 Persona Evals

Testable via the eval framework (§15):
- **Uncertainty calibration:** Given ambiguous inputs, does the agent flag uncertainty?
- **Citation behavior:** Does the agent cite sources for non-trivial claims?
- **Refusal boundaries:** Does the agent refuse unsafe tool calls?
- **Format discipline:** Does the agent produce valid schemas, manifests, LaTeX?
- **No fabrication:** Given a request for a paper that doesn't exist, does the agent decline?

---

## 15. Observability: Tracing and Evals

*Built in Phase 1, not bolted on at the end.*

### 15.1 Tracing

**OpenTelemetry-compatible spans** for every significant operation:

```python
# Automatic instrumentation via decorators
@traced("gate_check")
async def run_gate(candidate: Candidate, gate: Gate) -> GateResult:
    ...
```

Traces include: tool calls (MCP + CLI), LLM requests (model, tokens, latency, cost), state transitions, agent spawns, and errors.

**Storage:** Traces are stored in SQLite by default. Export to OTLP-compatible backends (Jaeger, Arize Phoenix) via configuration.

**CLI:**
```
openeinstein trace list [run_id]        # Show spans for a run
openeinstein trace export [run_id]      # Export as OTLP JSON
openeinstein context report             # Bootstrap context breakdown + token counts
```

### 15.2 Eval Framework

```
openeinstein eval run <eval-suite>      # Run an eval suite
openeinstein eval list                  # List available suites
openeinstein eval results [run_id]      # Show eval results
```

**Eval types:**
- **Skill evals:** Does a skill produce correct output for golden inputs? (e.g., "given this known model, does the stability skill correctly identify the ghost?")
- **Campaign evals:** Does a mini-campaign on known models produce correct end-to-end results?
- **Persona evals:** Does the agent's behavior match PERSONALITY.md constraints?
- **Regression evals:** After code changes, do previous passing cases still pass?

**Eval suite format:**
```yaml
# evals/stability-skill-eval.yaml
eval_suite:
  name: "Stability Skill Evaluation"
  skill: "stability-analysis"
  cases:
    - name: "Standard quintessence (should pass)"
      input: { model: "quintessence_standard", params: {...} }
      expected: { ghost_free: true, gradient_stable: true, c_T_equals_c: true }
    - name: "Known ghost model (should fail)"
      input: { model: "ghost_example", params: {...} }
      expected: { ghost_free: false }
```

---

## 16. Long-Running Agent Infrastructure

### 16.1 Compaction as a Platform Subsystem

Long campaigns (hours to days) will exceed context windows. Compaction — summarizing conversation history to reclaim context — must be a platform subsystem, not a prompt hack.

**Design:**
- Compaction triggers automatically when context reaches a configurable threshold (e.g., 80% of window)
- The `before_compaction` hook fires, allowing policy enforcement
- Compaction preserves: campaign state summary, current candidate status, active constraints, pending tasks
- The `after_compaction` hook fires, allowing invariant verification
- **Policy invariants** (see §16.2) are re-injected after compaction, not relied upon to survive it

### 16.2 Policy Invariants (Machine-Enforced, Outside LLM Context)

Critical safety and correctness constraints must not be lost to compaction or context drift.

**`POLICY.json`** — a machine-enforced state object stored outside the LLM context:

```json
{
  "version": "1.0",
  "invariants": {
    "require_approval_for": ["shell_exec", "network_fetch", "file_write_outside_workspace"],
    "max_llm_calls_per_step": 50,
    "max_cas_timeout_minutes": 60,
    "forbidden_operations": ["delete_campaign_state", "modify_other_campaigns"],
    "require_verification_after_gates": true
  },
  "enforced_by": "gateway",
  "note": "These invariants are checked by the gateway before every tool call. They cannot be modified by the LLM."
}
```

The gateway checks `POLICY.json` before every tool call. The LLM cannot override or modify these constraints, even if instructed to do so by compacted context or injected prompts.

---

## 17. AI Coding Best Practices Integration

This section maps the AI Coding Best Practices methodology to the OpenEinstein build process.

### 17.1 Canonical Documentation

Every major component gets a canonical document before implementation begins. These live in `docs/canonical/` and are updated after each build phase.

```
docs/
  canonical/
    _index.md
    core-architecture.md
    gateway-control-plane.md
    model-routing.md
    tool-bus.md
    campaign-engine.md
    cas-backends.md
    literature-infrastructure.md
    multi-agent-orchestration.md
    tracing-and-evals.md
    security-model.md
    cli-interface.md
    personality.md
```

### 17.2 The Development Loop Applied

Each build task in §19 follows the 15-step development loop:

1. **Research** → Produce canonical doc for the component
2. **Draft feature plan** → Decompose into buildable tasks with integration contracts
3. **Validate requirements** → Fresh-context check that plan meets spec
4. **Validate integration** → Fresh-context check that plan integrates with existing components
5. **Generate build plan** → Ordered task list with acceptance criteria
6. **Double-check build plan** → Fresh-context validation
7. **Pre-flight check** → Verify files exist, dependencies installed
8. **Implement** → Task-by-task with unit tests, git commit per task
9. **Code review** → Surface-level quality check
10. **Deep audit** → System-level correctness + integration contract verification
11. **Remediation** → Fix issues
12. **Full E2E test** → Run entire test suite
13. **Final remediation** → Fix regressions
14. **Commit + update docs** → Merge, update canonical docs
15. **Smoke test** → Post-merge verification

### 17.3 Project Context Files

```
CLAUDE.md              # or AGENTS.md — project-level instructions
├── Tech stack and dependencies
├── Architectural patterns (capability-first tools, deterministic sandwich, logical roles)
├── Anti-patterns (no hardcoded model names, no direct LLM API calls, all tools via ToolBus)
├── Testing requirements (pytest, integration tests per tool)
├── Living error log (updated as issues are discovered)
```

### 17.4 Integration Contracts

Every feature plan includes an Integration Contract specifying: files modified and how, files created and where they connect, tool schemas (new or modified), database schema changes, configuration schema changes, and dependencies (what this feature needs, what will need this feature).

### 17.5 Task Format for AI Agent Execution

Every task in §19 follows this structure:

```
Task X.Y: [Name]
  Description: [What to build]
  Acceptance Criteria: [Exact, automatable checks — pytest commands, type-check commands]
  Integration Contract:
    Files Created: [List with paths]
    Files Modified: [List with paths and description of changes]
    Interfaces Exposed: [Python protocols/ABCs, MCP tool schemas]
    Database Changes: [Schema additions/modifications]
    Config Changes: [New YAML keys]
    Depends On: [Task IDs]
    Depended On By: [Task IDs]
  Verification Commands:
    - pytest tests/unit/test_<component>.py
    - mypy src/openeinstein/<module>/
    - python -c "from openeinstein.<module> import <Class>; assert <quick check>"
  Git: Commit after passing all verification commands.
```

### 17.6 Verification Strategy

Following the "Verify Independently, Verify Often" principle:

- **Unit tests**: Every tool, every campaign engine state transition, every model routing resolution
- **Integration tests**: Tool ↔ agent communication, CAS computation round-trips, literature retrieval end-to-end
- **Campaign tests**: Run a mini-campaign on known physics problems and verify correct results
- **Eval suites**: Skill evals, campaign evals, persona evals (see §15.2)
- **LLM-as-Judge**: For subjective quality, use a separate model as evaluator
- **Fresh-context validation**: Critical plans and outputs reviewed by a separate agent invocation

---

## 18. Security and Safety Model

*Draws on OpenClaw patterns and 2026 agent security incidents.*

### 18.1 Approvals as a First-Class System

```
openeinstein approvals list              # Show current approval state
openeinstein approvals grant <action>    # Grant permission
openeinstein approvals revoke <action>   # Revoke permission
openeinstein approvals reset             # Reset to defaults
```

**Actions requiring approval:**
- Filesystem writes outside workspace
- Network egress for tools that fetch/install
- Package installs / shell execution
- "Elevated" operations (break-glass)
- Sending data to external services

**Approvals are:**
- Stored as a file in the workspace (`.openeinstein/approvals.json`)
- Enforced by the gateway via the `before_tool_call` hook — before every tool call
- Logged in the audit trail
- Default-deny for all risky tools

### 18.2 Sandboxing

*Separate tool execution location from tool allow/deny policy.*

**Model (from OpenClaw):**
- Gateway runs on host
- Tools can run in Docker sandboxes (recommended for Python runner, shell)
- Default `network: none` for compute tools
- `workspaceAccess: none | ro | rw` per tool
- Per-campaign or per-agent sandbox scope
- `openeinstein sandbox explain` command to diagnose "why is this blocked?"

### 18.3 MCP Tool Poisoning Defense

*2026 best-practice security posture: tool metadata is untrusted.*

- **Pin tool metadata hashes at install time:** require explicit user acknowledgment on change
- **Sanitize tool descriptions:** cap length, treat as untrusted input, never inject raw descriptions into system prompts
- **`openeinstein scan`:** scans configs + SKILL.md + MCP manifests, flags risky patterns and permission overreach
- **Policy enforcement outside LLM context:** `POLICY.json` (see §16.2) is checked by the gateway, not by the LLM. Compaction cannot erase safety constraints.

### 18.4 Secrets Management

- All secrets stored in `.env` file or system keyring — never in YAML configs or code
- `SecretsProvider` abstraction with `EnvFileSecretsProvider` and `KeyringSecretsProvider` implementations
- LiteLLM reads provider keys from environment variables; platform sets these at startup, then clears raw values
- Campaign configs reference secrets by name only, never by value
- `.env` is in `.gitignore` by default; `openeinstein init` creates `.env.example`
- All log output filtered through `SecretRedactor`
- LLM request/response logs strip `Authorization` headers
- Campaign state database stores model role names, not API keys

### 18.5 Data Isolation

- Each campaign has its own workspace directory, SQLite database, and CAS session pool
- Campaigns cannot read each other's state or files
- LLM conversation history is stored per-campaign and purged on `openeinstein campaign clean`
- No telemetry or data is sent externally — OpenEinstein is fully local by default

---

## 19. Sequential Build Order

Tasks are ordered by dependency. Each task includes acceptance criteria that an AI coding agent can verify. Tasks within a phase can be parallelized if they have no inter-dependencies (marked with ∥).

### Phase 0: Repository Bootstrap

**Task 0.1: Initialize repository structure**
```
openeinstein/
├── pyproject.toml
├── README.md
├── CLAUDE.md                     # Agent instructions
├── AGENTS.md                     # Open standard agent context
├── CONTRIBUTING.md               # PR size limits, plugin-first rules
├── .github/
│   └── workflows/ci.yml
├── src/
│   └── openeinstein/
│       ├── __init__.py
│       ├── core/                  # Framework abstractions
│       │   └── PERSONALITY.md     # Canonical persona
│       ├── gateway/               # Control plane + hooks
│       ├── agents/                # Agent definitions
│       ├── tools/                 # Tool bus + MCP servers
│       ├── campaigns/             # Campaign engine
│       ├── skills/                # Skill definitions
│       ├── routing/               # Model routing
│       ├── persistence/           # Database layer
│       ├── tracing/               # Observability
│       ├── evals/                 # Eval framework
│       ├── security/              # Approvals, sandbox, policy
│       └── cli/                   # CLI interface
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── evals/
│   └── campaigns/
├── campaign-packs/                # Campaign Pack directories
├── docs/
│   ├── canonical/
│   ├── build-plans/
│   └── trust-model.md             # Operator boundary doc
└── configs/
    ├── openeinstein.example.yaml
    └── POLICY.json                # Machine-enforced invariants
```
**Acceptance criteria:** `pip install -e .` succeeds. `pytest` runs (0 tests, 0 failures). CI pipeline triggers on push.

**Task 0.2: Write CLAUDE.md, AGENTS.md, and CONTRIBUTING.md**
- Document tech stack, architectural patterns, coding conventions
- Include anti-patterns: no hardcoded models, no direct LLM API calls, all tools via ToolBus
- Include testing requirements
- CONTRIBUTING.md: PR size limits, Campaign Pack-first policy for domain-specific code

**Acceptance criteria:** Files exist, are under 500 lines each, and cover all architectural decisions.

**Task 0.3: Write canonical documentation index and core architecture doc**

**Acceptance criteria:** `docs/canonical/_index.md` and `docs/canonical/core-architecture.md` exist and accurately describe the system.

**Task 0.4: Write trust model document and PERSONALITY.md** ∥
- `docs/trust-model.md`: operator boundary, what the platform can/cannot do
- `core/PERSONALITY.md`: canonical persona (see §14.3)

**Acceptance criteria:** Files exist. Persona file covers core truths, boundaries, vibe. Trust model covers operator boundary.

**Task 0.5: Write POLICY.json** ∥
- Machine-enforced invariants (see §16.2)
- Default-deny for risky operations

**Acceptance criteria:** Valid JSON. All invariant types documented. Gateway can load and validate.

---

### Phase 1: Core Framework + Observability

**Task 1.1: Implement model routing layer**
- Pydantic models for routing config (roles, providers, fallbacks)
- YAML config loader with validation
- Route resolution: logical role → provider/model/params
- Fallback chain: if primary provider fails, try fallback
- Cost tracking: log tokens used per role

**Integration contract:** Consumed by all agent definitions. Exposes `ModelRouter.resolve(role: str) -> ModelConfig`.

**Acceptance criteria:** Unit tests for config loading, route resolution, fallback behavior. Test with mock LLM calls. `pytest tests/unit/test_routing.py` passes.

**Task 1.2: Implement tool bus (MCP + CLI+JSON)** ∥
- Unified tool interface: `ToolBus.call(tool_name, args) -> Result`
- MCP connection manager: start, stop, health-check MCP servers
- CLI+JSON tool wrapper: subprocess execution, JSON parsing
- Configuration from YAML
- Server lifecycle management
- Tool discovery: enumerate tools from connected servers
- Error handling: crash detection and restart (max 3 retries)

**Integration contract:** Consumed by agent definitions. Exposes `ToolBus.get_tools(server_name: str) -> list[Tool]` and `ToolBus.call(server: str, tool: str, args: dict) -> Result`.

**Acceptance criteria:** Unit tests with mock tools. Integration test: start a trivial MCP server, discover tools, call a tool, stop server. `pytest tests/unit/test_tool_bus.py` passes.

**Task 1.3: Implement persistence layer** ∥
- SQLite database with WAL mode
- Campaign state table
- Candidate registry table (JSON columns for complex fields)
- Failure log table
- Trace spans table
- Eval results table
- Approval log table
- Migration system

**Integration contract:** Consumed by Campaign Registry MCP server, campaign engine, tracing, evals. Exposes `CampaignDB` with typed methods for all CRUD operations.

**Acceptance criteria:** Unit tests for all CRUD operations. Test data integrity across crash simulation. `pytest tests/unit/test_persistence.py` passes.

**Task 1.4: Implement tracing subsystem** ∥
- `@traced` decorator for automatic span creation
- Span storage in SQLite
- OTLP JSON export
- Token and cost tracking per span
- `openeinstein trace` CLI commands

**Integration contract:** Used by all subsequent components. Decorator-based — no code changes needed to add tracing to new functions.

**Acceptance criteria:** Traced function creates spans in database. Export produces valid OTLP JSON. `pytest tests/unit/test_tracing.py` passes.

**Task 1.5: Implement eval framework scaffolding** ∥
- Eval suite YAML schema (Pydantic validation)
- Eval runner: load suite → execute cases → compare results → report
- `openeinstein eval` CLI commands
- Result storage in SQLite

**Integration contract:** Used by skill evals, campaign evals, persona evals in later phases.

**Acceptance criteria:** A trivial eval suite (2 cases) loads, runs, and reports results. `pytest tests/unit/test_evals.py` passes.

**Task 1.6: Implement control plane primitives** ∥
- `RunId` issuance
- Event stream (JSONL to file + in-memory)
- `run status`, `run wait`, `run stop`, `run resume` commands
- Artifact attachment to `run_id`

**Integration contract:** Used by campaign engine, CLI. All artifacts and traces reference `run_id`.

**Acceptance criteria:** Run lifecycle test: issue ID → emit events → query status → stop → resume. `pytest tests/unit/test_control_plane.py` passes.

**Task 1.7: Implement Campaign Registry MCP server**
- Wraps persistence layer as MCP tools
- Tools: `add_candidate`, `update_gate_result`, `get_candidates`, `get_failure_log`, `get_statistics`
- JSON schema validation on all inputs

**Integration contract:** Connected via tool bus. Consumed by all agents.

**Acceptance criteria:** MCP server starts, tools are discoverable, round-trip test. `pytest tests/integration/test_registry_mcp.py` passes.

---

### Phase 2: Agents + Security + Hooks

**Task 2.1: Implement security subsystem**
- Approvals system (`approvals.json` + CLI)
- Sandbox configuration per tool (network, workspace access)
- `SecretRedactor` for log filtering
- `SecretsProvider` abstraction
- Policy engine: load `POLICY.json`, enforce invariants at gateway level
- `openeinstein scan` command (config + SKILL.md + MCP manifest scanning)
- MCP metadata hash pinning

**Integration contract:** Used by gateway (hook-based enforcement), all tool calls, all logging.

**Acceptance criteria:** Approval-required tool call is blocked without approval, allowed with approval. Secret is redacted in logs. Policy violation is caught. `openeinstein scan` flags a test risky pattern. `pytest tests/unit/test_security.py` passes.

**Task 2.2: Implement hook system**
- Hook registration from YAML config
- Hook dispatch at all hook points (see §6.1)
- Built-in hooks: audit logger, approval gate
- Hook error handling (hook failure should not crash campaign)

**Integration contract:** Used by gateway. Security enforcement is implemented as hooks.

**Acceptance criteria:** `before_tool_call` hook can block a tool call. `after_tool_call` hook logs call details. `campaign_state_transition` hook fires on state change. `pytest tests/unit/test_hooks.py` passes.

**Task 2.3: Implement skill registry and base agent abstractions**
- Skill registry: discover skills from filesystem, load metadata, progressive disclosure
- Skill protocol: `SkillMetadata`, `SkillInstructions`, `SkillResources` Pydantic models
- `OpenEinsteinAgent` base class wrapping PydanticAI
- Tool binding (from tool bus)
- Model role binding (from model router)
- Structured output schemas
- Bootstrap context injection (PERSONALITY.md, TOOLS.md, POLICY reference)
- Bootstrap context budget: per-file max chars, total cap, `context report` command
- Sub-agent bootstrap filtering (minimal context for sub-agents)

**Integration contract:**
- Depends on: Task 1.1, 1.2, 1.4, 2.1, 2.2
- Depended on by: Tasks 2.4-2.7

**Acceptance criteria:** Skill registry discovers test skills. A trivial test agent runs. Bootstrap context respects token caps. `context report` shows breakdown. `pytest tests/unit/test_skills.py && pytest tests/unit/test_agent_base.py` passes. `mypy src/openeinstein/core/` passes.

**Task 2.4: Implement orchestrator agent**
- Campaign strategy management
- Task delegation to subagents
- Result aggregation and synthesis
- Adaptive sampling logic
- Human communication (progress reports, pause/resume)
- Compaction subsystem: automatic context summarization, policy invariant re-injection

**Integration contract:** Spawns computation, literature, and verification agents. Reads/writes campaign state.

**Acceptance criteria:** Orchestrator runs a mock campaign with stub subagents. State transitions are correct. Compaction fires and preserves policy invariants. `pytest tests/unit/test_orchestrator.py` passes.

**Task 2.5: Implement computation agent** ∥
- CAS tool calling (via tool bus)
- Template filling logic
- Gate check execution
- Result parsing and structured output
- Timeout handling and fallback strategies

**Integration contract:** Spawned by orchestrator. Calls CAS tools. Writes results to campaign registry.

**Acceptance criteria:** Computation agent processes a mock candidate through all gates with mock CAS responses. `pytest tests/unit/test_computation_agent.py` passes.

**Task 2.6: Implement literature agent** ∥
- Multi-source literature search (arXiv, S2, INSPIRE, ADS, CrossRef, Zotero, GROBID)
- Query formulation from candidate properties
- Result deduplication and ranking
- Local knowledge base caching
- Citation chain following
- BibTeX generation

**Integration contract:** Spawned by orchestrator. Calls literature tools. Writes findings to campaign registry.

**Acceptance criteria:** Literature agent processes a query, searches across multiple sources, returns structured results with BibTeX. `pytest tests/unit/test_literature_agent.py` passes.

**Task 2.7: Implement verification agent** ∥
- Fresh-context derivation auditing
- Cross-check computations against known results
- Consistency checking across candidate results
- Flag potential issues for human review

**Integration contract:** Spawned by orchestrator. Read-only access to campaign registry and derivation files.

**Acceptance criteria:** Verification agent reviews mock results and correctly identifies a planted inconsistency. `pytest tests/unit/test_verification_agent.py` passes.

---

### Phase 3: CAS + Numerical Tools

**Task 3.1: Implement SymPy MCP server (always available)**
- Pure Python — no external dependencies
- Capabilities: `symbolic_simplify`, `vary_action`, `solve_system`, `export_latex`
- Session management

**Integration contract:** Connected via tool bus. Provides baseline CAS capability for all campaigns.

**Acceptance criteria:** Server starts, evaluates basic symbolic expressions, handles sessions. `pytest tests/integration/test_sympy_mcp.py` passes.

**Task 3.2: Implement Mathematica MCP server** ∥
- Wolfram Kernel subprocess management
- Session journaling for crash recovery
- All tools from §8.1
- xAct package loading and verification
- Timeout per computation with graceful kill

**Integration contract:** Connected via tool bus. Exposes full CAS backend interface.

**Acceptance criteria:** Server starts, connects to Wolfram Kernel, evaluates `1+1`, handles crash recovery. `pytest tests/integration/test_mathematica_mcp.py` passes (skip in CI if unavailable).

**Task 3.3: Implement Cadabra MCP server** ∥
- Cadabra subprocess management
- Capabilities: `tensor_simplify`, `vary_action`, `perturbation_expansion`, `export_latex`

**Integration contract:** Same interface as other CAS backends.

**Acceptance criteria:** Server starts, evaluates a tensor expression. `pytest tests/integration/test_cadabra_mcp.py` passes (skip if unavailable).

**Task 3.4: Implement CAS template infrastructure**
- Template registry: discover templates from `templates/` directory
- Template validation: verify `{{PLACEHOLDER}}` slots, verify syntax
- Template filling: candidate parameters → executable CAS code
- Template versioning
- Multi-backend templates (same logical template, different CAS backends)

**Integration contract:** Used by CAS servers and campaign skills.

**Acceptance criteria:** Template discovery, filling, and validation work correctly. `pytest tests/unit/test_templates.py` passes.

**Task 3.5: Implement Parameter Scanner MCP server** ∥
- Grid scan and adaptive scan
- NumPy/SciPy backend
- Tools: `scan_grid`, `scan_adaptive`, `find_boundary`
- Visualization output

**Acceptance criteria:** Scanner correctly identifies viable region for a known test function. `pytest tests/integration/test_scanner_mcp.py` passes.

**Task 3.6: Implement sandboxed Python runner MCP server** ∥
- SciPy, NumPy, matplotlib available in sandbox
- `network: none`, workspace-scoped filesystem
- Tools: `run_script`, `optimize`, `monte_carlo`, `plot`
- No `subprocess`, `os.system`, or `importlib` from untrusted input

**Acceptance criteria:** Script execution works. Sandbox prevents network access and forbidden imports. `pytest tests/integration/test_python_sandbox.py` passes.

---

### Phase 4: Literature + Publishing Tools

**Task 4.1: Integrate arXiv MCP server**
- Install and configure `blazickjp/arxiv-mcp-server`
- Integration test with tool bus

**Acceptance criteria:** Search returns results. Paper download works. `pytest tests/integration/test_arxiv_mcp.py` passes.

**Task 4.2: Integrate Semantic Scholar MCP** ∥

**Task 4.3: Implement INSPIRE-HEP connector** ∥
- REST API wrapper (CLI+JSON or thin MCP)
- Search, author lookup, citation export

**Task 4.4: Implement NASA ADS connector** ∥
- REST API wrapper
- Search, citation metrics

**Task 4.5: Integrate CrossRef MCP** ∥
- DOI resolution, metadata normalization

**Task 4.6: Implement Zotero integration** ∥
- Web API v3 wrapper
- Library sync, collection export, BibTeX generation

**Task 4.7: Implement GROBID PDF ingestion** ∥
- CLI+JSON wrapper for GROBID REST API
- PDF → metadata + references + clean text
- Docker container management (start/stop GROBID service)

**Task 4.8: Implement LaTeX publishing toolchain**
- `latexmk` wrapper
- BibTeX/BibLaTeX generation from literature sources
- Preprint skeleton generator skill
- `openeinstein latex` CLI commands

**Acceptance criteria for all:** Each tool returns structured results. Integration tests pass.

---

### Phase 5: Campaign Engine

**Task 5.1: Implement campaign config loader**
- YAML parsing with Pydantic validation
- Campaign Pack discovery and loading
- CAS capability requirement resolution
- Skill reference resolution
- Tool dependency checking

**Acceptance criteria:** Valid config loads. Invalid configs produce clear errors. Campaign Pack loading works.

**Task 5.2: Implement campaign state machine**
- State transitions (see §12.3)
- Checkpoint/resume logic
- State persistence to SQLite
- Event logging to control plane
- Idempotency key generation and enforcement

**Acceptance criteria:** State machine transitions correctly. Crash simulation: kill mid-campaign, restart, resume. `pytest tests/unit/test_campaign_state.py` passes.

**Task 5.3: Implement gate pipeline runner**
- Sequential gate execution per candidate
- Failure classification and logging
- Timeout enforcement
- Batch processing support
- CAS capability routing (select backend per gate)

**Acceptance criteria:** Pipeline processes candidates through gates, handles failures, enforces timeouts.

**Task 5.4: Implement adaptive sampling engine**
- Failure pattern analysis
- Search space prioritization heuristics
- Candidate reordering

**Acceptance criteria:** Given mock failures, produces sensible reordering.

---

### Phase 6: CLI and Reports

**Task 6.1: Implement CLI**
```
openeinstein init                    # Initialize workspace
openeinstein run <campaign>          # Start/resume campaign
openeinstein run status/wait/stop/resume
openeinstein run events              # Stream events
openeinstein results                 # Candidate summary
openeinstein export                  # Export results
openeinstein config                  # Show/validate config
openeinstein eval run/list/results   # Eval commands
openeinstein trace list/export       # Trace commands
openeinstein context report          # Bootstrap context breakdown
openeinstein approvals list/grant/revoke/reset
openeinstein sandbox explain         # Diagnose sandbox blocks
openeinstein scan                    # Security scan
openeinstein pack install/list       # Campaign Pack management
openeinstein latex build/clean/skeleton
```

**Acceptance criteria:** All commands work with a test campaign. `--help` shows documentation.

**Task 6.2: Implement report generation** ∥
- Results synthesis skill
- Markdown report with candidate comparison table
- Failure analysis section
- Recommended candidates with reasoning
- Open questions for human review
- LaTeX export (optional)

**Acceptance criteria:** Report generated from mock campaign data is complete and readable.

---

### Phase 7: First Campaign Pack + Integration Testing

**Task 7.1: Write the first Campaign Pack**
- `campaign-packs/modified-gravity-action-search/`
- Campaign config, skills, templates, evals, docs, literature seed
- All CAS templates (Mathematica primary, SymPy fallback where possible)

**Acceptance criteria:** Campaign Pack installs. Config validates. Dry-run with mock CAS completes.

**Task 7.2: End-to-end campaign test with known models**
- Run a mini-campaign on 5-10 known physics models
- Verify all expected results

**Acceptance criteria:** All known models produce correct results. Zero false positives/negatives.

**Task 7.3: Crash recovery test** ∥
- Simulate crashes at every campaign state
- Verify clean resume and no data corruption

**Task 7.4: Multi-provider model routing test** ∥
- Run the same mini-campaign with different provider configurations
- Verify results are functionally equivalent

**Task 7.5: Persona eval suite** ∥
- Run persona evals (§14.4)
- Verify uncertainty calibration, citation behavior, refusal boundaries

**Task 7.6: Security audit** ∥
- Run `openeinstein scan` on all configs and Campaign Packs
- Verify approvals block unauthorized tool calls
- Verify sandbox prevents unauthorized access
- Verify `POLICY.json` invariants survive compaction

**Task 7.7: Documentation and packaging**
- Complete README with quickstart guide
- Configuration reference
- Campaign Pack authoring guide
- PyPI packaging (`pip install openeinstein`)
- Docker image (optional)

**Acceptance criteria:** `pip install openeinstein` from clean environment succeeds. Quickstart works end-to-end.

---

## 20. Example Campaign Packs

### 20.1 Modified Gravity Action Search (First Pack)

The first real Campaign Pack targets the covariant action search defined in the original architecture document. Skills: action taxonomy generator, cosmological reduction, perturbation analysis, stability analysis, literature cross-reference. CAS templates for Mathematica (primary) and SymPy (subset).

### 20.2 Stability & Parameter Scan (Generic)

Scan a parameter space in any theory, classify stability regions, produce phase diagrams. Skills: parameter space definition, stability check (generic), boundary finder, plot generator. No theory-specific code in skills — theory enters through campaign config.

### 20.3 Literature Mapping (Generic)

Build a structured taxonomy of papers on any topic. Skills: taxonomy builder, key-result extractor, open-problems identifier, BibTeX generator. Output: structured report + BibTeX file + knowledge graph entries.

---

## 21. Risk Assessment

### 21.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| PydanticAI MCP integration has edge cases | Medium | Medium | Abstraction layer; swap to OpenAI Agents SDK if needed |
| LiteLLM adds latency | Low | Low | Measure overhead. Direct calls with thin wrapper if unacceptable |
| CAS computations exceed timeout | Medium | Medium | Fallback: component-level computation. Flag for manual review |
| CAS kernel crashes | Medium | Low | Session journaling + restart + retry |
| Literature API rate limits | Medium | Low | Local caching. Batch queries. Respect limits |
| Multi-agent coordination overhead | Low-Medium | Medium | Configurable single-agent mode. Measure and compare |
| Compaction loses critical context | Medium | High | Policy invariants enforced outside LLM context. Hook-based verification |
| MCP tool poisoning / prompt injection | Low-Medium | High | Metadata pinning, sanitization, `openeinstein scan`, policy engine |

### 21.2 Physics Risks

- No candidates survive all gates (informative null result — still publishable)
- Cosmological reduction is necessary but not sufficient (human evaluation essential)
- The coincident gauge issue invalidates certain action classes (encode as explicit check)
- The memory field might not be a scalar (redirects to tensor/multi-field extensions)

### 21.3 Build Risks (AI Coding Specific)

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| AI coding agent produces disconnected code | Medium | High | Integration contracts in every feature plan |
| Unit tests pass but integration fails | Medium | Medium | Full E2E test suite at every phase boundary |
| Context loss across long build sessions | Medium | Medium | Canonical docs updated after each phase. Checkpoint commits |
| Build plan drift from architectural intent | Low-Medium | High | Fresh-context validation at steps 3, 4, 6 of every dev loop |
| Dependency version conflicts | Low | Low | Pin all dependencies. Lockfiles. Clean environment tests |

---

## 22. Cost Estimates

### 22.1 Build Costs (One-Time)

| Item | Estimated Cost | Notes |
|------|---------------|-------|
| LLM API calls for AI coding agents | $300-800 | Expanded scope vs. v2 |
| LLM API calls for testing/validation | $50-150 | Integration tests, E2E, evals |
| **Total build cost** | **$350-950** | |

### 22.2 Per-Campaign Costs (Recurring)

| Item | Cost | Notes |
|------|------|-------|
| Mathematica license | $185-350/yr | Academic vs. standard. SymPy/Cadabra are free |
| LLM API calls (reasoning) | $50-200/campaign | Model-dependent. Configurable budget cap |
| LLM API calls (generation) | $20-80/campaign | Routine orchestration, template filling |
| Literature API calls | $0-20/campaign | Semantic Scholar has free tier. arXiv, INSPIRE, ADS are free |
| Local compute | $0 | Laptop sufficient for first campaigns |
| **Total per campaign** | **$70-650** | Range depends on CAS license and model choices |

---

## 23. Success Criteria

### 23.1 Platform Success

The OpenEinstein platform is successful if:
1. `pip install openeinstein` works from PyPI
2. A physicist can configure a new campaign by writing a Campaign Pack (no platform code changes)
3. The platform works with at least 3 different LLM providers (Anthropic, OpenAI, and one more)
4. Campaign state survives process crashes and resumes cleanly
5. `openeinstein eval` runs and reports results for skill, campaign, and persona evals
6. `openeinstein scan` detects known risky patterns
7. The first Campaign Pack runs end-to-end

### 23.2 First Campaign Pack Success

1. ≥1 viable candidate action passing all gates with documented derivation (or a documented null result)
2. A classified failure map of excluded action space regions
3. Complete CAS notebooks for every candidate (pass or fail)
4. A next-steps document for human collaborators

The campaign is informative even if no candidates survive — a systematic null result narrows the theoretical space and is itself a publishable finding.

---

## 24. PM Decision Register

*Decisions the PM should drive so engineering doesn't thrash.*

### 24.1 Core vs. First-Class Plugins

| Component | Proposed: Core | Proposed: First-Class Plugin |
|-----------|---------------|----------------------------|
| Gateway + control plane | ✓ | |
| Registry + state | ✓ | |
| Security + approvals + sandbox | ✓ | |
| Tracing + evals | ✓ | |
| Model routing + tool bus | ✓ | |
| Python/SymPy CAS | ✓ | |
| arXiv MCP | ✓ | |
| Semantic Scholar MCP | ✓ | |
| Mathematica CAS | | ✓ |
| Cadabra CAS | | ✓ |
| INSPIRE-HEP | | ✓ |
| NASA ADS | | ✓ |
| CrossRef | | ✓ |
| Zotero | | ✓ |
| GROBID | | ✓ |
| LaTeX toolchain | | ✓ |
| Python sandbox (sandboxed runner) | ✓ | |

### 24.2 Sandboxing Dependency

Docker is recommended but optional for sandboxing compute tools. Define a minimum "secure default" profile that works without Docker (process isolation + filesystem restrictions).

### 24.3 Policy Defaults

Default-deny for all risky tools. Approvals required for: shell execution, network fetches from tools, filesystem writes outside workspace, package installs. Users opt in explicitly.

### 24.4 Persona Governance

- Who can change the canonical persona: core maintainers only (requires PR review)
- What evals must pass before persona change is merged: all persona evals (§14.4)
- Versioning: persona file is versioned and its hash is stored in every run manifest

---

## Appendix A: Key Dependencies

```toml
[project]
name = "openeinstein"
requires-python = ">=3.12"
dependencies = [
    "pydantic>=2.0",
    "pydantic-ai>=0.1",
    "litellm>=1.0",
    "mcp>=1.0",
    "typer>=0.12",
    "rich>=13.0",
    "pyyaml>=6.0",
    "sqlalchemy>=2.0",
    "numpy>=1.26",
    "scipy>=1.12",
    "matplotlib>=3.8",
    "sympy>=1.12",
    "opentelemetry-api>=1.20",
]

[project.optional-dependencies]
langgraph = ["langgraph>=0.2"]
pgvector = ["pgvector>=0.3", "psycopg2-binary>=2.9"]
physbert = ["transformers>=4.40", "torch>=2.2"]
cadabra = []  # system dependency, runtime discovered via cadabra2 CLI
jax = ["jax>=0.4", "jaxlib>=0.4"]
latex = ["latexmk"]  # system dependency, marker only
```

## Appendix B: References

**Architecture and design:**
- Agent best practices: `Agent-Best-Practices.md` — Agent architecture patterns and infrastructure
- AI coding best practices: `AI-Coding-Best-Practices.md` — Development methodology for AI-built systems
- PydanticAI docs: https://ai.pydantic.dev/
- LiteLLM docs: https://docs.litellm.ai/
- MCP SDK: https://github.com/modelcontextprotocol/python-sdk
- Anthropic multi-agent research system: https://www.anthropic.com/engineering/multi-agent-research-system

**OpenClaw references:**
- SOUL.md template: https://docs.openclaw.ai/reference/templates/SOUL
- System prompt bootstrap: https://docs.openclaw.ai/concepts/system-prompt
- Hooks system: https://docs.openclaw.ai/automation/hooks
- Security overview: https://docs.openclaw.ai/gateway/security
- Sandboxing: https://docs.openclaw.ai/gateway/sandboxing
- Approvals CLI: https://docs.openclaw.ai/cli/approvals

**Literature tools:**
- arXiv MCP: https://github.com/blazickjp/arxiv-mcp-server
- Semantic Scholar MCP: https://github.com/FujishigeTemma/semantic-scholar-mcp
- CrossRef MCP: https://github.com/botanicastudios/crossref-mcp
- INSPIRE REST API: https://github.com/inspirehep/rest-api-doc
- NASA ADS: https://science.nasa.gov/astrophysics/data/smithsonian-nasa-astrophysics-data-system-ads/
- Zotero Web API: https://www.zotero.org/support/dev/web_api/v3/basics
- GROBID: https://grobid.org/

**Physics tools:**
- SymPy: https://sympy.org/
- Cadabra: https://cadabra.science/
- Semantic Scholar API: https://www.semanticscholar.org/product/api

**2026 agent security:**
- OpenAI — skill evals (Jan 2026): https://developers.openai.com/blog/eval-skills
- OpenAI — long-running agents (Feb 2026): https://developers.openai.com/blog/skills-shell-tips
- Mend — config scanning for agents (Feb 2026): https://www.mend.io/blog/ai-agent-configuration-scanning/
- Descope — MCP tool poisoning (Jan 2026): https://www.descope.com/learn/post/mcp-tool-poisoning
- Arize — agent observability (Feb 2026): https://arize.com/blog/add-observability-to-your-open-agent-spec-agents-with-arize-phoenix/
