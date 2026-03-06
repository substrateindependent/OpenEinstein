# OpenClaw Technical Architecture Research Note (as of March 3, 2026)

## Abstract

OpenClaw is a self-hosted “gateway + agent runtime” system that lets you run a persistent personal AI assistant on infrastructure you control, while interacting through chat apps you already use (WhatsApp, Telegram, Slack, Discord, iMessage via integrations, etc.). Its architectural differentiators are not “an LLM loop” (lots of projects have that), but a **durable control plane (Gateway)**, **transport normalization (Channels)**, **explicit session + memory persistence**, **proactivity via Heartbeat/Cron**, and a **file- and directory-based extensibility model (Skills/Hooks/Plugins)**—all wrapped in a typed protocol with pairing and security affordances. ([OpenClaw][1])

This document is written as a reference for teams building personal-assistant-style agents (local-first or self-hosted) and focuses on the design choices that make OpenClaw feel like a productized “agent OS,” including tradeoffs and security implications.

---

## 1) What OpenClaw is (and why people care)

**OpenClaw is a single long-lived Gateway process** that connects multiple chat channels to an agent runtime (derived from Pi/pi-mono), exposing the assistant through messaging surfaces rather than a bespoke UI. It is open-source (MIT) and runs cross-platform. ([OpenClaw][1])

### Context / adoption snapshot

OpenClaw’s rapid adoption is unusual even for OSS. As of **March 3, 2026**, the main repository shows ~**253k stars** and ~**48.5k forks**. ([GitHub][2])

The project’s creator, **Peter Steinberger**, is widely reported as joining OpenAI, with OpenClaw continuing under a foundation model rather than being “closed up.” ([Reuters][3])

---

## 2) Glossary (terms people throw around)

* **Gateway**: the control-plane daemon; the source of truth for sessions, routing, and channel connections. ([OpenClaw][4])
* **Channel adapter**: a transport integration (Telegram/Discord/Slack/WhatsApp, etc.) that normalizes inbound messages and enforces routing policies and queue modes. ([OpenClaw][5])
* **Agent loop**: the deterministic pipeline from inbound message → context assembly → model/tool loop → streaming/delivery → persistence. ([OpenClaw][6])
* **Harness**: the runtime wrapper around the agent loop (OpenClaw-native embedded Pi session) or an external runtime driven via ACP sessions. ([OpenClaw][7])
* **Heartbeat**: periodic “agent turns” to create proactivity with noise controls (`HEARTBEAT_OK`, active hours, delivery rules). ([OpenClaw][8])
* **Cron jobs**: precise scheduling in the Gateway, running either as main-session system events or isolated runs (`cron:<jobId>`). ([OpenClaw][9])
* **Hooks / Webhooks**: event-driven automation triggered by commands/lifecycle events (hooks) or external HTTP triggers (webhooks). ([OpenClaw][10])
* **Skills**: capability packs (folders with `SKILL.md`) that teach the agent how to use tools/APIs; load-time gating and precedence rules. ([OpenClaw][11])
* **Nodes**: paired devices that provide capability surfaces (camera/screen/location/canvas/browser relay, etc.) to the Gateway. ([OpenClaw][4])
* **Lane queue / command queue**: per-session serialization + global concurrency caps; queue modes like `collect`, `steer`, `followup`. ([OpenClaw][12])

---

## 3) High-level architecture: “control plane” vs “data plane”

### 3.1 Conceptual diagram

```
            ┌───────────────────────────────────────────────────┐
            │                    Clients                         │
            │  macOS app / CLI / Web Control UI (WS)             │
            └───────────────┬───────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────────────┐
│                           Gateway (Control Plane)                  │
│  - WS protocol, pairing, device identity, auth                     │
│  - Channel connections + routing + policy                          │
│  - Sessions source of truth                                        │
│  - Schedulers: Heartbeat + Cron                                    │
│  - Automation: Hooks/Webhooks                                      │
└───────────────┬───────────────────────────┬────────────────────────┘
                │                           │
                │                           │ (WS, role=node)
                ▼                           ▼
      ┌───────────────────┐       ┌───────────────────────────┐
      │ Agent Runtime(s)  │       │ Nodes (Capability Providers)│
      │ - Embedded Pi     │       │ - canvas/camera/screen/etc. │
      │ - Subagents       │       └───────────────────────────┘
      │ - ACP sessions    │
      └─────────┬─────────┘
                ▼
         Tools / Skills / Plugins
         (policy + sandboxing + logging)
```

