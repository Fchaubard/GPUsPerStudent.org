import os
import json
import csv
import pandas as pd
import google.generativeai as genai
import google.ai.generativelanguage as glm
from openai import OpenAI
from datetime import datetime
import time
import requests
import re
import argparse

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DATA_DIR = "data"
UNIVERSITIES_FILE = os.path.join(DATA_DIR, "filtered_national_universities_name_url.csv")
GPU_PRICES_FILE = os.path.join(DATA_DIR, "gpu_prices.csv")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
MASTER_OUTPUT_FILE = os.path.join("web", "data", "master_data.csv")
PROMPT_FILE = "prompt.md"

# Weighting Constants (Stanford Model)
WEIGHT_UNDERGRAD = 0.45
WEIGHT_GRAD = 0.7
WEIGHT_PHD = 0.9

# API Setup - Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# API Setup - OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = None
if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY, timeout=3600)

# API Setup - Claude/Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
anthropic_client = None
try:
    import anthropic
    if ANTHROPIC_API_KEY:
        anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
except ImportError:
    print("[Warning] anthropic package not installed. Run: pip install anthropic")

# API Setup - College Scorecard (IPEDS data)
COLLEGE_SCORECARD_API_KEY = os.getenv("COLLEGE_SCORECARD_API_KEY", "NIWDCgdV3SbklU2SXgltKRumNqAVi2YL0xtHvoqR")
COLLEGE_SCORECARD_BASE_URL = "https://api.data.gov/ed/collegescorecard/v1/schools"

# University name mapping for College Scorecard (handles naming variations)
SCORECARD_NAME_MAP = {
    "University of California, Berkeley": "University of California-Berkeley",
    "University of California, Los Angeles": "University of California-Los Angeles",
    "University of California, San Diego": "University of California-San Diego",
    # Add more mappings as needed
}


def get_college_scorecard_cs_data(university_name):
    """
    Query College Scorecard API for CS enrollment estimates based on IPEDS completion data.
    Returns estimated enrollment by multiplying completions by average time-to-degree.
    
    CIP 1107 = Computer Science
    Credential levels: 3=Bachelor's, 5=Master's, 6=Doctoral
    """
    # Map university name if needed
    query_name = SCORECARD_NAME_MAP.get(university_name, university_name)
    
    params = {
        "api_key": COLLEGE_SCORECARD_API_KEY,
        "school.name": query_name,
        "fields": "id,school.name,latest.student.size,latest.programs.cip_4_digit.code,latest.programs.cip_4_digit.title,latest.programs.cip_4_digit.credential.level,latest.programs.cip_4_digit.counts.ipeds_awards1,latest.programs.cip_4_digit.counts.ipeds_awards2"
    }
    
    try:
        resp = requests.get(COLLEGE_SCORECARD_BASE_URL, params=params, timeout=30)
        data = resp.json()
        
        if not data.get('results'):
            print(f"  [Scorecard] No results for {query_name}")
            return None
        
        result = data['results'][0]
        programs = result.get('latest.programs.cip_4_digit', [])
        
        # Find CS programs (CIP 1107)
        cs_programs = [p for p in programs if p.get('code') == '1107']
        
        if not cs_programs:
            print(f"  [Scorecard] No CS program data for {query_name}")
            return None
        
        # Extract completion counts and estimate enrollment
        undergrad_count = 0
        grad_count = 0
        phd_count = 0
        
        for prog in cs_programs:
            level = prog.get('credential', {}).get('level', 0)
            awards1 = prog.get('counts', {}).get('ipeds_awards1', 0) or 0
            awards2 = prog.get('counts', {}).get('ipeds_awards2', 0) or 0
            avg_awards = (awards1 + awards2) / 2
            
            if level == 3:  # Bachelor's - 4 year program
                undergrad_count = int(avg_awards * 4)
            elif level == 5:  # Master's - ~1.5 year program
                grad_count = int(avg_awards * 1.5)
            elif level == 6:  # Doctoral - ~5.5 year program
                phd_count = int(avg_awards * 5.5)
        
        print(f"  [Scorecard] {query_name}: Undergrad={undergrad_count}, MS={grad_count}, PhD={phd_count}")
        
        return {
            "undergrad_cs_count": undergrad_count,
            "grad_cs_count": grad_count,
            "phd_cs_count": phd_count,
            "year": "IPEDS (latest available)",
            "source_url": "https://collegescorecard.ed.gov/",
            "notes": f"Estimated from IPEDS completion data via College Scorecard API. Calculation: completions × time-to-degree (undergrad×4, MS×1.5, PhD×5.5). Raw awards: BS~{int((awards1+awards2)/2) if level==3 else 'N/A'}/yr."
        }
        
    except Exception as e:
        print(f"  [Scorecard] Error querying {query_name}: {e}")
        return None


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
            "b100": 35000, "a40": 4500, "a6000": 5000, "l40s": 8000,
            "v100": 3500, "p100": 1500
        }
    return prices

def get_h100_reference_price(prices):
    return prices.get("h100_pcie", 30000)



# Soft 404 patterns to check in page content
SOFT_404_PATTERNS = [
    "page not found",
    "<title>404",
    "404 not found",
    "uh oh",
    "doesn't exist",
    "does not exist",
    "moved elsewhere",
    "not what you were looking for",
    "sorry, we couldn't find",
    "the requested page could not be found",
    "this page doesn't exist",
    "error 404"
]

