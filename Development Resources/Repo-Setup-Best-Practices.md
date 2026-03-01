# Repository Setup Best Practices for AI-Agent-Built Applications

**Parent:** [AI-Coding-Best-Practices](AI-Coding-Best-Practices.md)
**Related:** [Development Loop — Full Reference](Development-Loop-Full-Reference.md) · [Project Context Files](Project-Context-Files.md) · [Context Engineering](Context-Engineering.md) · [Canonical Documentation](Canonical-Documentation.md) · [Integration Contracts](Integration-Contracts.md) · [Deterministic Sandwich](Deterministic-Sandwich.md) · [Environment Setup — Full Reference](Environment-Setup-Full-Reference.md)

**Author:** Glenn Clayton, Fieldcrest Ventures
**Version:** 1.0 — February 2026
**Purpose:** Canonical reference for setting up and structuring repositories where AI coding agents are the primary builders. Covers directory structure, context file architecture, documentation layout, quality gates, and the mapping between repo artifacts and the development loop.

---

## What This Document Covers

This document defines how to set up a repository so that AI coding agents can build, extend, and maintain a web application reliably across sessions, across tools, and across time. It is specifically designed for projects where the AI agent handles the majority of implementation — not just autocomplete or copilot-style assistance, but autonomous feature construction guided by the 15-step development loop defined in the [Development Loop — Full Reference](Development-Loop-Full-Reference.md).

The guidance synthesizes three sources: the core principles and development loop from the AI-Coding-Best-Practices vault, production experience from the Pepper project (a vertical-slice monorepo with six feature pillars), and external research on agent context management patterns from teams at Anthropic, HumanLayer, GitHub, and others working with Claude Code, Cursor, Codex, and AGENTS.md-compatible tools through early 2026.

The document is organized in three layers. First, the structural principles that drive every decision — why the repo is shaped the way it is. Second, the concrete directory layout, file conventions, and context file architecture — what goes where. Third, the mapping between repo artifacts and the development loop — how the structure supports the 15-step pipeline from research through shipping.

---

## Part 1: Structural Principles

### The Repo Is the Communication Layer

In traditional development, the repository stores code. In AI-agent-built applications, the repository is the primary communication layer — not between humans and AI, but between AI sessions across time. Every future agent session starts from cold. It has no memory of what the last session did, what decisions were made, or what traps to avoid. The repo is the only thing that persists.

This shifts what belongs in a repo. Code is necessary but not sufficient. The repo must also contain the institutional memory that lets any agent session pick up where the last one left off: what was built (canonical documentation), how things connect (integration contracts), what was decided and why (architecture decision records), what went wrong and how to avoid it (living error logs), and what comes next (development plans and build plans).

The Thoughtworks SDD research found that teams using written specifications as primary artifacts experience 70% less rework. In agent-built applications, this compounds — each feature builds on documented understanding from previous sessions. Without durable documentation, every session starts from scratch, and the 70% rework penalty applies to every feature, not just the first.

### Vertical Slices Over Horizontal Layers

Code should be organized by domain feature, not by technical layer. A "vertical slice" architecture groups everything needed to understand and modify a domain — business logic, types, database queries, API handlers, background workers, AI prompts, and UI components — into one directory tree.

This matters for agents because it minimizes the context they need to load. An agent working on email classification loads `features/email/` and gets everything relevant. In a horizontal-layer architecture (`components/`, `lib/`, `api/`, `db/`), the same task requires reading across four directories, loading irrelevant code from other domains at each level. The token cost is higher, the signal-to-noise ratio is worse, and cross-feature contamination is more likely.

The vertical slice pattern also makes cross-domain dependencies explicit. Each feature exports a public API via `index.ts`. Imports between features go through this file — never into internal subdirectories. When an agent sees `import { getEmailById } from '@/features/email'`, the dependency is visible. When it sees `import { getEmailById } from '@/lib/db/emails'`, the dependency is invisible — any domain could be importing from any database file, and the coupling is impossible to reason about without reading every import in the project.

### Thin Shared Layer

The `shared/` directory contains only code that is genuinely used across all or most features — database client singletons, authentication, API client configuration, error handling utilities, and shared type definitions. If something is only used by two features, it stays in those features (one imports from the other via its public API). The shared layer must stay small and stable because every feature depends on it, and changes to shared code create a blast radius across the entire application.

### Thin Routing Layer

In Next.js projects, the App Router forces routes into the `app/` directory, but route files should be thin wrappers — typically under 15 lines — that delegate to feature logic. The `app/` directory handles routing and page composition. The `features/` directory handles business logic. This separation keeps business logic testable independently of the routing framework, and makes the routing layer swappable without touching domain logic.

### Explicit Public APIs

Each feature directory exports a public API via `index.ts`. Cross-feature imports go through this file — never into a feature's internal subdirectories. This gives AI agents a clear contract to work against: the `index.ts` is the definition of what a feature makes available to the rest of the application.

```typescript
// features/email/index.ts — Public API
export type { ClassificationResult, EmailSummary } from './types';
export { getEmailById, getRecentThreadsForContact } from './db/emails';
export { getClassificationForEmail } from './db/classifications';
export { CONFIDENCE } from './constants';
```

Cross-feature imports must go through this file:

```typescript
// ✅ CORRECT — import through public API
import { getRecentThreadsForContact } from '@/features/email';

// ❌ WRONG — reaching into internal implementation
import { getRecentThreadsForContact } from '@/features/email/db/emails';
```