OpenClaw’s key move is making the Gateway the **durable broker** for *everything* that needs to be consistent: routing, session keys, device trust, concurrency, and delivery invariants. The agent runtime then becomes a replaceable “engine” behind this interface. ([OpenClaw][4])

---

## 4) The Gateway: protocol-first control plane

### 4.1 Single source of truth

OpenClaw explicitly treats the Gateway as the system’s authority for session state; UIs and clients are expected to query the Gateway rather than reading local files. ([OpenClaw][13])

### 4.2 WebSocket protocol, pairing, and device identity

Key protocol properties (important if you’re building something similar):

* **Handshake invariants**: the first WS frame must be `connect`; non-JSON or non-connect-first closes the socket. ([OpenClaw][4])
* **Challenge signing**: clients must sign a `connect.challenge` nonce; signature payload binds device metadata, and paired metadata is pinned on reconnect. ([OpenClaw][4])
* **Pairing approvals**: new device IDs require approval; a device token is issued for future connects (with local-trust shortcuts for same-host UX). ([OpenClaw][4])

### 4.3 Typed schemas + code generation

OpenClaw defines protocol frames with TypeBox schemas, generates JSON Schema, and uses that for client codegen (including Swift models). This is a major contributor to “ecosystem coherence” across CLI/mac app/web UI. ([OpenClaw][4])

### 4.4 Idempotency keys (reliability under retries)

Side-effecting methods (notably `send` and `agent`) require idempotency keys so retries don’t duplicate actions; the Gateway maintains a short-lived dedupe cache. This is a small detail that dramatically reduces “agents sent that twice” problems in the wild. ([OpenClaw][4])

### 4.5 Remote access model

Docs recommend remote connectivity via Tailscale/VPN or SSH tunnels; the same handshake and auth requirements apply. ([OpenClaw][4])

---

## 5) Channels: transport normalization + routing + policy

Channel adapters solve: message shape differences, media handling, auth models, rate limits, presence/typing semantics, and “when should the agent respond?” policies (mentions, allowlists, group policies, etc.). ([OpenClaw][5])

A key architectural stance: **routing and delivery are deterministic** based on transport/session policy—*not* “whatever the model decides.” That is essential for safety and debugging in multi-channel systems.

---

## 6) Sessions: isolation, continuity, and secure DM mode

### 6.1 Default “main DM session” for continuity

By default, OpenClaw collapses all DMs into a single “main” session (`dmScope: "main"`) for continuity. ([OpenClaw][13])

### 6.2 Secure DM mode (critical for multi-user exposure)

If your agent can receive DMs from multiple people, docs strongly recommend isolating DM context per sender by setting `session.dmScope: "per-channel-peer"` (or `per-account-channel-peer` for multi-account setups). ([OpenClaw][13])

OpenClaw also supports `session.identityLinks` to collapse identities across channels when you *do* want “same person, same session” semantics. ([OpenClaw][13])

### 6.3 Session key patterns

Group/channel chats get distinct keys; special sources like cron/hook/node use their own key namespaces (`cron:<jobId>`, `hook:<uuid>`, etc.). ([OpenClaw][13])

**Design lesson:** In agent systems, “session key policy” is a security primitive, not just a UX detail.

---

## 7) The Agent Runtime + “Harness”

### 7.1 Embedded Pi integration (OpenClaw-native harness)

OpenClaw embeds Pi’s `AgentSession` directly (imports/instantiates) rather than running Pi as a subprocess/RPC service. The docs call out benefits that map neatly to “agent productization” needs: lifecycle control, custom tool injection, per-channel system prompt customization, session persistence/compaction, auth profile rotation, and provider-agnostic model switching. ([OpenClaw][7])

OpenClaw also documents the Pi package dependencies it embeds (useful if you’re chasing reproducibility). ([OpenClaw][7])

### 7.2 External harness via ACP sessions

OpenClaw supports **ACP sessions** to run external coding harnesses (Claude Code, Codex, Gemini CLI, etc.) through an ACP backend plugin. The mental model:

* **Native runtime**: OpenClaw controls tool injection tightly via embedded Pi.
* **ACP runtime**: OpenClaw acts as a control-plane router and streams input/output to a separate ACP-speaking harness. ([OpenClaw][14])

