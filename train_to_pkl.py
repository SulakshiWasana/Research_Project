# train_to_pkl.py
import argparse, joblib, pandas as pd, numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

EXPECTED = [
    "face_visible","eyes_open_prob","head_yaw_deg","head_pitch_deg","head_roll_deg",
    "looking_away","multi_person_count","speech_detected","tab_switched","copy_paste",
    "window_blur","dwell_time_ms","blink_rate_hz"
]
NUMERIC = ["eyes_open_prob","head_yaw_deg","head_pitch_deg","head_roll_deg","dwell_time_ms","blink_rate_hz"]

def main(csv_path, pkl_out):
    # 1) load
    df = pd.read_csv(csv_path)

    # 2) features/target
    feats = [c for c in EXPECTED if c in df.columns]
    if "target" not in df.columns:
        raise ValueError("CSV must contain a 'target' column (0=normal, 1=suspicious).")
    if not feats:
        raise ValueError("None of the expected feature columns were found.")
    X, y = df[feats].copy(), df["target"].astype(int)

    # 3) clean
    for c in feats:
        X[c] = pd.to_numeric(X[c], errors="coerce")
    X = X.fillna(X.median(numeric_only=True))

    # 4) pipeline
    num_cols = [c for c in NUMERIC if c in X.columns]
    bin_cols = [c for c in feats if c not in num_cols]
    pre = ColumnTransformer([
        ("num", StandardScaler(), num_cols),
        ("bin", "passthrough", bin_cols),
    ])
    clf = RandomForestClassifier(
        n_estimators=300,
        random_state=42,
        class_weight="balanced_subsample",
        n_jobs=-1,
    )
    pipe = Pipeline([("pre", pre), ("clf", clf)])

    # 5) split, train, eval
    strat = y if y.nunique() > 1 else None
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=42, stratify=strat)
    pipe.fit(Xtr, ytr)
    pred = pipe.predict(Xte)

    # 6) report
    acc = accuracy_score(yte, pred)
    print("Features used:", feats)
    print("Train size:", len(Xtr), " Test size:", len(Xte))
    print("Accuracy:", round(acc, 4))
    print("Confusion matrix:\n", confusion_matrix(yte, pred))
    print(classification_report(yte, pred, digits=4))

    # 7) save
    joblib.dump({"pipeline": pipe, "features": feats, "labels": {0:"normal", 1:"suspicious"}}, pkl_out)
    print("Saved:", pkl_out)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="Path to monitoring.csv")
    ap.add_argument("out", help="Output .pkl file, e.g., monitoring_model.pkl")
    args = ap.parse_args()
    main(args.csv, args.out)
