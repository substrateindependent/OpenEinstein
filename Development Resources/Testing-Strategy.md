# Testing Strategy

**Parent:** [AI-Coding-Best-Practices](AI-Coding-Best-Practices.md)
**Related:** [Agent Self-Verification](Agent-Self-Verification.md) · [Integration Contracts](Integration-Contracts.md) · [Development Loop — Full Reference](Development-Loop-Full-Reference.md)

---

## Why Testing Matters More with AI Coding

AI-generated code has a peculiar property: it looks right. The syntax is correct, the style follows conventions, and the logic reads plausibly. Subtle bugs — off-by-one errors, edge case failures, race conditions, incorrect state transitions — are often invisible on first glance. Traditional code review catches style issues readily but frequently misses these bugs because they're plausible enough to fool human reviewers.

This is the core insight from Qodo's 2025 research: AI-generated PRs are 18% larger, incidents per PR are up 24%, and change failure rates are up 30%. The code isn't fundamentally worse — it's just that plausible-looking bugs are harder to catch without automation.

This is why testing becomes your agent's self-verification mechanism. Tests don't care how the code looks; they measure what it *does*. A test suite is the agent's most direct line of evidence that its implementation works. Running tests after implementation isn't optional verification — it's the mechanism that separates shipped code from code-that-happened-to-work-in-isolation.

> *See: [Agent Self-Verification](Agent-Self-Verification.md) for how testing maps to the broader feedback loop pattern.*

---

## The Three-Tier Testing Pyramid

Modern testing distinguishes between three kinds of tests, each catching different failure modes:

### Tier 1: Unit Tests

**What:** Tests for individual functions or components in isolation. Does this function return the correct output for these inputs?

**When to write:** Alongside implementation (Step 8 of the Development Loop), before you move to the next task. Unit tests are the **checkpoint gate** — they verify the current task's work before committing.

**What they catch:**
- Off-by-one errors, calculation mistakes
- Edge cases (empty inputs, null values, boundary conditions)
- Type mismatches, missing error handling
- Logic branches and conditional correctness

**What they miss:** Integration issues. A function can pass all unit tests and still break when called by other code with unexpected timing, state, or data.

**Example:** If you're implementing an authentication service, you'd write unit tests for: password hashing (is the salt applied?), token generation (are tokens unique?), token validation (are expired tokens rejected?).

### Tier 2: Component/Integration Tests

**What:** Tests for interactions between modules or components. Does module A correctly call module B? Are the data contracts honored?

**When to write:** After unit tests pass, during the same implementation task. These tests verify that pieces work together.

**What they catch:**
- Incorrect API contracts (caller sends X, receiver expects Y)
- State management bugs (module A modifies state that module B depends on)
- Async coordination issues (one module waits for another; timing breaks)
- Database/persistence correctness (data written correctly, retrieved correctly)

**What they miss:** Whole-application flows. A component test might pass because it mocks external dependencies, but the real production code might fail when those dependencies are slow or fail.

**Example:** For the authentication service, component tests verify: login flow (user service → auth service → session store), permission checks (auth service → permission service → resource), token refresh (auth service talks to cache correctly).

### Tier 3: End-to-End (E2E) Tests

**What:** Tests for full application flows, from user action to system response. Does the entire system work?

**When to run:** After implementation completes (Step 12 of the Development Loop), *and on the full test suite, not just new tests*. E2E tests catch regressions.

