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
   - Excludes: National labs, shared consortiums, grant-based allocations
   - Excludes: Private GPUs not accessible to students (e.g., Lincoln Labs)

3. **GPUs per Student**: H100-equivalent count / Weighted student count

## What We Exclude (Important!)

These shared/national resources are NOT counted for any university:
- Ohio Supercomputer Center (OSC) - shared by 2,700 institutions
- NCAR-Wyoming Supercomputing Center - shared by 575 universities
- Texas Advanced Computing Center (TACC)
- San Diego Supercomputer Center (SDSC)
- Massachusetts Green HPC Center (MGHPCC)
- DOE Labs (Oak Ridge, Argonne, LBNL/NERSC, etc)
- MIT Lincoln Labs
- Cloud allocations (AWS, GCP, Azure)
- XSEDE/ACCESS allocations

Only resources the university directly owns and operates count.

## Project Structure

```
GPUsPerStudent/
├── data/
│   ├── filtered_national_universities_name_url.csv  # List of 165 universities
│   ├── gpu_prices.csv                               # GPU market prices
│   ├── master_data.csv                              # Generated output
│   └── cache/
│       ├── ensemble/                                # Raw LLM ensemble results
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
   - Output: JSON files in `data/cache/ensemble/`

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

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set API keys
export GEMINI_API_KEY="your_key"
export OPENAI_API_KEY="your_key"  
export ANTHROPIC_API_KEY="your_key"

# Run full ensemble (takes hours)
python run_monthly_analysis.py --provider ensemble

# Or just regenerate CSV from existing data
python scripts/generate_master_data.py
cp data/master_data.csv web/data/

# Run local server
cd web && python -m http.server 8080
```

## Deployment

### Netlify Drop (Easiest)
1. Run `python scripts/generate_master_data.py`
2. Go to [app.netlify.com/drop](https://app.netlify.com/drop)
3. Drag the `web` folder onto the page
4. Done!

## Data Files

Each university has a JSON file in `data/cache/final/` containing:
- Student counts (undergrad, grad, PhD)
- GPU counts by type (H100, A100, V100, etc)
- Source URLs for verification
- Validation notes explaining any adjustments

## Contributing

PRs welcome! If your university's data is wrong:
1. Check the JSON file in `data/cache/final/YourUniversity.json`
2. Submit a PR with corrected data and sources
3. I will review and merge if valid

## License

MIT License - Copyright (c) 2025 Francois Chaubard

See LICENSE file for details.
