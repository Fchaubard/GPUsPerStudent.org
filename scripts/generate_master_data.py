#!/usr/bin/env python3
"""
Generate master_data.csv from final/*.json files.
Core metric: H100-equivalent GPUs per weighted student

Also checks individual model caches for max student counts if final has zeros.
"""

import os
import json
import csv
import csv
import shutil
from glob import glob

# Load GPU prices from file
def load_gpu_prices():
    prices = {}
    with open('data/gpu_prices.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            gpu_name = row['GPU'].replace('NVIDIA ', '')
            prices[gpu_name] = float(row['Price_USD'])
    return prices

# Load university URLs
def load_university_urls():
    urls = {}
    with open('data/filtered_national_universities_name_url.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            urls[row['name']] = row['url']
    return urls

# JSON field mappings for GPU counts
JSON_FIELD_MAP = {
    'H100 SXM': 'h100_sxm_count',
    'H100 PCIe': 'h100_pcie_count',
    'H200': 'h200_count',
    'A100 80GB': 'a100_80gb_count',
    'A100 40GB': 'a100_40gb_count',
    'B200': 'b200_count',
    'B100': 'b100_count',
    'A40': 'a40_count',
    'RTX A6000': 'a6000_count',
    'L40S': 'l40s_count',
    'V100': 'v100_count',
    'P100': 'p100_count',
    'GH200': 'gh200_count',
    'A10': 'a10_count',
}

# Student weighting constants
WEIGHT_UNDERGRAD = 0.45
WEIGHT_GRAD = 0.7
WEIGHT_PHD = 0.9

def get_max_student_data(filename):
    """
    Check all model caches (openai, claude, gemini, ensemble) and return max student counts.
    This fixes the issue where ensemble aggregation incorrectly took 0s.
    """
    basename = os.path.basename(filename)
    model_dirs = ['data/cache/openai', 'data/cache/claude', 'data/cache/gemini', 'data/cache/ensemble']
    
    max_ug = 0
    max_ms = 0
    max_phd = 0
    
    for model_dir in model_dirs:
        model_file = os.path.join(model_dir, basename)
        if os.path.exists(model_file):
            try:
                with open(model_file) as f:
                    data = json.load(f)
                sd = data.get('student_data', {})
                ug = max(0, sd.get('undergrad_cs_count', 0) or 0)
                ms = max(0, sd.get('grad_cs_count', 0) or 0)
                phd = max(0, sd.get('phd_cs_count', 0) or 0)
                
                max_ug = max(max_ug, ug)
                max_ms = max(max_ms, ms)
                max_phd = max(max_phd, phd)
            except:
                pass
    
    return max_ug, max_ms, max_phd

def main():
    gpu_prices = load_gpu_prices()
    university_urls = load_university_urls()
    
    # Get H100 SXM price as the baseline for "H100 equivalent"
    h100_price = gpu_prices.get('H100 SXM', 35000)
    print(f"H100 SXM price (baseline): ${h100_price:,}")
    
    results = []
    student_fixes = 0
    
    for json_file in glob('data/cache/final/*.json'):
        with open(json_file) as f:
            data = json.load(f)
        
        uni_name = data.get('university_name', os.path.basename(json_file).replace('.json', '').replace('_', ' '))
        sd = data.get('student_data', {})
        gd = data.get('gpu_resources', {})
        
        # Student counts from final (handle -1 and None)
        ug = max(0, sd.get('undergrad_cs_count', 0) or 0)
        ms = max(0, sd.get('grad_cs_count', 0) or 0)
        phd = max(0, sd.get('phd_cs_count', 0) or 0)
        
        # ALWAYS check all model caches for max values - ensemble/validation may have underestimated
        max_ug, max_ms, max_phd = get_max_student_data(json_file)
        if max_ug > ug or max_ms > ms or max_phd > phd:
            print(f"  📊 {uni_name}: Using max from model caches - UG:{ug}->{max_ug}, MS:{ms}->{max_ms}, PhD:{phd}->{max_phd}")
            ug = max(ug, max_ug)
            ms = max(ms, max_ms)
            phd = max(phd, max_phd)
            student_fixes += 1
        
        # Weighted student count
        weighted_students = (ug * WEIGHT_UNDERGRAD) + (ms * WEIGHT_GRAD) + (phd * WEIGHT_PHD)
        
        # Calculate total GPU value and H100-equivalent count
        gpu_counts = {}
        total_gpu_value = 0
        for gpu_name, price in gpu_prices.items():
            json_field = JSON_FIELD_MAP.get(gpu_name)
            if json_field:
                count = gd.get(json_field, 0) or 0
                gpu_counts[gpu_name] = count
                total_gpu_value += count * price
        
        # H100-equivalent count = total value / H100 price
        h100_equivalent = total_gpu_value / h100_price if h100_price > 0 else 0
        
        # GPUs per student (H100-equivalent)
        gpus_per_student = h100_equivalent / weighted_students if weighted_students > 0 else 0
        
        # Get university URL
        url = university_urls.get(uni_name, '#')
        
        # Copy JSON to web/data/ for popup charts (REQUIRED for local file:// usage due to CORS)
        # Filename format must match getJsonFilename() in index.html: spaces->underscores, - -> _-_
        web_json_name = uni_name.replace(',', '').replace("'", '').replace('"', '').replace(' ', '_').replace('-', '_-_') + '.json'
        web_json_path = os.path.join('web', 'data', web_json_name)
        shutil.copy2(json_file, web_json_path)

        # Build result row
        row = {
            'university': uni_name,
            'url': url,
            'undergrad': ug,
            'ms': ms,
            'phd': phd,
            'weighted_students': round(weighted_students, 1),
        }
        # Add notes (sanitized to remove newlines for CSV compatibility)
        notes = data.get('gpu_resources', {}).get('notes', '') + " " + data.get('student_data', {}).get('notes', '')
        row['Notes'] = notes.replace('\n', ' ').replace('\r', ' ')
        
        # Add all GPU columns
        for gpu_name in gpu_prices.keys():
            col_name = gpu_name.replace(' ', '_')
            row[col_name] = gpu_counts.get(gpu_name, 0)
        
        row['total_gpu_value'] = round(total_gpu_value)
        row['h100_equivalent'] = round(h100_equivalent, 2)
        row['gpus_per_student'] = round(gpus_per_student, 4)
        row['sources'] = len(data.get('sources', []))
        
        results.append(row)
    
    # Sort by GPUs per student (descending)
    results.sort(key=lambda x: x['gpus_per_student'], reverse=True)
    
    # Save to CSV
    output_file = 'data/master_data.csv'
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
        
    # Also save to web/data/master_data.csv for local file:// usage
    web_output_file = 'web/data/master_data.csv'
    with open(web_output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\n✅ Generated {output_file} with {len(results)} universities")
    print(f"📊 Fixed student data for {student_fixes} universities using model cache max values")
    print("\n🏆 TOP 15 LEADERBOARD:")
    print(f"{'Rank':<5} {'University':<40} {'GPUs/Student':<12} {'H100 Equiv':<10} {'Sources':<8}")
    print("-" * 80)
    for i, r in enumerate(results[:15]):
        print(f"{i+1:<5} {r['university'][:39]:<40} {r['gpus_per_student']:<12.4f} {r['h100_equivalent']:<10.1f} {r['sources']:<8}")

if __name__ == '__main__':
    main()
