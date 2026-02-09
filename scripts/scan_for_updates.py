import os
import csv
import time
import argparse
import google.generativeai as genai
import google.ai.generativelanguage as glm
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Configuration
DATA_DIR = "data"
UNIVERSITIES_FILE = os.path.join(DATA_DIR, "filtered_national_universities_name_url.csv")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def scan_university(university_name):
    """
    Asks Gemini if there's recent news about new GPU clusters for this university.
    Returns: (boolean, string_reason)
    """
    print(f"Scanning {university_name}...")
    
    prompt = f"""
    Search for recent news (late 2025 or 2026) regarding new supercomputers, high-performance computing (HPC) clusters, or GPU acquisitions for "{university_name}".

    Focus on:
    1. Announcements of CLUSTERS (not just a few GPUs).
    2. Keywords like "H100", "H200", "B100", "B200", "GH200", "NVIDIA DGX", "SuperPOD".
    3. Dates: Late 2025 to present (Feb 2026).

    IGNORE:
    - National resources (ACCESS, NSF-owned) UNLESS the university is the primary owner/operator for its own students.
    - Small grants of <10 GPUs.
    - Research papers using existing GPUs.

    Return JSON ONLY:
    {{
      "has_new_large_cluster": true/false,
      "summary": "Brief summary of what was found or 'No new major announcements'."
    }}
    """

    try:
        # Use Gemini 3 Pro with Google Search
        tools = [glm.Tool(google_search={})]
        model = genai.GenerativeModel('gemini-3-pro-preview', tools=tools)
        response = model.generate_content(prompt)
        
        # Parse response
        import json
        import re
        
        text = response.text
        match = re.search(r"```json(.*?)```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
        elif text.startswith("```"):
            text = text.replace("```", "")
            
        data = json.loads(text)
        return data.get("has_new_large_cluster", False), data.get("summary", "")
        
    except Exception as e:
        print(f"  Error scanning {university_name}: {e}")
        return False, f"Error: {e}"

def main():
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY not found.")
        return

    # Load universities
    universities = []
    try:
        with open(UNIVERSITIES_FILE, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                universities.append(row['name']) # Verify column name 'name' or use 'University_Name' check
    except Exception as e:
        print(f"Error reading universities file: {e}")
        return

    flagged_universities = []
    
    print(f"Starting scan for {len(universities)} universities...")
    
    for i, uni in enumerate(universities):
        # Rate limit prevention (simple sleep)
        if i > 0 and i % 10 == 0:
            print("Sleeping 10s to be nice to API...")
            time.sleep(10)
            
        has_news, summary = scan_university(uni)
        
        if has_news:
            print(f"  [FLAGGED] {uni}: {summary}")
            flagged_universities.append(uni)
        else:
            print(f"  [Clean] {uni}")
            
    print("\n" + "="*40)
    print(f"Scan Complete. Found {len(flagged_universities)} universities with potential updates.")
    print("="*40)
    
    if flagged_universities:
        print("\nRun the following commands to update details:")
        for uni in flagged_universities:
            print(f'python3 scripts/run_monthly_analysis.py --university "{uni}" --provider ensemble')

if __name__ == "__main__":
    main()
