from pathlib import Path
from datetime import datetime
from typing import Any, Optional
import json

class InteractionLogger:
    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            with open(self.log_path, "w") as f:
                f.write("# AI Interaction Log\n\nChronological log of all AI inputs and outputs.\n\n")

    def log(
        self,
        agent: str,
        step: str,
        model: str,
        prompt: Any,
        response: Any,
        metadata: Optional[dict] = None
    ):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Format prompt
        if isinstance(prompt, list):
            # Handle interleaved content
            formatted_prompt = ""
            for item in prompt:
                if isinstance(item, str):
                    formatted_prompt += f"{item}\n"
                else:
                    formatted_prompt += "[IMAGE/BINARY DATA]\n"
        else:
            formatted_prompt = str(prompt)

        # Format response
        formatted_response = str(response)
        
        # Format metadata
        meta_str = ""
        if metadata:
            meta_str = f"**Metadata**: `{json.dumps(metadata)}`\n"

        entry = f"""
## [{timestamp}] {agent.upper()}: {step}
**Model**: `{model}`
{meta_str}

### Input
```text
{formatted_prompt.strip()}
```

### Output
```text
{formatted_response.strip()}
```

---
"""
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(entry)