**Design lesson:** treating “runtime” as pluggable lets you keep the control plane stable while swapping execution substrates as the ecosystem evolves.

### 7.3 Sub-agents (OpenClaw-native parallel work)

Sub-agents are background agent runs spawned from a requester session, with their own session keys and a dedicated queue lane (`subagent`) with default concurrency limits (e.g., 8). Tool availability differs from the main agent by default (notably session/system tool restrictions). ([OpenClaw][15])

---

## 8) The Agent Loop: the deterministic pipeline

OpenClaw’s agent loop doc is unusually explicit and worth copying as a pattern:

1. `agent` RPC validates params, resolves session metadata, returns `{runId, acceptedAt}` immediately.
2. `agentCommand` resolves defaults, loads a skills snapshot, calls `runEmbeddedPiAgent`.
3. `runEmbeddedPiAgent` serializes via per-session + global queues, builds the Pi session, streams events, enforces timeouts, returns usage metadata.
4. `subscribeEmbeddedPiSession` bridges Pi events into OpenClaw streams (`assistant`, `tool`, `lifecycle`).
5. `agent.wait` waits server-side for completion states. ([OpenClaw][6])

**Design lesson:** a well-defined run lifecycle with explicit IDs is one of the fastest ways to make agents debuggable.

---

## 9) Concurrency: lane-aware queuing + “queue modes”

OpenClaw serializes runs **per session key** and then also optionally through a **global lane** to cap overall parallelism (defaults like `main=4`, `subagent=8`). ([OpenClaw][12])

Channels can choose “queue modes” that define what happens when new messages arrive mid-run:

* `collect` (default): coalesce queued messages into one follow-up turn
* `steer`: inject into the current run (cancels pending tool calls after a tool boundary)
* `followup`: enqueue for the next turn
* `steer-backlog`: steer now and preserve for follow-up ([OpenClaw][12])

**Design lesson:** “interrupt handling” is not optional in messaging-first agents. Queue modes are an architectural feature.

---

## 10) Workspace + bootstrapping: file-based “identity + memory”

### 10.1 Workspace is the agent’s home (but not a sandbox)

The workspace is the working directory used for file tools and workspace context, separate from `~/.openclaw/` (config/credentials/sessions). Importantly: it’s **default cwd, not a hard sandbox**; absolute paths can reach elsewhere unless sandboxing is enabled. ([OpenClaw][16])

### 10.2 Bootstrap files (persona + operating policy)

OpenClaw uses a set of workspace-root files to define agent identity and behavior:

* `AGENTS.md` (operating instructions + “memory policy”)
* `SOUL.md` (persona/boundaries/tone)
* `TOOLS.md` (tool notes / conventions)
* `IDENTITY.md` (name/vibe/emoji)
* `USER.md` (user profile + address style)
* `HEARTBEAT.md` (optional heartbeat checklist)
* `BOOTSTRAP.md` (first-run ritual; deleted after completion) ([OpenClaw][17])

### 10.3 System prompt injection (token economics matter)

These files are trimmed and injected into context every turn (with caps and truncation behavior); daily memory files under `memory/` are not auto-injected and are accessed on-demand via memory tools. ([OpenClaw][18])

**Design lesson:** file-based “brain scaffolding” is powerful because it’s inspectable, editable, and versionable—*but it has real token/cost tradeoffs*.

---

## 11) Skills, Plugins, and the extensibility model

### 11.1 Skills: folders with `SKILL.md`, not just docs

A skill is a directory containing `SKILL.md` (with YAML frontmatter and instructions), optionally with scripts/resources. Skills are loaded from bundled + managed (`~/.openclaw/skills`) + workspace (`<workspace>/skills`) locations with clear precedence rules (workspace > managed > bundled). ([OpenClaw][11])

### 11.2 ClawHub: public skills registry

ClawHub is a public registry for skills with versioning and metadata; OpenClaw provides CLI flows for install/update/sync. ([OpenClaw][19])

### 11.3 Plugins: ship tools, skills, hooks, and provider auth

Plugins can:

* register hooks at runtime (`api.registerHook`) ([OpenClaw][20])
* ship skills via plugin manifests ([OpenClaw][11])
* register provider auth flows (OAuth, API keys, device code, etc.), integrating with model auth CLI. ([OpenClaw][20])

