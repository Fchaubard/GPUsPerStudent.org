import google.generativeai as genai
import google.ai.generativelanguage as glm

print("Attempting to construct Tool with google_search={}...")

try:
    # Try passing empty dict to google_search field
    tool = glm.Tool(google_search={})
    print("Success: Created Tool(google_search={})")
    print("Tool repr:", tool)
except Exception as e:
    print("Error creating Tool(google_search={}):", e)

try:
    # Try finding it as a nested type?
    if hasattr(glm.Tool, "GoogleSearch"):
        print("glm.Tool.GoogleSearch exists")
    else:
        print("glm.Tool.GoogleSearch does NOT exist")
except Exception as e:
    print(e)
