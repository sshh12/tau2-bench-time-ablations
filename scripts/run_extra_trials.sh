#!/bin/bash
# Run trials 4 and 5 for all offsets (resumes existing runs)
# The framework will skip trials 0-2 that are already complete

set -e

OFFSETS="-36500 -3650 -1825 -1460 -1095 -730 -365 0 365 730 1095 1460 1825 3650 36500"

echo "This will run 2 additional trials (4 and 5) for each offset."
echo "Existing trials 0-2 will be skipped automatically."
echo ""
echo "Offsets: $OFFSETS"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

for offset in $OFFSETS; do
    echo ""
    echo "========================================"
    echo "Running offset: $offset"
    echo "========================================"

    # Use 'yes y' to auto-confirm the resume prompts
    yes y | python -m experiments.time_ablation.cli run \
        --offsets $offset \
        --num-trials 5 \
        --agent-llm claude-sonnet-4-5-20250929 \
        || echo "Offset $offset completed or errored"
done

echo ""
echo "Done! Run 'python -m experiments.time_ablation.cli analyze' to see updated results."
