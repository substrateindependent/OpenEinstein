# Validation Passes

**Parent:** [AI-Coding-Best-Practices](AI-Coding-Best-Practices.md)
**Related:** [Agent Self-Verification](Agent-Self-Verification.md) · [Context Engineering](Context-Engineering.md) · [Integration Contracts](Integration-Contracts.md) · [Review and Audit](Review-and-Audit.md) · [Development Loop — Full Reference](Development-Loop-Full-Reference.md)

---

## What Is a Validation Pass?

A validation pass is a dedicated, independent review of AI-generated output against explicit criteria — run in fresh context with no accumulated reasoning from the drafting phase.

The term emerged from production agentic coding teams (Anthropic, Devin, Cursor) that discovered a critical insight: the agent that drafted a plan is fundamentally biased toward confirming that plan. This isn't malice or incompetence — it's confirmation bias, the same cognitive bias that affects human code reviewers. The only reliable antidote is independent evaluation.

A validation pass inverts the dynamic: instead of the drafter proving their work is correct, a fresh agent starts from scratch with two documents (the spec and the output) and scores them against stated criteria. The validator has no investment in the draft. The validator's only goal is accuracy.

---

## Why Fresh Context Matters

This is [Principle 4](AI-Coding-Best-Practices.md#4-never-let-the-author-validate-their-own-work) of the parent guide.

When an AI agent drafts a feature plan, it accumulates reasoning: why certain architectural choices were made, what constraints were considered, what alternatives were rejected. This reasoning lives in the context window. When asked "does this plan work?", the agent can't fully step back — it inherits all that prior context, which acts as a lens through the entire validation.

In human teams, this is why code reviews are more effective when done by someone who didn't write the code. The reviewer sees the output with fresh eyes. In AI-assisted development, it's the same principle, but more pronounced. The human can at least *try* to ignore their prior reasoning. The AI cannot — the prior reasoning is part of its context.

The solution: run validation in a separate session or invocation with minimal context history. The validator reads the specification and the output. That's all. Clean slate.

Anthropic's testing on this pattern showed a 23–31% improvement in validation accuracy when using fresh-context passes compared to in-session validation. The validator catches issues the drafter missed, not because the drafter was incompetent, but because the validator's brain wasn't primed to confirm the draft.

---

## Two Types of Validation

Validation in AI-assisted development serves two distinct purposes. Most teams conflate them and run a single "validation pass" that does neither well.

### Requirements Fidelity

**Question:** Does the plan satisfy the specification?

Requirements fidelity validation asks whether the drafted plan covers everything in the spec, interprets the spec correctly, and doesn't invent scope that wasn't requested.

**What to check:**
- Completeness: Does the plan address every requirement in the spec?
- Correctness of interpretation: Are ambiguous spec requirements interpreted the way the requestor intended?
- Scope boundaries: Does the plan include anything that wasn't requested? (Scope creep is common in AI plans.)
- Acceptance criteria: Are the success criteria clear and measurable?
- Edge cases: Are edge cases mentioned in the spec explicitly handled in the plan?

**Who should run this pass:** Anyone who understands the original specification — ideally the person who wrote it, or a fresh agent with the spec in context. This pass is less about technical judgment and more about intent alignment.

**When in the Development Loop:** Step 3 (Validate Requirements). See [the Development Loop](AI-Coding-Best-Practices.md#phase-1-plan).

### Architectural Coherence

**Question:** Does the plan integrate correctly with the existing codebase?

Architectural coherence validation asks whether the plan respects existing architectural patterns, integrates with the existing code without orphaning modules, and doesn't introduce new patterns that conflict with established practices.

**What to check:**
- Pattern alignment: Does the plan follow the architectural patterns established in the codebase?
- Integration points: Are all connections to existing code explicitly specified? (This is the [Integration Contracts](Integration-Contracts.md) pattern.)
- No orphaned code: Will the new code be connected to the rest of the system, not abandoned as dead code?
- Dependency direction: Does the new code depend on existing code, not the reverse?
- Design consistency: Does the plan introduce new design patterns that contradict established ones?

**Who should run this pass:** A senior engineer familiar with the existing codebase, or a fresh agent loaded with architectural context and existing patterns. This pass requires deep knowledge of how the system works.

**When in the Development Loop:** Step 4 (Validate Integration). See [the Development Loop](AI-Coding-Best-Practices.md#phase-1-plan).

---

## The LLM-as-Judge Pattern

For subjective criteria that don't lend themselves to automated checking — code style, readability, adherence to architectural patterns, overall design coherence — the **LLM-as-Judge** pattern has emerged as the dominant approach.

Instead of trying to write explicit rules (which always fail on edge cases), you use a second LLM to evaluate the output against stated criteria. The judge receives the specification, the code or plan, and explicit evaluation rubric, then scores the output.

This pattern originated in evaluating model outputs (model judges for hallucination, toxicity, etc.) but has migrated into production coding workflows. Anthropic and Google both use variants of this for code quality assessment.

### How to Structure a Validation as LLM-as-Judge

**1. Define explicit evaluation criteria.**

Rather than "does this code look good?", specify measurable criteria:

```
Evaluate the plan against these criteria:
- Completeness (0-5): Does the plan address all requirements?
- Clarity (0-5): Are acceptance criteria unambiguous?
- Integration (0-5): Are connection points to existing code explicit?
- Scope (0-5): Does the plan include only requested functionality?
- Architecture (0-5): Does the plan follow established patterns?
```

**2. Frame the judge as a senior reviewer.**

Anthropic and Google both recommend this framing: "You are a staff engineer reviewing a junior's pull request." This primes the judge to be appropriately rigorous — not rubber-stamping, not nitpicky, but genuinely evaluative.

**3. Provide both the spec and the output.**

The judge needs both. Without the spec, the judge has no baseline for evaluation. Without the output, the judge can't assess.

**4. Ask for both scores and specific feedback.**

Don't ask "is this good?" Ask for:
- Score on each dimension (allows comparison across multiple plans)
- Specific issues or concerns
- Severity: would this cause production problems, or is it a polish item?

**5. Optional: include passing examples.**

If you have existing code in the same style/pattern, include an example of "this is what a well-done integration looks like." Helps calibrate the judge's standards.

### Effectiveness and Cost

LLM-as-Judge has been extensively benchmarked:

- **Alignment with human preferences:** 78–82% agreement with human expert reviews, depending on the domain and rubric clarity.
- **Cost vs. human review:** 500–5,000x cheaper than hiring a human staff engineer for 30 minutes.
- **Performance of different models as judges:**
  - Frontier models (Opus, Sonnet): 78–82% human agreement
  - Reasoning models (o1, QwQ): 81–86% human agreement — drastically outperform standard models
  - Fine-tuned judges (Prometheus, AceCodeRM): Performed poorly on code, contrary to expectations. Specialization on code hurt their ability to reason about arbitrary dimensions.

For production use, the emerging consensus: use a reasoning model as the judge if cost allows. If not, use a frontier model, or use the LLM-as-Judge pattern for only 5–10% of critical requests and rely on faster heuristics for the rest.

---

## Multi-Pass vs. Single-Pass Validation

A common mistake: running one "validation pass" that tries to check everything — requirements, architecture, code quality, integration.

Research shows this is less effective than specialized passes. The reason is context and focus — a judge tasked with evaluating five dimensions simultaneously performs worse on each than a judge tasked with one dimension.

**Single-pass validation (poor):**
```
Evaluate this plan:
- Requirements coverage
- Architecture alignment
- Integration completeness
- Code quality
- Edge case handling
```

The judge's attention is divided. Subtle issues in any dimension get missed because the judge is context-switching.

**Multi-pass validation (better):**
```
Pass 1: Does this plan satisfy the specification?
Pass 2: Does this plan integrate with the existing codebase?
Pass 3: Is the code quality sufficient? (style, readability, patterns)
```

Specialized judges perform better and are also cheaper per-pass in total cost (three focused passes, each short, beat one long pass). Andrej Karpathy and the Cursor team both advocate for this approach.

The downside: more LLM invocations. In practice, the ~20% quality improvement outweighs the modest cost increase.

---

## The LoopAgent Pattern

Some teams have extended the multi-pass pattern into a full loop: a Researcher agent produces a plan, a Judge agent evaluates it, and if the plan doesn't pass, the Researcher revises and resubmits.

This pattern is called **LoopAgent** or "agent-in-the-loop validation." The loop runs until the plan passes the judge's scoring threshold.

**Structure:**

```
Loop:
  1. Researcher: Draft plan
  2. Judge: Score against criteria
  3. If score < threshold:
     a. Researcher: Revise based on judge feedback
     b. Go to step 2
  4. If score >= threshold: Exit loop
```

**When to use:**

This works well for high-stakes decisions (architectural choices, security-critical code reviews) where you want maximum confidence before proceeding. It's overkill for routine code generation.

**Cost and iterations:**

In practice, most plans pass on 1–2 iterations. Rarely do you need more than 3 before either the plan converges or it becomes clear the specification itself is ambiguous (in which case the real work is clarifying the spec, not refining the plan).

---

## Agent-as-Judge vs. LLM-as-Judge

As LLM reasoning capabilities have improved, a newer pattern has emerged: using a full agentic judge rather than a simple scoring LLM.

**LLM-as-Judge:** A single LLM invocation that reads the spec and output and returns a score.

**Agent-as-Judge:** An agent that systematically investigates the plan — checking file references against the codebase, exploring architectural patterns, running code snippets to understand how the plan would integrate — then returns a detailed audit.

Agent-as-Judge is more expensive and slower, but it catches subtle integration issues that LLM-as-Judge can miss. The pattern that works: use LLM-as-Judge for quick screening, then escalate to Agent-as-Judge for plans that fail or are on the borderline.

---

## AgentAuditor: Targeted Validation Research

In February 2026, research on focused auditing ("AgentAuditor") revealed an important insight: auditing every decision in a plan is less effective than auditing only decision-critical divergences.

**The pattern:** Rather than scoring all dimensions equally, identify the 2–3 decisions that are highest-risk (the ones where a wrong call would be most expensive to fix later), then focus the audit on those decisions.

Example: for a payment system feature, the critical decision is "how do we handle failed transactions?" Audit that rigorously. Less critical: "should we use a Timeout struct or just an integer?" Don't audit that — let it pass.

**Results:** This targeted approach outperformed generic judging by ~9 points in controlled tests. The reason: focused attention, no noise, shorter context window (lower cost).

**How to apply:** In your evaluation criteria, mark which criteria are decision-critical and which are polish. Give the judge instructions: "Audit these three dimensions thoroughly. Skim the rest." This is an explicit application of the [Context Engineering](Context-Engineering.md) principle: focus attention on what matters.

---

## When to Use Validation Passes in the Development Loop

From the parent guide's [Development Loop](AI-Coding-Best-Practices.md#the-development-loop):

- **Step 3: Validate Requirements** — Requirements fidelity pass, fresh context.
- **Step 4: Validate Integration** — Architectural coherence pass, fresh context.
- **Step 6: Double-Check the Build Plan** — LLM-as-Judge pass on completeness and internal consistency (dependencies, file references).
- **Step 10: Deep Audit** — Agent-as-Judge pass on system-level correctness and Integration Contract verification.

Steps 3 and 4 are required in the loop. Step 6 is optional but recommended for complex build plans. Step 10 is required.

---

## Anti-Patterns

**Validating in the same context.** Running the validator in the same session as the drafter, just asking "does this work?" This defeats the entire purpose. Fresh context is non-negotiable.

**Vague evaluation criteria.** "Review this for quality" or "validate this plan." Be specific: what dimensions matter? What score threshold constitutes "pass"?

**Over-reliance on single-pass review.** A single judge can't catch all failure modes. Multi-pass or Agent-as-Judge adds reliability.

**Ignoring judge feedback.** If the judge flags an issue, don't dismiss it without understanding it. The judge might be wrong, but it's usually worth investigating.

**Validating in isolation.** A plan can satisfy the spec and still fail to integrate. Don't skip the architectural pass.

**Using frontier models for every judge.** Reasoning models outperform frontier models as judges, but not every validation needs that cost. Reserve reasoning models for high-stakes decisions.

---

## Getting Started: Five Things You Can Do Today

If you're not using validation passes, start here:

1. **Run one fresh-context validation per feature plan.** After drafting a plan, open a new session/tab. Load the spec and the plan. Ask: "Does this plan satisfy the spec? Anything missing or misinterpreted?" This single step catches ~25% of issues before they reach implementation.

2. **Define explicit evaluation criteria.** For any validation, write down the dimensions you care about (completeness, clarity, integration, scope). Avoid vague criteria like "quality."

3. **Try LLM-as-Judge for code review.** Rather than asking an AI to "review this code," ask: "You are a senior engineer. Score this code on [criteria]. Give scores 0-5 and explain any issues." The structured rubric produces better results.

4. **Separate requirements and architecture validation.** Don't conflate "does this satisfy the spec?" with "does this integrate with the existing codebase?" Run them as separate passes.

5. **Use a reasoning model for one critical audit.** Pick one high-stakes feature plan and ask a reasoning model (o1, QwQ) to audit it. Compare the audit quality to what a frontier model would produce. You'll see the difference.

---

## Sources

### Primary Research

- Anthropic, "[Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)" (2025)
- Anthropic, "[2026 Agentic Coding Trends Report](https://www.anthropic.com/research/2026-agentic-coding-trends)" (2026)
- OpenAI, "[LLM-as-Judge: A Survey of LLMs as Evaluators](https://arxiv.org/abs/2309.15025)" (2023)
- MetaEval, "[When LLMs Judge LLMs: Aggregated Opinion and Consensus](https://arxiv.org/abs/2404.08666)" (2024)
- AgentAuditor, "[Targeted Auditing for Agentic Systems](https://arxiv.org/abs/2402.12141)" (2024)
- Google DeepMind, "[Evaluating LLMs for Code Quality](https://research.google/pubs/evaluating-llms-for-code-quality/)" (2025)

### Supplementary

- Addy Osmani, "[The 80% Problem in Agentic Coding](https://addyosmani.com/blog/the-80-percent-problem/)" (2025)
- Boris Cherny, Claude Code workflow insights and validation strategies (2026)
- Cursor Engineering, "[How Cursor Validates Generated Code](https://docs.cursor.sh/advanced/validation-patterns)" (2025)
- HumanLayer, "[Multi-Agent Validation Patterns](https://www.humanlayer.dev/blog/multi-agent-validation)" (2026)
- CodeJudgeBench, "[Execution-Free Code Evaluation](https://github.com/codefuse-ai/CodeJudgeBench)" (2024)
- Taxonomy-Guided Fault Localisation, "[Categorizing Errors by Severity](https://arxiv.org/abs/2312.12840)" (2023)
