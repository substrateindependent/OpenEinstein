# Environment Setup Instructions

Run these commands in order before beginning any implementation work.

## Step 1: Install system dependencies

```bash
cd /path/to/OpenEinstein
chmod +x scripts/setup-dev-environment.sh
./scripts/setup-dev-environment.sh
```

This installs (via Homebrew) Node.js/npx, Docker, BasicTeX/latexmk, and verifies Python 3.12+. It also runs `pip install -e ".[dev]"` and creates `.env` from `.env.example` if one doesn't exist.

## Step 2: Wolfram Engine setup

Wolfram Engine is already installed. Run these commands to install xAct (the tensor algebra package used by OpenEinstein's Mathematica MCP server):

```bash
# Install xAct into Mathematica's Applications directory
git clone https://github.com/xAct-contrib/xAct ~/Library/Mathematica/Applications/xAct

# Verify Wolfram Engine works
wolframscript -code '1+1'
# Expected output: 2

# Verify xAct loads
wolframscript -code 'Needs["xAct`xTensor`"]; Print["xAct loaded successfully"]'
# Expected output: xAct loaded successfully
```

## Step 3: Verify the environment

After both steps above, run:

```bash
# Full verification
python3 --version          # Should be 3.12+
node --version             # Should be 18+
npx --version              # Should be available
docker --version           # Should be installed
latexmk --version          # Should be installed
wolframscript -code '1+1'  # Should return 2

# Project install check
cd /path/to/OpenEinstein
pip install -e ".[dev]"
pytest --tb=short -q       # Should exit 0 (0 tests initially)
ruff check src/ tests/     # Should pass
mypy src/openeinstein/ --ignore-missing-imports  # Should pass
```

## Step 4: Confirm .env is populated

The `.env` file should already exist with API keys filled in. Verify:

```bash
# Check keys are present (don't print values)
grep -c "=.\+" .env
# Should show 7+ lines with values set
```

Keys currently populated: ANTHROPIC_API_KEY, OPENAI_API_KEY, ADS_API_KEY, ZOTERO_API_KEY, ZOTERO_USER_ID, CROSSREF_MAILTO. S2_API_KEY is pending (Semantic Scholar approval in progress).

## Step 5: Begin implementation

Once all verifications pass, read these files in order:

1. `CLAUDE.md` — project rules and architecture guards
2. `BUILD-READY.md` — scope, environment contract, verification loop, stop conditions
3. `OpenEinstein-Implementation-Plan.md` §19 — sequential build order

Then begin with **Task 0.1** and proceed in order.