### Hierarchical AI Context

Context files (CLAUDE.md, AGENTS.md, and tool-specific rule files) are placed at the root and within each feature directory. AI tools automatically load the relevant context files based on which directory they're working in. This provides focused, domain-specific context without loading the entire codebase's conventions into every session.

The key insight from HumanLayer and the GitHub analysis of 2,500+ repositories: keep context files lean. The root CLAUDE.md should be a map, not a manual — under 300 lines. Feature-level context files should stay under 200 lines. Deep reference content belongs in dedicated documentation files that context files point to but don't duplicate. This is the progressive disclosure pattern: the agent loads what it needs for the current scope, with pointers to deeper content if it needs to go further.

A critical anti-pattern identified by AI Hero: don't document file paths in context files. File paths change constantly as the codebase evolves, and stale paths in context files poison the agent's understanding. Instead, document capabilities and domain concepts. Let the agent discover current file paths through the file system.

### Aligned with the Development Loop

The directory structure must reinforce the development loop. Every artifact the 15-step pipeline produces — research docs, epic plans, build plans, implementation code, post-build documentation, audit reports, context file updates — needs a defined home in the repo. If an artifact doesn't have a home, it gets lost. If it gets lost, the next session can't find it, and institutional memory degrades.

This is the principle from the parent guide: "If it's not durable and visible, it doesn't exist."

---

## Part 2: Directory Structure and File Conventions

### The Complete Layout

The following structure represents the target layout for an AI-agent-built monorepo. It is derived from the Pepper project's production structure, generalized for any vertical-slice web application, and annotated with the development loop artifact each directory supports.

```
project-root/
│
├── CLAUDE.md                              # Root AI context (≤300 lines)
├── AGENTS.md                              # Synced with CLAUDE.md for non-Claude tools
├── package.json
├── tsconfig.json
├── vitest.config.ts                       # (or jest.config.ts — unit/integration test runner)
├── playwright.config.ts                   # E2E test runner
├── Dockerfile
│
├── prisma/
│   └── schema.prisma                      # Unified schema — all features, one file
│
├── .cursor/
│   ├── epic_prompt.md                     # Standard prompt template for epic plan generation
│   ├── audit_prompt.md                    # Standard prompt template for post-epic audits
│   ├── rules/                             # Cursor-specific coding rules (one file per topic)
│   │   ├── core.mdc                       #   Core conventions
│   │   ├── typescript.mdc                 #   TypeScript patterns
│   │   ├── database.mdc                   #   Database / ORM patterns
│   │   ├── testing.mdc                    #   Testing conventions
│   │   ├── error-handling.mdc             #   Error handling patterns
│   │   ├── git-workflow.mdc               #   Git commit and branch conventions
│   │   └── [framework-specific].mdc       #   Framework-specific rules (Next.js, React, etc.)
│   └── plans/                             # Build plans generated during Step 5
│       ├── epic_[name].plan.md
│       └── ...
│
├── .claude/
│   ├── settings.json                      # Agent permissions, tool scoping
│   └── agents/                            # Claude Code subagent definitions
│       ├── [feature]-specialist.md        #   One per feature, scoped context + permissions
│       └── ...
│
├── docs/
│   ├── ARCHITECTURE.md                    # System architecture (updated after structural changes)
│   ├── CHANGELOG.md                       # Dated changelog entries
│   ├── EPIC_BUILD_INSTRUCTIONS.md         # Standard instructions appended to every epic handoff
│   │
│   ├── development-plans/                 # ── PLANNING ARTIFACTS (Steps 1-2) ──
│   │   ├── DEVELOPMENT_PLAN.md            #   Master plan: project → epics breakdown
│   │   ├── EPIC_TEMPLATE.md               #   Template for drafting new epics
│   │   ├── EPIC_DRAFTING_INSTRUCTIONS.md  #   Instructions for the epic drafting process
│   │   ├── EPIC-A.md                      #   Individual epic specifications
│   │   ├── EPIC-B.md
│   │   └── ...                            #   Future epics follow same naming pattern
│   │
│   ├── epics/                             # ── POST-BUILD DOCUMENTATION (Step 14) ──
│   │   ├── EPIC-A-[name].md              #   What was actually built (canonical doc)
│   │   ├── EPIC-B-[name].md
│   │   └── ...
│   │
│   ├── audits/                            # ── POST-EPIC AUDIT REPORTS (Step 15) ──
│   │   ├── AUDIT-EPIC-A-[NAME].md
│   │   ├── AUDIT-EPIC-B-[NAME].md
│   │   └── ...
│   │
│   ├── research/                          # ── PRE-BUILD RESEARCH (Step 1) ──
│   │   ├── [Topic]_Research.md
│   │   ├── [Topic]_Spec.md
│   │   └── [Feature Domain]/              #   Subdirectories for larger research areas
│   │       └── ...
│   │
│   ├── decisions/                         # ── ARCHITECTURE DECISION RECORDS ──
│   │   └── ADR-[NNN]-[name].md
│   │
│   └── walkthroughs/                      # ── FEATURE GUIDES AND WALKTHROUGHS ──
│       └── ...
│
├── src/
│   │
│   ├── app/                               # ═══ ROUTING LAYER (THIN WRAPPERS) ═══
│   │   ├── layout.tsx
│   │   ├── error.tsx
│   │   ├── middleware.ts
│   │   ├── api/                           # API routes → delegate to features/
│   │   │   ├── [feature]/                 #   One directory per feature domain
│   │   │   ├── webhooks/                  #   External webhook receivers
│   │   │   └── workers/                   #   Background worker trigger routes
│   │   └── [ui-routes]/                   # UI pages → import from features/
│   │
│   ├── features/                          # ═══ VERTICAL SLICES (CORE OF THE CODEBASE) ═══
│   │   ├── [feature-a]/                   #   Each feature follows identical internal structure
│   │   │   ├── CLAUDE.md                  #     Domain context for agents (≤200 lines)
│   │   │   ├── INTEGRATION.md             #     Cross-feature dependencies and contracts
│   │   │   ├── index.ts                   #     Public API — what other features can import
│   │   │   ├── types.ts                   #     Feature-specific TypeScript types
│   │   │   ├── constants.ts               #     Feature-specific configuration
│   │   │   ├── [subdomain]/               #     Business logic grouped by subdomain
│   │   │   ├── prompts/                   #     AI prompts specific to this feature
│   │   │   ├── db/                        #     Data access layer (ORM queries)
│   │   │   ├── workers/                   #     Background pipeline definitions
│   │   │   └── components/                #     UI components for this feature
│   │   ├── [feature-b]/
│   │   └── ...
│   │
│   ├── shared/                            # ═══ SHARED LAYER (THIN, CROSS-CUTTING) ═══
│   │   ├── ai/                            #   LLM client, model routing, token budgets
│   │   ├── db/                            #   Database client singleton, shared queries
│   │   ├── auth/                          #   Authentication configuration
│   │   ├── queue/                         #   Job queue infrastructure
│   │   ├── types/                         #   Shared type definitions
│   │   ├── constants.ts                   #   Global configuration
│   │   ├── errors.ts                      #   Custom error classes
│   │   └── api-helpers.ts                 #   Response formatting, error handling
│   │
│   └── ui/                                # ═══ SHARED UI PRIMITIVES ═══
│       ├── button.tsx
│       ├── card.tsx
│       └── ...
│
├── __tests__/                             # ═══ TESTS (MIRROR FEATURES STRUCTURE) ═══
│   ├── setup.ts
│   ├── features/
│   │   ├── [feature-a]/                   #   Tests mirror source structure
│   │   └── ...
│   ├── integration/                       #   Cross-feature integration tests
│   └── graduation/                        #   Phase gate tests (epic-level verification)
│
├── e2e/                                   # ═══ END-TO-END TESTS ═══
│   ├── auth.setup.ts
│   └── *.spec.ts
│
└── public/                                # Static assets
```

