# GPUs Per Student Initiative (gpusperstudent.org)

This project tracks and analyzes the availability of GPUs relative to the student population in Computer Science departments across US universities. 

# Why

After [this](https://x.com/FrancoisChauba1/status/1997095264923078856) tweet went viral, it was clear to me that more effort on this analysis would be valuable to the world. Students are clearly unhappy and going to bigger labs to get their research done because of access to GPUs and some faculty are clearly unaware of the issue. Students argued we should include the full university, faculty argued we shouldnt include any undergrads, faculty argued we should include external compute resources (NCSU, Oak Ridge, etc), students argued that we shouldnt include anything that requires a tedious grant process, etc. So I have tried to toe the line to try to make everyone happy and make it as fair as possible. 

The goal is to provide a standardized metric ("GPUs per Student") to quantify access to compute for research and education. If we want more AI talent, students need GPUs to learn and try stuff. If we want more research, students need minimally sufficient GPUs to conduct research (at least 1 modern GPU!). We want to open this up to the world to shine light on the issue of GPU availability across the US which we have seen be suboptimal. 

# Dispute Process
Since this is highly contentious topic as my tweet highlighted, a dispute process is needed. I have made all the analysis, code, and raw data with receipts available in this repo. If you disagree with any of it, you can submit a PR and I will look at it and if valid, I will update your numbers for your university. 

# GPUs Per Student

## Methodology

The analysis focuses on three key metrics:
1.  **Weighted Student Count**: Weighted sum of CS students (0.45 * Undergrad + 0.7 * Grad + 0.9 * PhD) who would benefit from access to GPUs in general. These weights comes from surveys done at Stanford on who would like access, and would admittedly vary from university to university and from time to time. While we could arguably add all of EE, maybe all of eng, and some of bio, we limit it to CS dept only. 
2.  **H100-equivalent GPU Resources**: Count of university-owned, generally accessible to degree program students, high-performance GPUs (H100, A100, etc.), weighted by market value relative to an H100 reference price. For example, if a university has 10 A100-80G (retail price $9,000 lets say) and no H100s (retail price $40,000 lets say), then we will compute the estimated H100-equivalent GPUs to be 2.25 H100-equivalent GPUs (or more simply 2.25 GPUs for short). If a university doesnt own GPUs, but does provide $40k of compute credits available to each student per month, then we convert this to 1.14 H100-equivalent GPUs (assuming an H100-hour is $4/hr then 40000/(4*365*24) = 1.14). If a university doesnt own GPUs, but claim they can apply for grants to national labs or cloud providers or NVIDIA Academic Grant Program to access GPUs, this is not provided. If a university has private GPUs that are not accessible to degree program students, and only a separate group such as is the case for Lincoln Labs, these GPUs will NOT be included as they are not available to the students. 
3.  **GPUs per Student**: The ratio of the H100-equivalent count to the weighted student count.

Data is aggregated monthly via an automated pipeline that queries university resources and enrollment data.

## Project Structure

*   `data/`: Contains the core datasets (universities list, GPU prices) and the generated master dataset.
*   `run_monthly_analysis.py`: Main execution script for data gathering and processing.
*   `.github/workflows`: Automation configuration for monthly updates.

## Usage

To run the analysis locally:

1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

2.  Set the environment variable for the automated research agent:
    ```bash
    export GEMINI_API_KEY="your_key"
    ```

3.  Execute the script:
    ```bash
    python run_monthly_analysis.py
    ```

## License

MIT License

Copyright (c) 2025 [Francois Chaubard]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this data or software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

