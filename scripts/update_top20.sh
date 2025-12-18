#!/bin/bash

# Top 20 universities (excluding Harvard which is done)
universities=(
    "Princeton University"
    "Yale University"
    "Stanford University"
    "University of Florida"
    "New York University"
    "University of Vermont"
    "California Institute of Technology"
    "Clemson University"
    "Rensselaer Polytechnic Institute"
    "University of Washington"
    "Johns Hopkins University"
    "University of Wyoming"
    "Rice University"
    "Southern Methodist University"
    "University of Virginia"
    "Washington University in St. Louis"
    "St. Louis University"
    "Massachusetts Institute of Technology"
    "Mississippi State University"
)

# Export keys (assuming they are set in the environment where this runs)
# source venv/bin/activate should be run before this script

mkdir -p logs

echo "Starting batch update for ${#universities[@]} universities..."

for uni in "${universities[@]}"; do
    echo "================================================================="
    echo "Processing: $uni"
    echo "Time: $(date)"
    echo "================================================================="
    
    python scripts/run_monthly_analysis.py --provider ensemble --university "$uni"
    
    echo "Finished $uni (Exit code: $?)"
    echo ""
    # Small sleep to be nice to APIs
    sleep 5
done

echo "Batch update complete!"
