import argparse
import json
from pathlib import Path
from typing import Tuple

import joblib
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from ..chatbot.nlp_processor import NLPProcessor


def load_dataset(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = [
            {"text": pattern, "intent": intent["tag"]}
            for intent in data.get("intents", [])
            for pattern in intent.get("patterns", [])
        ]
        return pd.DataFrame(rows)

    df = pd.read_csv(path)
    missing = {"text", "intent"} - set(df.columns.str.lower())
    if missing:
        raise ValueError(f"Kolom wajib text & intent, kurang: {missing}")
    df = df.rename(columns={"Text": "text", "Intent": "intent"})
    return df[["text", "intent"]].dropna()


def build_pipeline(calibrated: bool = True, cv: int = 5) -> Pipeline:
    vectorizer = TfidfVectorizer(
        tokenizer=NLPProcessor(),
        lowercase=False,
        token_pattern=None,
        ngram_range=(1, 2),
        min_df=1,
    )

    base_model = LinearSVC()
    if calibrated:
        clf = CalibratedClassifierCV(base_model, cv=cv)
    else:
        clf = base_model

    return Pipeline(
        [
            ("tfidf", vectorizer),
            ("clf", clf),
        ]
    )


def train(dataset: Path, model_out: Path, test_size: float = 0.2) -> Tuple[Pipeline, pd.DataFrame]:
    df = load_dataset(dataset)

    n_classes = df["intent"].nunique()
    n_samples = len(df)

    # Ensure test_size is large enough for stratification
    # test_size (as a proportion) * n_samples must be >= n_classes
    required_test_size = n_classes / n_samples
    if test_size < required_test_size:
        print(
            f"Warning: test_size ({test_size}) is too small for stratification with {n_classes} classes. "
            f"Adjusting test_size to {required_test_size:.2f}"
        )
        test_size = required_test_size

    # Also handle the case where a class has only one sample
    # In this case, even with adjusted test_size, stratified split is impossible
    # A simple solution is to not stratify if any class has only one sample
    counts = df["intent"].value_counts()
    stratify = None if any(counts < 2) else df["intent"]
    if stratify is None:
        print("Warning: Cannot stratify because some classes have only one sample.")

    X_train, X_test, y_train, y_test = train_test_split(
        df["text"], df["intent"], test_size=test_size, random_state=42, stratify=stratify
    )

    train_counts = y_train.value_counts()
    min_class_count = train_counts.min() if not train_counts.empty else 0

    default_cv = 5
    if min_class_count < default_cv:
        if min_class_count < 2:
            print(
                "Warning: Disabling calibration as some classes have less than 2 samples in the training data, "
                "which is insufficient for cross-validation."
            )
            pipeline = build_pipeline(calibrated=False)
        else:
            print(
                f"Warning: Adjusting cross-validation folds for calibration to {min_class_count} "
                "due to small class sizes."
            )
            pipeline = build_pipeline(calibrated=True, cv=min_class_count)
    else:
        pipeline = build_pipeline(calibrated=True, cv=default_cv)

    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    print(classification_report(y_test, y_pred, digits=4, zero_division=0))

    model_out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, model_out)
    print(f"Model tersimpan di {model_out}")
    return pipeline, df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Training model intent Chatbot ISP.")
    parser.add_argument("--dataset", type=Path, default=Path("data/intent_dataset.csv"))
    parser.add_argument("--model-out", type=Path, default=Path("models/intent_classifier.joblib"))
    parser.add_argument("--test-size", type=float, default=0.2)
    args = parser.parse_args()

    train(args.dataset, args.model_out, args.test_size)
