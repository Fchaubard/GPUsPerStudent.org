import os
import json
import csv
from glob import glob

# Load GPU prices dynamically
gpu_prices = {}
with open('data/gpu_prices.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        gpu_name = row['GPU'].replace('NVIDIA ', '')
        price = float(row['Price_USD'])
        gpu_prices[gpu_name] = price

# JSON field mappings
json_field_map = {
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

# Weighting Constants
WEIGHT_UNDERGRAD = 0.45
WEIGHT_GRAD = 0.7
WEIGHT_PHD = 0.9

# Process all final JSONs
results = []
for json_file in glob('data/cache/final/*.json'):
    with open(json_file) as f:
        data = json.load(f)
    
    uni_name = data.get('university_name', os.path.basename(json_file).replace('.json', ''))
    sd = data.get('student_data', {})
    gd = data.get('gpu_resources', {})
    
    ug = max(0, sd.get('undergrad_cs_count', 0) or 0)
    ms = max(0, sd.get('grad_cs_count', 0) or 0)
    phd = max(0, sd.get('phd_cs_count', 0) or 0)
    weighted_students = (ug * WEIGHT_UNDERGRAD) + (ms * WEIGHT_GRAD) + (phd * WEIGHT_PHD)
    
    gpu_counts = {}
    total_gpu_value = 0
    for gpu_name, price in gpu_prices.items():
        json_field = json_field_map.get(gpu_name)
        count = gd.get(json_field, 0) or 0
        gpu_counts[gpu_name] = count
        total_gpu_value += count * price
    
    gpus_per_student = total_gpu_value / weighted_students if weighted_students > 0 else 0
    
    row = {'university': uni_name, 'undergrad': ug, 'ms': ms, 'phd': phd, 'weighted_students': round(weighted_students, 1)}
    for gpu_name in gpu_prices.keys():
        row[gpu_name.replace(' ', '_')] = gpu_counts[gpu_name]
    row['total_gpu_value'] = round(total_gpu_value)
    row['gpus_per_student_value'] = round(gpus_per_student, 2)
    row['sources'] = len(data.get('sources', []))
    results.append(row)

results.sort(key=lambda x: x['gpus_per_student_value'], reverse=True)

with open('data/master_data.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)

print(f'✅ Generated data/master_data.csv with {len(results)} universities')
print('\\n🏆 TOP 15 LEADERBOARD:')
print(f'{"Rank":<5} {"University":<40} {"$/Student":<12} {"H100":<6} {"H200":<6}')
print('-'*70)
for i, r in enumerate(results[:15]):
    h100 = r.get('H100_SXM', 0) + r.get('H100_PCIe', 0)
    print(f'{i+1:<5} {r["university"][:39]:<40} \${r["gpus_per_student_value"]:>10,.0f} {h100:>5} {r.get("H200",0):>5}')