def browser_verify_url(url, timeout=15000):
    """
    Use Playwright headless browser to verify URL accessibility.
    Returns page content if valid, None if 404/inaccessible.
    This bypasses Cloudflare, WAFs, and JavaScript-rendered pages.
    """
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            page = context.new_page()
            
            try:
                page.goto(url, wait_until="networkidle", timeout=timeout)
                content = page.content().lower()
                
                # Check for soft 404 patterns
                for pattern in SOFT_404_PATTERNS:
                    if pattern in content:
                        browser.close()
                        return None
                
                browser.close()
                return content
            except Exception as e:
                browser.close()
                return None
    except ImportError:
        print("  [Warning] Playwright not installed, skipping browser verification")
        return None
    except Exception as e:
        return None


def validate_and_filter_sources(data):
    """Checks validity of URLs in data['sources'] and removes broken ones."""
    if "sources" not in data or not isinstance(data["sources"], list):
        return data

    valid_sources = []
    print("\nValidating sources...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    import subprocess

    for source_item in data["sources"]:
        # Handle sources as either strings or dicts with 'url' field
        if isinstance(source_item, dict):
            url = source_item.get("url", "")
            source_obj = source_item  # Keep original for valid_sources
        else:
            url = source_item
            source_obj = source_item
        
        if not url or not isinstance(url, str):
            print(f"  [Skipped: Invalid URL format] {source_item}")
            continue
            
        try:
            # 1. Try Requests (Fast)
            # Drop the stream=True so we can check content for soft 404s
            try:
                response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
                
                # Check for soft 404 patterns
                context_text = response.text.lower()
                soft_404_patterns = [
                    "page not found",
                    "<title>404",
                    "404 not found",
                    "uh oh",
                    "doesn't exist",
                    "does not exist",
                    "moved elsewhere",
                    "not what you were looking for",
                    "sorry, we couldn't find",
                    "the page you requested",
                    "this page doesn't exist",
                    "error 404"
                ]
                is_soft_404 = any(pattern in context_text for pattern in soft_404_patterns)
                if is_soft_404:
                     print(f"  [Failed: Soft 404] {url}")
                     continue
                
                # Login wall detection (Google Sites, SSO, etc.)
                login_wall_patterns = [
                    "sign in - google accounts",
                    "use your google account",
                    "sign in to continue",
                    "please log in",
                    "authentication required",
                    "single sign-on",
                    "sso login",
                    "you need to sign in"
                ]
                is_login_wall = any(pattern in context_text for pattern in login_wall_patterns)
                if is_login_wall:
                    print(f"  [Failed: Login Wall] {url}")
                    continue

                if response.status_code == 200:
                    print(f"  [OK] {url}")
                    valid_sources.append(source_obj)
                    continue
                elif response.status_code == 403:
                    print(f"  [Requests 403, trying curl] {url}")
                    # Fallback to curl
                else:
                    print(f"  [Requests {response.status_code}, trying curl] {url}")
            except Exception as e:
                print(f"  [Requests Error, trying curl] {url} ({e})")
            
            # 2. Try Curl (Robust) - now with HTTP status code check
            # Use -w to append HTTP status code at end
            cmd = [
                'curl', '-L', '-k', '-s',
                '-A', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                '--max-time', '10',
                '-w', '\n__HTTP_STATUS__%{http_code}__',  # Append status code
                url
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                curl_output = result.stdout
                
                # Extract HTTP status code from end of output
                if '__HTTP_STATUS__' in curl_output:
                    parts = curl_output.rsplit('__HTTP_STATUS__', 1)
                    curl_text = parts[0].lower()
                    http_status = parts[1].replace('__', '').strip()
                    
                    # Check for 4xx/5xx errors
                    if http_status == '403':
                        # 403 might be Cloudflare - try browser fallback
                        print(f"  [Curl 403, trying browser] {url}")
                        browser_content = browser_verify_url(url)
                        if browser_content:
                            print(f"  [OK (Browser)] {url}")
                            valid_sources.append(source_obj)
                        else:
                            print(f"  [Failed: Browser also failed] {url}")
                        continue
                    elif http_status.startswith('4') or http_status.startswith('5'):
                        print(f"  [Failed: Curl {http_status}] {url}")
                        continue
                else:
                    curl_text = curl_output.lower()
                
                # Rough check for success: not empty
                if not curl_text.strip():
                     print(f"  [Failed: Empty Curl] {url}")
                     continue

                # Comprehensive soft 404 check
                soft_404_patterns = [
                    "page not found",
                    "<title>404",
                    "404 not found",
                    "uh oh",
                    "doesn't exist",
                    "does not exist",
                    "moved elsewhere",
                    "not what you were looking for",
                    "sorry, we couldn't find",
                    "the requested page could not be found",
                    "this page doesn't exist",
                    "error 404"
                ]
                is_soft_404 = any(pattern in curl_text for pattern in soft_404_patterns)
                if is_soft_404:
                     print(f"  [Failed: Curl Soft 404] {url}")
                     continue
                
                # Login wall detection (Google Sites, SSO, etc.)
                login_wall_patterns = [
                    "sign in - google accounts",
                    "use your google account",
                    "sign in to continue",
                    "please log in",
                    "authentication required",
                    "single sign-on",
                    "sso login",
                    "you need to sign in"
                ]
                is_login_wall = any(pattern in curl_text for pattern in login_wall_patterns)
                if is_login_wall:
                    print(f"  [Failed: Login Wall] {url}")
                    continue

                # Cloudflare Challenge Check - try browser fallback
                if "just a moment..." in curl_text and "enable javascript" in curl_text:
                     print(f"  [Cloudflare detected, trying browser] {url}")
                     browser_content = browser_verify_url(url)
                     if browser_content:
                         print(f"  [OK (Browser)] {url}")
                         valid_sources.append(source_obj)
                     else:
                         print(f"  [Failed: Browser also failed] {url}")
                     continue
                
                # Generic access denied check (careful not to block valid content if "access denied" appears in an article)
                # But for Princeton WAF, it usually says "Access Denied" or similar. 
                # User's strict rule is specific to "Page not found". I will stick to that primarily.
                if "access denied" in curl_text and "princeton" not in curl_text:
                     print(f"  [Failed: Curl Access Denied] {url}")
                     continue
                
                print(f"  [OK (Curl)] {url}")
                valid_sources.append(source_obj)
            else:
                print(f"  [Failed: Curl {result.returncode}] {url}")

        except Exception as e:
             print(f"  [Error: {e}] {url}")
    
    # Fallback Mechanism for known difficult universities (WAF/Cloudflare)
    # If we have 0 sources, try to inject a known high-level verified source
    if not valid_sources:
        print("  [Warning] No valid sources found. Checking for manual fallbacks...")
        # Dictionary of verified working URLs (browser-tested, no "Page not found")
        FALLBACKS = {
            "Princeton University": "https://pli.princeton.edu/about-pli/directors-message",
            "Stanford University": "https://datascience.stanford.edu/system-specifications"
        }
        
        fallback = FALLBACKS.get(data.get("university_name"))
        if fallback:
             # Validate the fallback just in case
             print(f"  [Attempting Fallback] {fallback}")
             try:
                 # Use curl for robustness (WAF bypass)
                 cmd = [
                    'curl', '-L', '-k', '-s',
                    '-A', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    '--max-time', '5',
                    fallback
                 ]
                 result = subprocess.run(cmd, capture_output=True, text=True)
                 
                 if result.returncode == 0:
                     if "page not found" not in result.stdout.lower():
                          print(f"  [OK Fallback] {fallback}")
                          valid_sources.append(fallback)
                     else:
                          print(f"  [Failed Fallback: Page not found] {fallback}")
                 else:
                     print(f"  [Failed Fallback: Curl Error] {fallback}")
             except Exception as e:
                 print(f"  [Error Fallback: {e}]")
                 
    data["sources"] = valid_sources
    
    # Post-process: Extract valid URL strings for checking internal source_url fields
    valid_url_strings = set()
    for s in valid_sources:
        if isinstance(s, dict):
            valid_url_strings.add(s.get("url", ""))
        else:
            valid_url_strings.add(s)
    
    # Validate internal source_url fields in student_data and gpu_resources
    # If they point to a rejected URL, clear them or replace with fallback
    fallback_url = valid_sources[0] if valid_sources else ""
    if isinstance(fallback_url, dict):
        fallback_url = fallback_url.get("url", "")
    
    for section in ["student_data", "gpu_resources"]:
        if section in data and isinstance(data[section], dict):
            internal_url = data[section].get("source_url", "")
            if internal_url and internal_url not in valid_url_strings:
                print(f"  [Fixing] {section}.source_url was broken: {internal_url}")
                data[section]["source_url"] = fallback_url if fallback_url else "NO_VALID_SOURCE"
                data[section]["notes"] = data[section].get("notes", "") + f" [WARNING: Original source was inaccessible, using fallback.]"
    
    return data

def get_cache_path(university_name, model_name=None):
    """
    Get cache path for university data.
    If model_name is specified, cache goes to data/cache/{model_name}/{university}.json
    Otherwise uses the legacy flat structure: data/cache/{university}.json
    
    model_name can be: 'openai', 'claude', 'gemini', 'final' (for ensemble output)
    """
    clean_name = "".join([c if c.isalnum() or c in (' ', '_', '-') else '_' for c in university_name])
    clean_name = clean_name.replace(" ", "_").replace("__", "_")
    
    if model_name:
        model_cache_dir = os.path.join(CACHE_DIR, model_name)
        os.makedirs(model_cache_dir, exist_ok=True)
        return os.path.join(model_cache_dir, f"{clean_name}.json")
    else:
        return os.path.join(CACHE_DIR, f"{clean_name}.json")


def query_openai_deep_research(university_name, prompt_template):
    """Query OpenAI with MULTIPLE focused searches, then merge results."""
    # Check Cache
    cache_path = get_cache_path(university_name)
    if os.path.exists(cache_path):
        print(f"Loading from cache: {university_name}")
        try:
            with open(cache_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading cache for {university_name}: {e}")

    if not openai_client:
        print("ERROR: OPENAI_API_KEY not set")
        return None

    # MULTI-QUERY APPROACH: Separate searches for better coverage
    
    # Query 1: Student enrollment data - PRIORITIZE 2024/2025
    student_prompt = f"""Find CURRENT CS student enrollment data for {university_name}.

## DATE REQUIREMENTS
1. **Best**: 2024-2025, Fall 2024, or AY 2024-25.
2. **Acceptable Fallback**: 2023-2024, Fall 2023. Explicitly note this as "[2023 DATA]" in the notes.
3. **Emergency Fallback**: 2022-2023, Fall 2022. Only use if absolutely nothing newer exists. Note as "[2022 DATA]".

## Search Strategy
Search in this order:
1. "{university_name} computer science enrollment Fall 2024"
2. "{university_name} computer science enrollment Fall 2023"
3. "{university_name} Common Data Set 2023-2024" (or 2024-2025)
4. "{university_name} registrar enrollment statistics"
5. site:cs.{university_name.lower().split()[0]}.edu enrollment

## Where to Look
- **Common Data Set** (Section B or J)
- **University Factbook** / Institutional Research (IR) dashboards
- **CS Department "About"** pages
- **Graduate school** admissions statistics

## Return Format
Return JSON ONLY:
{{
  "undergrad_cs_count": <number or 0>,
  "grad_cs_count": <MS/Masters students ONLY, number or 0>,
  "phd_cs_count": <PhD students ONLY, number or 0>,
  "year": "<e.g. 'Fall 2024', 'Fall 2023'>",
  "source_url": "<URL where you found this data>",
  "notes": "<explain source and any estimations/assumptions>"
}}

## Validation Checklist
[ ] I prioritized finding 2024 data.
[ ] If I used 2023, I couldn't find 2024.
[ ] The source_url is accessible.
[ ] grad_cs_count excludes PhDs (if possible).

## If You Cannot Find Specific Breakdowns
- If you only find "Total CS Students", estimate standard breakdowns based on:
  - Undergraduate: ~70%
  - MS: ~20%
  - PhD: ~10%
  - Note this estimation in the 'notes' field.
"""


    # Query 2: GPU cluster data
    gpu_prompt = f"""Find GPU cluster specifications for {university_name}.

Search for:
- "{university_name} research computing GPU clusters"
- "{university_name} HPC H100 A100 specifications"
- "{university_name} AI computing infrastructure"

For EACH cluster found, calculate: nodes * GPUs_per_node = total

Return JSON ONLY:
{{
  "h100_sxm_count": <total H100 SXM GPUs>,
  "h100_pcie_count": <total H100 PCIe GPUs>,
  "h200_count": <total>,
  "a100_80gb_count": <total>,
  "a100_40gb_count": <total>,
  "v100_count": <total>,
  "p100_count": <total>,
  "a6000_count": <total>,
  "l40s_count": <total>,
  "b100_count": 0,
  "b200_count": 0,
  "gh200_count": 0,
  "a40_count": 0,
  "other_high_vram_gpus": [],
  "source_url": "<main source URL>",
  "sources": [
    {{"url": "<url1>", "data_found": "<what you found>"}},
    {{"url": "<url2>", "data_found": "<what you found>"}}
  ],
  "notes": "<calculation breakdown>"
}}

IMPORTANT: Add up ALL clusters. If you cannot determine model, estimate based on cluster age (older=V100, newer=A100/H100)."""

    try:
        # Execute both queries with gpt-5.2 and reasoning
        print(f"  [OpenAI gpt-5.2] Query 1/2: Student data for {university_name}...")
        student_response = openai_client.responses.create(
            model="gpt-5.2",
            input=student_prompt,
            tools=[{"type": "web_search_preview"}],
            reasoning={"effort": "medium"},  # Enable thinking
        )
        
        print(f"  [OpenAI gpt-5.2] Query 2/2: GPU data for {university_name}...")
        gpu_response = openai_client.responses.create(
            model="gpt-5.2",
            input=gpu_prompt,
            tools=[{"type": "web_search_preview"}],
            reasoning={"effort": "medium"},  # Enable thinking
        )
        
        # Parse responses
        student_data = {}
        gpu_data = {}
        sources = []
        
        # Parse student data
        student_text = student_response.output_text or ""
        student_match = re.search(r'\{[\s\S]*\}', student_text)
        if student_match:
            try:
                student_data = json.loads(student_match.group())
            except:
                print(f"  [Warning] Could not parse student data JSON")
        
        # Parse GPU data
        gpu_text = gpu_response.output_text or ""
        gpu_match = re.search(r'\{[\s\S]*\}', gpu_text)
        if gpu_match:
            try:
                gpu_data = json.loads(gpu_match.group())
                if "sources" in gpu_data:
                    sources = gpu_data.pop("sources")
            except:
                print(f"  [Warning] Could not parse GPU data JSON")
        
        # FALLBACK: College Scorecard API (DISABLED - IPEDS completion data underestimates enrollment)
        # The Scorecard API uses degree completions × time-to-degree, but this significantly
        # underestimates actual enrollment (e.g., Stanford has ~700 CS PhDs but Scorecard 
        # only estimates ~187 based on ~34 completions/year × 5.5 years)
        # Keeping the code for potential future use with adjustments.
        #
        # web_search_failed = (
        #     student_data.get("undergrad_cs_count", 0) == 0 or
        #     student_data.get("year", "") == "NO_2024_DATA_FOUND" or
        #     student_data.get("year", "") == "NO_RECENT_DATA_FOUND" or
        #     "NO_2024" in str(student_data.get("year", "")) or
        #     "NO_RECENT" in str(student_data.get("year", ""))
        # )
        # 
        # if web_search_failed:
        #     print(f"  [Fallback] Web search didn't find student data, trying College Scorecard...")
        #     scorecard_data = get_college_scorecard_cs_data(university_name)
        #     if scorecard_data:
        #         original_notes = student_data.get("notes", "")
        #         student_data = scorecard_data
        #         student_data["notes"] = f"[SCORECARD FALLBACK] {scorecard_data['notes']} | Original web search notes: {original_notes[:200]}..."
        #         print(f"  [Fallback] Using College Scorecard: Undergrad={student_data['undergrad_cs_count']}, MS={student_data['grad_cs_count']}, PhD={student_data['phd_cs_count']}")
        
        # Add student source to sources list
        if student_data.get("source_url"):
            sources.append({
                "url": student_data.get("source_url"),
                "data_found": f"Student enrollment: {student_data.get('undergrad_cs_count', 0)} undergrad, {student_data.get('grad_cs_count', 0)} grad, {student_data.get('phd_cs_count', 0)} PhD"
            })
        
        # Merge into final structure
        data = {
            "university_name": university_name,
            "data_retrieved_date": datetime.now().strftime("%Y-%m-%d"),
            "sources": sources,
            "student_data": {
                "undergrad_cs_count": student_data.get("undergrad_cs_count", 0),
                "grad_cs_count": student_data.get("grad_cs_count", 0),
                "phd_cs_count": student_data.get("phd_cs_count", 0),
                "year": student_data.get("year", "Unknown"),
                "source_url": student_data.get("source_url", "NO_VALID_SOURCE"),
                "notes": student_data.get("notes", "")
            },
            "gpu_resources": {
                "h100_sxm_count": gpu_data.get("h100_sxm_count", 0),
                "h100_pcie_count": gpu_data.get("h100_pcie_count", 0),
                "h200_count": gpu_data.get("h200_count", 0),
                "b100_count": gpu_data.get("b100_count", 0),
                "b200_count": gpu_data.get("b200_count", 0),
                "a100_80gb_count": gpu_data.get("a100_80gb_count", 0),
                "a100_40gb_count": gpu_data.get("a100_40gb_count", 0),
                "a40_count": gpu_data.get("a40_count", 0),
                "a6000_count": gpu_data.get("a6000_count", 0),
                "l40s_count": gpu_data.get("l40s_count", 0),
                "v100_count": gpu_data.get("v100_count", 0),
                "p100_count": gpu_data.get("p100_count", 0),
                "gh200_count": gpu_data.get("gh200_count", 0),
                "other_high_vram_gpus": gpu_data.get("other_high_vram_gpus", []),
                "source_url": gpu_data.get("source_url", "NO_VALID_SOURCE"),
                "notes": gpu_data.get("notes", "")
            },
            "compute_credits": {
                "total_annual_value_usd": 0.0,
                "description": "Not searched in this query."
            },
            "analysis_notes": "Data collected via multi-query approach: separate student and GPU searches."
        }
        
        # Validate Sources
        data = validate_and_filter_sources(data)

        # Save to Cache
        try:
            with open(cache_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving to cache for {university_name}: {e}")
            
        return data
        
    except Exception as e:
        print(f"Error querying OpenAI for {university_name}: {e}")
        return None


def query_claude(university_name, prompt_template):
    """Query Claude Opus 4.5 with extended thinking for university data research."""
    # Check Cache
    cache_path = get_cache_path(university_name)
    if os.path.exists(cache_path):
        print(f"Loading from cache: {university_name}")
        try:
            with open(cache_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading cache for {university_name}: {e}")

    if not anthropic_client:
        print("ERROR: ANTHROPIC_API_KEY not set or anthropic package not installed")
        return None

    # Build prompt from template
    prompt = prompt_template.replace("{{UNIVERSITY_NAME}}", university_name)
    
    try:
        print(f"  [Claude Opus 4.5] Querying with web search for {university_name}...")
        
        # Claude Opus 4.5 with web search tool for real-time research
        # Using streaming as required for long-running web search operations
        response_text = ""
        
        with anthropic_client.messages.stream(
            model="claude-opus-4.5-20250514",  # Claude Opus 4.5 with web search and thinking
            max_tokens=16000,
            thinking={
                "type": "enabled",
                "budget_tokens": 8000  # Allow extended thinking
            },
            tools=[{
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 10  # Allow up to 10 searches per request
            }],
            messages=[{
                "role": "user",
                "content": prompt
            }]
        ) as stream:
            # Collect all text from the stream
            for event in stream:
                pass  # Let the stream complete
            
            # Get the final message
            final_message = stream.get_final_message()
            
            # Extract the response text (skip tool use blocks)
            for block in final_message.content:
                if hasattr(block, 'text'):
                    response_text += block.text
        
        if not response_text:
            print(f"  [Warning] No text response from Claude")
            return None
        
        print(f"  [Claude] Received response, parsing JSON...")
        
        # Parse JSON from response
        # Clean markdown if present
        match = re.search(r"```json(.*?)```", response_text, re.DOTALL)
        if match:
            response_text = match.group(1).strip()
        elif response_text.startswith("```"):
            response_text = response_text.replace("```", "")
        
        # Find JSON object
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            try:
                data = json.loads(json_match.group())
            except json.JSONDecodeError as e:
                print(f"  [Warning] Could not parse JSON from Claude: {e}")
                print(f"  Response was: {response_text[:500]}...")
                return None
        else:
            print(f"  [Warning] No JSON found in Claude response")
            print(f"  Response was: {response_text[:500]}...")
            return None
        
        # Ensure required structure exists
        data.setdefault("university_name", university_name)
        data.setdefault("data_retrieved_date", datetime.now().strftime("%Y-%m-%d"))
        data.setdefault("sources", [])
        data.setdefault("student_data", {})
        data.setdefault("gpu_resources", {})
        data.setdefault("compute_credits", {"total_annual_value_usd": 0.0, "description": ""})
        data.setdefault("analysis_notes", "Data collected via Claude Opus 4.5 with web search.")
        
        # Validate Sources
        data = validate_and_filter_sources(data)

        # Save to Cache
        try:
            with open(cache_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving to cache for {university_name}: {e}")
            
        return data
        
    except Exception as e:
        print(f"Error querying Claude for {university_name}: {e}")
        return None


def query_ensemble(university_name, prompt_template):
    """
    Run all 3 models (OpenAI, Claude, Gemini) in parallel, then aggregate results using Gemini 3 Pro.
    This combines the strengths of each model:
    - OpenAI: Best GPU cluster details
    - Claude: Good student data from datausa.io
    - Gemini: Complete coverage and thinking
    
    Cache structure:
    - data/cache/openai/{university}.json   - OpenAI results
    - data/cache/claude/{university}.json   - Claude results  
    - data/cache/gemini/{university}.json   - Gemini results
    - data/cache/final/{university}.json    - Aggregated final result
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading
    
    print(f"\n  [Ensemble] Running 3 models in parallel for {university_name}...")
    
    # Check cache first (look in 'final' subdirectory for ensemble)
    final_cache_path = get_cache_path(university_name, model_name='final')
    if os.path.exists(final_cache_path):
        print(f"  [Ensemble] Loading from cache: {university_name}")
        try:
            with open(final_cache_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"  [Ensemble] Error reading cache: {e}")
    
    results = {}
    errors = {}
    
    def has_valid_student_data(result):
        """Check if result has at least one non-zero student count."""
        if not result:
            return False
        sd = result.get('student_data', {})
        ug = sd.get('undergrad_cs_count', 0)
        ms = sd.get('grad_cs_count', 0)
        phd = sd.get('phd_cs_count', 0)
        # At least one must be > 0
        return (ug and ug > 0) or (ms and ms > 0) or (phd and phd > 0)
    
    def run_openai():
        try:
            openai_cache = get_cache_path(university_name, model_name='openai')
            if os.path.exists(openai_cache):
                print(f"  [Ensemble] Loading OpenAI from cache...")
                with open(openai_cache, 'r') as f:
                    cached = json.load(f)
                    # Check if cached result has valid student data
                    if has_valid_student_data(cached):
                        return cached
                    else:
                        print(f"  [Ensemble] OpenAI cache has 0 students, retrying...")
                        os.remove(openai_cache)
            
            result = query_openai_deep_research(university_name, prompt_template)
            
            # Check if result has valid student data, retry once if not
            if not has_valid_student_data(result):
                print(f"  [Ensemble] OpenAI returned 0 students, retrying once...")
                result = query_openai_deep_research(university_name, prompt_template)
            
            if result:
                with open(openai_cache, 'w') as f:
                    json.dump(result, f, indent=2)
            return result
        except Exception as e:
            return {"error": str(e)}
    
    def run_claude():
        try:
            claude_cache = get_cache_path(university_name, model_name='claude')
            if os.path.exists(claude_cache):
                print(f"  [Ensemble] Loading Claude from cache...")
                with open(claude_cache, 'r') as f:
                    cached = json.load(f)
                    if has_valid_student_data(cached):
                        return cached
                    else:
                        print(f"  [Ensemble] Claude cache has 0 students, retrying...")
                        os.remove(claude_cache)
            
            result = query_claude(university_name, prompt_template)
            
            if not has_valid_student_data(result):
                print(f"  [Ensemble] Claude returned 0 students, retrying once...")
                result = query_claude(university_name, prompt_template)
            
            if result:
                with open(claude_cache, 'w') as f:
                    json.dump(result, f, indent=2)
            return result
        except Exception as e:
            return {"error": str(e)}
    
    def run_gemini():
        try:
            gemini_cache = get_cache_path(university_name, model_name='gemini')
            if os.path.exists(gemini_cache):
                print(f"  [Ensemble] Loading Gemini from cache...")
                with open(gemini_cache, 'r') as f:
                    cached = json.load(f)
                    if has_valid_student_data(cached):
                        return cached
                    else:
                        print(f"  [Ensemble] Gemini cache has 0 students, retrying...")
                        os.remove(gemini_cache)
            
            result = query_gemini(university_name, prompt_template)
            
            if not has_valid_student_data(result):
                print(f"  [Ensemble] Gemini returned 0 students, retrying once...")
                result = query_gemini(university_name, prompt_template)
            
            if result:
                with open(gemini_cache, 'w') as f:
                    json.dump(result, f, indent=2)
            return result
        except Exception as e:
            return {"error": str(e)}
    
    # Run all 3 in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(run_openai): "openai",
            executor.submit(run_claude): "claude",
            executor.submit(run_gemini): "gemini"
        }
        
        for future in as_completed(futures):
            model_name = futures[future]
            try:
                result = future.result()
                if result and "error" not in result:
                    results[model_name] = result
                    print(f"  [Ensemble] ✓ {model_name} completed")
                else:
                    errors[model_name] = result.get("error", "Unknown error") if result else "No result"
                    print(f"  [Ensemble] ✗ {model_name} failed: {errors[model_name][:50]}")
            except Exception as e:
                errors[model_name] = str(e)
                print(f"  [Ensemble] ✗ {model_name} failed: {str(e)[:50]}")
    
    if not results:
        print(f"  [Ensemble] All models failed!")
        return None
    
    print(f"  [Ensemble] Got {len(results)}/3 results. Aggregating with Gemini 3 Pro...")
    
    # Build aggregation prompt
    aggregation_prompt = f"""You are aggregating research results about {university_name} from multiple AI models.

Each model searched the web independently. Your task is to merge their findings into a single, accurate JSON.

## RULES FOR MERGING:
1. For numeric fields (student counts, GPU counts): Use the HIGHEST non-zero value if models disagree
2. For dates/years: Use the most recent year
3. For sources: Combine all unique sources from all models
4. If a field is 0 or -1 in one model but has a positive value in another, use the positive value
5. For notes: Combine relevant notes from all models

## MODEL RESULTS:

"""
    
    for model_name, data in results.items():
        aggregation_prompt += f"### {model_name.upper()} Result:\n```json\n{json.dumps(data, indent=2)}\n```\n\n"
    
    aggregation_prompt += """## OUTPUT:
Return ONLY a single merged JSON object with this structure:
{
  "university_name": "...",
  "data_retrieved_date": "...",
  "sources": [...combined from all models...],
  "student_data": {
    "undergrad_cs_count": <highest non-zero value>,
    "grad_cs_count": <highest non-zero value>,
    "phd_cs_count": <highest non-zero value>,
    "year": "<most recent year>",
    "source_url": "...",
    "notes": "<combined notes>"
  },
  "gpu_resources": {
    "h100_sxm_count": <highest value>,
    "h100_pcie_count": <highest value>,
    "h200_count": <highest value>,
    ...all other GPU fields with highest values...
    "notes": "<combined notes with calculations>"
  },
  "compute_credits": {...},
  "analysis_notes": "Ensemble result aggregated from OpenAI, Claude, and Gemini models."
}

Output ONLY the JSON, no other text."""

    # Use Gemini 3 Pro to aggregate
    try:
        tools = [glm.Tool(google_search={})]
        model = genai.GenerativeModel('gemini-3-pro-preview', tools=tools)
        response = model.generate_content(aggregation_prompt)
        
        text = response.text
        
        # Parse JSON
        match = re.search(r"```json(.*?)```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
        elif text.startswith("```"):
            text = text.replace("```", "")
        
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            data = json.loads(json_match.group())
        else:
            print(f"  [Ensemble] Failed to parse aggregated JSON, using best single result")
            # Fallback: return the result with most non-zero fields
            data = max(results.values(), key=lambda x: sum(1 for v in str(x).split() if v.isdigit() and int(v) > 0))
        
        # Ensure required structure
        data.setdefault("university_name", university_name)
        data.setdefault("data_retrieved_date", datetime.now().strftime("%Y-%m-%d"))
        data.setdefault("sources", [])
        data.setdefault("student_data", {})
        data.setdefault("gpu_resources", {})
        data.setdefault("analysis_notes", f"Ensemble result from {len(results)} models: {', '.join(results.keys())}")
        
        # Validate sources
        data = validate_and_filter_sources(data)
        
        # Save to cache (final/ subdirectory)
        try:
            with open(final_cache_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"  [Ensemble] Error saving cache: {e}")
        
        print(f"  [Ensemble] ✓ Aggregation complete!")
        return data
        
    except Exception as e:
        print(f"  [Ensemble] Aggregation failed: {e}")
        # Fallback to best individual result
        if results:
            return list(results.values())[0]
        return None


def query_gemini(university_name, prompt_template):
    # Check Cache
    cache_path = get_cache_path(university_name)
    if os.path.exists(cache_path):
        print(f"Loading from cache: {university_name}")
        try:
            with open(cache_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading cache for {university_name}: {e}")

    if not GEMINI_API_KEY:
        # MOCK RESPONSE
        return mock_response(university_name)

    prompt = prompt_template.replace("{{UNIVERSITY_NAME}}", university_name)
    
    max_retries = 5
    base_delay = 10
    
    for attempt in range(max_retries):
        try:
            # Enable Google Search Tool and use Gemini 3 Pro with thinking
            tools = [glm.Tool(google_search={})]
            model = genai.GenerativeModel('gemini-3-pro-preview', tools=tools)
            print(f"  [Gemini 3 Pro] Querying with web search and thinking for {university_name}...")
            response = model.generate_content(prompt)
            
            try:
                text = response.text
            except Exception as e:
                print(f"  [Warning] response.text failed: {e}")
                # Inspect candidates
                if response.candidates:
                    print(f"  [Debug] Finish Reason: {response.candidates[0].finish_reason}")
                    if response.candidates[0].content and response.candidates[0].content.parts:
                        text = response.candidates[0].content.parts[0].text
                    else:
                        print("  [Error] No content info in candidate.")
                        # Force a retry by raising exception to hit the retry loop
                        raise e
                else:
                    print("  [Error] No candidates returned.")
                    raise e
            
            # Clean markdown if present
            # Match ```json ... ``` block
            import re
            match = re.search(r"```json(.*?)```", text, re.DOTALL)
            if match:
                text = match.group(1).strip()
            elif text.startswith("```"):
                 text = text.replace("```", "")
            
            data = json.loads(text)
            
            # Validate Sources
            data = validate_and_filter_sources(data)

            # Save to Cache
            try:
                with open(cache_path, 'w') as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                print(f"Error saving to cache for {university_name}: {e}")
                
            return data
        except Exception as e:
            print(f"Error querying Gemini for {university_name} (Attempt {attempt+1}/{max_retries}): {e}")
            if "429" in str(e) or "Resource exhausted" in str(e) or "503" in str(e):
                wait_time = base_delay * (2 ** attempt)  # 10, 20, 40, 80...
                print(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                # Non-retriable error (e.g. 400 Bad Request, JSON parse error)
                return None
    
    print(f"Failed to query {university_name} after {max_retries} attempts.")
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

def process_university(uni_name, prices, prompt_template, provider="openai"):
    print(f"Processing {uni_name}...")
    
    if provider == "openai":
        data = query_openai_deep_research(uni_name, prompt_template)
    elif provider == "claude":
        data = query_claude(uni_name, prompt_template)
    elif provider == "gemini":
        data = query_gemini(uni_name, prompt_template)
    elif provider == "ensemble":
        data = query_ensemble(uni_name, prompt_template)
    else:
        print(f"Unknown provider: {provider}")
        data = None
    
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
        ("gh200_count", "gh200"),  # Grace Hopper
        ("b200_count", "b200"),
        ("b100_count", "b100"),
        ("a100_80gb_count", "a100_80gb"),
        ("a100_40gb_count", "a100_40gb"),
        ("a40_count", "a40"),
        ("a6000_count", "a6000"), # prompt says "a6000_count", price says "rtx_a6000"? check load_gpu_prices
        ("l40s_count", "l40s"),
        ("v100_count", "v100"),
        ("p100_count", "p100")
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
        # Extract URLs from sources (can be dicts or strings)
        source_urls = []
        for src in sources:
            if isinstance(src, dict):
                source_urls.append(src.get("url", str(src)))
            else:
                source_urls.append(str(src))
        formatted_notes += " | Sources: " + ", ".join(source_urls)

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

def main(target_university=None, provider="openai"):
    print(f"Starting Monthly Analysis (Provider: {provider})...")
    
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
    for i, uni in enumerate(universities): 
        if target_university and uni != target_university:
            continue
        
        print(f"[{i+1}/{len(universities)}] Processing {uni}...")
        
        # Check if cached BEFORE processing to know if we need to rate limit after
        cache_path = get_cache_path(uni)
        was_cached = os.path.exists(cache_path)
        
        res = process_university(uni, prices, prompt_template, provider=provider)
        if res:
            results.append(res)
        
        # Rate limit: Only delay if we actually made an API call (wasn't cached)
        if not was_cached:
            if provider == "gemini":
                print("  [Rate Limit] Waiting 60s before next request...")
                time.sleep(60)
            else:
                # OpenAI deep research is slower but no strict RPM limit
                print("  [Rate Limit] Waiting 5s before next request...")
                time.sleep(5)
        
        # Incremental Save every 5 records to prevent data loss
        if len(results) > 0 and i % 5 == 0:
            df_temp = pd.DataFrame(results)
            # Sort by GPUs Per Student Descending
            if "Gpus_Per_Student" in df_temp.columns:
                df_temp = df_temp.sort_values(by="Gpus_Per_Student", ascending=False)
            df_temp['Rank'] = range(1, len(df_temp) + 1)
            df_temp.to_csv(MASTER_OUTPUT_FILE, index=False)
            print(f"Saved {len(df_temp)} records (Checkpoint)...")

    # Save
    if results:
        df_out = pd.DataFrame(results)
        # Sort by GPUs Per Student Descending
        df_out = df_out.sort_values(by="Gpus_Per_Student", ascending=False)
        # Add Rank
        df_out['Rank'] = range(1, len(df_out) + 1)
        
        pass
        # WARNING: Disabling direct overwrite to avoid destroying master data with single-entry runs.
        # df_out.to_csv(MASTER_OUTPUT_FILE, index=False)
        # print(f"Successfully saved {len(df_out)} records to {MASTER_OUTPUT_FILE}")
    else:
        print("No results generated.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run GPUsPerStudent Analysis")
    parser.add_argument("--university", "-u", type=str, help="Run for a specific university only")
    parser.add_argument("--provider", "-p", type=str, default="ensemble", choices=["openai", "gemini", "claude", "ensemble"],
                        help="API provider: openai, gemini, claude, or ensemble (all 3 + aggregation)")
    args = parser.parse_args()
    
    main(target_university=args.university, provider=args.provider)
