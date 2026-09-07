from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import nbformat as nbf
from nbclient import NotebookClient


WORKSPACE = Path(__file__).resolve().parents[4]
V3_ROOT = WORKSPACE / "NewBenchmark" / "PhilosophyHL_v3"
AUDIT_DIR = V3_ROOT / "audit" / "annotation_quality_v1"
OUTPUT = AUDIT_DIR / "PhiloVista-1800_annotation_audit.ipynb"


def markdown(text: str):
    return nbf.v4.new_markdown_cell(dedent(text).strip())


def code(text: str):
    return nbf.v4.new_code_cell(dedent(text).strip())


def main() -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    notebook = nbf.v4.new_notebook()
    notebook["metadata"]["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    notebook["metadata"]["language_info"] = {"name": "python", "version": "3.12"}
    notebook["cells"] = [
        markdown("""
        # PhiloVista-1800 Annotation Quality Audit

        ## tl;dr

        All 1,800 item records now pass structural, mapping, image-integrity, English-only, separator, export-consistency, and sensitive-data checks. The audit corrected six confirmed cross-image annotation mismatches, 26 boundary-track overinterpretation gaps, and one excessive caption. Seventeen medium-severity review reminders remain; none is a confirmed factual or structural error. These records remain non-independent AI drafts rather than human gold annotations.
        """),
        markdown("""
        ## Context & Methods

        The unit of analysis is one annotation JSON per frozen blind image. The audit compares item records with the batch plan, blind image index, final-selection manifest, mapped image bytes, and three exported files.

        ### Key Assumptions

        - `formal_gold=false` and both human-review flags must remain set.
        - Scene, Action, and Rationale require exactly three English references; Object requires five.
        - Boundary-track items need at least one interpretation that explicitly records insufficient evidence.
        - Repeated but accurate negative observations and mirrored actions are review reminders, not automatic errors.
        """),
        code("""
        import csv
        import json
        from collections import Counter
        from pathlib import Path

        workspace = Path.cwd()
        v3_root = workspace / "NewBenchmark" / "PhilosophyHL_v3"
        workflow = v3_root / "annotation_workflow"
        audit_dir = v3_root / "audit" / "annotation_quality_v1"
        report = json.loads((audit_dir / "PhiloVista-1800_quality_report.json").read_text(encoding="utf-8"))
        with (audit_dir / "PhiloVista-1800_remaining_issues.csv").open(encoding="utf-8-sig", newline="") as handle:
            issues = list(csv.DictReader(handle))
        repairs = [json.loads(line) for line in (audit_dir / "PhiloVista-1800_repair_log.jsonl").read_text(encoding="utf-8").splitlines() if line]
        print({
            "expected_items": report["expected_items"],
            "parsed_items": report["parsed_items"],
            "unique_ids": report["unique_annotation_item_ids"],
            "remaining_by_severity": report["issues"]["by_severity"],
            "unique_repaired_items": len({row["annotation_item_id"] for row in repairs}),
            "release_readiness": report["release_readiness"],
        })
        """),
        markdown("""
        ## Data

        The frozen population contains 600 HL Dataset images, 550 HAIVMet images, 500 IRFL images, and 150 MM-MoralBench images. It contains 1,620 positive-track and 180 boundary-track items, arranged as 36 batches of 50.
        """),
        code("""
        print("Source distribution:", report["source_distribution"])
        print("Track distribution:", report["track_distribution"])
        print("Method distribution:", report["method_distribution"])
        print("Caption word-length profile:", report["caption_word_length"])
        """),
        markdown("""
        ## Results

        The remaining automated reminders are intentionally not auto-rewritten: 16 records use one of two accurate sentences stating that no readable text is present, and one record describes symmetric left/right actions with nearly identical token sets. Automatic rewriting would risk introducing hallucinations merely to increase surface diversity.
        """),
        code("""
        remaining = Counter(row["code"] for row in issues)
        print("Remaining review reminders:", dict(sorted(remaining.items())))

        export_dir = workflow / "drafts" / "api_en" / "exports"
        with (export_dir / "PhiloVista-1800_HL.csv").open(encoding="utf-8-sig", newline="") as handle:
            csv_rows = list(csv.DictReader(handle))
        hl_rows = [json.loads(line) for line in (export_dir / "PhiloVista-1800_HL.jsonl").read_text(encoding="utf-8").splitlines() if line]
        philosophy_rows = [json.loads(line) for line in (export_dir / "PhiloVista-1800_philosophy.jsonl").read_text(encoding="utf-8").splitlines() if line]
        assert len(csv_rows) == len(hl_rows) == len(philosophy_rows) == 1800
        assert not report["issues"]["by_severity"].get("critical", 0)
        assert not report["issues"]["by_severity"].get("high", 0)
        print("Export row counts and critical/high severity assertions passed.")
        """),
        markdown("""
        ## Takeaways

        - The seven confirmed content/length defects and 26 boundary-labeling defects were repaired with backups and SHA-256 revision receipts.
        - The hardened exporter now validates the full dataset in memory and atomically replaces outputs only after all checks pass.
        - The AI draft is technically consistent and conditionally ready for human review, but it is not eligible for formal HL release until independent human annotation/rating and the confidence, purity, and diversity procedures are completed.
        """),
    ]
    nbf.write(notebook, OUTPUT)
    client = NotebookClient(notebook, timeout=180, kernel_name="python3", resources={"metadata": {"path": str(WORKSPACE)}})
    client.execute()
    nbf.write(notebook, OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
