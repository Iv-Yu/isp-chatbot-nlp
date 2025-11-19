import argparse
import os
import sys
import pandas as pd
from chatbot.rule_engine import RuleEngine


def evaluate(csv_path: str):
    if not os.path.exists(csv_path):
        print(f"File tidak ditemukan: {csv_path}")
        return 1

    df = pd.read_csv(csv_path)
    engine = RuleEngine()

    # Pastikan kolom yang diperlukan ada
    expected_cols = ["Text_Pertanyaan", "Label_Intent"]
    for c in expected_cols:
        if c not in df.columns:
            print(f"Kolom yang diperlukan tidak ditemukan di CSV: {c}")
            print("Kolom yang ada:", df.columns.tolist())
            return 2

    total = len(df)
    if total == 0:
        print("Dataset kosong.")
        return 3

    correct = 0
    results = []

    for idx, row in df.iterrows():
        user_text = str(row["Text_Pertanyaan"]).strip()
        true_label = str(row["Label_Intent"]).strip()

        intent, _ = engine.detect_intent(user_text)
        predicted = intent.replace("_", " ").title()

        is_correct = predicted == true_label

        results.append([user_text, true_label, predicted, is_correct])

        if is_correct:
            correct += 1

    # Hitung akurasi
    accuracy = correct / total * 100
    print(f"Akurasi chatbot: {accuracy:.2f}% ({correct}/{total})")

    # Simpan hasil evaluasi ke file di folder yang sama dengan CSV
    out_dir = os.path.dirname(csv_path) or "."
    out_path = os.path.join(out_dir, "hasil_evaluasi_chatbot_v2.csv")
    report = pd.DataFrame(results, columns=["Pertanyaan", "Label_Asli", "Prediksi", "Benar?"])
    report.to_csv(out_path, index=False)
    print(f"Hasil evaluasi disimpan ke {out_path}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evaluate rule-based chatbot on a CSV dataset")
    parser.add_argument("--csv", "-c", default="datasheet/Dummy_Dataset.csv",
                        help="Path to CSV file (default: src/datasheet/Dummy_Dataset.csv relative to src)")
    args = parser.parse_args(argv)

    # If the user passed a relative path, make it relative to the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = args.csv
    if not os.path.isabs(csv_path):
        csv_path = os.path.join(script_dir, csv_path)

    try:
        return evaluate(csv_path)
    except Exception as e:
        print("Terjadi error saat evaluasi:", e)
        return 99


if __name__ == "__main__":
    sys.exit(main())