### Feature Directory Anatomy

Every feature follows the same internal structure. This consistency is what allows AI agents to navigate any feature using the same mental model — the agent doesn't need to learn a new organizational pattern for each domain.

```
features/{feature}/
├── CLAUDE.md              # Domain context for AI agents working in this feature
├── INTEGRATION.md         # Cross-feature dependencies and contracts
├── index.ts               # Public API — what other features can import
├── types.ts               # Feature-specific TypeScript types
├── constants.ts           # Feature-specific configuration values
│
├── {subdomain}/           # Business logic grouped by subdomain
│   └── *.ts               #   Implementation files
│
├── prompts/               # AI prompts specific to this feature
│   └── *.ts               #   System prompts, user prompts, response schemas
│
├── db/                    # Data access layer (ORM queries)
│   └── *.ts               #   CRUD, filtering, stats queries
│
├── workers/               # Background pipeline definitions
│   └── *.ts               #   Queue-triggered worker logic
│
└── components/            # UI components for this feature
    └── *.tsx              #   Client and server components
```

Not every feature will need every subdirectory. A simple feature might have just `index.ts`, `types.ts`, `db/`, and `components/`. The template is the ceiling, not the floor. But when a feature does need prompts, workers, or subdomain groupings, the location is predetermined — the agent doesn't have to decide where to put things.

### File Naming Conventions

Consistent naming eliminates an entire class of agent decisions. These conventions should be documented in the root CLAUDE.md and enforced by linting rules, not by hoping the agent remembers:

- TypeScript files: `kebab-case.ts` (e.g., `classify-email.ts`, `voice-profile.ts`)
- React components: `kebab-case.tsx` (e.g., `classification-feed.tsx`)
- Types files: `types.ts` (one per feature, plus `shared/types/index.ts`)
- Constants files: `constants.ts` (one per feature, plus `shared/constants.ts`)
- Test files: `*.test.ts` or `*.test.tsx` (in `__tests__/`, mirroring source path)
- E2E specs: `*.spec.ts` (in `e2e/`)
- AI context files: `CLAUDE.md`, `INTEGRATION.md` (uppercase, markdown)
- Epic-level documentation: `UPPERCASE-WITH-DASHES.md` (e.g., `EPIC-B-GMAIL-INTEGRATION.md`)

### TypeScript Path Aliases

Configure path aliases so that import statements are clean and consistent across the codebase:

```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./src/*"],
      "@/features/*": ["./src/features/*"],
      "@/shared/*": ["./src/shared/*"],
      "@/ui/*": ["./src/ui/*"]
    }
  }
}
```

This produces imports that are self-documenting:

```typescript
import { getEmailById } from '@/features/email';
import { prisma } from '@/shared/db/prisma';
import { Button } from '@/ui/button';
```

---

## Part 3: AI Agent Context File Architecture

Context files are the operating system for AI-agent-built applications. They determine what the agent knows before it reads a single line of code. Getting them right is the highest-leverage investment in the entire repo setup.

