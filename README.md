# GPUs Per Student (gpusperstudent.org)

This project tracks GPU availability relative to CS student population across US universities.

## Why This Exists

After [this tweet](https://x.com/FrancoisChauba1/status/1997095264923078856) went viral, it was clear more effort on this analysis would be valuable. Students are unhappy and leaving for bigger labs because they cannot get GPU access. Some faculty are unaware of the problem. 

There was a lot of debate:
- Students: Include only university-owned resources, not grant-based access
- Faculty: Include external compute (NCSA, Oak Ridge, etc)
- Some said include all students, others said only PhD students

I tried to find a reasonable middle ground. The goal is to provide a standardized metric ("GPUs per Student") to quantify compute access for research and education. If we want more AI talent, students need GPUs to learn. If we want more research, students need at least one modern GPU.

This project shines a light on GPU availability across US universities, which we have seen be suboptimal.

## Dispute Process

This is a contentious topic. All analysis, code, and raw data with receipts are available in this repo. If you disagree with anything, submit a PR and I will review it. If valid, I will update the numbers for your university.

## Methodology

Three key metrics:

1. **Weighted Student Count**: Weighted sum of CS students
   - 0.45 x Undergrad + 0.7 x Grad + 0.9 x PhD
   - Weights based on who uses GPUs most (surveys done at Stanford)
   - Limited to CS department only (could arguably include EE, bio, etc)

2. **H100-equivalent GPU Count**: University-owned GPUs accessible to students
   - Converted to H100 equivalents using market prices
   - Example: 10 A100-80GB at $15k each = 4.3 H100-equivalents (H100 = $35k)

3. **GPUs per Student**: H100-equivalent count / Weighted student count

## Exclusion Criteria (Important!)

We define "University GPUs" as hardware **owned and operated** by the university for its students. We exclude resources that are shared nationally or restricted by external grant walls.

| Resource Type | Status | Reason for Exclusion |
|:--- |:--- |:--- |
| **National Supercomputing Centers** (OSC, NCSA, etc.) | **Excluded** | These are shared utilities used by thousands of researchers from hundreds of universities. Counting them would double-count resources across every member institution. |
| **DOE National Labs** (Oak Ridge, Argonne, NERSC) | **Excluded** | These are federal government facilities, not university assets. Access is by competitive grant, not student enrollment. |
| **TACC (Frontera/Stampede3)** | **Excluded** | These specific systems are NSF-funded national resources open to all US researchers via ACCESS-CI (grant wall). <br> *Exception: UT Austin-owned systems hosted at TACC (e.g., Vista, Lonestar6 UT queues) ARE included.* |
| **Cloud Allocations** (AWS, Azure, GCP) | **Excluded** | Temporary, grant-based credits are not permanent infrastructure. They expire and vary wildly year-to-year. |
| **Consortium/Shared Clusters** (MGHPCC, SDSC) | **Partially Excluded** | We exclude the "general shared" partitions used by external partners. We **include** the dedicated partitions owned specifically by the university (e.g., Harvard's Cannon cluster at MGHPCC). |
| **MIT Lincoln Labs** | **Excluded** | Restricted-access government/defense facility. Most MIT students cannot access these GPUs. |

## Project Structure

```
GPUsPerStudent/
├── data/
│   ├── filtered_national_universities_name_url.csv  # List of 165 universities
│   ├── gpu_prices.csv                               # GPU market prices and conversion weights
│   ├── master_data.csv                              # SOURCE OF TRUTH (Backend Artifact)
│   └── cache/
│       └── final/                                   # Validated JSON files (The actual data)
├── web/
│   ├── index.html                                   # Main website (Frontend)
│   ├── style.css
│   └── data/
│       └── master_data.csv                          # DEPLOYMENT COPY (Served by website)
├── scripts/
│   ├── run_monthly_analysis.py                      # Main data collection script (LLM Extraction)
│   ├── generate_master_data.py                      # JSON -> CSV Aggregation & Deployment
│   └── validate_gpu_data.py                         # Validation Logic
├── prompt.md                                        # LLM prompt for data collection
└── prompt_validation.md                             # LLM prompt for validation
```

**Note on CSVs**: 
*   `data/master_data.csv` is the generated source of truth.
*   `web/data/master_data.csv` is a copy automatically generated for the frontend to load locally without CORS issues.

## How It Works

1.  **Data Collection** (`scripts/run_monthly_analysis.py`)
    *   Queries 3 LLMs (OpenAI, Claude, Gemini) for each university using `prompt.md`.
    *   Aggregates results and validates them against `prompt_validation.md`.
    *   Output: JSON files in `data/cache/final/`.

2.  **Aggregation & Deployment** (`scripts/generate_master_data.py`)
    *   Reads all valid JSONs from `data/cache/final/`.
    *   Calculates "H100 Equivalents" and "GPUs Per Student".
    *   Generates `data/master_data.csv`.
    *   **Deploys** data to `web/data/` (CSV + JSONs) for the frontend.

3.  **Website** (`web/index.html`)
    *   Static HTML/JS that reads the deployed CSV/JSONs.
    *   Sortable leaderboard with detailed source transparency.
