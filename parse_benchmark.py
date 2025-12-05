import pandas as pd
import re
import json

file_path = "c:/Pfsense_Benchmark_Tool/Pf Sense Benchmark.xlsx"

# Read everything as raw rows (no header)
df = pd.read_excel(file_path, header=None)

items = []
current_section = None

for idx, row in df.iterrows():
    # Turn row into a simple list
    cols = row.tolist()

    # Normalize to length 5
    while len(cols) < 5:
        cols.append(None)
    col0, col1, col2, col3, col4 = cols[:5]

    # Detect section header rows like:
    # '1 General Setting Policy', 'Rational', 'Fix Text', 'Reviewed', 'Comment'
    if (
        isinstance(col0, str)
        and isinstance(col1, str)
        and isinstance(col2, str)
        and col1.strip() == "Rational"
        and col2.strip() == "Fix Text"
    ):
        current_section = col0.strip()
        # print(f"Detected section: {current_section}")
        continue

    # Skip completely empty rows
    if all(c is None or (isinstance(c, float) and pd.isna(c)) for c in [col0, col1, col2, col3, col4]):
        continue

    # Only treat rows with strings in first 4 cols as potential controls
    if not (isinstance(col0, str) and isinstance(col1, str) and isinstance(col2, str) and isinstance(col3, str)):
        continue

    # Try to extract control ID from the start of col0
    # e.g. "1.1 Ensure SSH warning banner..." -> control_id="1.1", title="Ensure SSH warning banner..."
    m = re.match(r"^\s*(\d+(\.\d+)*)\s+(.*)", col0.strip())
    if m:
        control_id = m.group(1)
        title = m.group(3).strip()
    else:
        control_id = None
        title = col0.strip()

    item = {
        "section": current_section,
        "control_id": control_id,
        "title": title,
        "rationale": col1.strip(),
        "fix_text": col2.strip(),
        "status": col3.strip(),
        "comment": col4.strip() if isinstance(col4, str) else "",
        "row_index": int(idx),
    }
    items.append(item)

print(f"Parsed {len(items)} checklist items.\n")

# Print the first 5 so you can eyeball it
for item in items[:5]:
    print(f"[{item['section']}] {item['control_id']} - {item['title']}")
    print(f"  Status : {item['status']}")
    print(f"  Comment: {item['comment']}")
    print()

# Save to JSON for later use by the app
output_path = "c:/Pfsense_Benchmark_Tool/pfsense_benchmark.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(items, f, indent=2)

print(f"Saved structured data to: {output_path}")
