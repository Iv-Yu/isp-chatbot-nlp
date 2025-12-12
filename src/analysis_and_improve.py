import os
import argparse
import pandas as pd
from collections import Counter, defaultdict
from chatbot.rule_engine import RuleEngine
from chatbot.rules import INTENT_RULES
from chatbot.nlp_processor import NLPProcessor


def normalize_label(s: str) -> str:
    return str(s).strip().lower()


def tokens(text: str, n=1):
    p = NLPProcessor()
    norm = p.normalize(text)
    toks = norm.split()
    if n == 1:
        return toks
    out = []
    for i in range(len(toks) - n + 1):
        out.append(" ".join(toks[i : i + n]))
    return out


def analyze(csv_path: str, top_k=20):
    if not os.path.exists(csv_path):
        print("File tidak ditemukan:", csv_path)
        return 1

    df = pd.read_csv(csv_path)
    required = ["Text_Pertanyaan", "Label_Intent"]
    for c in required:
        if c not in df.columns:
            print("CSV tidak memiliki kolom yang diperlukan:", c)
            return 2

    engine = RuleEngine()
    p = NLPProcessor()

    total = len(df)
    results = []

    # For metrics
    labels_true = []
    labels_pred = []

    # For suggestions
    per_intent_texts = defaultdict(list)

    # existing patterns per intent (normalized)
    existing_patterns = {r["name"]: set(p.normalize(x) for x in r.get("patterns", [])) for r in INTENT_RULES}

    for idx, row in df.iterrows():
        text = str(row["Text_Pertanyaan"]).strip()
        true_label = normalize_label(row["Label_Intent"])  # expected like 'gangguan umum'

        intent, _, score = engine.detect_with_score(text)
        pred_label = intent.replace("_", " ").strip().lower()

        labels_true.append(true_label)
        labels_pred.append(pred_label)

        is_correct = pred_label == true_label
        results.append((text, true_label, pred_label, is_correct, score))

        # collect text by true intent for suggestion building
        per_intent_texts[true_label].append(text)

    # Build DataFrame of misclassifications
    df_res = pd.DataFrame(results, columns=["Pertanyaan", "Label_Asli", "Prediksi", "Benar?", "Score"]) 
    mis = df_res[~df_res["Benar?"]]
    cor = df_res[df_res["Benar?"]]

    accuracy = cor.shape[0] / total * 100
    print(f"Akurasi: {accuracy:.2f}% ({cor.shape[0]}/{total})")

    # Confusion matrix counts
    labels = sorted(set(labels_true) | set(labels_pred))
    label_index = {l: i for i, l in enumerate(labels)}
    import numpy as np

    cm = np.zeros((len(labels), len(labels)), dtype=int)
    for t, p in zip(labels_true, labels_pred):
        cm[label_index[t], label_index[p]] += 1

    print("\nConfusion matrix (rows=true, cols=pred):")
    print(labels)
    print(cm)

    # Precision/Recall/F1 per label
    prf = {}
    for i, lab in enumerate(labels):
        tp = cm[i, i]
        fn = cm[i, :].sum() - tp
        fp = cm[:, i].sum() - tp
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        prf[lab] = (prec, rec, f1)

    print("\nPer-intent metrics:")
    for lab, (prec, rec, f1) in prf.items():
        print(f"- {lab}: Precision={prec:.2f}, Recall={rec:.2f}, F1={f1:.2f}")

    # Show top misclassified examples
    print("\nContoh misclassifications (top 20):")
    for _, row in mis.head(20).iterrows():
        print(f"[{row['Score']}] True={row['Label_Asli']} Pred={row['Prediksi']} -> {row['Pertanyaan']}")

    # Suggest candidate patterns per true intent: frequent unigrams and bigrams that are
    # present in true texts but not present in existing patterns.
    suggestions = {}
    for intent_label, texts in per_intent_texts.items():
        uni = Counter()
        bi = Counter()
        for t in texts:
            for tok in tokens(t, 1):
                uni[tok] += 1
            for gram in tokens(t, 2):
                bi[gram] += 1
        # remove tokens already in existing patterns for that intent (normalize names)
        # map intent_label like 'gangguan umum' to internal name 'gangguan_umum'
        internal_name = intent_label.replace(" ", "_")
        existing = existing_patterns.get(internal_name, set())
        cand_uni = [w for w, c in uni.most_common(top_k) if w not in existing]
        cand_bi = [w for w, c in bi.most_common(top_k) if w not in existing]
        suggestions[intent_label] = {"unigrams": cand_uni[:10], "bigrams": cand_bi[:10]}

    # Print summary suggestions
    print("\nSaran pattern kandidat per intent (top tokens not already in patterns):")
    for intent_label, s in suggestions.items():
        print(f"- {intent_label}: unigrams={s['unigrams'][:6]} | bigrams={s['bigrams'][:6]}")

    # Save misclassification CSV for further inspection
    out_dir = os.path.dirname(csv_path) or "."
    out_mis = os.path.join(out_dir, "misclassifications.csv")
    df_res.to_csv(out_mis, index=False)
    print(f"\nMisclassification report saved to {out_mis}")

    # Save suggestions to CSV
    sugg_rows = []
    for intent_label, s in suggestions.items():
        for u in s["unigrams"]:
            sugg_rows.append([intent_label, "unigram", u])
        for b in s["bigrams"]:
            sugg_rows.append([intent_label, "bigram", b])
    df_sugg = pd.DataFrame(sugg_rows, columns=["Intent", "Type", "PatternCandidate"]) 
    out_sugg = os.path.join(out_dir, "suggested_patterns.csv")
    df_sugg.to_csv(out_sugg, index=False)
    print(f"Pattern suggestions saved to {out_sugg}")

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", "-c", default="datasheet/Dummy_Dataset.csv")
    args = parser.parse_args()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = args.csv if os.path.isabs(args.csv) else os.path.join(script_dir, args.csv)
    analyze(csv_path)
