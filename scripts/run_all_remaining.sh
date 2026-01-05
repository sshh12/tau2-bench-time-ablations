#!/bin/bash
# Run extra trials for all remaining offsets

OFFSETS="-36500 -3650 -1825 -1460 -1095 -730 -365 365 730 1095 1460 1825 3650 36500"

echo "Starting runs at $(date)"
echo "Offsets: $OFFSETS"
echo ""

for offset in $OFFSETS; do
    echo ""
    echo "========================================"
    echo "[$(date +%H:%M:%S)] Running offset: $offset"
    echo "========================================"

    yes y | python -m experiments.time_ablation.cli run \
        --offsets $offset \
        --num-trials 5 \
        --agent-llm claude-sonnet-4-5-20250929 \
        2>&1 | grep -E "(Running|Skipping|Completed|Pass\^k|Average Reward|Error|✨)"

    echo "[$(date +%H:%M:%S)] Completed offset: $offset"
done

echo ""
echo "========================================"
echo "All offsets completed at $(date)"
echo "========================================"
