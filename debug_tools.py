import google.generativeai as genai
import google.ai.generativelanguage as glm

print("GENAI Version:", genai.__version__)

try:
    print("\n--- Protos Inspection ---")
    t = glm.Tool()
    print("Available fields in Tool proto:", [f.name for f in t._pb.DESCRIPTOR.fields])
except Exception as e:
    print("Error inspecting Tool proto:", e)

print("\n--- String Shortcut Test ---")
try:
    model = genai.GenerativeModel('gemini-flash-latest', tools='google_search_retrieval')
    print("Successfully created model with tools='google_search_retrieval'")
except Exception as e:
    print("Failed with string shortcut:", e)