**Design lesson:** an agent platform needs extensibility at multiple layers: tools, instructions, event automation, and auth.

---

## 12) Proactivity and scheduling: Heartbeat vs Cron

### 12.1 Heartbeat

Heartbeat runs periodic agent turns (default 30m; sometimes 1h depending on auth mode) with a standardized prompt contract:

* read `HEARTBEAT.md` if present
* if nothing needs attention: reply `HEARTBEAT_OK`
* active hours windows can skip heartbeats outside the configured window ([OpenClaw][8])

**Important correction to common summaries:** Heartbeat *is* an agent turn (LLM call) by default. If you want “cheap prechecks,” you implement them via scripts/hooks/cron and only escalate to LLM turns as needed; OpenClaw’s default heartbeat is intentionally broad, not inherently “two-tier.” ([OpenClaw][8])

### 12.2 Cron jobs

Cron runs inside the Gateway and persists under `~/.openclaw/cron/`. There are two execution styles:

* **Main session**: enqueue a system event and run on the next heartbeat (optionally “wake now”).
* **Isolated session**: dedicated agent turn in `cron:<jobId>` with configurable delivery modes (`announce`, `webhook`, `none`). ([OpenClaw][9])

Cron also does deterministic staggering of “top-of-hour” recurring schedules by default (0–5 minutes), which is a small but practical ops detail. ([OpenClaw][21])

---

## 13) Automation: Hooks and Webhooks

### 13.1 Hooks (in-Gateway event automation)

Hooks are discovered from directories (workspace hooks, managed hooks, bundled hooks) with enable/disable via CLI, similar to skills. They trigger on command/lifecycle events (e.g., `/new`, `/reset`, `/stop`, session boundaries), and OpenClaw ships bundled hooks like `session-memory` and `command-logger`. ([OpenClaw][10])

### 13.2 Webhooks (external triggers)

Webhook hooks run isolated agent turns and post summaries back into main sessions; OpenClaw disables request-supplied session key overrides by default and recommends fixed defaults to avoid remote callers steering execution into sensitive sessions. ([OpenClaw][22])

**Design lesson:** event-driven automation is the difference between “agent as chat bot” and “agent as system.”

---

## 14) Memory, transcripts, and compaction

OpenClaw maintains:

* **JSONL transcripts** (audit-style event logs per session)
* **session metadata stores** (`sessions.json` mappings, token counts, etc.)
* **workspace memory files** (`MEMORY.md` and/or `memory.md`, plus daily `memory/YYYY-MM-DD.md` notes) ([OpenClaw][13])

### 14.1 Silent memory flush with `NO_REPLY`

Before compaction, OpenClaw can run a silent “memory flush” turn that instructs the model to write durable notes to disk, using `NO_REPLY` to suppress delivery. ([OpenClaw][23])

**Design lesson:** compaction is not just summarization—it’s an operational regime (token budgeting, silent bookkeeping, write permissions, and retry behavior). ([OpenClaw][24])

---

## 15) Tooling and policy: sandboxing, allow/deny, and “elevated” execution

### 15.1 Workspace vs sandbox

Because the workspace is not a hard sandbox, OpenClaw provides sandbox modes and workspace access controls; when sandboxing is enabled and `workspaceAccess` is not `"rw"`, tools operate inside a sandbox workspace under `~/.openclaw/sandboxes`. ([OpenClaw][16])

### 15.2 Tool profiles and allow/deny

OpenClaw supports tool profiles (`minimal`, `coding`, `messaging`, `full`) and layered allow/deny rules (deny wins). This matters for “least privilege” builds and for restricting risky tools on weaker providers or in shared environments. ([OpenClaw][25])

### 15.3 Browser control + nodes

Browser control can be proxied via a browser relay extension and/or node host when the Gateway is remote; sandbox constraints apply (host control is not free). ([OpenClaw][26])

---

## 16) Security: architectural attack surface and mitigations

OpenClaw’s architecture is powerful precisely because it crosses trust boundaries: it can read messages (often from untrusted senders), access credentials, run code, and write persistent “memory.” Its docs reflect this reality with explicit warnings and security configuration guidance (pairing, allowlists, secure DM mode). ([OpenClaw][27])

### 16.1 Skills supply-chain risk is not hypothetical

