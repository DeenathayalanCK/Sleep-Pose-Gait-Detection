#!/usr/bin/env python3
"""
label_signals.py — Back-fill true_label using video position (seconds).

HOW TO USE:
  1. Open your recording in VLC
     Enable View → Status Bar — shows position as HH:MM:SS
     Convert to seconds: e.g. 00:35:22 = 35*60+22 = 2122s

  2. Watch the recording alongside the annotated live stream
     (stream shows person IDs drawn on each person's bounding box)

  3. Note video positions where someone is genuinely sleeping/drowsy:
     e.g. "P6 was drowsy from 2122s to 2180s in the video"

  4. Create labels.csv:
       person_id,start_sec,end_sec,true_label
       6,2122.0,2180.0,drowsy
       1,2700.0,2820.0,sleeping
       209,3070.0,3200.0,drowsy

  5. Run:
       python app/scripts/label_signals.py \
         --signals data/signals/signals_2026-03-11.csv \
         --labels  labels.csv \
         --out     data/signals/labelled_signals.csv

NOTES:
  - Rows with video_pos_sec=0.0 are automatically discarded (ReID glitches)
  - Rows with system_state=unknown/no_person are discarded
  - All rows outside a labelled window get true_label=awake
"""
import argparse
import csv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--signals", required=True)
    ap.add_argument("--labels",  required=True)
    ap.add_argument("--out",     required=True)
    args = ap.parse_args()

    # ── Load label windows ────────────────────────────────────────────
    windows = []
    with open(args.labels) as f:
        for row in csv.DictReader(f):
            windows.append({
                "person_id":  int(row["person_id"]),
                "start_sec":  float(row["start_sec"]),
                "end_sec":    float(row["end_sec"]),
                "true_label": row["true_label"].strip().lower(),
            })

    print(f"Loaded {len(windows)} label windows:")
    for w in windows:
        dur = w['end_sec'] - w['start_sec']
        print(f"  P{w['person_id']}  {w['start_sec']:.0f}s → {w['end_sec']:.0f}s  "
              f"({dur:.0f}s)  {w['true_label']}")

    def get_label(person_id, pos_sec):
        for w in windows:
            if (w["person_id"] == person_id
                    and w["start_sec"] <= pos_sec <= w["end_sec"]):
                return w["true_label"]
        return "awake"

    # ── Process signals CSV ───────────────────────────────────────────
    counts = {}
    skipped = 0

    with open(args.signals) as fin, open(args.out, "w", newline="") as fout:
        reader = csv.DictReader(fin)
        writer = csv.DictWriter(fout, fieldnames=reader.fieldnames,
                                extrasaction="ignore")
        writer.writeheader()

        for row in reader:
            # Discard no-signal rows
            if row.get("system_state", "") in ("unknown", "no_person", ""):
                skipped += 1
                continue

            # Discard rows with no valid video position
            try:
                pos = float(row["video_pos_sec"])
                if pos <= 0.0:
                    skipped += 1
                    continue
            except (ValueError, KeyError):
                skipped += 1
                continue

            try:
                pid = int(row["person_id"])
            except (ValueError, KeyError):
                skipped += 1
                continue

            label = get_label(pid, pos)
            row["true_label"] = label
            writer.writerow(row)
            counts[label] = counts.get(label, 0) + 1

    # ── Summary ───────────────────────────────────────────────────────
    total = sum(counts.values())
    written = total
    print(f"\nRows written: {written}  |  Skipped: {skipped}")
    print("Label distribution:")
    for k in ["sleeping", "drowsy", "awake"]:
        v = counts.get(k, 0)
        pct = 100 * v / total if total else 0
        print(f"  {k:12s}  {v:6d}  ({pct:.1f}%)")

    pos = counts.get("sleeping", 0) + counts.get("drowsy", 0)
    print()
    if pos == 0:
        print("⚠  No positives assigned — check person_id and seconds match VLC.")
    elif pos < 200:
        print(f"⚠  Only {pos} positive rows — need 500+ for reliable training.")
    else:
        print(f"✓  {pos} positive rows — ready to train.")

    print(f"\nOutput → {args.out}")


if __name__ == "__main__":
    main()