### Root CLAUDE.md (≤300 Lines)

The root CLAUDE.md is the project constitution. Every agent session that touches the repo reads this file. It should contain:

- **Architecture overview** — what kind of project this is, how domains relate to each other, the organizing principle (vertical slices, monorepo, etc.)
- **Tech stack** — frameworks, database, queue system, AI provider, CSS approach. Version numbers matter — they prevent the agent from generating code for outdated APIs.
- **Global conventions** — naming, file organization, import path rules, error handling patterns.
- **Directory map** — brief description of each top-level directory's purpose. Describe capabilities, not file paths (paths change; capabilities don't).
- **Cross-feature rules** — "Import through `index.ts` only. Never reach into another feature's internals."
- **Testing conventions** — test runner, test file locations, how to run tests.
- **Pointer to detailed rules** — "See `.cursor/rules/` for detailed coding conventions" rather than duplicating that content.
- **Living error log** — mistakes the agent has made in past sessions, with the fix. This is how the system learns across sessions.

The 300-line limit is deliberate. HumanLayer's analysis of production CLAUDE.md files found that beyond ~100 lines for simple projects and ~300 lines for complex monorepos, additional content degrades agent performance — the signal gets lost in the noise. The root context file should be a map that points to deeper content, not the deep content itself.

What does NOT belong in root CLAUDE.md: linting rules (use a linter), formatting rules (use Prettier), detailed API documentation (put it in feature CLAUDE.md files or docs/), copy-pasted code examples that could go stale (point to the actual source files instead).

As HumanLayer puts it: "Never send an LLM to do a linter's job." Every rule that can be enforced deterministically should be enforced by a tool, not by spending context window tokens asking the agent to remember it.

#### Living Error Log

The living error log is a section in the root CLAUDE.md (or a dedicated file it points to) that records mistakes the agent has made and the corrective pattern:

```markdown
## Common Mistakes (Living Error Log)
1. Forgot NOT NULL on new DB columns. (Learned: Epic C1)
   Fix: Always specify `nullable: false` explicitly in migrations.
2. Used setTimeout for async coordination. (Learned: Epic C3)
   Fix: Use async/await with proper error boundaries everywhere.
3. Created API route but didn't wire it to the router. (Learned: Epic B)
   Fix: Integration Contract verification must include route registration check.
```

Boris Cherny's Claude Code team reports adding to this log "anytime we see Claude do something incorrectly." For agent-built applications, this is the primary mechanism for cross-session learning. Without it, the agent makes the same mistake in every session.

### Feature-Level CLAUDE.md (≤200 Lines)

Each feature's CLAUDE.md provides domain-specific context for agents working within that feature. It should contain:

- **What this feature does** — one-paragraph summary of the domain.
- **Key entities** — the database models this feature owns (table names, key fields, relationships).
- **State machine** — if the feature has processing states (e.g., `fetched → classifying → classified → error`), document the transitions.
- **API contracts** — key endpoints and their request/response shapes.
- **Cross-feature dependencies** — what this feature imports from other features (via their `index.ts`), and what other features import from this one.
- **Pointer to canonical documentation** — link to the relevant doc in `docs/epics/` or `docs/research/`.
- **Post-build update reminder** — "After completing any work in this feature, update `docs/epics/EPIC-[#]-[name].md` and this CLAUDE.md to reflect what was built."

The 200-line limit keeps feature context focused. If the feature's context is approaching 200 lines, it's a signal that some content should be extracted to a dedicated document in `docs/` and referenced by pointer.

### INTEGRATION.md (Per-Feature)

Each feature's INTEGRATION.md is the durable form of the Integration Contract. It documents the live wiring between features — not what was planned, but what currently exists:

- **Exports** — what this feature makes available via `index.ts` (functions, types, constants).
- **Imports** — what this feature consumes from other features, with the source feature and function name.
- **Shared entities** — database entities this feature reads from or writes to that are owned by other features.
- **Schema dependencies** — ORM model relationships that cross feature boundaries.
- **Worker triggers** — background pipelines in this feature that are triggered by events from other features.

This file is updated in Step 14 of the development loop (commit + update docs) after every epic that modifies cross-feature boundaries. The deep audit in Step 10 must verify that the INTEGRATION.md accurately reflects the code.

### AGENTS.md (Root)

AGENTS.md is the portable, open-standard equivalent of CLAUDE.md. It is read by Cursor, Zed, OpenCode, GitHub Copilot, and other AGENTS.md-compatible tools. Content should be functionally identical to the root CLAUDE.md. When one is updated, update the other.

The reason to maintain both: CLAUDE.md supports Claude Code-specific features (subagent definitions, hook configuration, settings.json references). AGENTS.md is the lowest-common-denominator format that any tool can read. Having both ensures maximum tool compatibility without sacrificing Claude Code's deeper capabilities.

### .cursor/rules/ (Detailed Coding Conventions)

For Cursor-based workflows, detailed coding conventions live in `.cursor/rules/` as individual `.mdc` files — one file per topic (TypeScript patterns, database patterns, testing conventions, etc.). The root CLAUDE.md and AGENTS.md point to these files rather than duplicating their content.

This is the progressive disclosure pattern in action: the root context file gives the agent a high-level map, and the rule files provide deep reference when the agent is working in a specific area. The agent only loads the rules relevant to its current task.

When rules change, update the `.cursor/rules/` files first and ensure the root CLAUDE.md stays consistent.

