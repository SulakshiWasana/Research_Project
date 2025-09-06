from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import random, glob, sys

# ---------- paths (edit if your folder names differ) ----------
ROOT = Path(__file__).parent

HP_DIR  = ROOT / "kaggle_raw" / "head-pose-estimation-data-pitch-roll-yaw"
EYE_DIR = ROOT / "kaggle_raw" / "open-closed-eyes-dataset"
PF_DIR  = ROOT / "kaggle_raw" / "pennfudan-database-for-pedestrian-detection-zip"
AUDIO_DIR_ROOT = ROOT / "kaggle_raw_audio" / "speech-activity-detection-datasets"  # contains 'Audio' subfolder

OUT_CSV = ROOT / "monitoring.csv"

RNG = random.Random(42)
np.random.seed(42)

# ---------- output schema ----------
COLUMNS = [
    "session_id","timestamp_ms",
    "face_visible","eyes_open_prob",
    "head_yaw_deg","head_pitch_deg","head_roll_deg",
    "looking_away","multi_person_count","speech_detected",
    "tab_switched","copy_paste","window_blur",
    "dwell_time_ms","blink_rate_hz",
    "suspicion_score","target"
]

def looking_away(yaw, pitch):
    return 1 if (abs(yaw) > 35 or abs(pitch) > 25) else 0

def suspicion(face_visible, eyes_open_prob, away, multi, speech, tab, copy_ev, blur, blink):
    s = (
        (1-face_visible)*0.9 +
        (1-eyes_open_prob)*0.6 +
        away*0.8 +
        min(multi,2)*0.7 +
        speech*0.5 + tab*1.0 + copy_ev*1.0 + blur*0.7 +
        (1.0 if blink < 0.05 or blink > 0.9 else 0.0)
    )
    return round(float(s), 3)

# --------- 1) Head pose → yaw/pitch/roll ----------
def rows_headpose(max_rows=2000):
    csv_path = None
    for p in HP_DIR.rglob("*.csv"):
        try:
            df5 = pd.read_csv(p, nrows=5)
            cols = {c.lower() for c in df5.columns}
            if {"yaw","pitch","roll"} <= cols:
                csv_path = p; break
        except Exception:
            pass
    if not csv_path:
        print(f"[headpose] CSV with yaw/pitch/roll not found under {HP_DIR}")
        return []

    df = pd.read_csv(csv_path).rename(columns=str.lower)
    if len(df) > max_rows:
        df = df.sample(max_rows, random_state=42).reset_index(drop=True)

    rows, t = [], 0
    for _, r in df.iterrows():
        yaw, pitch, roll = float(r.get("yaw",0)), float(r.get("pitch",0)), float(r.get("roll",0))
        face_visible = 1
        eyes_open_prob = 0.8
        away = looking_away(yaw, pitch)
        multi = 1
        speech = tab = copy_ev = blur = 0
        dwell = int(np.random.randint(800,5000))
        blink = float(np.clip(np.random.normal(0.3,0.15), 0.0, 1.5))
        score = suspicion(face_visible, eyes_open_prob, away, multi, speech, tab, copy_ev, blur, blink)
        target = 1 if score >= 1.3 else 0
        t += int(np.random.randint(400,1200))
        rows.append(["HP", t, face_visible, round(eyes_open_prob,3),
                     round(yaw,3), round(pitch,3), round(roll,3),
                     away, multi, speech, tab, copy_ev, blur,
                     dwell, round(blink,3), score, target])
    print(f"[headpose] {len(rows)} rows")
    return rows

