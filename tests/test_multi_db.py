#!/usr/bin/env python3

import argparse
import atexit
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".mp4", ".wv", ".ape", ".wma"}
NUM_DBS = 3


def collect_files(directory: Path, extensions: set[str]) -> list[Path]:
    files = sorted(
        f for f in directory.rglob("*") if f.suffix.lower() in extensions and f.is_file()
    )
    log.info(f"Found {len(files)} files in {directory}")
    return files


def split_into_batches(items: list, n: int) -> list[list]:
    batches = [[] for _ in range(n)]
    for i, item in enumerate(items):
        batches[i % n].append(item)
    return batches


def run_olaf(args: list[str], label: str = "") -> subprocess.CompletedProcess:
    cmd = ["olaf"] + args
    log.debug(f"Running: {' '.join(str(a) for a in cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.error(f"olaf failed ({label}): {result.stderr.strip()}")
    return result


def store_file(db_path: Path, file: Path, db_index: int, progress: str) -> bool:
    t0 = time.monotonic()
    result = run_olaf(
        ["--db", str(db_path), "store", str(file)],
        label=f"store DB {db_index} <- {file.name}",
    )
    elapsed = time.monotonic() - t0
    if result.returncode == 0:
        log.info(f"  [{progress}] DB {db_index}: stored {file.name} ({elapsed:.1f}s)")
        return True
    log.error(f"  [{progress}] DB {db_index}: failed to store {file.name} ({elapsed:.1f}s)")
    return False


def run_stats(db_path: Path, db_index: int):
    result = run_olaf(["--db", str(db_path), "stats"], label=f"stats DB {db_index}")
    if result.stdout.strip():
        log.info(f"DB {db_index} stats:\n{result.stdout.strip()}")
    return result


def parse_query_output(stdout: str) -> list[dict]:
    hits = []
    for line in stdout.strip().splitlines():
        parts = line.split(",")
        if len(parts) < 11:
            continue
        try:
            match_count = int(parts[4].strip())
        except ValueError:
            continue
        if match_count > 0:
            hits.append({
                "query_basename": parts[2].strip(),
                "match_count": match_count,
                "ref_path": parts[7].strip(),
            })
    return hits


def query_file_against_db(db_path: Path, query_file: Path, db_index: int) -> list[dict]:
    result = run_olaf(
        ["--db", str(db_path), "query", str(query_file)],
        label=f"query DB {db_index} <- {query_file.name}",
    )
    if result.returncode != 0:
        return []
    return parse_query_output(result.stdout)


def main():
    args = parse_args()
    db_paths, cleanup = setup_dbs()
    atexit.register(cleanup)
    run_test(args, db_paths)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test Olaf multi-DB functionality")
    parser.add_argument(
        "--music-dir", type=Path, required=True,
        help="Directory of mp3 files to index",
    )
    parser.add_argument(
        "--creatives-dir", type=Path, required=True,
        help="Directory of audio files to query",
    )
    parser.add_argument(
        "--max-queries", type=int, default=20,
        help="Maximum number of creative files to query (default: 20)",
    )
    return parser.parse_args()


def setup_dbs() -> tuple[list[Path], callable]:
    tmp_root = Path(tempfile.mkdtemp(prefix="olaf_multidb_test_"))
    log.info(f"Temp root: {tmp_root}")
    db_paths = []
    for i in range(NUM_DBS):
        db_dir = tmp_root / f"db_{i}"
        db_dir.mkdir()
        db_paths.append(db_dir)

    def cleanup():
        log.info(f"Cleaning up {tmp_root}")
        shutil.rmtree(tmp_root, ignore_errors=True)

    return db_paths, cleanup


def run_test(args: argparse.Namespace, db_paths: list[Path]):
    music_files = collect_files(args.music_dir, {".mp3"})
    if not music_files:
        log.error("No mp3 files found in music directory")
        sys.exit(1)

    batches = split_into_batches(music_files, NUM_DBS)
    total_stores = len(music_files)
    log.info(f"--- Storing {total_stores} files across {NUM_DBS} DBs ---")
    store_start = time.monotonic()
    completed = 0
    for i, (db_path, batch) in enumerate(zip(db_paths, batches)):
        for f in batch:
            completed += 1
            store_file(db_path, f, i, f"{completed}/{total_stores}")
    store_elapsed = time.monotonic() - store_start
    log.info(f"All stores completed in {store_elapsed:.1f}s ({store_elapsed / max(total_stores, 1):.2f}s avg)")

    log.info("--- Stats ---")
    for i, db_path in enumerate(db_paths):
        run_stats(db_path, i)

    creative_files = collect_files(args.creatives_dir, AUDIO_EXTENSIONS)
    if not creative_files:
        log.error("No audio files found in creatives directory")
        sys.exit(1)

    query_files = creative_files[: args.max_queries]
    total_queries = len(query_files) * NUM_DBS
    log.info(f"--- Querying {len(query_files)} creatives against {NUM_DBS} DBs ({total_queries} total queries) ---")

    db_match_counts = [0] * NUM_DBS
    db_hit_details: list[list[tuple[str, list[dict]]]] = [[] for _ in range(NUM_DBS)]

    query_start = time.monotonic()
    completed = 0
    for qf in query_files:
        for i, db_path in enumerate(db_paths):
            t0 = time.monotonic()
            hits = query_file_against_db(db_path, qf, i)
            elapsed = time.monotonic() - t0
            completed += 1
            if hits:
                total = sum(h["match_count"] for h in hits)
                db_match_counts[i] += total
                db_hit_details[i].append((qf.name, hits))
                log.info(f"  [{completed}/{total_queries}] {qf.name} -> DB {i}: {total} matches ({elapsed:.1f}s)")
            else:
                log.info(f"  [{completed}/{total_queries}] {qf.name} -> DB {i}: no match ({elapsed:.1f}s)")
    query_elapsed = time.monotonic() - query_start
    log.info(f"All queries completed in {query_elapsed:.1f}s ({query_elapsed / max(completed, 1):.2f}s avg)")

    log.info("--- Summary ---")
    for i in range(NUM_DBS):
        detail_count = len(db_hit_details[i])
        log.info(f"DB {i}: {db_match_counts[i]} total matches from {detail_count} query files")
    log.info(f"Overall: {sum(db_match_counts)} total matches across all DBs")


if __name__ == "__main__":
    main()
