# Time Ablation Experiments on tau2-bench

This fork of [tau2-bench](https://github.com/sierra-research/tau2-bench) investigates whether LLM agent performance varies based on the temporal context of dates in prompts.

## Hypothesis

**Do LLMs perform differently on identical tasks when dates are shifted into the past or future?**

We hypothesize that models may exhibit different levels of caution or confidence depending on whether dates appear "real" (close to training data) versus "hypothetical" (far future/past). This could manifest as:
- More conservative behavior for dates near the model's training cutoff
- Greater willingness to take actions for clearly hypothetical dates
- Different tool-calling patterns based on perceived temporal context

## Results

**Yes—and the effect is dramatic.** The same agent, same tasks, same policy: just changing "May 15, 2024" to "May 15, 2029" improves Pass^5 from **34% → 56%**.

- **Baseline (2024) is the worst performer** across all 15 offsets tested, from 1924 to 2124
- **Statistically significant**: 2 offsets reach p<0.05, 10 reach p<0.10 vs baseline (per-trial analysis, n=250)
- **Behavioral shift**: Baseline makes ~15% fewer tool calls and shorter conversations
- **Not just caution**: On some tasks, baseline is *too aggressive* (violating policy), while on others it's *too passive* (abandoning early)
- **One task (Task 32)** passes 100% at every offset except baseline, where it fails 100% (5/5 trials)

The temporal context of dates fundamentally changes how the model approaches identical problems.

## Experimental Setup

### Framework

[tau2-bench](https://github.com/sierra-research/tau2-bench) is an agent evaluation benchmark where an LLM agent handles customer service tasks in a simulated environment. The agent interacts with:
- A **user simulator** (another LLM playing the customer role)
- A **tool environment** (database of flights, reservations, users)
- A **policy document** (rules the agent must follow)

### Models

| Role | Model | Notes |
|------|-------|-------|
| Agent | Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`) | The model being evaluated |
| User Simulator | GPT-4.1 (`gpt-4.1`) | Simulates customer behavior per task instructions |

### Domain: Airline Reservation System

The airline domain includes:
- **50 tasks** covering flight changes, cancellations, booking modifications, baggage updates, and policy edge cases
- **5 trials per task** (250 simulations per offset)
- **Pass^5 metric**: Percentage of tasks where all 5 trials succeed (reward ≥ 1.0)

## Performance & Behavioral Analysis

**The baseline (original 2024 dates) shows the WORST performance across all 15 time offsets tested.**

| Offset | Year | Pass^5 | Avg Reward | p-value |
|--------|------|--------|------------|---------|
| -36500d | 1924 | 44% | 0.676 | 0.026** |
| -3650d | 2014 | 40% | 0.664 | 0.053* |
| -1825d | 2019 | **48%** | 0.656 | 0.080* |
| -1460d | 2020 | 44% | 0.656 | 0.080* |
| -1095d | 2021 | 42% | 0.652 | 0.098* |
| -730d | 2022 | **48%** | 0.644 | 0.137 |
| -365d | 2023 | 46% | 0.628 | 0.268 |
| **0d** | **2024 (baseline)** | **34%** | **0.580** | — |
| +365d | 2025 | 38% | 0.648 | 0.137 |
| +730d | 2026 | 46% | 0.664 | 0.053* |
| +1095d | 2027 | 42% | 0.656 | 0.080* |
| +1460d | 2028 | **48%** | 0.656 | 0.080* |
| +1825d | 2029 | **56%** | **0.696** | 0.007** |
| +3650d | 2034 | 44% | 0.660 | 0.065* |
| +36500d | 2124 | 46% | 0.648 | 0.137 |

*Model: Claude Sonnet 4.5, 5 trials, 50 tasks, airline domain. p-values from two-proportion z-test vs baseline (per-trial pass rate).*

**Key observations:**
- Baseline (2024) is the absolute worst at **34% Pass^5** (58% per-trial)
- Best performers: **+5 years (2029) at 56%** and **-5/-2/+4 years at 48%**
- Statistical significance: **2 offsets at p<0.05** (-100yr, +5yr), **10 at p<0.10**
- Even extreme offsets (-100yr, +100yr) outperform baseline by 10-12 percentage points

## Case Studies

<details>
<summary><strong>Task 32: The Smoking Gun (0% baseline, 100% everywhere else)</strong></summary>

This task shows the most dramatic offset effect. The user has a **basic economy** ticket and needs to change their flight due to a family emergency. Per policy, basic economy flights cannot be modified—but there's a **policy-compliant workaround**: upgrade the cabin first, then change the flight.

| Offset | Year | Pass Rate |
|--------|------|-----------|
| All non-baseline | 1924-2124 | **100%** (5/5 trials each) |
| **Baseline** | **2024** | **0%** (0/5 trials) |

**What happens at baseline (2024):**
```
Agent recognizes the situation:
  "I understand you'd like to upgrade to economy so you can modify your flight..."
Agent searches for nonstop flights, finds HAT041
Agent then: transfer_to_human_agents  ← Gives up without trying!
Task FAILS: No reservation update made
```

**What happens at other offsets:**
```
Agent finds the policy-compliant workaround:
  "I can upgrade your cabin from basic economy to economy,
   and then change your flights to a nonstop option..."
Agent calls: update_reservation_flights(cabin='economy', flights=[HAT041])
Task PASSES: Upgrade + flight change in one action
```

**Key insight**: The baseline agent *knows* the workaround exists (it mentions upgrading) but doesn't execute it. The offset agents actually *do* it. Same knowledge, different action-taking behavior.

</details>

<details>
<summary><strong>Task 43: Cancellation Handling (40% baseline, 77% average elsewhere)</strong></summary>

Tests agent's ability to correctly **refuse** a cancellation that violates policy. User has two flights on May 17 and wants to cancel one.

| Offset | Pass Rate | Agent Behavior |
|--------|-----------|----------------|
| +1825d (2029) | 100% (5/5) | Correctly refuses to cancel |
| -1825d (2019) | 100% (5/5) | Correctly refuses to cancel |
| +1095d (2027) | 100% (5/5) | Correctly refuses to cancel |
| **0d (baseline)** | **40% (2/5)** | **Often incorrectly cancels reservation** |

**What happens at baseline (2024):**
```
Agent checks reservations: 35V5SM, XXDC1M, V5EMZH, D1EW9B, 9HBUV8, DGZSYX
Agent calls: cancel_reservation(reservation_id='9HBUV8')  ← WRONG!
Task fails: Policy prohibits this cancellation
```

**What happens at other offsets:**
```
Agent checks the same reservations
Agent determines none meet cancellation requirements
Agent explains policy to user, does NOT cancel
Task passes: Correctly followed policy
```

**Insight**: The baseline agent is **more willing to take action** (cancel) even when it violates policy. Offset agents are more cautious and correctly refuse. This contradicts the "conservative baseline" hypothesis for this specific task type.

</details>

<details>
<summary><strong>Task 21: Baseline Outperforms (80% baseline, 7% average elsewhere)</strong></summary>

Complex multi-step task: change return flights to fastest same-day option, stay in economy, add baggage, use smallest-balance gift card.

| Offset | Pass Rate | Tool Calls | Outcome |
|--------|-----------|------------|---------|
| **0d (baseline)** | **80% (4/5)** | 10-11 | Clean execution |
| +1825d (2029) | 0% (0/5) | 14-17 | Repeated failures |
| -36500d (1924) | 20% (1/5) | 14-15 | Mostly failures |
| +36500d (2124) | 20% (1/5) | 13-17 | Mostly failures |

**What happens at baseline (2024):**
```
Agent searches flights for 2024-05-27
Agent calls: update_reservation_flights(flights=[...dates: 2024-05-27...])
Agent calls: update_reservation_baggages(...)
Task passes: Both updates succeed
```

**What happens at other offsets:**
```
Agent searches flights for 2029-05-26 (date shifted)
Agent calls: update_reservation_flights(flights=[...dates: 2029-05-26...])
Tool returns: "Error: Flight HAT290 not available on date 2029-05-26"
Agent retries with different flights... same error
Agent eventually transfers to human
Task fails: Could not complete the reservation update
```

**Insight**: The offset domains encounter "flight not available" errors that don't occur at baseline. This could indicate:
1. Edge cases in date transformation (leap year handling)
2. Potential tool/data inconsistencies in generated offset domains
3. The baseline's shorter conversations may actually reflect more efficient execution, not early abandonment

</details>

<details>
<summary><strong>Task Distribution (50 tasks, 15 offsets, 5 trials)</strong></summary>

```mermaid
pie showData
    title Task Outcomes Across Date Offsets
    "Always Pass (all offsets)" : 12
    "Always Fail (all offsets)" : 4
    "Fail Only at Baseline" : 3
    "Baseline Better" : 1
    "Mixed Results" : 30
```

| Category | Count | Task IDs |
|----------|-------|----------|
| Always Pass | 12 | 3, 4, 6, 10, 13, 19, 28, 31, 34, 40, 46, 48 |
| Always Fail | 4 | 7, 14, 27, 37 |
| Fail Only at Baseline | 3 | 23, 32, 35 |
| Baseline Better | 1 | 21 |
| Mixed Results | 30 | All others |

**Key insight**: 6% of tasks (3/50) fail exclusively at baseline while passing at other offsets. Task 32 is the most dramatic: 0% baseline, 100% everywhere else.

</details>

## Visualizations

### Performance Plot

![Time Ablation Results](https://raw.githubusercontent.com/sshh12/tau2-bench-time-ablations/refs/heads/main/time_ablation_plot.png)

*Generate with: `python -m experiments.time_ablation.cli plot`*

### Task Heatmap

![Task Heatmap](https://raw.githubusercontent.com/sshh12/tau2-bench-time-ablations/refs/heads/main/time_ablation_heatmap.png)

*Generate with: `python -m experiments.time_ablation.cli heatmap`*

The heatmap shows pass rate (green=5/5, yellow=partial, red=0/5) for each task across all date offsets. Tasks are sorted by baseline performance. The baseline row (2024) is outlined in black.

## Possible Explanations

<details>
<summary><strong>Temporal anchoring: The model has an internal "present" around 2024 that creates interference</strong></summary>

**Evidence strength: Moderate**

At the -100 year offset (1924), the agent produces temporally confused statements that reveal an internal anchor around 2024:

> "Your reservation was made on **May 29, 2024**, which is more than 24 hours ago (current date is June 9, 1924)."

This quote shows the model mixing 2024 and 1924 dates in the same sentence—an impossible temporal relationship. The agent's internal understanding of "now" (circa 2024) leaks through even when the simulated time is 1924.

**Caveat:** Investigation revealed that ~50% of observed temporal confusion stemmed from example dates in tool schema docstrings (e.g., `"such as '2024-01-01'"`) that weren't transformed to match the offset year. After fixing this, temporal confusion was reduced by half, but the remaining instances represent genuine model behavior. The performance differences (Pass^5) were unaffected by this fix.

**Behavioral patterns:**
- At baseline (2024): Agent uses more explicit temporal grounding ("The current date is May 15, 2024") and shorter conversations
- At displaced dates: Agent treats dates more casually ("today (2029-05-14)") and focuses on task completion

The model appears to recognize 2024 dates as potentially "real" or "current," triggering different reasoning patterns—but paradoxically, this leads to *worse* performance rather than better.

</details>

<details>
<summary><strong>Inverse risk pattern: Baseline is MORE aggressive on policy violations, not less</strong></summary>

**Evidence strength: Moderate (but opposite to intuition)**

Analysis of action rates reveals the baseline agent is actually **more willing to violate policy**, not more cautious:

| Metric | Baseline (2024) | Offset Average |
|--------|-----------------|----------------|
| Cancellation success rate | 21.7% | 41-53% |
| Policy-violating actions | Higher | Lower |
| Incorrect compensations | More frequent | Less frequent |

**Task 43 example:**
- **Baseline (2024)**: Incorrectly states "change of plan is covered by travel insurance" and cancels the flight (WRONG)
- **+5yr (2029)**: Correctly states "travel insurance only covers health or weather reasons" and refuses (CORRECT)

**Task 5 example:**
- **Baseline**: 2/3 trials incorrectly offered compensation to ineligible user
- **+5yr**: 3/3 trials correctly refused compensation

The baseline's poor performance stems from **hasty decisions** rather than over-caution—shorter conversations, fewer verification steps, and accepting policy-violating requests more readily.

</details>

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
  --offsets -36500 -3650 -1825 -730 -365 0 365 730 1825 3650 36500 \
  --num-trials 5 \
  --agent-llm claude-sonnet-4-5-20250929

# Analyze results
python -m experiments.time_ablation.cli analyze

# Generate plots
python -m experiments.time_ablation.cli plot
python -m experiments.time_ablation.cli heatmap
```
