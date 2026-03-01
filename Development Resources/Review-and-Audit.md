# Review and Audit

**Parent:** [AI-Coding-Best-Practices](AI-Coding-Best-Practices.md)
**Related:** [Model Routing](Model-Routing.md) · [Validation Passes](Validation-Passes.md) · [Integration Contracts](Integration-Contracts.md) · [Deterministic Sandwich](Deterministic-Sandwich.md)

---

## Why Separate Passes Matter

Code review and deep audit are fundamentally different activities that catch different failure classes. Treating them as a single "review everything" pass is one of the costliest mistakes in AI-assisted development.

Research shows that specialized review agents with focused prompts outperform a general-purpose reviewer. Each pass has a distinct job: surface-level pattern matching (code review) or deep system reasoning (audit). Conflating them forces a single agent to context-switch between two incompatible cognitive modes, degrading performance on both.

Addy Osmani's data illustrates the cost: PRs are 18% larger, incidents per PR are up 24%, and change failure rates are up 30%. A significant portion of these failures are integration bugs — the kind that a focused audit catches but a surface-level review misses. Conversely, style inconsistencies and naming issues often slip through deep audits because the auditor is focused on system behavior, not readability.

The solution is the "Council of Sub Agents" pattern: deploy multiple specialized agents, each with a narrowly scoped prompt and a focused set of criteria.

---

## Code Review (Step 9): Surface-Level Correctness

Code review is the first pass after implementation. It answers: "Does each piece of code look correct in isolation?"

### What to Check

- **Style and formatting:** Is the code consistent with project conventions? Naming, indentation, line lengths?
- **Obvious bugs:** Off-by-one errors, null pointer dereferences, unreachable code, logic inversions?
- **Anti-patterns:** Forbidden patterns documented in your project context (Cursor Rules, CLAUDE.md, AGENTS.md)?
- **Type safety:** Are types declared? Are casts justified? Are any unchecked type assertions present?
- **Error handling:** Are errors caught? Are edge cases handled? Are error messages clear?
- **Documentation:** Are public functions documented? Are complex blocks commented?

### Model Tier

**Mid-tier.** Code review is pattern matching — comparing the code against a checklist of known issues. A mid-tier model (Claude 3.5 Sonnet or equivalent) has sufficient pattern-matching capability and produces good results at 40–50% the cost of a frontier model. Reserve frontier models for tasks that require deep reasoning.

### Prompt Template Structure

```
You are a code reviewer for [PROJECT].

CODE STANDARDS (from CLAUDE.md):
[Copy relevant sections from your project context]

ANTI-PATTERNS TO FLAG:
[List forbidden patterns, architectural violations, documented mistakes]

RECENT CODE REVIEW FEEDBACK:
[Last 3–5 issues found in this codebase, so the reviewer knows the project's quality bar]

---

Review the following code for surface-level issues:
- Style and naming consistency
- Obvious bugs and logic errors
- Anti-pattern violations
- Type safety issues
- Error handling gaps
- Missing or unclear documentation

CODE:
[Code to review]

For each issue, provide:
1. Line number(s)
2. Category (style, bug, anti-pattern, type, error handling, docs)
3. Severity (critical, major, minor)
4. Description and suggested fix

Format as a structured issue report.
```

### Interpreting Results

- **Critical issues:** Prevent the code from working or expose major bugs. Must be fixed before audit.
- **Major issues:** Violate architectural patterns or introduce subtle bugs. Should be fixed before audit.
- **Minor issues:** Style inconsistencies or incomplete documentation. Can be addressed concurrently with audit, but escalate patterns (e.g., "all error handlers missing") to major.

---

## Deep Audit (Step 10): System-Level Correctness

Deep audit is the second pass, run *after* code review issues are remediated. It answers: "Does the code work correctly as a system?"

### What to Check

- **Cross-file integration:** Do new components connect to existing code correctly? Are all connections bidirectional and complete?
- **Async and concurrency bugs:** Are promises awaited? Are race conditions prevented? Are locks held as expected?
- **Resource management:** Are file handles, connections, and memory properly released? Are cleanup operations guaranteed?
- **Security:** Are inputs validated? Are secrets properly handled? Are dependencies audited for known vulnerabilities?
- **Performance:** Are expensive operations cached? Are database queries optimized? Are n+1 queries prevented?
- **Integration Contract verification:** Does the implementation match the contract specified in the plan? Are all promised connections present and correct?

