#!/usr/bin/env python3
"""
generate_all.py — Orchestrates generation of 500 manufacturing PDFs.

Distribution:
  Type 1  equipment_spec        80 PDFs  (50–60 pages each)
  Type 2  maintenance_report    80 PDFs  (60–80 pages each)
  Type 3  qc_report             70 PDFs  (55–70 pages each)
  Type 4  safety_data_sheet     70 PDFs  (50–55 pages each)
  Type 5  production_log        70 PDFs  (80–100 pages each)
  Type 6  parts_catalog         65 PDFs  (70–90 pages each)
  Type 7  fmea_worksheet        65 PDFs  (60–75 pages each)
  TOTAL                        500 PDFs

Usage:
  python generate_all.py              # generate all 500
  python generate_all.py --count 10   # quick test: 10 PDFs
  python generate_all.py --type equipment_spec --count 5
  python generate_all.py --workers 4  # override parallel workers
"""

import argparse
import multiprocessing
import os
import sys
import time
import traceback
from pathlib import Path
from dataclasses import dataclass
from typing import Callable

from tqdm import tqdm

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent
PDFS_DIR = ROOT / "pdfs"
PDFS_DIR.mkdir(exist_ok=True)

# Ensure pdf_generators is importable
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Job descriptor
# ---------------------------------------------------------------------------
@dataclass
class GenerateJob:
    doc_type: str
    seed: int
    output_path: str
    max_pages: int = 20


# ---------------------------------------------------------------------------
# Worker function (runs in subprocess)
# ---------------------------------------------------------------------------
def _run_job(job: GenerateJob) -> tuple[bool, str, float]:
    """Returns (success, output_path, elapsed_seconds)."""
    t0 = time.time()
    try:
        # Import lazily inside subprocess to avoid sharing state
        if job.doc_type == "equipment_spec":
            from pdf_generators.doc_types.equipment_spec import generate
        elif job.doc_type == "maintenance_report":
            from pdf_generators.doc_types.maintenance_report import generate
        elif job.doc_type == "qc_report":
            from pdf_generators.doc_types.qc_report import generate
        elif job.doc_type == "safety_data_sheet":
            from pdf_generators.doc_types.safety_data_sheet import generate
        elif job.doc_type == "production_log":
            from pdf_generators.doc_types.production_log import generate
        elif job.doc_type == "parts_catalog":
            from pdf_generators.doc_types.parts_catalog import generate
        elif job.doc_type == "fmea_worksheet":
            from pdf_generators.doc_types.fmea_worksheet import generate
        else:
            return False, job.output_path, 0.0

        generate(job.output_path, job.seed, max_pages=job.max_pages)
        elapsed = time.time() - t0
        return True, job.output_path, elapsed
    except Exception:
        elapsed = time.time() - t0
        tb = traceback.format_exc()
        # Print to stderr so tqdm doesn't mangle it
        print(f"\n[ERROR] {job.output_path}:\n{tb}", file=sys.stderr)
        return False, job.output_path, elapsed


# ---------------------------------------------------------------------------
# Job list builder
# ---------------------------------------------------------------------------
DOC_TYPES = [
    ("equipment_spec",     80),
    ("maintenance_report", 80),
    ("qc_report",          70),
    ("safety_data_sheet",  70),
    ("production_log",     70),
    ("parts_catalog",      65),
    ("fmea_worksheet",     65),
]


def build_jobs(
    filter_type: str | None = None,
    max_count: int | None = None,
    skip_existing: bool = True,
    max_pages: int = 20,
) -> list[GenerateJob]:
    jobs: list[GenerateJob] = []
    seed_offset = 0

    for doc_type, count in DOC_TYPES:
        if filter_type and doc_type != filter_type:
            seed_offset += count
            continue

        type_count = count if max_count is None else min(count, max_count)

        for i in range(type_count):
            seed = seed_offset + i
            fname = f"{doc_type}_{seed:04d}.pdf"
            out_path = str(PDFS_DIR / fname)

            if skip_existing and Path(out_path).exists():
                seed_offset += 1
                continue

            jobs.append(GenerateJob(
                doc_type=doc_type,
                seed=seed,
                output_path=out_path,
                max_pages=max_pages,
            ))
            seed_offset += 1

    return jobs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Generate manufacturing PDFs")
    parser.add_argument(
        "--count", type=int, default=None,
        help="Max PDFs per type (default: full distribution = 500 total)",
    )
    parser.add_argument(
        "--type", dest="doc_type", default=None,
        choices=[t for t, _ in DOC_TYPES],
        help="Generate only this document type",
    )
    parser.add_argument(
        "--workers", type=int,
        default=min(8, multiprocessing.cpu_count()),
        help="Number of parallel workers (default: min(8, cpu_count))",
    )
    parser.add_argument(
        "--pages", type=int, default=20,
        help="Target pages per PDF (default: 20)",
    )
    parser.add_argument(
        "--no-skip", action="store_true",
        help="Regenerate PDFs that already exist",
    )
    args = parser.parse_args()

    jobs = build_jobs(
        filter_type=args.doc_type,
        max_count=args.count,
        skip_existing=not args.no_skip,
        max_pages=args.pages,
    )

    if not jobs:
        print("No jobs to run (all PDFs already exist — use --no-skip to regenerate).")
        return

    print(f"Generating {len(jobs)} PDFs using {args.workers} workers → {PDFS_DIR}")
    print(f"Doc types: {', '.join(set(j.doc_type for j in jobs))}\n")

    success_count = 0
    error_count = 0
    total_elapsed = 0.0
    t_start = time.time()

    with multiprocessing.Pool(processes=args.workers) as pool:
        with tqdm(total=len(jobs), unit="pdf", dynamic_ncols=True) as pbar:
            for success, out_path, elapsed in pool.imap_unordered(_run_job, jobs):
                total_elapsed += elapsed
                fname = Path(out_path).name
                if success:
                    success_count += 1
                    pbar.set_postfix_str(f"OK: {fname} ({elapsed:.1f}s)")
                else:
                    error_count += 1
                    pbar.set_postfix_str(f"ERR: {fname}")
                pbar.update(1)

    wall_time = time.time() - t_start
    avg_time = total_elapsed / max(success_count, 1)

    print(f"\n{'='*60}")
    print(f"Done in {wall_time:.1f}s wall time")
    print(f"  Generated : {success_count}")
    print(f"  Errors    : {error_count}")
    print(f"  Avg/PDF   : {avg_time:.1f}s (worker time)")
    print(f"  Output    : {PDFS_DIR}")

    # List generated files
    pdf_files = sorted(PDFS_DIR.glob("*.pdf"))
    print(f"  Total PDFs on disk: {len(pdf_files)}")

    by_type: dict[str, int] = {}
    for f in pdf_files:
        dtype = "_".join(f.stem.split("_")[:-1])
        by_type[dtype] = by_type.get(dtype, 0) + 1
    for dtype, cnt in sorted(by_type.items()):
        print(f"    {dtype:<25} {cnt:>3}")

    if error_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    # On macOS, multiprocessing needs spawn context
    multiprocessing.set_start_method("spawn", force=True)
    main()
