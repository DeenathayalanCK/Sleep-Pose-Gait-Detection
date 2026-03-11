#!/usr/bin/env python3
"""
label_signals.py — Back-fill true_label column from your labelled events.

HOW TO USE:
  1. Run the system on your recording → data/signals/signals_YYYY-MM-DD.csv
  2. Watch the footage, note timestamps where people are sleeping/drowsy
  3. Create a labels.csv:
       person_id, start_sec, end_sec, true_label
       4, 342.0, 410.0, sleeping
       7, 891.0, 934.0, drowsy
       4, 1205.0, 1290.0, sleeping
  4. Run: python scripts/label_signals.py \
            --signals data/signals/signals_2026-03-11.csv \
            --labels labels.csv \
            --out data/signals/labelled_signals.csv

The script:
  - Copies all rows from signals CSV
  - For rows where (person_id matches AND video_pos_sec is in [start_sec, end_sec])
    → sets true_label = sleeping/drowsy
  - All other rows → sets true_label = awake
  - Prints a summary of label counts
"""
import argparse
import csv
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--signals", required=True, help="signals CSV path")
    ap.add_argument("--labels",  required=True, help="labels CSV path")
    ap.add_argument("--out",     required=True, help="output labelled CSV path")
    args = ap.parse_args()

    # Load label windows
    windows = []
    with open(args.labels) as f:
        reader = csv.DictReader(f)
        for row in reader:
            windows.append({
                "person_id":  int(row["person_id"]),
                "start_sec":  float(row["start_sec"]),
                "end_sec":    float(row["end_sec"]),
                "true_label": row["true_label"].strip().lower(),
            })
    print(f"Loaded {len(windows)} label windows")

    def get_label(person_id, video_pos_sec):
        if video_pos_sec == "":
            return "awake"
        try:
            pos = float(video_pos_sec)
        except ValueError:
            return "awake"
        for w in windows:
            if w["person_id"] == person_id and w["start_sec"] <= pos <= w["end_sec"]:
                return w["true_label"]
        return "awake"

    counts = {"awake": 0, "drowsy": 0, "sleeping": 0, "other": 0}

    with open(args.signals) as fin, open(args.out, "w", newline="") as fout:
        reader = csv.DictReader(fin)
        writer = csv.DictWriter(fout, fieldnames=reader.fieldnames,
                                extrasaction="ignore")
        writer.writeheader()
        for row in reader:
            try:
                pid = int(row["person_id"])
            except (ValueError, KeyError):
                continue
            label = get_label(pid, row.get("video_pos_sec", ""))
            row["true_label"] = label
            writer.writerow(row)
            counts[label] = counts.get(label, 0) + 1

    total = sum(counts.values())
    print(f"\nLabel distribution:")
    for k, v in sorted(counts.items()):
        print(f"  {k:12s}  {v:6d}  ({100*v/total:.1f}%)")
    print(f"  {'TOTAL':12s}  {total:6d}")
    print(f"\nOutput → {args.out}")

    # Warn if too few positives
    pos = counts.get("sleeping", 0) + counts.get("drowsy", 0)
    if pos < 200:
        print(f"\n⚠  Only {pos} positive rows (sleeping+drowsy).")
        print("   Need 500+ for reliable training. Record more footage.")
    else:
        print(f"\n✓  {pos} positive rows — sufficient for training.")


if __name__ == "__main__":
    main()