### Model Tier

**Frontier.** Deep audit requires understanding cross-file behavior, async semantics, and system-level correctness — tasks that demand deep reasoning. Use a frontier model (Claude Opus 4.6 or equivalent). This is where a more expensive model provides genuine value, not marginal improvement.

### Mandatory: Integration Contract Verification

Every audit must include a dedicated Integration Contract section. This is non-negotiable.

The Integration Contract verification checks:
- Files modified: Do the plan and implementation agree on which files change?
- Files created: Are all promised new files present and connected?
- API contracts: Do new/modified endpoints match the specified signatures?
- Data model changes: Are migrations written? Is the schema what was promised?
- Component interfaces: Do new UI components connect to navigation, state, and parent layouts?
- Dependencies: Does the implementation depend only on what was planned? Are there unexpected coupling points?

### Prompt Template Structure

```
You are a deep auditor for [PROJECT]. Your job is system-level correctness.

PROJECT CONTEXT:
[Canonical documentation for affected systems]

ARCHITECTURAL CONSTRAINTS:
[Integration patterns, concurrency models, security requirements from CLAUDE.md]

FEATURE PLAN:
[The feature plan and Integration Contract]

---

Audit the following code for system-level correctness:

CODE:
[Full implementation]

EXISTING CODEBASE CONNECTIONS:
[Paths to files that this code integrates with]

Perform a deep audit across:
1. Cross-file integration
2. Async and concurrency correctness
3. Resource management
4. Security
5. Performance
6. Integration Contract verification (MANDATORY)

For Integration Contract verification, check:
- Files modified: Do implementation changes match the plan?
- Files created: Are all promised new files present and integrated?
- API contracts: Do endpoint signatures match the plan?
- Data model: Does the schema match? Are migrations included?
- Component connections: Do UI components integrate correctly?
- Dependencies: Are unexpected couplings introduced?

For each finding, provide:
1. Category (integration, async, resource, security, performance, contract)
2. Severity (critical, major, minor)
3. Location (file, function)
4. Description and recommendation

Format as a structured issue report. Conclude with a summary of Integration Contract alignment.
```

### Interpreting Results

- **Integration Contract misalignment:** The implementation doesn't match the plan. This is a hard blocker — the feature doesn't integrate with the system as promised.
- **Critical issues:** Security vulnerabilities, unhandled async bugs, resource leaks, or blocking integration problems. Must be fixed before merging.
- **Major issues:** Performance problems, incomplete error paths, or subtle concurrency issues. Should be fixed before merging.
- **Minor issues:** Code clarity, non-critical optimizations, or secondary audit findings. Can be deferred to post-ship if time is critical, but escalate patterns.

---

## The "Council of Sub Agents" Approach

OpenObserve introduced the Sentinel concept: a specialized agent that audits for framework violations, anti-patterns, and security concerns — read-only, never modifying code, reporting findings back to the main development agent.

This pattern extends naturally:

