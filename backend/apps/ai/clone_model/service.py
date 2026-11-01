from pathlib import Path

import joblib
import numpy as np
from django.conf import settings
from sklearn.ensemble import IsolationForest

from apps.ai.models import CloneModelVersion
from apps.ai.clone_model.features import FEATURE_LABELS, FEATURE_NAMES, extract_code_features
from apps.products.models import UnitCode

MODEL_VERSION = 1
MODEL_FILE = Path(settings.BASE_DIR) / 'models' / 'clone_isolation_forest.joblib'
_cached_artifact = None
_cached_mtime = None


def latest_version():
    return CloneModelVersion.objects.order_by('-trained_at').first()


def train_model(seed=42, contamination=0.08):
    codes = UnitCode.objects.filter(scans__isnull=False).distinct().select_related('batch')
    rows = [extract_code_features(code)[0] for code in codes]
    if len(rows) < 10:
        raise ValueError('At least 10 scanned unit codes are required to train the clone model.')

    matrix = np.asarray(rows, dtype=float)
    model = IsolationForest(
        n_estimators=150,
        contamination=contamination,
        random_state=seed,
        n_jobs=-1,
    )
    model.fit(matrix)
    scores = model.decision_function(matrix)
    baseline = {
        'means': matrix.mean(axis=0).tolist(),
        'stds': np.maximum(matrix.std(axis=0), 1e-6).tolist(),
        'score_threshold': float(np.percentile(scores, contamination * 100)),
        'score_std': max(float(scores.std()), 1e-6),
        'feature_names': list(FEATURE_NAMES),
    }

    MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({'model': model, 'baseline': baseline, 'features': list(FEATURE_NAMES)}, MODEL_FILE)
    version_number = (CloneModelVersion.objects.count() + 1)
    version = CloneModelVersion.objects.create(
        version=f'1.{version_number}',
        training_samples=len(rows),
        model_path=str(MODEL_FILE),
        feature_baseline=baseline,
        training_report={
            'contamination': contamination,
            'seed': seed,
            'score_threshold': baseline['score_threshold'],
        },
    )
    invalidate_cache()
    return version


def invalidate_cache():
    global _cached_artifact, _cached_mtime
    _cached_artifact = None
    _cached_mtime = None


def _load_artifact():
    global _cached_artifact, _cached_mtime
    if not MODEL_FILE.is_file():
        return None
    mtime = MODEL_FILE.stat().st_mtime
    if _cached_artifact is None or _cached_mtime != mtime:
        _cached_artifact = joblib.load(MODEL_FILE)
        _cached_mtime = mtime
    return _cached_artifact


def score_code(unit_code, current_lat=None, current_lon=None, current_ip=None,
               current_ua=None, channel='WEB_QR'):
    artifact = _load_artifact()
    if artifact is None:
        return None
    vector, raw_features = extract_code_features(
        unit_code,
        current_lat=current_lat,
        current_lon=current_lon,
        current_ip=current_ip,
        current_ua=current_ua,
        channel=channel,
    )
    model = artifact['model']
    baseline = artifact['baseline']
    decision = float(model.decision_function([vector])[0])
    threshold = baseline['score_threshold']
    scale = max(baseline['score_std'] * 2, 1e-6)
    anomaly_score = round(min(100.0, max(0.0, 50.0 + ((threshold - decision) / scale) * 50.0)), 1)

    means = baseline['means']
    stds = baseline['stds']
    deviations = []
    for index, name in enumerate(FEATURE_NAMES):
        z_score = abs(vector[index] - means[index]) / max(stds[index], 1e-6)
        deviations.append((z_score, name, vector[index], means[index]))
    deviations.sort(reverse=True)

    reasons = []
    for z_score, name, value, average in deviations:
        if z_score < 1.5:
            continue
        unit = ' km/h' if name == 'max_speed_kmh' else ''
        direction = 'higher' if value > average else 'lower'
        reasons.append(
            f'{FEATURE_LABELS[name]} is {direction} than training average '
            f'({value:.1f}{unit} vs {average:.1f}{unit})'
        )
        if len(reasons) == 3:
            break
    return {
        'score': anomaly_score,
        'reasons': reasons,
        'features': raw_features,
        'decision_function': decision,
    }
