#!/usr/bin/env python3
"""
Validate GPU data using Gemini 3 Pro to filter out shared/national resources.
Reads from data/cache/ensemble/*.json and writes validated data to data/cache/final/*.json
"""

import os
import json
import time
from glob import glob
from datetime import datetime

import google.generativeai as genai

# Configure Gemini
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable required")

genai.configure(api_key=GEMINI_API_KEY)

# Directories
ENSEMBLE_DIR = 'data/cache/ensemble'
FINAL_DIR = 'data/cache/final'
PROMPT_FILE = 'prompt_validation.md'

def load_validation_prompt():
    """Load the validation prompt template."""
    with open(PROMPT_FILE, 'r') as f:
        return f.read()

def validate_university(json_path, prompt_template):
    """Validate a single university's GPU data using Gemini."""
    
    filename = os.path.basename(json_path)
    
    # Load existing data
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    university_name = data.get('university_name', filename.replace('.json', ''))
    print(f"  Validating {university_name}...")
    
    # Build prompt
    prompt = f"""{prompt_template}

---

## DATA TO VALIDATE

Here is the JSON data for {university_name}:

```json
{json.dumps(data, indent=2)}
```

Please validate this data and return the corrected JSON. Remember:
1. Remove any GPUs from shared/national resources
2. Keep all student data unchanged
3. Add a "validation_notes" field explaining changes
4. Return ONLY valid JSON, no other text
"""
    
    try:
        # Use Gemini 2.0 Flash for faster validation
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        response = model.generate_content(
            prompt,
            generation_config={
                'temperature': 0.1,
                'max_output_tokens': 4096,
            }
        )
        
        response_text = response.text.strip()
        
        # Extract JSON from response
        if '```json' in response_text:
            json_start = response_text.find('```json') + 7
            json_end = response_text.find('```', json_start)
            response_text = response_text[json_start:json_end].strip()
        elif '```' in response_text:
            json_start = response_text.find('```') + 3
            json_end = response_text.find('```', json_start)
            response_text = response_text[json_start:json_end].strip()
        
        validated_data = json.loads(response_text)
        
        # Ensure we have the required fields
        if 'university_name' not in validated_data:
            validated_data['university_name'] = university_name
        if 'validation_notes' not in validated_data:
            validated_data['validation_notes'] = "No changes needed"
        
        # Check if any changes were made
        orig_gpus = data.get('gpu_resources', {})
        new_gpus = validated_data.get('gpu_resources', {})
        
        changes = []
        for key in ['h100_sxm_count', 'h100_pcie_count', 'h200_count', 'a100_80gb_count', 
                    'a100_40gb_count', 'v100_count', 'l40s_count', 'a40_count']:
            orig_val = orig_gpus.get(key, 0) or 0
            new_val = new_gpus.get(key, 0) or 0
            if orig_val != new_val:
                changes.append(f"{key}: {orig_val} -> {new_val}")
        
        if changes:
            print(f"    CHANGES: {', '.join(changes)}")
        else:
            print(f"    No changes")
        
        return validated_data
        
    except json.JSONDecodeError as e:
        print(f"    ERROR: Invalid JSON response - {e}")
        # Return original data with note
        data['validation_notes'] = f"Validation failed: {e}"
        return data
    except Exception as e:
        print(f"    ERROR: {e}")
        data['validation_notes'] = f"Validation error: {e}"
        return data

def main():
    print(f"GPU Data Validation Pipeline")
    print(f"=" * 60)
    print(f"Started at: {datetime.now()}")
    print()
    
    # Load validation prompt
    prompt_template = load_validation_prompt()
    print(f"Loaded validation prompt from {PROMPT_FILE}")
    
    # Get all ensemble files
    ensemble_files = sorted(glob(f'{ENSEMBLE_DIR}/*.json'))
    print(f"Found {len(ensemble_files)} files to validate")
    print()
    
    # Process each file
    results = {'success': 0, 'error': 0, 'changed': 0}
    
    for i, json_path in enumerate(ensemble_files):
        filename = os.path.basename(json_path)
        print(f"[{i+1}/{len(ensemble_files)}] {filename}")
        
        try:
            validated_data = validate_university(json_path, prompt_template)
            
            # Save to final directory
            output_path = os.path.join(FINAL_DIR, filename)
            with open(output_path, 'w') as f:
                json.dump(validated_data, f, indent=2)
            
            results['success'] += 1
            
            # Check if data changed
            if 'validation_notes' in validated_data and validated_data['validation_notes'] != "No changes needed":
                results['changed'] += 1
            
            # Rate limiting - Gemini has limits
            time.sleep(1)
            
        except Exception as e:
            print(f"  FAILED: {e}")
            results['error'] += 1
    
    print()
    print(f"=" * 60)
    print(f"Completed at: {datetime.now()}")
    print(f"Success: {results['success']}, Changed: {results['changed']}, Errors: {results['error']}")

if __name__ == '__main__':
    main()
