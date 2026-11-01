import csv
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score

from apps.ai.clone_model.features import extract_code_features
from apps.ai.clone_model.service import score_code
from apps.ai.models import CloneEvaluationCase
from apps.reports.models import SystemSettings


DETECTORS = ('rules_only', 'ml_only', 'hybrid')


class Command(BaseCommand):
    help = 'Evaluate rules-only, ML-only, and hybrid clone detection on synthetic scenarios.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            default=str(Path(settings.BASE_DIR).parent / 'evaluation'),
        )

    def handle(self, *args, **options):
        cases = list(CloneEvaluationCase.objects.select_related('unit_code', 'unit_code__batch'))
        if not cases:
            raise CommandError('No evaluation cases found. Run generate_synthetic_scans first.')
        if not any(score_code(case.unit_code) is not None for case in cases[:1]):
            raise CommandError('No trained model artifact found. Run train_clone_model first.')

        config = SystemSettings.get_settings()
        predictions = {name: [] for name in DETECTORS}
        actuals = []
        for case in cases:
            _, raw = extract_code_features(case.unit_code)
            ml_result = score_code(case.unit_code)
            if ml_result is None:
                raise CommandError('The trained clone model is not available.')
            rule_score, rule_flag = _rule_result(raw, config)
            hybrid_score = (
                rule_score * config.rule_weight + ml_result['score'] * config.ml_weight
            ) / max(config.rule_weight + config.ml_weight, 1e-6)
            actual = case.is_attack
            actuals.append(actual)
            predictions['rules_only'].append(rule_flag)
            predictions['ml_only'].append(ml_result['score'] >= config.ml_threshold)
            predictions['hybrid'].append(
                rule_flag
                or ml_result['score'] >= config.ml_threshold
                or hybrid_score >= config.hybrid_threshold
            )

        rows = []
        for detector in DETECTORS:
            predicted = predictions[detector]
            tn, fp, fn, tp = confusion_matrix(actuals, predicted, labels=[False, True]).ravel()
            precision = precision_score(actuals, predicted, zero_division=0)
            recall = recall_score(actuals, predicted, zero_division=0)
            f1 = f1_score(actuals, predicted, zero_division=0)
            fpr = fp / (fp + tn) if fp + tn else 0
            rows.append({
                'detector': detector,
                'attack_type': 'ALL',
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'detection_rate': recall,
                'false_positive_rate': fpr,
                'tn': tn,
                'fp': fp,
                'fn': fn,
                'tp': tp,
            })
            for attack_type in sorted({case.attack_type for case in cases if case.is_attack}):
                selected = [index for index, case in enumerate(cases) if case.attack_type in ('GENUINE', attack_type)]
                target = [cases[index].attack_type == attack_type for index in selected]
                detected = [predicted[index] for index in selected]
                c_tn, c_fp, c_fn, c_tp = confusion_matrix(target, detected, labels=[False, True]).ravel()
                rows.append({
                    'detector': detector,
                    'attack_type': attack_type,
                    'precision': precision_score(target, detected, zero_division=0),
                    'recall': recall_score(target, detected, zero_division=0),
                    'f1': f1_score(target, detected, zero_division=0),
                    'detection_rate': recall_score(target, detected, zero_division=0),
                    'false_positive_rate': c_fp / (c_fp + c_tn) if c_fp + c_tn else 0,
                    'tn': c_tn,
                    'fp': c_fp,
                    'fn': c_fn,
                    'tp': c_tp,
                })

        output_dir = Path(options['output_dir'])
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / 'clone_detection_results.csv'
        with csv_path.open('w', newline='', encoding='utf-8') as output:
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        chart_path = output_dir / 'clone_detection_results.png'
        _write_chart(rows, chart_path)

        self.stdout.write('Detector      Precision  Recall  F1     Detection  FPR')
        self.stdout.write('------------  ---------  ------  -----  ---------  -----')
        for row in rows:
            if row['attack_type'] == 'ALL':
                self.stdout.write(
                    f"{row['detector']:<12}  {row['precision']:.3f}      {row['recall']:.3f}  "
                    f"{row['f1']:.3f}  {row['detection_rate']:.3f}      {row['false_positive_rate']:.3f}"
                )
        self.stdout.write(f'Per-attack confusion matrices and metrics: {csv_path}')
        self.stdout.write(f'Chart: {chart_path}')


def _rule_result(features, config):
    frequency = min(100.0, features['scan_total'] / max(1, config.max_scan_threshold) * 100)
    velocity = 100.0 if features['max_speed_kmh'] > config.max_velocity_kmh else 0.0
    entropy = 100.0 if features['distinct_ips'] >= config.distinct_ip_threshold else 0.0
    score = (
        frequency * config.weight_frequency
        + velocity * config.weight_velocity
        + entropy * config.weight_entropy
    )
    flag = (
        features['scan_total'] >= config.max_scan_threshold
        or velocity > 0
        or entropy > 0
        or score >= 60
    )
    return score, flag


def _write_chart(rows, path):
    all_rows = [row for row in rows if row['attack_type'] == 'ALL']
    types = sorted({row['attack_type'] for row in rows if row['attack_type'] != 'ALL'})
    fig, (left, right) = plt.subplots(1, 2, figsize=(12, 4.5))
    x = range(len(all_rows))
    left.bar([i - 0.25 for i in x], [r['f1'] for r in all_rows], width=0.25, label='F1')
    left.bar([i for i in x], [r['detection_rate'] for r in all_rows], width=0.25, label='Detection rate')
    left.bar([i + 0.25 for i in x], [r['false_positive_rate'] for r in all_rows], width=0.25, label='False positive rate')
    left.set_xticks(list(x), [r['detector'].replace('_', ' ') for r in all_rows], rotation=15)
    left.set_ylim(0, 1)
    left.legend()
    left.set_title('Overall detector metrics')
    for detector in DETECTORS:
        rows_for_detector = [r for r in rows if r['detector'] == detector and r['attack_type'] != 'ALL']
        right.plot(types, [r['detection_rate'] for r in rows_for_detector], marker='o', label=detector.replace('_', ' '))
    right.set_ylim(0, 1)
    right.set_title('Detection rate by attack type')
    right.tick_params(axis='x', rotation=20)
    right.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
