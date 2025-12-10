import os
import json
import csv
import pandas as pd
import google.generativeai as genai
from datetime import datetime
import time

# Configuration
DATA_DIR = "data"
UNIVERSITIES_FILE = os.path.join(DATA_DIR, "universities.csv")
GPU_PRICES_FILE = os.path.join(DATA_DIR, "gpu_prices.csv")
MASTER_OUTPUT_FILE = os.path.join(DATA_DIR, "master_data.csv")
PROMPT_FILE = "prompt.md"

# Weighting Constants (Stanford Model)
WEIGHT_UNDERGRAD = 0.45
WEIGHT_GRAD = 0.7
WEIGHT_PHD = 0.9

# API Setup
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("WARNING: GEMINI_API_KEY not found in environment. Running in MOCK mode.")

def load_gpu_prices():
    prices = {}
    try:
        df = pd.read_csv(GPU_PRICES_FILE)
        # Normalize keys for easier matching
        for _, row in df.iterrows():
            key = row['GPU'].lower().replace(" ", "_")
            prices[key] = float(row['Price_USD'])
            # Add specific variations if needed
            if "h100" in key and "svm" in key: prices["h100_sxm"] = row['Price_USD']
            if "h100" in key and "pcie" in key: prices["h100_pcie"] = row['Price_USD']
    except Exception as e:
        print(f"Error loading GPU prices: {e}")
        # Fallback defaults
        prices = {
            "h100_sxm": 35000, "h100_pcie": 30000, "a100_80gb": 15000, 
            "a100_40gb": 10000, "h200": 40000, "b200": 45000, 
            "b100": 35000, "a40": 4500, "a6000": 5000
        }
    return prices

def get_h100_reference_price(prices):
    return prices.get("h100_pcie", 30000)

def query_gemini(university_name, prompt_template):
    if not GEMINI_API_KEY:
        # MOCK RESPONSE
        return mock_response(university_name)

    prompt = prompt_template.replace("{{UNIVERSITY_NAME}}", university_name)
    
    try:
        model = genai.GenerativeModel('gemini-1.5-pro-latest') # Or appropriate model
        response = model.generate_content(prompt)
        text = response.text
        # Clean markdown if present
        if text.startswith("```json"):
            text = text.replace("```json", "").replace("```", "")
        elif text.startswith("```"):
            text = text.replace("```", "")
        return json.loads(text)
    except Exception as e:
        print(f"Error querying Gemini for {university_name}: {e}")
        return None

def mock_response(university_name):
    """Returns dummy data for testing without API Key"""
    import random
    return {
        "university_name": university_name,
        "data_retrieved_date": datetime.now().strftime("%Y-%m-%d"),
        "sources": ["mock_source_1", "mock_source_2"],
        "student_data": {
            "undergrad_cs_count": random.randint(500, 2000),
            "grad_cs_count": random.randint(100, 500),
            "phd_cs_count": random.randint(50, 200),
            "year": "Fall 2024",
            "notes": "Mock data"
        },
        "gpu_resources": {
            "h100_count": random.choice([0, 0, 8, 16]),
            "a100_80gb_count": random.choice([0, 4, 16, 32]),
            "a6000_count": random.randint(10, 50),
            "other_high_vram_gpus": [],
            "notes": "Mock cluster"
        },
        "compute_credits": {
            "total_annual_value_usd": 0,
            "description": "None"
        },
        "analysis_notes": "Mock analysis"
    }