# --------- 2) Eyes open/closed ----------
def rows_eyes(max_rows=2000):
    opens   = glob.glob(str(EYE_DIR / "**" / "*open*"  / "*.*"), recursive=True)
    closes  = glob.glob(str(EYE_DIR / "**" / "*clos*"  / "*.*"), recursive=True)
    if not opens or not closes:
        print(f"[eyes] open/closed folders not found under {EYE_DIR}")
        return []

    opens   = opens[:max_rows//2]
    closes  = closes[:max_rows//2]
    pairs = [(p,1) for p in opens] + [(p,0) for p in closes]
    RNG.shuffle(pairs)

    rows, t = [], 0
    for _, is_open in pairs:
        face_visible = 1
        eyes_open_prob = 0.95 if is_open else 0.05
        yaw = pitch = roll = 0.0
        away = 0
        multi = 1
        speech = tab = copy_ev = blur = 0
        dwell = int(np.random.randint(800,5000))
        blink = float(np.clip(np.random.normal(0.4 if is_open else 0.9, 0.1), 0.0, 1.5))
        score = suspicion(face_visible, eyes_open_prob, away, multi, speech, tab, copy_ev, blur, blink)
        target = 1 if score >= 1.3 else 0
        t += int(np.random.randint(400,1200))
        rows.append(["EYE", t, face_visible, round(eyes_open_prob,3),
                     yaw, pitch, roll, away, multi, speech, tab, copy_ev, blur,
                     dwell, round(blink,3), score, target])
    print(f"[eyes] {len(rows)} rows")
    return rows

# --------- 3) People count (Penn-Fudan) ----------
def rows_pennfudan(max_rows=300):
    ann_dir = None
    for p in PF_DIR.rglob("Annotation"):
        if p.is_dir():
            ann_dir = p; break
    if ann_dir is None:
        print(f"[pennfudan] Annotation folder not found under {PF_DIR}")
        return []

    xmls = list(ann_dir.glob("*.xml"))
    RNG.shuffle(xmls)
    xmls = xmls[:max_rows]

    rows, t = [], 0
    for x in xmls:
        try:
            root = ET.parse(x).getroot()
            objs = root.findall(".//object")
            persons = [o for o in objs if (o.findtext("name") or "").lower() == "person"]
            count = len(persons) if persons else len(objs)
        except Exception:
            count = 1

        face_visible = 1; eyes_open_prob = 0.8
        yaw=pitch=roll=0.0; away=0
        multi = max(1, int(count))
        speech = tab = copy_ev = blur = 0
        dwell = int(np.random.randint(800,5000))
        blink = float(np.clip(np.random.normal(0.3,0.15), 0.0, 1.5))
        score = suspicion(face_visible, eyes_open_prob, away, multi, speech, tab, copy_ev, blur, blink)
        target = 1 if score >= 1.3 else 0
        t += int(np.random.randint(400,1200))
        rows.append(["PENN", t, face_visible, round(eyes_open_prob,3),
                     yaw, pitch, roll, away, multi, speech, tab, copy_ev, blur,
                     dwell, round(blink,3), score, target])
    print(f"[pennfudan] {len(rows)} rows")
    return rows

# --------- 4) Audio → simple energy-based speech_detected ----------
def rows_audio(max_rows=800):
    try:
        import librosa
    except Exception as e:
        print(f"[audio] librosa not available ({e}); skipping audio.")
        return []

    audio_base = next((p for p in AUDIO_DIR_ROOT.rglob("Audio") if p.is_dir()), AUDIO_DIR_ROOT)
    files = [str(p) for p in audio_base.rglob("*") if p.suffix.lower() in (".wav",".mp3",".flac",".ogg",".m4a")]
    if not files:
        print(f"[audio] no audio found under {audio_base}; skipping audio.")
        return []
    RNG.shuffle(files)
    files = files[:max_rows]

    def is_speech_energy(path, top_db=25, min_ratio=0.20):
        try:
            y, sr = librosa.load(path, sr=16000, mono=True)
            if y.size == 0: return 0
            intervals = librosa.effects.split(y, top_db=top_db)  # non-silent segments
            voiced = sum((e - s) for s, e in intervals)
            return 1 if (voiced / len(y)) > min_ratio else 0
        except Exception:
            return 0

    rows, t = [], 0
    for p in files:
        speech = is_speech_energy(p)
        face_visible=1; eyes_open_prob=0.8
        yaw=pitch=roll=0.0; away=0; multi=1
        tab=copy_ev=blur=0
        dwell=int(np.random.randint(800,5000))
        blink=float(np.random.normal(0.3,0.15))
        blink=float(np.clip(blink,0.0,1.5))
        score = suspicion(face_visible, eyes_open_prob, away, multi, speech, tab, copy_ev, blur, blink)
        target = 1 if score >= 1.3 else 0
        t += int(np.random.randint(400,1200))
        rows.append(["AUDIO", t, face_visible, round(eyes_open_prob,3),
                     yaw, pitch, roll, away, multi, speech, tab, copy_ev, blur,
                     dwell, round(blink,3), score, target])
    print(f"[audio] {len(rows)} rows")
    return rows

def main():
    rows = []
    rows += rows_headpose()
    rows += rows_eyes()
    rows += rows_pennfudan()
    rows += rows_audio()          # 4th dataset (audio)

    if not rows:
        print("No rows created. Check folder paths at top.")
        sys.exit(1)

    df = pd.DataFrame(rows, columns=COLUMNS)
    df.to_csv(OUT_CSV, index=False)
    print(f"\n[OK] wrote {OUT_CSV} with {len(df)} rows.")

if __name__ == "__main__":
    main()

