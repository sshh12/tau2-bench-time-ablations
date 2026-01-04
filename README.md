# Time Ablation Experiments on tau2-bench

This fork of [tau2-bench](https://github.com/sierra-research/tau2-bench) investigates whether LLM agent performance varies based on the temporal context of dates in prompts.

## Hypothesis

**Do LLMs perform differently on identical tasks when dates are shifted into the past or future?**

We hypothesize that models may exhibit different levels of caution or confidence depending on whether dates appear "real" (close to training data) versus "hypothetical" (far future). This could manifest as:
- More conservative behavior for dates near the model's training cutoff
- Greater willingness to take actions for clearly hypothetical future dates
- Different tool-calling patterns based on perceived temporal context

## Key Finding

**The baseline (original 2024 dates) shows the WORST performance.**

| Offset | Simulated Year | Pass^3 | Avg Reward |
|--------|----------------|--------|------------|
| -365d  | 2023           | 50%    | 0.647      |
| **0d (baseline)** | **2024** | **42%** | **0.560** |
| +365d  | 2025           | 48%    | 0.620      |
| +1825d | 2029           | **60%** | **0.693** |

*Model: Claude Sonnet 4.5, 3 trials, 50 tasks, airline domain*

## Behavioral Analysis

The baseline agent is **more conservative** than agents operating on shifted dates:

| Metric | Baseline (2024) | Other Offsets |
|--------|-----------------|---------------|
| Avg tool calls per task | **6.9** | 7.9-8.4 |
| Avg conversation length | **25.6** | 28-29 messages |
| Transfer to human count | **27** | 53-59 |

The model makes fewer attempts and gives up earlier when operating on dates close to its training data.

## Case Study: Task 32 (Flight Change)

**Baseline (2024):** 0/3 trials passed
- Agent searched for flights, found options, then immediately transferred to human
- Did not attempt `update_reservation_flights`

**+5 Years (2029):** 3/3 trials passed
- Agent searched for flights, found options, and executed `update_reservation_flights`
- Successfully completed the reservation change

The same task, same model, same policy - different outcomes based purely on date context.

## Task Distribution (50 tasks, 4 offsets)

```
15 tasks: Always pass (all offsets)
16 tasks: Always fail (all offsets)
10 tasks: Pass in +1825d, fail in baseline ← date-sensitive
 1 task:  Pass only in baseline
 8 tasks: Mixed results
```

## Running Experiments

```bash
# Install
pip install -e .

# Generate offset datasets
python -m experiments.time_ablation.cli generate --offset-days 365   # +1 year
python -m experiments.time_ablation.cli generate --offset-days -365  # -1 year
python -m experiments.time_ablation.cli generate --offset-days 1825  # +5 years

# Run experiments
python -m experiments.time_ablation.cli run \
  --offsets -365 0 365 1825 \
  --num-trials 3 \
  --agent-llm claude-sonnet-4-5-20250929

# Analyze results
python -m experiments.time_ablation.cli analyze
```

## Possible Explanations

1. **Training data bias**: Model more cautious with 2024 dates due to proximity to real events in training data
2. **Hypothetical framing effect**: Far-future dates trigger "hypothetical scenario" reasoning, reducing hesitation
3. **Confidence calibration**: Model may perceive lower stakes for clearly fictional future dates

## Repository Structure

```
src/experiments/time_ablation/   # Experiment infrastructure
  cli.py                         # Command-line interface
  date_transformer.py            # Date transformation logic
  run_ablation.py                # Experiment runner
  analyze.py                     # Results analysis

data/tau2/domains/               # Generated offset domains
  airline_offset_p365d/          # +1 year offset
  airline_offset_n365d/          # -1 year offset
  airline_offset_p1825d/         # +5 year offset

data/simulations/time_ablation/  # Experiment results
```

## Main Repository

For full tau2-bench documentation, installation instructions, and domain details, see the [main repository](https://github.com/sierra-research/tau2-bench).
