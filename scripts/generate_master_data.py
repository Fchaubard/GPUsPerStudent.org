#!/usr/bin/env python3
"""
Generate master_data.csv from final/*.json files.
Core metric: H100-equivalent GPUs per weighted student
"""

import os
import json
import csv
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

def main():
    gpu_prices = load_gpu_prices()
    university_urls = load_university_urls()
    
    # Get H100 SXM price as the baseline for "H100 equivalent"
    h100_price = gpu_prices.get('H100 SXM', 35000)
    print(f"H100 SXM price (baseline): ${h100_price:,}")
    
    results = []
    
    for json_file in glob('data/cache/final/*.json'):
        with open(json_file) as f:
            data = json.load(f)
        
        uni_name = data.get('university_name', os.path.basename(json_file).replace('.json', '').replace('_', ' '))
        sd = data.get('student_data', {})
        gd = data.get('gpu_resources', {})
        
        # Student counts (handle -1 and None)
        ug = max(0, sd.get('undergrad_cs_count', 0) or 0)
        ms = max(0, sd.get('grad_cs_count', 0) or 0)
        phd = max(0, sd.get('phd_cs_count', 0) or 0)
        
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
        
        # Build result row
        row = {
            'university': uni_name,
            'url': url,
            'undergrad': ug,
            'ms': ms,
            'phd': phd,
            'weighted_students': round(weighted_students, 1),
        }
        
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
    
    print(f"\n✅ Generated {output_file} with {len(results)} universities")
    print("\n🏆 TOP 15 LEADERBOARD:")
    print(f"{'Rank':<5} {'University':<40} {'GPUs/Student':<12} {'H100 Equiv':<10} {'Sources':<8}")
    print("-" * 80)
    for i, r in enumerate(results[:15]):
        print(f"{i+1:<5} {r['university'][:39]:<40} {r['gpus_per_student']:<12.4f} {r['h100_equivalent']:<10.1f} {r['sources']:<8}")

if __name__ == '__main__':
    main()
