import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google import genai
from app.core.config import settings

api_key = settings.GOOGLE_API_KEY
print(f"Key starts with: {api_key[:5] if api_key else 'None'}")

client = genai.Client(api_key=api_key)
print("Available embedding models:")
for m in client.models.list():
    if "embed" in getattr(m, "supported_actions", []):
        print(m.name)