### .claude/agents/ (Subagent Definitions)

For projects with multiple feature domains, specialized subagent definitions scope the agent's context and permissions when delegating focused work. Each feature gets a subagent definition that specifies:

- **Working directory** — which source and test directories the subagent operates in.
- **Related docs** — which research, epic, and audit documents are relevant.
- **Allowed tools** — read/write permissions, test commands, type-check commands.
- **Constraints** — what the subagent cannot modify (e.g., shared code, other features' internals).

```markdown
# Email Specialist — .claude/agents/email-specialist.md

You are a specialized agent for the Email feature.

## Scope
- Working directory: src/features/email/
- Test directory: __tests__/features/email/
- Related docs: docs/research/Email/, docs/epics/EPIC-B*, EPIC-C*

## Context
Read features/email/CLAUDE.md for domain context before starting work.

## Allowed tools
- Read/write files within features/email/ and __tests__/features/email/
- Read (not write) files in shared/ and other features' index.ts
- Run tests: npm test __tests__/features/email/
- Run typecheck: npx tsc --noEmit

## Constraints
- Do not modify files outside features/email/ without explicit permission
- Do not modify shared/ code — propose changes to the main agent
- Import from other features through their index.ts only
```

These subagent definitions support parallel agent workflows — multiple Claude Code sessions can work on different features simultaneously, each with focused context and scoped access, without stepping on each other's code.

---

## Part 4: Documentation Architecture

Documentation in an agent-built repo serves a fundamentally different purpose than in a human-built one. In a human-built repo, documentation explains the code to humans. In an agent-built repo, documentation is the institutional memory that prevents every session from starting from scratch. The documentation directories are as critical to the build process as the source code directories.

### docs/development-plans/ — Planning Artifacts

This directory holds the pre-build planning artifacts from Phase 1 of the development loop (Steps 1–6).

**DEVELOPMENT_PLAN.md** is the master plan that breaks the entire project into ordered epics. It defines the scope and sequence of the build — which epics exist, what order they should be built in, and what dependencies exist between them. This file is written once during initial project planning and updated when the scope changes.

**EPIC_TEMPLATE.md** and **EPIC_DRAFTING_INSTRUCTIONS.md** standardize how new epics are drafted. The template ensures every epic includes the same sections (overview, requirements, data model changes, integration contract, acceptance criteria). The drafting instructions tell the agent (or human) exactly how to fill out the template. Standardized templates prevent the agent from inventing a new epic structure for every feature.

**Individual epic files** (e.g., `EPIC-B.md`, `EPIC-C1.md`) are the feature specifications drafted in Step 2 of the development loop. Each contains the full specification for one epic: what to build, why, how it integrates with existing code, what data model changes are needed, and what the acceptance criteria are. The Integration Contract section is mandatory — it explicitly specifies every point where new code connects to existing code.

These files are the input to the build plan generation in Step 5. They are the spec that the validation passes in Steps 3–4 validate against. They persist in the repo as the record of what was planned.

### docs/epics/ — Post-Build Canonical Documentation

This directory holds post-build documentation — what was actually built, as opposed to what was planned. These are the canonical documents described in [Canonical Documentation](Canonical-Documentation.md).

After every epic is complete (Step 14), a canonical document is created or updated in this directory. It describes: the implementation approach and rationale, the data model as it was actually built, the integration points that actually exist, edge cases that were discovered during implementation, and explicit decisions about what was and wasn't included.

The distinction between `development-plans/` (what was planned) and `epics/` (what was built) is critical. Plans drift during implementation — scope gets adjusted, edge cases surface, integration points shift. The canonical doc in `epics/` is the authoritative record of the current state. Future agent sessions doing research in Step 1 should read the canonical docs in `epics/`, not the original plans in `development-plans/`.

### docs/audits/ — Post-Epic Audit Reports

This directory holds the audit reports generated after each epic is complete. An audit is a comprehensive review by a fresh-context agent (Step 15 of the development loop) that evaluates the epic against multiple quality dimensions: code quality, integration correctness, test coverage, security, performance, and documentation completeness.

Audit reports serve two purposes. First, they catch issues that slipped through the build process — bugs, integration gaps, documentation gaps. Second, they create a quality record over time. If the same category of issue appears in multiple audit reports, it signals a systematic problem in the development process, and the root CLAUDE.md's living error log should be updated with a corrective pattern.

The audit report template should include: a summary of what was audited, findings organized by category (critical, major, minor), specific file references for each finding, remediation recommendations, and an overall quality assessment.

### docs/research/ — Pre-Build Research Artifacts

This directory holds research artifacts produced during Step 1 of the development loop. Before any epic is drafted, the agent (or human) investigates the technical landscape: API capabilities, data model implications, architectural options, and prior art. The research is written up as a standalone document that the epic specification references.

Research documents differ from epic specifications in an important way: research is exploratory and may cover options that weren't selected. Epic specifications are prescriptive — they define what will be built. Keeping them separate means the agent can reference the research to understand why certain approaches were rejected, without confusing research findings with implementation decisions.

Organize research by topic or by feature domain. Larger research areas can have their own subdirectories (e.g., `docs/research/Email Management/`).

### docs/decisions/ — Architecture Decision Records

Architecture Decision Records (ADRs) capture significant architectural decisions: what was decided, why, what alternatives were considered, and what the consequences are. They're numbered sequentially (`ADR-001-use-prisma.md`, `ADR-002-vertical-slices.md`) and never deleted or modified after the decision is made (if a decision is reversed, a new ADR records the reversal).

ADRs are especially valuable in agent-built repos because they prevent future agent sessions from re-litigating settled decisions. When an agent encounters an architectural question during research, it should check the ADR directory first. If the question has already been decided, the agent follows the decision rather than re-evaluating from scratch.

### docs/ARCHITECTURE.md and CHANGELOG.md

**ARCHITECTURE.md** is a living document that describes the system's current architecture at a high level. It is updated after any structural change (new feature added, shared layer modified, infrastructure changed). It's the "big picture" document that feature-level CLAUDE.md files don't provide.

**CHANGELOG.md** is a dated, reverse-chronological record of changes to the codebase. Each entry includes the date, the epic or change that was made, and a brief description. This provides a timeline that agents can reference when understanding the evolution of the codebase.

---

## Part 5: Quality Gates and Deterministic Enforcement

The [Deterministic Sandwich](Deterministic-Sandwich.md) principle states that every LLM reasoning step should be bracketed by deterministic checks — validation before the agent reasons, and verification after it produces output. In an agent-built repo, this is the only systematic defense against quality degradation.

### Pre-Processing Gates (Before Agent Reasons)

**Pre-flight checks (Step 7)** run before implementation begins. They are automated (no LLM needed) and binary pass/fail:

- All files referenced in the build plan exist in the repo.
- All dependencies are installed and at expected versions.
- The database schema matches what the build plan expects.
- Required environment variables are present.
- No uncommitted changes from a prior interrupted session.

If any pre-flight check fails, the agent halts and reports the failure. The human (or orchestrating agent) resolves the issue before implementation proceeds. This prevents the most common class of implementation failure: building against assumptions that don't match reality.

### Post-Processing Gates (After Agent Produces Output)

**Auto-formatting and linting** should run after every file write. This is the "10% fix" identified by Boris Cherny's team — auto-formatting catches the formatting inconsistencies that AI-generated code reliably produces, preventing CI failures without wasting context window tokens asking the agent to remember style rules.

Implementation via Claude Code hooks:

- **PostToolUse hooks:** After every file write, automatically run Prettier and ESLint. The agent's code is reformatted to match project conventions without the agent needing to know the conventions.
- **PreToolUse hooks:** Before file writes to sensitive directories (e.g., `shared/`, `prisma/`), require explicit confirmation. This prevents subagents from modifying shared infrastructure without oversight.

**Type checking** (`tsc --noEmit`) should run after each task's implementation is complete, before the git commit. Type errors caught here are cheap to fix — the agent still has the full context of what it just built. Type errors caught in CI are expensive because the agent may have moved on to the next task.

**Test execution** is the primary quality gate:

- **Unit tests:** Run after each task (Step 8), before committing. The checkpoint gate — verify the current task's work before moving on.
- **Component/integration tests:** Run after unit tests pass, during the same task. Verify that pieces work together.
- **Full E2E suite:** Run after all tasks are complete (Step 12), on the entire test suite — not just tests for the new feature. The most common bugs that survive unit testing are integration regressions where new code breaks previously-working functionality.

### CI/CD as the Final Gate

The CI pipeline must block merges on any test failure. A typical pipeline runs: lint → type-check → unit tests → integration tests → E2E tests. The agent checks CI results and iterates on failures (Step 13: final remediation).

For agent-built applications, CI is not just a safety net — it's the agent's feedback loop. The agent submits code, CI runs the full verification suite, and the agent reads the results to determine whether its implementation is correct. This is the "verify independently, verify often" principle in automated form.

### Git Workflow as Checkpoint System

Git commits are not just version control — they're the checkpoint system for failure recovery. The convention:

- **One commit per task** (not per feature, not per file). Each commit is an atomic, potentially recoverable checkpoint. If a session crashes after task 7 of 12, the next session resumes from commit 7 — not from the beginning.
- **Descriptive commit messages** that include: what was implemented, what was tested, what decisions were made. The git log is a narrative of the build process that future agents can read.
- **Feature branches per epic.** Work happens on a branch (`epic-b-gmail-integration`). The branch merges to main only after the full verification suite passes. This keeps main clean and deployable.

---

## Part 6: Mapping Repo Artifacts to the Development Loop

The 15-step development loop (documented in [Development Loop — Full Reference](Development-Loop-Full-Reference.md)) produces artifacts at every step. The repo structure must have a defined location for each one, or artifacts get lost and institutional memory degrades.

### Phase 1: Plan (Steps 1–6)

| Step | Activity | Repo Artifact | Location |
|------|----------|--------------|----------|
| 1 | Research the feature | Research document | `docs/research/{topic}.md` |
| 2 | Draft feature plan + Integration Contract | Epic specification | `docs/development-plans/EPIC-{#}.md` |
| 3 | Validate requirements (fresh context) | Validation notes (in epic or inline) | Appended to epic spec or separate validation doc |
| 4 | Validate integration + architecture (fresh context) | Validation notes | Appended to epic spec |
| 5 | Generate build plan (dual-format) | Build plan with checkboxes | `.cursor/plans/epic_{name}.plan.md` |
| 6 | Double-check build plan (fresh context) | Validated build plan | Same file, validated flag |

### Phase 2: Build (Steps 7–11)

| Step | Activity | Repo Artifact | Location |
|------|----------|--------------|----------|
| 7 | Pre-flight check (automated) | Pass/fail log | Console output (no persistent artifact) |
| 8 | Implement + commit per task | Source code + tests | `src/features/{feature}/` + `__tests__/features/{feature}/` |
| 9 | Code review | Review findings | Inline comments or review doc |
| 10 | Deep audit (fresh context) | Audit findings | Temporary — feeds into Step 11 |
| 11 | Remediation | Fixed code + tests | Same source/test locations |

### Phase 3: Verify & Ship (Steps 12–15)

| Step | Activity | Repo Artifact | Location |
|------|----------|--------------|----------|
| 12 | Full E2E test suite | Test results | Console output + CI logs |
| 13 | Final remediation | Fixed code | Same source locations |
| 14 | Commit + update docs | Canonical doc, context updates, changelog | `docs/epics/EPIC-{#}-{name}.md`, feature CLAUDE.md, INTEGRATION.md, CHANGELOG.md, ARCHITECTURE.md |
| 15 | Post-epic audit | Audit report | `docs/audits/AUDIT-EPIC-{#}-{NAME}.md` |

### The Epic Lifecycle Summary

The full lifecycle of an epic produces artifacts across the repo:

```
1. Research           → docs/research/{topic}.md
2. Epic draft         → docs/development-plans/EPIC-{#}.md
3. Build plan         → .cursor/plans/epic_{name}.plan.md
4. Implementation     → src/features/{feature}/ (git commit per task)
5. Post-build doc     → docs/epics/EPIC-{#}-{name}.md
6. Audit report       → docs/audits/AUDIT-EPIC-{#}-{NAME}.md
7. Context updates    → features/{feature}/CLAUDE.md, INTEGRATION.md
8. Architecture docs  → docs/ARCHITECTURE.md, docs/CHANGELOG.md
```

### Integration Contract Enforcement

The Integration Contract exists at two levels in the repo:

**In the epic specification** — a mandatory section in `docs/development-plans/EPIC-{#}.md` declaring every point where new code connects to existing code. This is the planning artifact, written in Step 2 and validated in Steps 3–4. It specifies: which existing files will be modified, which new files will be created, what API contracts are introduced or changed, what data model changes are required, and how new components integrate with existing navigation and state.

**In the feature directory** — `features/{feature}/INTEGRATION.md` is the durable artifact that persists after the epic is complete. It reflects what was actually built, not what was planned. It is updated in Step 14 of the development loop.

The build plan (Step 5) must reference both. The deep audit (Step 10) must verify both. The post-epic audit (Step 15) must confirm the INTEGRATION.md was updated to reflect reality.

---

## Part 7: Conventions for AI Agents

These conventions should be included in the root CLAUDE.md (or referenced from it) so that every agent session follows the same workflow.

### When Working in a Specific Feature

1. Read the feature's `CLAUDE.md` before starting work.
2. Check `INTEGRATION.md` for cross-feature dependencies.
3. Import from other features through their `index.ts` only.
4. Write tests in `__tests__/features/{feature}/` mirroring the source structure.
5. Run `tsc --noEmit` after each task to catch type errors early.
6. Git commit after each completed task with a descriptive message.
7. After completing work, update the feature's `CLAUDE.md` and `INTEGRATION.md` if any contracts changed.

### When Adding a New Feature

1. Determine which feature domain the work belongs to (or whether a new feature directory is needed).
2. Reference `docs/development-plans/EPIC-{#}.md` for the feature specification.
3. Reference `docs/EPIC_BUILD_INSTRUCTIONS.md` for standard workflow instructions.
4. Follow the development loop: tests alongside implementation → type check → commit per task.
5. Verify Integration Contract compliance before marking complete.
6. Update `docs/epics/EPIC-{#}-{name}.md` with what was actually built.

### When Adding a New Feature Domain

1. Create the full directory structure from the Feature Directory Anatomy template.
2. Create `CLAUDE.md`, `INTEGRATION.md`, `index.ts`, `types.ts`, `constants.ts`.
3. Add a subagent definition in `.claude/agents/{feature}-specialist.md`.
4. Add new entity models to the schema file.
5. Update the root `CLAUDE.md` directory map.
6. Update `docs/ARCHITECTURE.md`.

### Context File Maintenance Rules

- When CLAUDE.md changes, update AGENTS.md to match (and vice versa).
- When `.cursor/rules/` change, verify root CLAUDE.md is still consistent.
- Treat context file edits with the same care as code changes — a bad rule in CLAUDE.md propagates to every future session.
- Review context files after every epic. Remove stale references, add new patterns, update the living error log.

---

## Part 8: Unique Considerations for Agent-Only Repos

When the AI agent handles the majority of development — not just implementation, but the full loop from research through audit — several additional patterns become essential. These go beyond what's needed for AI-assisted development (where a human is actively steering) and address the challenges of sustained autonomous construction.

### Schema-First Development

Define database schemas, API contracts, and TypeScript interfaces before implementation begins. These are deterministic anchors that keep the agent grounded. When the agent generates implementation code, it has concrete types to code against rather than inventing shapes from the specification prose. The schema becomes a compile-time check on the agent's understanding of the data model.

In practice, this means the epic specification (Step 2) should include the actual Prisma schema changes, the TypeScript interface definitions, and the API request/response types. The agent implements against these contracts, and type checking (the deterministic post-processing gate) catches any deviations.

### Automated Validation with Fresh Context

The agent that wrote code is biased toward confirming its own output. This is the confirmation bias problem that [Validation Passes](Validation-Passes.md) addresses. For agent-only repos, automate this: after a build completes, invoke a separate agent session (fresh context, no implementation history) that reads the specification and the code, then evaluates whether the implementation satisfies the spec.

Anthropic's testing shows a 23–31% improvement in validation accuracy when using fresh-context passes compared to in-session validation. For agent-only repos, this improvement compounds — every fresh-context validation catches issues that would otherwise propagate to downstream features.

### Aggressive Pre-Flight Checks

Before feature implementation begins, a pre-flight script should verify: all files referenced in the build plan exist, all dependencies are installed, the database schema matches what the build plan expects, environment variables are present, and no uncommitted changes remain from a prior session. If any check fails, the agent halts.

This is more aggressive than what most human-supervised workflows need, because in a human-supervised workflow, the human catches environmental issues through ambient awareness ("oh, I forgot to run the migration"). In an agent-only workflow, the agent has no ambient awareness — it will cheerfully build against a stale schema or missing dependency and produce code that looks correct but doesn't work.

### Documentation as System Memory

Without humans who "remember" what was built, canonical documentation is the only way future agent sessions understand existing code. This means documentation updates are not optional cleanup — they are as critical as the code itself. The post-build documentation step (Step 14) is a hard gate: the epic is not complete until `docs/epics/EPIC-{#}-{name}.md` is written or updated, the feature CLAUDE.md reflects what was built, and the INTEGRATION.md reflects current contracts.

The compounding effect is significant. Each epic builds on the documented understanding from previous epics. Without documentation updates, the Nth epic operates on stale context from epic N-2, the Integration Contract check fails silently because the contracts were never updated, and the agent makes incorrect assumptions about code that has since changed. This is the "70% rework" finding from Thoughtworks, applied recursively.

### Subagent Specialization

Emerging patterns from Anthropic's internal teams and production Claude Code deployments suggest that specialized subagents with scoped permissions produce better results than a single general-purpose agent for larger projects. The pattern:

- **Architect agent:** Read-heavy, plans and validates design. Has access to the full docs/ directory and all feature CLAUDE.md files.
- **Implementer agent (per feature):** Write access within a single feature directory. Reads from shared/ and other features' public APIs but cannot modify them.
- **Test agent:** Runs and analyzes tests, reports failures. Read access to source code, write access to test directories.
- **Audit agent:** Fresh-context agent that reads the specification and the implementation and evaluates quality. No write access.

Each subagent gets its own system prompt (the `.claude/agents/` definitions), tool permissions, and context. Claude Code hooks gate transitions between subagent roles.

---

## References

### Internal Documents

- [AI-Coding-Best-Practices](AI-Coding-Best-Practices.md) — Core principles, development loop summary, environment setup overview
- [Development Loop — Full Reference](Development-Loop-Full-Reference.md) — Authoritative 15-step pipeline with model routing, failure recovery, and state machine
- [Context Engineering](Context-Engineering.md) — Writing, selecting, compressing, and isolating context
- [Canonical Documentation](Canonical-Documentation.md) — Templates, update practices, index management
- [Integration Contracts](Integration-Contracts.md) — Contract template, verification checklist, orphaned-code patterns
- [Project Context Files](Project-Context-Files.md) — CLAUDE.md, AGENTS.md, .cursor/rules/ patterns
- [Deterministic Sandwich](Deterministic-Sandwich.md) — Pre/post-processing deterministic gates
- [Validation Passes](Validation-Passes.md) — Fresh-context validation, LLM-as-Judge pattern
- [Review and Audit](Review-and-Audit.md) — Code review vs. deep audit, prompt templates
- [Testing Strategy](Testing-Strategy.md) — Three-tier testing pyramid, when to run what
- [Externalized State](Externalized-State.md) — Dual-format build plans, checkpoint-per-task, failure recovery
- [Environment Setup — Full Reference](Environment-Setup-Full-Reference.md) — Complete environment setup guide

### External Research (2025–2026)

- HumanLayer: "Writing a Good CLAUDE.md" — Keep context files lean (60–100 lines for simple projects); never send an LLM to do a linter's job
- AI Hero: "A Complete Guide to AGENTS.md" — Document capabilities, not file paths; portable open standard
- GitHub Blog: "How to Write a Great agents.md" — Analysis of 2,500+ repositories; patterns that work vs. patterns that poison context
- Builder.io: "Improve Your AI Code Output with AGENTS.md" — AGENTS.md as portable agent instructions
- Matthew Groff: "Implementing CLAUDE.md and Agent Skills" — Progressive disclosure pattern; agent-guides directory for deep reference
- Dometrain: "Creating the Perfect CLAUDE.md for Claude Code" — Enterprise CLAUDE.md patterns
- PubNub: "Best Practices for Claude Code Subagents" — Specialized agent roles with scoped permissions
- Shrivu Shankar: "How I Use Every Claude Code Feature" — Token budget allocation across context sources
- Boris Cherny / Anthropic: Claude Code workflow (2026) — Living error logs, auto-formatting as "the 10% fix," verification loops as highest-leverage practice
- Thoughtworks: "Spec-Driven Development" (2025) — Written specifications prevent 70% of rework
- Spectro Cloud: "Will AI Turn 2026 Into the Year of the Monorepo?" — Monorepo advantages for AI agent workflows
- Anthropic: "2026 Agentic Coding Trends Report" — Context editing improved agent performance by 29%; memory + context editing by 39%
