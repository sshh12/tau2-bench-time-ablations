# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **fork of tau2-bench focused on time ablation experiments**. The main research question: do LLM agents perform differently on identical tasks when dates are shifted into the past or future?

Key finding: The baseline (2024 dates) shows the **worst** performance (42% Pass^3), while +5 years (2029) shows the **best** (60% Pass^3). The baseline agent makes ~20% fewer tool calls and produces ~15% shorter conversations.

## Time Ablation Experiments

### Quick Start

```bash
# Install
pip install -e .

# List existing offset domains
python -m experiments.time_ablation.cli list

# Generate a new offset dataset (e.g., +2 years)
python -m experiments.time_ablation.cli generate --offset-days 730

# Validate generated datasets
python -m experiments.time_ablation.cli validate-all

# Run experiments on specific offsets
python -m experiments.time_ablation.cli run \
  --offsets -365 0 365 \
  --num-trials 3 \
  --agent-llm claude-sonnet-4-5-20250929

# Analyze results
python -m experiments.time_ablation.cli analyze
```

### CLI Commands

| Command | Description |
|---------|-------------|
| `generate --offset-days N` | Generate offset dataset (N days from 2024 baseline) |
| `generate-all` | Generate all default offset datasets |
| `validate --offset-days N` | Validate a specific offset dataset |
| `validate-all` | Validate all generated datasets |
| `list` | List all generated offset domains |
| `sanity-check` | Quick test run on sampled tasks |
| `run` | Run full ablation experiment |
| `analyze` | Analyze experiment results |
| `plot` | Generate results plot (Pass^3 + trial averages) |
| `heatmap` | Generate task heatmap (pass/fail by task and offset) |

### Experiment Configuration

Edit `src/experiments/time_ablation/config.py`:

```python
DEFAULT_OFFSETS = [-365, 0, 365, 1825]  # Days from baseline
DEFAULT_NUM_TRIALS = 3
DEFAULT_AGENT_LLM = "claude-sonnet-4-20250514"
DEFAULT_USER_LLM = "gpt-4.1"
```

### Directory Structure

```
src/experiments/time_ablation/
  cli.py                  # Main CLI entry point
  config.py               # Experiment configuration
  generate_dataset.py     # Offset dataset generation
  date_utils.py           # Date transformation utilities
  run_ablation.py         # Experiment runner
  analyze.py              # Results analysis
  plot.py                 # Results visualization
  validate.py             # Dataset validation
  domain_loader.py        # Dynamic domain loading

data/tau2/domains/
  airline/                # Original baseline (2024)
  airline_offset_n365d/   # -1 year (2023)
  airline_offset_p365d/   # +1 year (2025)
  airline_offset_p1825d/  # +5 years (2029)
  ...

data/simulations/time_ablation/
  offset_p0d/             # Baseline results
  offset_p365d/           # +1 year results
  ...
```

### Offset Domain Naming Convention

- `airline_offset_p365d` = +365 days (future)
- `airline_offset_n365d` = -365 days (past)
- `p` = positive (future), `n` = negative (past)

### What Gets Transformed

When generating an offset dataset, these files are transformed:

- **db.json**: Flight dates, timestamps, DOBs, reservation created_at
- **tasks.json**: Instructions, evaluation criteria with dates
- **policy.md**: "The current time is..." timestamp
- **tools.py**: `_get_datetime()` return value

## Common Commands

```bash
# Install (development mode)
pip install -e .

# Run tests
make test
pytest tests/

# Linting and formatting
make lint        # check with ruff
make format      # format with ruff
make lint-fix    # auto-fix linting issues

# Run a single agent evaluation (non-ablation)
tau2 run --domain airline --agent-llm gpt-4.1 --user-llm gpt-4.1 --num-trials 1 --num-tasks 5

# View simulation results
tau2 view
```

## tau2-bench Architecture

### Core Simulation Flow

The `Orchestrator` (`src/tau2/orchestrator/orchestrator.py`) manages message flow between:
- **Agent**: Responds to user requests and makes tool calls (`src/tau2/agent/`)
- **User**: Simulates customer behavior (`src/tau2/user/`)
- **Environment**: Handles tool execution and state (`src/tau2/environment/`)

### Registry System

`src/tau2/registry.py` registers components:
- **Domains**: `airline`, `airline_offset_p365d`, `airline_offset_n1825d`, etc.
- **Agents**: `llm_agent`, `llm_agent_gt` (oracle plan)
- **Users**: `user_simulator`, `dummy_user`

Generated offset domains are automatically registered.

### Domain Structure

Each domain in `src/tau2/domains/<domain>/` contains:
- `environment.py`: `get_environment()` and `get_tasks()` functions
- `tools.py`: Agent toolkit
- `data_model.py`: Database models
- `utils.py`: Path constants

Data files in `data/tau2/domains/<domain>/`:
- `db.json`: Database state
- `tasks.json`: Task definitions
- `policy.md`: Agent policy document
- `split_tasks.json`: Task splits

### Evaluation Metrics

- **Pass^k**: Percentage of tasks where all k trials succeed (reward >= 1.0)
- **Avg Reward**: Mean reward across all trials
- **Behavioral metrics**: Tool calls per task, conversation length

## Key Configuration

`src/tau2/config.py`:
- `DEFAULT_MAX_STEPS = 200`
- `DEFAULT_MAX_ERRORS = 10`

LLM API keys: Copy `.env.example` to `.env`. Uses LiteLLM for provider abstraction.

## Tips for Working with This Codebase

1. **Running experiments**: Always use the time ablation CLI (`python -m experiments.time_ablation.cli`) rather than `tau2 run` directly for ablation experiments.

2. **Adding new offsets**: Use `generate --offset-days N` - it handles all the date transformations automatically.

3. **Debugging date issues**: Check `date_utils.py` for the transformation logic. Use `validate` to verify dataset integrity.

4. **Results location**: All ablation results go to `data/simulations/time_ablation/offset_*/`.

5. **Comparing results**: Use `analyze` command or read JSON files directly - each contains `simulations` array with `reward_info.reward` per trial.
