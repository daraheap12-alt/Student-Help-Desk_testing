from __future__ import annotations

import json
from pathlib import Path


def generate_student_faq() -> None:
    data_path = Path(__file__).resolve().parent / "student_help_desk.json"
    with data_path.open("r", encoding="utf-8") as fh:
        rows = json.load(fh)

    faq_path = Path(__file__).resolve().parent / "student_faq.json"
    with faq_path.open("w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


if __name__ == "__main__":
    generate_student_faq()
    print("Generated student_faq.json")