**What they catch:**
- "Works alone but breaks together" bugs (new feature breaks existing features)
- Performance regressions (feature causes database queries to slow down)
- Integration failures that unit/component tests couldn't predict (external service timeouts, resource contention)
- User-facing bugs (UI doesn't match backend assumptions, workflow broken end-to-end)

**What they miss (sometimes):** They're slow and brittle. They depend on external systems, timing, and UI selectors that break when code changes.

**Example:** For the authentication service, E2E tests verify: new user signs up → receives email → clicks link → logs in → accesses protected resource → logs out → can't access protected resource.

---

## "Works in Isolation" ≠ "Works in Context"

This is [Principle 11](AI-Coding-Best-Practices.md#11-works-in-isolation-works-in-context) from the best practices guide, and it's critical to understanding why you can't skip the full E2E suite.

A scenario that illustrates this:

You implement a new payment processing feature that integrates with Stripe. Unit tests verify: payment calculations are correct, Stripe API calls are formatted correctly, error responses are handled. Component tests verify: the payment service receives the correct order data, writes the correct records to the database.

All tests pass. You ship. Production breaks because the payment webhook processing accidentally shares a database connection pool with the reporting service, and under load, reports start failing because the payment processor consumed all connections. This bug would be invisible to unit and component tests because they don't exercise the shared resource under realistic load.

This is why Principle 11 mandates: **run the full E2E suite, not just tests for the new feature.** You're not looking for bugs only in the new code; you're looking for regressions anywhere in the system.

The discipline this requires is higher than it initially seems. It's tempting to run a quick smoke test ("does the app start?") and call it done. But the "slopacolypse" research shows that teams doing this end up with higher change failure rates. Teams that run the full test suite have measurably better outcomes.

---

## Testing During Implementation (Step 8)

During the implementation phase, after each task is complete:

1. **Write unit tests** that cover the task's code — happy path, edge cases, error conditions.
2. **Run unit tests immediately** to verify the task works before moving on. The test results are your evidence of correctness.
3. **Commit** (including the test code). This is your checkpoint. If later work breaks this, you can revert to a known-good state.
4. **Move to the next task.**

This is fast feedback. You're not waiting for a full E2E suite; you're just confirming that the current task's code works. If a unit test fails, you fix it immediately before committing — the task isn't done until the test passes.

---

## Full E2E Suite After Implementation (Step 12)

After all implementation tasks are complete and code review and audit are done:

1. **Run the entire test suite** — not just new tests, everything.
2. **Note any failures.** These could be:
   - New tests failing (implementation didn't work as intended).
   - Old tests failing (regression — new code broke something that was working).
3. **Report failures.** These become the issue list for the final remediation phase.

The goal here is discovering regressions *before* you merge. This is the agent's last feedback loop before the code goes to production.

---

## Final Remediation (Step 13)

When E2E tests reveal failures:

1. **Identify the root cause** — is this a bug in the new code, or did the new code break something old?
2. **Fix the bug** in the implementation code.
3. **Re-run the full test suite** to confirm the fix doesn't introduce new failures.
4. **Commit the fix** with a message identifying what was broken and how you fixed it.
5. **Repeat until all tests pass.**

This isn't "quick fixes to make tests pass." This is real debugging. The test is telling you something is wrong; your job is to find the actual problem and fix it correctly.

---

## Self-Healing Tests: Adapting to Change

A critical challenge in E2E testing: UI locators change. If your tests select elements by CSS class or xpath, and a UI refactor changes those classes, tests break not because the functionality broke but because the selector broke.

This is where self-healing test technology comes in. BrowserStack's test repair tools and OpenObserve's Healer Agent watch when E2E tests fail and attempt to repair the locators automatically. If a test selected `.login-button` and that no longer exists, the Healer can detect that and update the selector to find the button by its new path or accessible name.

OpenObserve's results quantify the impact: organizations moving to self-healing tests increased coverage from 380 to 700+ tests while reducing flaky test maintenance by 85%. The time that was spent on maintenance got redirected to writing more tests.

This doesn't mean your tests should be brittle. It means: write your tests with the assumption that selectors *will* change, and use tools that minimize the manual effort of keeping up.

---

## Agentic Test Planning

Beyond writing tests, there's an emerging pattern of agents that design the testing strategy itself:

- **Application Analysis Agents** explore the codebase and identify what needs testing. What are the critical paths? What features have the most failure risk?
- **Risk Assessment Agents** look at changes and estimate what could break. "You've modified the database schema; here are the tests most likely to be affected."
- **Strategy Generation Agents** produce test plans from specs. "Your feature requires user authentication, payment processing, and email notifications; here's a test strategy covering all three and their interactions."

This is still emerging in 2026, but teams building production agents are starting to use AI not just to implement tests but to design which tests to write. The agent reads the specification, analyzes the code, and produces a test plan. Then another session implements the tests. This separation allows the planning agent to focus on strategy and the implementation agent to focus on execution.

---

## The Feedback Loop: Tests as Self-Verification

Testing isn't a gate at the end of implementation. It's the mechanism that allows the agent to verify its own work. This closes the loop that Boris Cherny identifies as critical to agent quality: "giving the agent a verification loop improves output quality 2–3x."

The loop works like this:

1. **Agent implements a feature** based on the build plan.
2. **Agent writes tests** that specify what the feature should do.
3. **Agent runs tests.** If they pass, the feature works. If they fail, the agent knows something is wrong and can debug.
4. **Agent fixes failures** and re-runs tests until they pass.
5. **Agent reports: "Tests pass. Feature is done."**

Without this loop, the agent says "I think it's done" based on its own assessment. With the loop, the agent says "Tests confirm it's done" based on evidence. That difference is what separates production-quality code from plausible-looking code.

---

## E2E Testing Tools in 2026

The standard tools have converged by 2026:

- **Playwright** (language-agnostic, all browsers, active development, excellent documentation)
- **Cypress** (web-focused, strong DX, good for component and integration tests)
- **WebdriverIO** (mature, broad ecosystem, enterprise adoption)

Playwright is the default choice for new projects. The best practices from Playwright's official documentation are directly applicable:

- **User-centric selectors.** Don't select by internal class names or data attributes. Select by accessible labels, button text, form input names — things that survive refactors.
- **Wait for readiness, not delay.** Don't use hardcoded sleeps (`await page.waitForTimeout(5000)`). Wait for the element you need to be visible or interactive.
- **Isolate tests.** Each test should be independent. Don't rely on test A to set up state for test B.
- **Page Object Model or similar abstraction.** Group interactions with a page/component into a class. This makes selectors centralized and updates propagate automatically.

---

## Anti-Patterns

**Testing only new code.** You've written tests for your new feature; they pass. But you haven't run the full suite, and you shipped a regression. The new code works; the system doesn't.

**No regression suite.** Building features without a suite of tests covering the existing functionality. The first regression costs you more than maintaining a comprehensive suite.

**Flaky tests.** Tests that pass sometimes and fail sometimes. These are worse than no tests because they erode trust — developers ignore them. The root cause is usually timing-related (hardcoded delays) or environmental (tests depend on external state).

**Skipping E2E "to save time."** E2E tests are slow. But shipping a regression costs more time than running E2E tests. The math works out in favor of running them.

**Mock everything.** Excessive mocking means your tests verify "if this function is called, it calls this other function" but don't verify the system works. Components tests need *some* mocking (don't call the real Stripe API), but E2E tests should exercise real dependencies.

**Testing the test code's test code.** Avoiding testing implementation details is correct (test behavior, not internals), but taken to extremes, this means avoiding useful assertions. Test what matters: did the user action produce the intended effect?

---

## Getting Started

If you're not yet at three-tier testing:

1. **Start with unit tests during implementation.** After each task, write tests for that task. Don't move on until tests pass. This is the highest-ROI starting point.

2. **Add a smoke test.** A minimal E2E test that exercises your application's main flow. "User logs in → sees dashboard → logs out." This catches the most obvious breakage.

3. **Expand component tests.** Between unit tests and E2E tests, add tests for critical integrations. Payment processing, authentication, data persistence. These catch the regressions that hurt most.

4. **Build out the E2E suite.** Once you have the foundation, invest in comprehensive E2E coverage. Use page objects to keep tests maintainable. Prioritize user-visible flows.

5. **Automate test runs.** Don't rely on manual test execution. Run unit tests in pre-commit hooks. Run the full suite on every PR. Make failures visible immediately.

The compound effect of this discipline is what separates the systems that ship confidently from systems that ship nervously. After a few features, the suite becomes your safety net — you can refactor, optimize, and experiment knowing that if something breaks, the tests will catch it.

---

## Sources

- Qodo, "State of AI Code Quality in 2025"
- Boris Cherny, Claude Code workflow and team insights (2026)
- Playwright Official Documentation, "Best Practices"
- BrowserStack, "Test Repair and Self-Healing Tests" (2025)
- OpenObserve, "Healer Agent and E2E Test Optimization" (2025)
- Martin Fowler, "Continuous Integration" (foundational, applies to AI-assisted development)
- Anthropic, "Effective harnesses for long-running agents" (2025)
- Google Testing Blog, "Just Say No to More E2E Tests" (2021, remains relevant for test strategy trade-offs)
