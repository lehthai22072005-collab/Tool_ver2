from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


def evaluate(predictions: str, ground_truth: str, output="reports/evaluation") -> dict:
    out = Path(output); out.mkdir(parents=True, exist_ok=True)
    predicted = {}
    pred_path = Path(predictions)
    for path in pred_path.glob("*.json"):
        try:
            row = json.loads(path.read_text(encoding="utf-8")); predicted[row["document_id"]] = row["entities"]
        except Exception: pass
    truth = {row["document_id"]: row for row in _jsonl(ground_truth)}
    prediction_ids = set(predicted)
    truth_ids = set(truth)
    tp = Counter(); fp = Counter(); fn = Counter()
    false_pos, false_neg, boundary, confusion = [], [], [], Counter()
    for doc_id, doc in truth.items():
        gold = {(e["start_char"], e["end_char"], e["label"]) for e in doc["entities"]}
        pred = {(e["start_char"], e["end_char"], e["label"]) for e in predicted.get(doc_id, [])}
        for item in gold & pred: tp[item[2]] += 1
        for item in pred - gold:
            fp[item[2]] += 1; false_pos.append({"document_id": doc_id, "start_char": item[0], "end_char": item[1], "label": item[2]})
            overlaps = [g for g in gold if item[0] < g[1] and g[0] < item[1]]
            if overlaps:
                best = max(overlaps, key=lambda g: min(item[1], g[1]) - max(item[0], g[0]))
                confusion[(best[2], item[2])] += 1
                boundary.append({"document_id": doc_id, "pred_start": item[0], "pred_end": item[1],
                                 "pred_label": item[2], "gold_start": best[0], "gold_end": best[1], "gold_label": best[2]})
        for item in gold - pred:
            fn[item[2]] += 1; false_neg.append({"document_id": doc_id, "start_char": item[0], "end_char": item[1], "label": item[2]})
    labels = sorted(set(tp) | set(fp) | set(fn))
    rows = []
    for label in labels:
        p = tp[label] / max(tp[label] + fp[label], 1); r = tp[label] / max(tp[label] + fn[label], 1)
        rows.append({"label": label, "precision": p, "recall": r, "f1": 2*p*r/max(p+r, 1e-15), "support": tp[label]+fn[label]})
    total_tp, total_fp, total_fn = sum(tp.values()), sum(fp.values()), sum(fn.values())
    precision = total_tp / max(total_tp+total_fp, 1); recall = total_tp / max(total_tp+total_fn, 1)
    metrics = {"micro": {"precision": precision, "recall": recall, "f1": 2*precision*recall/max(precision+recall, 1e-15),
                         "tp": total_tp, "fp": total_fp, "fn": total_fn},
               "macro": {"precision": sum(r["precision"] for r in rows)/max(len(rows), 1),
                         "recall": sum(r["recall"] for r in rows)/max(len(rows), 1),
                         "f1": sum(r["f1"] for r in rows)/max(len(rows), 1)},
               "documents": len(truth), "predicted_documents": len(predicted),
               "matched_documents": len(prediction_ids & truth_ids),
               "missing_prediction_documents": sorted(truth_ids - prediction_ids),
               "unmatched_prediction_documents": sorted(prediction_ids - truth_ids),
               "overlap_errors": len(boundary)}
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    _csv(out/"metrics_by_label.csv", rows); _csv(out/"false_positives.csv", false_pos)
    _csv(out/"false_negatives.csv", false_neg); _csv(out/"boundary_errors.csv", boundary)
    _csv(out/"confusion_matrix.csv", [{"gold_label": a, "pred_label": b, "count": n} for (a,b),n in confusion.items()])
    (out/"error_analysis.md").write_text(
        "# Error analysis\n\n"
        f"- False positives: {len(false_pos)}\n- False negatives: {len(false_neg)}\n"
        f"- Overlap/boundary or label errors: {len(boundary)}\n\n"
        "Review CSV files for document-level evidence. Extraction, chunk-boundary and segmentation causes "
        "must be assigned only after inspecting affected source documents.\n", encoding="utf-8")
    return metrics


def _jsonl(path): return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x]
def _csv(path, rows):
    fields = list(rows[0]) if rows else ["document_id"]
    with Path(path).open("w", newline="", encoding="utf-8-sig") as f:
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
def main():
    p=argparse.ArgumentParser(); p.add_argument("--predictions",required=True); p.add_argument("--ground-truth",required=True)
    p.add_argument("--output",default="reports/evaluation"); a=p.parse_args()
    print(json.dumps(evaluate(a.predictions,a.ground_truth,a.output),indent=2))
if __name__=="__main__": main()
