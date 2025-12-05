"""
Utility script to parse pfSense benchmark Excel file into JSON format.
Run this script once to convert your Excel benchmark file.
"""

import pandas as pd
import re
import json
from pathlib import Path
import argparse


def parse_benchmark_excel(excel_path: Path, output_path: Path) -> None:
    """
    Parse benchmark Excel file into structured JSON.

    Args:
        excel_path: Path to input Excel file
        output_path: Path to output JSON file
    """
    # Read everything as raw rows (no header)
    df = pd.read_excel(excel_path, header=None)

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
            print(f"Detected section: {current_section}")
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

    print(f"\nParsed {len(items)} checklist items.")

    # Print the first 5 so you can eyeball it
    print("\nFirst 5 items:")
    for item in items[:5]:
        print(f"[{item['section']}] {item['control_id']} - {item['title']}")
        print(f"  Status : {item['status']}")
        print(f"  Comment: {item['comment']}")
        print()

    # Save to JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)

    print(f"Saved structured data to: {output_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Parse pfSense benchmark Excel file to JSON"
    )
    parser.add_argument(
        "excel_file",
        type=Path,
        help="Path to input Excel file (e.g., 'Pf Sense Benchmark.xlsx')"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("pfsense_benchmark.json"),
        help="Path to output JSON file (default: pfsense_benchmark.json)"
    )

    args = parser.parse_args()

    if not args.excel_file.exists():
        print(f"Error: Excel file not found: {args.excel_file}")
        return 1

    try:
        parse_benchmark_excel(args.excel_file, args.output)
        return 0
    except Exception as e:
        print(f"Error parsing Excel file: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