- **Code Reviewer:** Mid-tier model, focused on style and obvious bugs. Reports all findings to the developer.
- **Deep Auditor:** Frontier model, focused on integration and system correctness. Reports blocking issues and Integration Contract alignment.
- **Security Auditor:** Specialized agent with security context (OWASP, CWEs, your framework's known vulnerabilities). Reports security-specific findings.
- **Performance Auditor:** Specialized agent with performance context (benchmarks, bottlenecks, caching patterns). Reports performance regressions or opportunities.

Each agent operates independently with clean context, then results are aggregated. The developer sees a unified issue report but each agent was focused on what it does best.

### Qodo's 15+ Specialized Agents

Qodo offers a mature example of the sub-agent pattern: 15+ specialized review agents covering different concerns (null checks, naming, performance, error handling, documentation, etc.). Research shows this approach catches 23% more issues than a single "review everything" agent, while maintaining faster review times because each agent is laser-focused.

---

## Security-Focused Review

AI-generated code has higher defect rates than human-written code, and security defects are particularly common. Snyk DeepCode AI and similar tools demonstrate that security-focused review benefits from:

- **Explicit security context:** OWASP Top 10, framework-specific vulnerabilities, recent CVEs in dependencies.
- **Checklist-driven review:** Input validation, authentication/authorization, secret handling, injection prevention, CORS, CSRF.
- **Dependency auditing:** Are all transitive dependencies pinned? Are known-vulnerable versions included?
- **Threat modeling per feature:** What's the attack surface? What assumptions must hold for security?

For security-critical code, run a dedicated security audit pass before code review. Security issues are so high-impact that they justify a separate agent.

---

## Separation of Concerns in Multi-Agent Review

A critical constraint: **audit agents are read-only and cannot take destructive action.**

The Code Reviewer and Deep Auditor should have access to:
- Read all code files
- Run tests and linting
- Query the codebase for integration points

But NOT:
- Modify code (fixing issues is remediation, a different step)
- Delete files
- Modify configs or environments
- Push commits

This separation prevents a runaway agent from making unauthorized changes. The agent's job is to report, not to fix. The developer (or a dedicated remediation agent with explicit instructions) handles repairs.

---

## Tool Capability Boundaries

Map tools carefully to agent roles:

**Code Reviewer tools:**
- Read files (all code files)
- Run linters and formatters (dry-run only, no modifications)
- Query documentation

**Deep Auditor tools:**
- Read files (code and integration points)
- Search for references and dependencies (grep, imports)
- Run tests in dry-run mode
- Query git history for integration context

**Remediation Agent tools:**
- Read files (all code)
- Edit files (fixing issues)
- Run tests and linting (full execution, not dry-run)
- Git operations (commit, push)

This layering ensures each agent does what it's designed for and nothing more.

---

## Osmani's Data: The Review Bottleneck

Addy Osmani's findings put a quantitative edge on why this matters:

- **PR size:** 18% larger with AI-assisted development (more features, more code)
- **Incidents:** 24% more incidents per PR (higher defect rate in AI-generated code)
- **Change failure rate:** 30% increase (more broken deployments)

The cause is clear: review is the bottleneck. When code changes faster but review stays slow, quality suffers. The solution isn't faster reviews — it's smarter reviews. Specialized agents, focused prompts, and targeted checklists catch issues that generalist review misses.

---

## Anti-Patterns

**Single "review everything" pass.** One agent trying to do surface-level and system-level review simultaneously. Results: missed bugs in one category while spending tokens on the other.

**Review without criteria.** Asking an agent to "review the code" without providing standards, anti-patterns, or architectural context. The agent defaults to generic patterns that don't match your project's quality bar.

**Skipping audit for "simple" changes.** Even simple feature additions can have integration bugs. If a feature is in the plan, the audit is mandatory.

**Integration Contract review outside the audit pass.** The Integration Contract is so critical that it must be verified as part of deep audit, not as an afterthought. Make it a mandatory section in every audit report.

**No context about recent issues.** If the last 5 code reviews flagged missing error handling, that becomes part of the next reviewer's context. Let the agent learn from your project's actual quality bar.

**Remediation without re-review.** After issues are fixed, run the full review-audit cycle again. Don't assume fixes were applied correctly or that remediation introduced new issues.

---

## Getting Started

**Start with two passes.**

1. **Code Review (Step 9):** Give your mid-tier model a code review prompt template (see above) and a checklist of anti-patterns from your CLAUDE.md. Run this as the first pass after implementation.

2. **Deep Audit (Step 10):** Give your frontier model the audit prompt template above, including a mandatory Integration Contract section. Run this as the second pass after code review issues are fixed.

**Add a security pass if you handle sensitive data or external input.** Build a security-focused prompt based on OWASP principles and your framework's documented vulnerabilities.

**Specialize over time.** As you see patterns in review failures, extract those into specialized agents with tighter prompts. This is how the "Council of Sub Agents" grows naturally from experience.

**Externalize findings.** Maintain a log of every bug found in code review vs. audit. Over months, this reveals your actual quality bar — and exposes whether specialized agents are working (fewer bugs in their domain) or whether your prompt is drifting (same bugs reappearing).

---

## Sources

This section draws on:

- **Osmani, Addy.** "Agentic Engineering" (2026); "The 80% Problem in Agentic Coding" (2026)
- **Qodo.** "State of AI Code Quality in 2025" (research on specialized vs. generalist review agents)
- **OpenObserve.** "The Sentinel pattern for AI auditing" (2025)
- **Snyk DeepCode AI.** Security-focused code review research (2025–2026)
- **Anthropic.** "2026 Agentic Coding Trends Report"; internal validation of model tiers for review tasks
- **HumanLayer.** "Multi-agent code review patterns" (2025)
