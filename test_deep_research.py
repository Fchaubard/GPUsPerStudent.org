"""
Test script for Gemini Deep Research via Interactions API
Based on Google documentation: The Deep Research agent is exclusively available through the Interactions API
"""

import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def test_deep_research():
    """Test if Deep Research API is accessible"""
    
    print("Testing Deep Research API access...")
    
    # Try to list available models to see what we have access to
    print("\n1. Listing available models:")
    for model in genai.list_models():
        if "deep" in model.name.lower() or "research" in model.name.lower() or "agent" in model.name.lower():
            print(f"  Found: {model.name}")
    
    # Try the Interactions API approach
    print("\n2. Attempting to access Deep Research agent...")
    
    try:
        # Method 1: Try direct model access
        model = genai.GenerativeModel('gemini-2.0-flash-deep-research')
        response = model.generate_content("What is 2+2? Just answer briefly.")
        print(f"  Method 1 (direct model) SUCCESS: {response.text[:100]}")
    except Exception as e:
        print(f"  Method 1 (direct model) FAILED: {e}")
    
    try:
        # Method 2: Try with adk/agent approach
        # The Interactions API might use a different client
        from google.adk import Agent
        agent = Agent(model="deep_research")
        print(f"  Method 2 (ADK Agent) - Agent created successfully")
    except ImportError:
        print(f"  Method 2 (ADK Agent) - google.adk not installed (pip install google-adk)")
    except Exception as e:
        print(f"  Method 2 (ADK Agent) FAILED: {e}")
    
    try:
        # Method 3: Try via interactions endpoint
        # Based on the blog post, it might use a different API path
        import requests
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-deep-research:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": "What GPUs does Stanford University have?"}]}]
        }
        resp = requests.post(url, json=payload)
        if resp.status_code == 200:
            print(f"  Method 3 (REST API) SUCCESS")
            print(f"  Response: {resp.json()}")
        else:
            print(f"  Method 3 (REST API) FAILED: {resp.status_code} - {resp.text[:200]}")
    except Exception as e:
        print(f"  Method 3 (REST API) FAILED: {e}")

if __name__ == "__main__":
    test_deep_research()
