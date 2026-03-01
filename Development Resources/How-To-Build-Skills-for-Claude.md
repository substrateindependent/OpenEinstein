# How to Build Skills for Claude — A Concise Guide

A skill is a folder of instructions that teaches Claude how to handle specific tasks or workflows. Instead of re-explaining your preferences every conversation, you teach Claude once and it applies that knowledge consistently.

---

## What's in a Skill?

```
my-skill-name/
├── SKILL.md          # Required — main instructions
├── scripts/          # Optional — Python, Bash, etc.
├── references/       # Optional — docs loaded on demand
└── assets/           # Optional — templates, fonts, icons
```

**Hard rules:**
- File must be named exactly `SKILL.md` (case-sensitive)
- Folder must use kebab-case (`my-cool-skill`, not `My Cool Skill`)
- Do NOT include a `README.md` inside the skill folder
- No XML angle brackets (`< >`) in frontmatter
- Don't use "claude" or "anthropic" in the skill name

---

## Step 1: Define Your Use Cases

Before writing anything, identify 2–3 concrete tasks the skill should handle. For each, define:

- **Trigger** — What will the user say? (e.g., "help me plan this sprint")
- **Steps** — What does the workflow look like?
- **Result** — What's the deliverable?

Skills generally fall into three categories:

| Category | Example |
|---|---|
| **Document/Asset Creation** — Consistent output like docs, slides, code | `frontend-design`, `docx`, `pptx` |
| **Workflow Automation** — Multi-step processes with validation gates | `skill-creator` |
| **MCP Enhancement** — Workflow guidance layered on top of MCP tool access | `sentry-code-review` |

---

## Step 2: Write the SKILL.md

### The YAML Frontmatter (Critical)

This is how Claude decides whether to load your skill. It lives at the top of `SKILL.md`.

```yaml
---
name: my-skill-name
description: What it does. Use when user asks to [specific trigger phrases].
---
```

**The `description` must include both:**
1. What the skill does
2. When to use it (trigger conditions / phrases users would say)

**Good example:**
```yaml
description: Manages Linear project workflows including sprint planning,
  task creation, and status tracking. Use when user mentions "sprint",
  "Linear tasks", "project planning", or asks to "create tickets".
```

**Bad example:**
```yaml
description: Helps with projects.
```

**Optional fields:** `license`, `compatibility`, `metadata` (author, version, mcp-server, etc.)

### The Instructions Body

After the frontmatter, write clear Markdown instructions. Recommended structure:

```markdown
# Skill Name

## Instructions

### Step 1: [First Step]
Clear explanation. Include exact commands if applicable.
Expected output: [what success looks like]

### Step 2: [Next Step]
...

## Examples
**User says:** "Set up a new campaign"
**Actions:** 1. Fetch data → 2. Create resource → 3. Confirm
**Result:** Campaign created with link

## Troubleshooting
**Error:** [Common error]
**Cause:** [Why]
**Solution:** [Fix]
```

**Writing tips:**
- Be specific and actionable — not "validate the data" but "Run `python scripts/validate.py --input {filename}`"
- Put critical instructions at the top
- Move detailed reference docs into `references/` to keep SKILL.md under ~5,000 words
- For critical validations, use a bundled script rather than relying on language instructions alone

---

## Step 3: Test It

### Triggering Tests
- ✅ Does it activate on obvious requests?
- ✅ Does it activate on paraphrased requests?
- ❌ Does it stay silent on unrelated queries?

**Quick debug:** Ask Claude *"When would you use the [skill-name] skill?"* — it will quote the description back so you can spot gaps.

### Functional Tests
- Does it produce correct output?
- Do API/MCP calls succeed?
- Does error handling work?

### Performance Comparison
Compare with vs. without the skill: fewer messages, fewer failed calls, lower token usage.

**Pro tip:** Iterate on a single hard task until Claude nails it, then extract that approach into the skill. Expand to broader test cases after.

---

## Step 4: Fix Common Issues

| Problem | Likely Cause | Fix |
|---|---|---|
| Skill won't upload | `SKILL.md` misspelled or YAML malformed | Check exact filename, ensure `---` delimiters, close all quotes |
| Never triggers | Description too vague | Add specific trigger phrases and file types |
| Triggers too often | Description too broad | Add negative triggers ("Do NOT use for..."), narrow scope |
| MCP calls fail | Connection or auth issue | Test MCP independently first; check API keys and tool names |
| Instructions ignored | Too verbose or ambiguous | Shorten, prioritize critical info at top, use scripts for validation |
| Slow / degraded output | Too much context loaded | Move detail to `references/`, disable unneeded skills |

---

## Step 5: Distribute

### For Individual Users
1. Zip the skill folder
2. Upload via **Claude.ai → Settings → Capabilities → Skills**
3. Or place in the Claude Code skills directory

### For Organizations
Admins can deploy skills workspace-wide through centralized management.

### For Public Sharing
1. Host on GitHub with a clear repo-level README (separate from the skill folder)
2. Link the skill from your MCP docs and explain the combined value
3. Include an installation quick-start and example usage with screenshots

### Via API
Use the `/v1/skills` endpoint for programmatic deployments, automated pipelines, and agent systems. Requires the Code Execution Tool beta.

---

## Quick-Start Shortcut

Use the built-in **skill-creator** skill to generate your first draft in 15–30 minutes:

> *"Use the skill-creator skill to help me build a skill for [your use case]"*

Then validate against the checklist below.

---

## Pre-Upload Checklist

- [ ] 2–3 use cases defined
- [ ] Folder is kebab-case
- [ ] `SKILL.md` exists with exact spelling
- [ ] YAML frontmatter has `---` delimiters, `name`, and `description`
- [ ] Description includes WHAT it does and WHEN to use it
- [ ] No XML tags (`< >`) anywhere
- [ ] Instructions are specific and actionable
- [ ] Error handling and examples included
- [ ] Tested triggering (positive and negative cases)
- [ ] Functional tests pass

---

## Resources

- [Skills Documentation](https://docs.anthropic.com)
- [Best Practices Guide](https://docs.anthropic.com)
- [Example Skills Repo](https://github.com/anthropics/skills)
- [MCP Documentation](https://docs.anthropic.com)
- [Community Discord](https://discord.gg/claudedev)

---

*Based on [The Complete Guide to Building Skills for Claude](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf) by Anthropic.*