The combination of (a) a public skills registry and (b) agentic execution privileges is a classic supply-chain setup—except the payload can be both *code* and *behavioral instruction* in `SKILL.md`.

Several security orgs have published concrete warnings and mitigations:

* Cisco’s AI team highlights skills as a new attack surface and introduced tooling to scan skills for malicious patterns. ([Cisco Blogs][28])
* Microsoft’s security blog argues OpenClaw should be treated as “untrusted code execution,” recommending isolation and credential hygiene. ([Microsoft][29])
* Snyk reports large-scale scanning of agent skills and frames the ecosystem as “npm/PyPI-style supply chain risk,” amplified by agent privileges. ([Snyk][30])

### 16.2 Token-exhaustion / “agent burn” attacks

Academic work has started modeling *token amplification* attacks via Trojanized skills and tool-call loops (e.g., “Clawdrain”), showing multi-turn instructions can induce significantly higher token usage under realistic deployments. ([arXiv][31])

### 16.3 Practical mitigations implied by the architecture

If you’re building a similar system, the mitigations are architectural, not just patch-level:

* treat skill packs as **executable**, not documentation
* implement **signature / provenance / allowlist** rules for installed skills
* separate “read untrusted content” from “take actions” with explicit approval gates
* isolate agent execution environments (VM/sandbox) and rotate credentials aggressively
* enforce session isolation for multi-user messaging surfaces (secure DM mode)
* ensure the Gateway is not exposed as a raw public WS API ([OpenClaw][27])

---

## 17) OpenProse and deterministic workflows (optional but important)

OpenClaw ships **OpenProse**, a markdown-first workflow format that supports explicit control flow and multi-agent orchestration. This matters because many “assistant” workloads benefit from deterministic structure and approvals (e.g., code review, incident triage). ([OpenClaw][32])

**Design lesson:** a purely emergent agent loop is great for ad-hoc tasks; repeatable workflows often want a programmable layer above the loop.

---

## 18) Architectural lessons to steal (generalized)

1. **Make the Gateway a real control plane**
   Single source of truth for routing, sessions, concurrency, and device trust beats “distributed glue code.” ([OpenClaw][4])

2. **Schema-first protocols enable multi-client ecosystems**
   TypeBox → JSON Schema → codegen keeps mac/CLI/web clients aligned and upgradeable. ([OpenClaw][4])

3. **Session keys are a security boundary**
   Default continuity is convenient; secure DM isolation is mandatory for multi-user surfaces. ([OpenClaw][13])

4. **Proactivity needs a contract**
   Heartbeat works because it has quiet-hours, a suppression token (`HEARTBEAT_OK`), and delivery policies; noisy tasks belong in isolated cron sessions. ([OpenClaw][8])

5. **Directory-based extensibility (Skills/Hooks/Plugins) is “ops-friendly”**
   Discovery + precedence + gating + hot reload beats “recompile the agent.” ([OpenClaw][11])

6. **Interrupt handling is core, not polish**
   Lane-aware queues and queue modes (`collect`/`steer`) are what make a chat-native agent usable. ([OpenClaw][12])

7. **Treat agent capability markets as supply chains**
   If “install a skill” is one command, your security model must assume adversaries will publish skills. ([Cisco Blogs][28])

---

## Appendix A: Representative configuration snippets (illustrative)

### Secure DM mode (isolate per channel + sender)

```json5
// ~/.openclaw/openclaw.json
{
  session: {
    dmScope: "per-channel-peer",
  },
}
```

([OpenClaw][13])

### Heartbeat tuning / disable

```json5
{
  agents: {
    defaults: {
      heartbeat: {
        every: "2h", // or "0m" to disable
        // activeHours: { start: "09:00", end: "22:00", tz: "America/New_York" }
      },
    },
  },
}
```

([OpenClaw][8])

### Cron: isolated job with delivery

```bash
openclaw cron add \
  --name "Daily brief" \
  --every "24h" \
  --session isolated \
  --message "Summarize new urgent items and send me a brief." \
  --deliver announce
```

([OpenClaw][9])

### Tool restriction via profiles

```json5
{
  tools: {
    profile: "messaging",
    deny: ["group:runtime"], // e.g., deny exec/process
  },
}
```

([OpenClaw][25])

---

## References (primary)