def process_university(uni_name, prices, prompt_template):
    print(f"Processing {uni_name}...")
    data = query_gemini(uni_name, prompt_template)
    
    if not data:
        return None

    # Calculate Student Metrics
    s = data.get("student_data", {})
    u = s.get("undergrad_cs_count") or 0
    g = s.get("grad_cs_count") or 0
    p = s.get("phd_cs_count") or 0
    
    weighted_students = (u * WEIGHT_UNDERGRAD) + (g * WEIGHT_GRAD) + (p * WEIGHT_PHD)
    
    # Calculate GPU Value
    g_res = data.get("gpu_resources", {})
    total_value = 0
    
    # Map common keys from JSON to price dictionary
    # Assuming the prompt returns keys like "h100_count", "a100_80gb_count"
    # and prices dict has "h100_pcie", "h100_sxm", "a100_80gb"
    
    # H100
    h100_c = g_res.get("h100_count", 0) # Ambiguous, assumes PCIe or SXM avg? 
    # Use generic H100 price if specifics not known, or assume PCIe for lower bound?
    # Let's map "h100_count" to "h100_pcie" price for safety unless specified
    total_value += h100_c * prices.get("h100_pcie", 30000)
    
    total_value += g_res.get("h200_count", 0) * prices.get("h200", 40000)
    total_value += g_res.get("b200_count", 0) * prices.get("b200", 45000)
    total_value += g_res.get("a100_80gb_count", 0) * prices.get("a100_80gb", 15000)
    total_value += g_res.get("a100_40gb_count", 0) * prices.get("a100_40gb", 10000)
    total_value += g_res.get("a40_count", 0) * prices.get("a40", 4500)
    total_value += g_res.get("a6000_count", 0) * prices.get("a6000", 5000)

    # Compute Credits
    credits = data.get("compute_credits", {}).get("total_annual_value_usd", 0) or 0
    if credits:
        # Convert credits to H100 equivalents? 
        # User formula: H100s = credits / (365*24*hourly_rate)
        # H100 hourly rate ~ $3/hr? 
        HOURLY_RATE = 3.0
        h100_equiv = credits / (365 * 24 * HOURLY_RATE)
        # Value = H100 equiv * H100 Price (Purchase price)
        # Wait, user wants "weighted H100 count". 
        # If we just add the PURCHASE VALUE of the credits? 
        # No, credits are rental. 
        # A credit of $30k is ~1 H100 for a year (rental). 
        # Purchasing an H100 is also ~$30k (lifetime).
        # So $1 of credit ~= $1 of Hardware Value approx? 
        # Maybe slightly different, but for this draft, let's just add the credit value USD to total value.
        total_value += credits

    h100_ref_price = get_h100_reference_price(prices)
    weighted_h100_count = total_value / h100_ref_price if h100_ref_price else 0
    
    gpus_per_student = weighted_h100_count / weighted_students if weighted_students > 0 else 0

    return {
        "University": data.get("university_name"),
        "Rank": "N/A", # Placeholder
        "Undergrads_CS": u,
        "Grads_CS": g,
        "PhDs_CS": p,
        "B200s": g_res.get("b200_count", 0),
        "H100s": h100_c,
        "A100s": g_res.get("a100_80gb_count", 0) + g_res.get("a100_40gb_count", 0),
        "Weighted_Student_Count": round(weighted_students, 2),
        "Weighted_H100_Count": round(weighted_h100_count, 2),
        "Gpus_Per_Student": round(gpus_per_student, 4),
        "Notes": data.get("analysis_notes", "")
    }

def main():
    print("Starting Monthly Analysis...")
    
    # Load inputs
    try:
        uni_df = pd.read_csv(UNIVERSITIES_FILE)
        universities = uni_df['University_Name'].tolist()
    except Exception as e:
        print(f"Error reading universities file: {e}")
        return

    prices = load_gpu_prices()
    
    with open(PROMPT_FILE, 'r') as f:
        prompt_template = f.read()

    results = []
    
    # Process
    for uni in universities[:5]: # Limit to 5 for testing/draft
        res = process_university(uni, prices, prompt_template)
        if res:
            results.append(res)
        time.sleep(1) # Rate limit nice-ness

    # Save
    if results:
        df_out = pd.DataFrame(results)
        # Sort by GPUs Per Student Descending
        df_out = df_out.sort_values(by="Gpus_Per_Student", ascending=False)
        # Add Rank
        df_out['Rank'] = range(1, len(df_out) + 1)
        
        df_out.to_csv(MASTER_OUTPUT_FILE, index=False)
        print(f"Successfully saved {len(df_out)} records to {MASTER_OUTPUT_FILE}")
    else:
        print("No results generated.")

if __name__ == "__main__":
    main()
