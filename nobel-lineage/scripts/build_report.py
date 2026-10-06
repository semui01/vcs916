"""Embed output/results.json into the report template -> output/nobel-lineages.html."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "output" / "results.json").read_text())
tpl = (Path(__file__).parent / "report_template.html").read_text()
payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
(ROOT / "output" / "nobel-lineages.html").write_text(tpl.replace("/*DATA*/", payload))
print("wrote", ROOT / "output" / "nobel-lineages.html", len(payload) // 1024, "KB data")
