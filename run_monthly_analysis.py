import os
import json
import csv
import pandas as pd
import google.generativeai as genai
from datetime import datetime
import time

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DATA_DIR = "data"
UNIVERSITIES_FILE = os.path.join(DATA_DIR, "universities.csv")
GPU_PRICES_FILE = os.path.join(DATA_DIR, "gpu_prices.csv")
MASTER_OUTPUT_FILE = os.path.join("web", "data", "master_data.csv")
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
            # Clean: "NVIDIA H100 SXM" -> "h100_sxm"
            raw = row['GPU'].lower()
            key = raw.replace("nvidia ", "").replace(" ", "_").strip()
            # specific cleanup if needed
            if "rtx_a6000" in key: key = "a6000" # normalize to match prompt key if preferred
            
            prices[key] = float(row['Price_USD'])
            
    except Exception as e:
        print(f"Error loading GPU prices: {e}")
        # Fallback defaults
        prices = {
            "h100_sxm": 35000, "h100_pcie": 30000, "a100_80gb": 15000, 
            "a100_40gb": 10000, "h200": 40000, "b200": 45000, 
            "b100": 35000, "a40": 4500, "a6000": 5000, "l40s": 8000
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
    
    # GPU KEYS MAPPING (Prompt Key -> Price Key)
    # Price keys: h100_sxm, h100_pcie, h200, a100_80gb, a100_40gb, b200, b100, a40, a6000, l40s
    # Prompt keys: h100_sxm_count, h100_pcie_count, etc.
    
    gpu_counts = {}
    
    # helper to safely get count
    def get_cnt(key):
        val = g_res.get(key, 0)
        return int(val) if val is not None else 0

    # Explicit mapping for clarity and matching columns
    # (Count Key in JSON, Price Key in CSV)
    mapping = [
        ("h100_sxm_count", "h100_sxm"),
        ("h100_pcie_count", "h100_pcie"), # Fallback if just h100_count used?
        ("h200_count", "h200"),
        ("b200_count", "b200"),
        ("b100_count", "b100"),
        ("a100_80gb_count", "a100_80gb"),
        ("a100_40gb_count", "a100_40gb"),
        ("a40_count", "a40"),
        ("a6000_count", "a6000"), # prompt says "a6000_count", price says "rtx_a6000"? check load_gpu_prices
        ("l40s_count", "l40s")
    ]
    
    for json_key, price_key in mapping:
        count = get_cnt(json_key)
        # Handle "h100_count" legacy if key missing?
        if price_key == "h100_pcie" and count == 0 and "h100_count" in g_res:
             count = get_cnt("h100_count") # Assume PCIe if unspecified
        
        gpu_counts[price_key] = count
        price = prices.get(price_key, 0)
        if price == 0:
             # Try to find loose match in prices keys
             # load_gpu_prices normalizes to lower().replace(" ", "_")
             # e.g. "nvidia_rtx_a6000" -> "nvidia_rtx_a6000"? No, check load_gpu_prices
             pass

        total_value += count * price
        
    # Formatting Notes with Sources
    sources = data.get("sources", [])
    raw_notes = g_res.get("notes", "")
    student_notes = s.get("notes", "")
    
    formatted_notes = raw_notes + " ; " + student_notes
    if sources:
        formatted_notes += " | Sources: " + ", ".join(sources)

    # Compute Credits
    credits = data.get("compute_credits", {}).get("total_annual_value_usd", 0) or 0
    if credits:
        total_value += credits
        formatted_notes += f" | Credits: ${credits}"

    h100_ref_price = get_h100_reference_price(prices)
    weighted_h100_count = total_value / h100_ref_price if h100_ref_price else 0
    
    gpus_per_student = weighted_h100_count / weighted_students if weighted_students > 0 else 0

    # Build Result Dictionary
    res = {
        "University": data.get("university_name"),
        "Rank": "N/A",
        "Undergrads_CS": u,
        "Grads_CS": g,
        "PhDs_CS": p,
        "Weighted_Student_Count": round(weighted_students, 2),
        "Weighted_H100_Count": round(weighted_h100_count, 2),
        "Gpus_Per_Student": round(gpus_per_student, 4),
        "Notes": formatted_notes
    }
    
    # Add GPU columns
    for _, price_key in mapping:
        # format column name? user says "B200s", "H100s"..
        # Let's clean up key for display: "h100_sxm" -> "H100_SXM"
        col_name = price_key.upper().replace("_", " ")
        res[col_name] = gpu_counts[price_key]
        
    return res

def main():
    print("Starting Monthly Analysis...")
    
    # Load inputs
    try:
        uni_df = pd.read_csv(UNIVERSITIES_FILE)
        # Handle different column names
        if 'name' in uni_df.columns:
             universities = uni_df['name'].tolist()
        elif 'University_Name' in uni_df.columns:
             universities = uni_df['University_Name'].tolist()
        else:
             print("Error: Column 'name' or 'University_Name' not found in universities.csv")
             return
    except Exception as e:
        print(f"Error reading universities file: {e}")
        return

    prices = load_gpu_prices()
    
    with open(PROMPT_FILE, 'r') as f:
        prompt_template = f.read()

    results = []
    
    # Process
    for uni in universities: 
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
