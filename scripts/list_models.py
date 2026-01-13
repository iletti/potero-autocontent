import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
load_dotenv()


def main() -> int:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("GOOGLE_API_KEY is not set.")
        return 1

    client = genai.Client(api_key=api_key)
    print("Available models:")
    for model in client.models.list():
        print(model)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
