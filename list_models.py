
import google.generativeai as genai
import os

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print(f"Error: {e}")
