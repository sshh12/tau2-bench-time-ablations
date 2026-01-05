#!/bin/bash
# Run extra trials for all remaining offsets
# -36500 needs all 5 trials (data was lost)
# Others need only 2 more trials (will resume)

echo "Starting runs at $(date)"
echo ""

# First: run -36500 from scratch (5 trials)
echo "========================================"
echo "[$(date +%H:%M:%S)] Running offset -36500 (from scratch - 5 trials)"
echo "========================================"
python -m experiments.time_ablation.cli run \
    --offsets -36500 \
    --num-trials 5 \
    --agent-llm claude-sonnet-4-5-20250929 \
    2>&1 | grep -E "(Running task|Completed|Pass\^k|Average Reward|Error|✨|Skipping)"
echo "[$(date +%H:%M:%S)] Completed offset -36500"

# Then: run the rest (only need trials 4 and 5)
REMAINING_OFFSETS="-3650 -1825 -1460 -1095 -730 -365 365 730 1095 1460 1825 3650 36500"

for offset in $REMAINING_OFFSETS; do
    echo ""
    echo "========================================"
    echo "[$(date +%H:%M:%S)] Running offset: $offset (adding trials 4-5)"
    echo "========================================"

    yes y | python -m experiments.time_ablation.cli run \
        --offsets $offset \
        --num-trials 5 \
        --agent-llm claude-sonnet-4-5-20250929 \
        2>&1 | grep -E "(Running task|Completed|Pass\^k|Average Reward|Error|✨|Skipping.*trial [34])"

    echo "[$(date +%H:%M:%S)] Completed offset: $offset"
done

echo ""
echo "========================================"
echo "All offsets completed at $(date)"
echo "========================================"
