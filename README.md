# GPUs Per Student

This project tracks and analyzes the availability of high-performance computing resources (specifically GPUs) relative to the student population in Computer Science departments across US universities.

The goal is to provide a standardized metric ("GPUs per Student") to quantify access to compute for research and education.

## Methodology

The analysis focuses on three key metrics:
1.  **Student Count**: Weighted sum of CS students (0.45 * Undergrad + 0.7 * Grad + 0.9 * PhD).
2.  **GPU Resources**: Count of university-owned high-performance GPUs (H100, A100, etc.), weighted by market value relative to an H100 reference price.
3.  **GPUs per Student**: The ratio of the weighted H100 count to the weighted student count.

Data is aggregated monthly via an automated pipeline that queries university resources and enrollment data.

## Project Structure

*   `data/`: Contains the core datasets (universities list, GPU prices) and the generated master dataset.
*   `web/`: Static frontend for visualizing the data (Leaderboard and Charts).
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

Proprietary. All rights reserved.