* OpenClaw official docs (architecture, agent loop, sessions, heartbeat, cron, hooks, skills, security). ([OpenClaw][1])
* OpenClaw repo stats / license. ([GitHub][2])
* Background reporting on project governance + creator. ([Reuters][3])
* Security research and guidance (Cisco, Microsoft, Snyk; plus academic token-exhaustion work). ([Cisco Blogs][28])

[1]: https://docs.openclaw.ai/ "https://docs.openclaw.ai/"
[2]: https://github.com/openclaw/openclaw "https://github.com/openclaw/openclaw"
[3]: https://www.reuters.com/business/openclaw-founder-steinberger-joins-openai-open-source-bot-becomes-foundation-2026-02-15/ "https://www.reuters.com/business/openclaw-founder-steinberger-joins-openai-open-source-bot-becomes-foundation-2026-02-15/"
[4]: https://docs.openclaw.ai/concepts/architecture "https://docs.openclaw.ai/concepts/architecture"
[5]: https://docs.openclaw.ai/cli/channels "https://docs.openclaw.ai/cli/channels"
[6]: https://docs.openclaw.ai/concepts/agent-loop "https://docs.openclaw.ai/concepts/agent-loop"
[7]: https://docs.openclaw.ai/pi "https://docs.openclaw.ai/pi"
[8]: https://docs.openclaw.ai/gateway/heartbeat "https://docs.openclaw.ai/gateway/heartbeat"
[9]: https://docs.openclaw.ai/automation/cron-jobs "https://docs.openclaw.ai/automation/cron-jobs"
[10]: https://docs.openclaw.ai/automation/hooks "https://docs.openclaw.ai/automation/hooks"
[11]: https://docs.openclaw.ai/tools/skills "https://docs.openclaw.ai/tools/skills"
[12]: https://docs.openclaw.ai/concepts/queue "https://docs.openclaw.ai/concepts/queue"
[13]: https://docs.openclaw.ai/concepts/session "https://docs.openclaw.ai/concepts/session"
[14]: https://docs.openclaw.ai/tools/acp-agents "https://docs.openclaw.ai/tools/acp-agents"
[15]: https://docs.openclaw.ai/tools/subagents "https://docs.openclaw.ai/tools/subagents"
[16]: https://docs.openclaw.ai/concepts/agent-workspace "https://docs.openclaw.ai/concepts/agent-workspace"
[17]: https://docs.openclaw.ai/concepts/agent "https://docs.openclaw.ai/concepts/agent"
[18]: https://docs.openclaw.ai/concepts/system-prompt "https://docs.openclaw.ai/concepts/system-prompt"
[19]: https://docs.openclaw.ai/tools/clawhub "https://docs.openclaw.ai/tools/clawhub"
[20]: https://docs.openclaw.ai/tools/plugin "https://docs.openclaw.ai/tools/plugin"
[21]: https://docs.openclaw.ai/automation/cron-vs-heartbeat "https://docs.openclaw.ai/automation/cron-vs-heartbeat"
[22]: https://docs.openclaw.ai/automation/webhook "https://docs.openclaw.ai/automation/webhook"
[23]: https://docs.openclaw.ai/concepts/memory "https://docs.openclaw.ai/concepts/memory"
[24]: https://docs.openclaw.ai/zh-CN/gateway/configuration "https://docs.openclaw.ai/zh-CN/gateway/configuration"
[25]: https://docs.openclaw.ai/tools "https://docs.openclaw.ai/tools"
[26]: https://docs.openclaw.ai/tools/browser "https://docs.openclaw.ai/tools/browser"
[27]: https://docs.openclaw.ai/gateway/security "https://docs.openclaw.ai/gateway/security"
[28]: https://blogs.cisco.com/ai/personal-ai-agents-like-openclaw-are-a-security-nightmare "https://blogs.cisco.com/ai/personal-ai-agents-like-openclaw-are-a-security-nightmare"
[29]: https://www.microsoft.com/en-us/security/blog/2026/02/19/running-openclaw-safely-identity-isolation-runtime-risk/ "https://www.microsoft.com/en-us/security/blog/2026/02/19/running-openclaw-safely-identity-isolation-runtime-risk/"
[30]: https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub/ "https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub/"
[31]: https://arxiv.org/abs/2603.00902 "https://arxiv.org/abs/2603.00902"
[32]: https://docs.openclaw.ai/prose "https://docs.openclaw.ai/prose"
