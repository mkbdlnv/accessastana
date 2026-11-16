"""Export the OpenAPI specification of the API to docs/openapi.json (no DB needed)."""

import json
from pathlib import Path

from accessastana.api.main import create_app

out = Path(__file__).resolve().parents[1] / "docs" / "openapi.json"
out.write_text(json.dumps(create_app().openapi(), ensure_ascii=False, indent=2), encoding="utf-8")
print(f"wrote {out}")
