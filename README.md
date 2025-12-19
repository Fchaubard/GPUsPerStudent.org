# GPUs Per Student (GPUsPerStudent.org)

This project tracks GPU availability relative to CS student population across US universities.

## Why 

After [this tweet](https://x.com/FrancoisChauba1/status/1997095264923078856) went viral, it was clear more effort on this analysis would be valuable. Students are unhappy and leaving for bigger labs because they cannot get GPU access. US is falling behind in AI talent and research because we do not have enough GPUs for students. This "GPU Famine" is real, and leads to top talent leaving academia for industry which doesnt publish research anymore so therefore American research will suffer if not addressed. 

There was a lot of debate:
- Students argued to include only university-owned resources, not grant-based access
- Faculty argued that undergrads dont need any GPUs, only grads and PhDs, and to include external compute (NCSA, Oak Ridge, etc)
- Some said include ALL students, not just CS, others said only PhD students

I thought through all of these arguments carefully and tried to find a reasonable middle ground. The goal is to provide a standardized metric ("GPUs per Student") to quantify compute access for research and education. If we want more AI talent, students need GPUs to learn. 

It is my belief that: If we want more AI talent and research, students need access to at least one modern GPU. 

NOTE: I do NOT try to address allocation in this metric or analysis. There will of course be allocation issues. Some SLURM style setup with priority queues toggled by the PI will try to address, but that is independent of the # of GPUs per student. If you dont have enough GPUs, allocation policy doesnt really matter. And we are in that situation now in almost all major universities.

## Dispute Process

This is a contentious topic. All analysis, code, and raw data with receipts are available in this repo. If you disagree with anything, submit a PR with sources, and I will review it. If valid, I will update the numbers for your university.

## Methodology

Three key metrics:

1. **Weighted Student Count**: Weighted sum of CS students
   - 0.45 x Undergrad + 0.7 x Grad + 0.9 x PhD
   - Weights estimated based on % of students who have GPU demand (surveys done at Stanford)
   - Limited to CS department only (could arguably include EE, bio, etc)
   - We do not include online or part time CS students although we may in the future
   
2. **H100-equivalent GPU Count**: University-owned GPUs accessible to students
   - Converted to H100 equivalents using market prices
   - Example: 10 A100-80GB at $15k each = 4.3 H100-equivalents (H100 = $35k)

3. **GPUs per Student**: H100-equivalent count / Weighted student count

## National Lab / Grant-Wall GPU Exclusion Criteria 

We define "University GPUs" as hardware **owned and operated** by the university for its students. We exclude resources that are shared nationally or restricted to student access by grant walls.

| Resource Type | Status | Reason for Exclusion |
|:--- |:--- |:--- |
| **National Supercomputing Centers** (OSC, NCSA, etc.) | **Excluded** | These are shared utilities used by thousands of researchers from hundreds of universities. Counting them would double-count resources across every member institution. |
| **DOE National Labs** (Oak Ridge, Argonne, NERSC) | **Excluded** | These are federal government facilities, not university assets. Access is by competitive grant, not student enrollment. |
| **TACC (Frontera/Stampede3)** | **Excluded** | These specific systems are NSF-funded national resources open to all US researchers via ACCESS-CI (grant wall). <br> *Exception: UT Austin-owned systems hosted at TACC (e.g., Vista, Lonestar6 UT queues) ARE included.* |
| **Cloud Allocations** (AWS, Azure, GCP) | **Excluded** | Temporary, grant-based credits are not permanent infrastructure. They expire and vary wildly year-to-year. |
| **Consortium/Shared Clusters** (MGHPCC, SDSC) | **Excluded** | We exclude the "general shared" partitions used by external partners. We **include** the dedicated partitions owned specifically by the university (e.g., Harvard's Cannon cluster at MGHPCC). |
| **MIT Lincoln Labs** | **Excluded** | Restricted-access government/defense facility. Most MIT students cannot access these GPUs. |

## Project Structure

```
GPUsPerStudent/
├── data/
│   ├── filtered_national_universities_name_url.csv  # List of 165 universities
│   ├── gpu_prices.csv                               # GPU market prices
│   ├── master_data.csv                              # Generated output
│   └── cache/
│       └── final/                                   # Validated JSON files
├── web/
│   ├── index.html                                   # Main website
│   ├── style.css
│   └── data/
│       └── master_data.csv                          # Copy served by website
├── scripts/
│   ├── generate_master_data.py                      # Generates CSV from JSONs
│   └── validate_gpu_data.py                         # Validates GPU/student data
├── run_monthly_analysis.py                          # Main data collection script
├── prompt.md                                        # LLM prompt for data collection
└── prompt_validation.md                             # LLM prompt for validation
```

## How It Works

1. **Data Collection** (`run_monthly_analysis.py`)
   - Queries 3 LLMs (OpenAI, Claude, Gemini) for each university
   - Each LLM searches for student enrollment and GPU resources
   - Results aggregated using highest values with source validation
   - Output: JSON files in `data/cache/ensemble/` (internal cache)

2. **Validation** (`scripts/validate_gpu_data.py`)
   - Gemini reviews each JSON to filter shared resources
   - Estimates missing student counts
   - Output: Validated JSONs in `data/cache/final/`

3. **CSV Generation** (`scripts/generate_master_data.py`)
   - Reads validated JSONs
   - Calculates H100-equivalent counts and GPUs/student
   - Output: `data/master_data.csv`

4. **Website** (`web/`)
   - Static HTML/JS that reads master_data.csv
   - Sortable leaderboard with sources
   - Horizontal bar chart of all universities
