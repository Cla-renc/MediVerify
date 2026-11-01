"""
MediVerify Evaluation Toolkit (Phase 10)
=========================================
Simulates:
  (a) 10,000 genuine scan events
  (b) Cloned-code attacks of varying difficulty
  (c) Spatially-nearby location attacks

Measures:
  - Detection Rate (true positive rate)
  - False Positive Rate
  - Average Verification Response Time

Outputs:
  - Markdown table summary for final report
  - Per-category breakdown

Usage:
    cd backend
    python ../evaluation/benchmark.py
"""

import os
import sys
import time
import math
import random
import hmac
import hashlib
import statistics
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mediverify.settings')

import django
django.setup()

from apps.products.models import Manufacturer, Product, Batch, UnitCode
from apps.verification.models import VerificationScan, CloneAlert
from apps.reports.models import SystemSettings
from apps.verification.engine import CloneDetectionEngine, haversine_distance_km
from django.utils import timezone

def generate_test_code(batch_id, serial):
    secret = b'mediverify-hmac-secret-signature-key-998877'
    raw = f"{batch_id}:{serial}".encode()
    sig = hmac.new(secret, raw, hashlib.sha256).hexdigest()[:12].upper()
    return f"MV-{serial}-{sig}", sig

def get_or_create_test_batch():
    mfg, _ = Manufacturer.objects.get_or_create(
        license_number="BENCH-PPB-0000",
        defaults=dict(name="Benchmark Pharma", country="Kenya", contact_email="bench@test.co.ke", is_verified=True)
    )
    from apps.authentication.models import User
    p, _ = Product.objects.get_or_create(
        brand_name="BenchMedic 250",
        manufacturer=mfg,
        defaults=dict(
            generic_name="Bencholine",
            dosage_form="Tablet",
            strength="250mg",
            usage_instructions_en="Test only.",
            usage_instructions_sw="Mtihani peke yake.",
            side_effects_en="None.",
            side_effects_sw="Hakuna.",
            key_warnings_en="Test use only.",
            key_warnings_sw="Matumizi ya mtihani peke yake."
        )
    )
    b, _ = Batch.objects.get_or_create(
        batch_number="BENCH-EVAL-2026",
        defaults=dict(
            product=p,
            manufacture_date=(timezone.now().date() - timedelta(days=60)),
            expiry_date=(timezone.now().date() + timedelta(days=300)),
            total_quantity=15000
        )
    )
    return b

def create_unit_codes(batch, count):
    codes = []
    for i in range(1, count + 1):
        serial = f"BENCH-{i:06d}"
        secure_code, sig = generate_test_code(str(batch.id), serial)
        uc, _ = UnitCode.objects.get_or_create(
            batch=batch, serial_number=serial,
            defaults=dict(secure_code=secure_code, hmac_signature=sig, scan_count=0)
        )
        codes.append(uc)
    return codes

def reset_unit_code(uc):
    uc.scan_count = 0
    uc.is_flagged_clone = False
    uc.save()
    VerificationScan.objects.filter(unit_code=uc).delete()
    CloneAlert.objects.filter(unit_code=uc).delete()

def run_genuine_scan(uc, lat, lon, ip):
    engine = CloneDetectionEngine(uc, current_lat=lat, current_lon=lon, current_ip=ip)
    result = engine.evaluate()
    VerificationScan.objects.create(
        unit_code=uc, raw_code=uc.secure_code, channel='WEB_QR',
        result_status='GENUINE' if not result['is_clone'] else 'SUSPECTED_CLONE',
        latitude=lat, longitude=lon, ip_address=ip
    )
    uc.scan_count += 1
    uc.save()
    return result

def simulate_genuine_scans(unit_codes, n=10000):
    """Simulate N single genuine scans. Each code is scanned once from a random Kenyan location."""
    print(f"\n[A] Simulating {n:,} genuine single-scan events…")
    kenya_locs = [
        (-1.286389, 36.817223), (-4.043477, 39.668206), (-0.091702, 34.767956),
        (-0.303099, 36.080026), (0.514277, 35.269780), (-0.366667, 36.900000),
    ]
    results = []
    latencies = []

    for i in range(n):
        uc = unit_codes[i % len(unit_codes)]
        if i < len(unit_codes):
            reset_unit_code(uc)
        lat, lon = random.choice(kenya_locs)
        lat += random.uniform(-0.5, 0.5)
        lon += random.uniform(-0.5, 0.5)
        ip = f"197.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"

        t0 = time.perf_counter()
        result = run_genuine_scan(uc, lat, lon, ip)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        latencies.append(elapsed_ms)
        results.append(result)

        if (i + 1) % 1000 == 0:
            print(f"  Progress: {i+1:,}/{n:,} scans completed…")

    false_positives = sum(1 for r in results if r['is_clone'])
    return {
        'category': 'Genuine (single-scan)',
        'total': n,
        'flagged': false_positives,
        'detection_rate': 0.0,
        'false_positive_rate': round(false_positives / n * 100, 2),
        'avg_latency_ms': round(statistics.mean(latencies), 2),
        'p95_latency_ms': round(sorted(latencies)[int(len(latencies) * 0.95)], 2),
    }

def simulate_clone_attacks_high_frequency(unit_codes, n=500):
    """Simulate clone attacks: same code scanned > threshold times from different IPs."""
    print(f"\n[B1] Simulating {n} high-frequency clone attacks…")
    settings = SystemSettings.get_settings()
    threshold = settings.max_scan_threshold
    detected = 0
    latencies = []

    attack_codes = random.sample(unit_codes, min(n, len(unit_codes)))
    for uc in attack_codes[:n]:
        reset_unit_code(uc)
        lat, lon = -1.286389, 36.817223
        cloned = False
        for scan_n in range(threshold + 2):
            ip = f"10.{random.randint(0,255)}.{random.randint(0,255)}.{scan_n}"
            t0 = time.perf_counter()
            result = run_genuine_scan(uc, lat, lon, ip)
            latencies.append((time.perf_counter() - t0) * 1000)
            if result['is_clone']:
                cloned = True
                break
        if cloned:
            detected += 1

    return {
        'category': 'Clone Attack (High Frequency)',
        'total': n,
        'flagged': detected,
        'detection_rate': round(detected / n * 100, 2),
        'false_positive_rate': 0.0,
        'avg_latency_ms': round(statistics.mean(latencies), 2),
        'p95_latency_ms': round(sorted(latencies)[int(len(latencies) * 0.95)], 2),
    }

def simulate_velocity_attacks(unit_codes, n=300):
    """Simulate impossible travel: Nairobi then Mombasa within 5 minutes."""
    print(f"\n[B2] Simulating {n} velocity/impossible-travel attacks…")
    detected = 0
    latencies = []
    attack_codes = random.sample(unit_codes, min(n, len(unit_codes)))

    for uc in attack_codes[:n]:
        reset_unit_code(uc)
        # First scan: Nairobi
        VerificationScan.objects.create(
            unit_code=uc, raw_code=uc.secure_code, channel='WEB_QR',
            result_status='GENUINE',
            latitude=-1.286389, longitude=36.817223,
            ip_address='197.237.10.1',
            scanned_at=timezone.now() - timedelta(minutes=5)
        )
        uc.scan_count = 1; uc.save()

        # Second scan: Mombasa (5 min later → 5760 km/h)
        t0 = time.perf_counter()
        engine = CloneDetectionEngine(uc, current_lat=-4.043477, current_lon=39.668206, current_ip='41.203.220.10')
        result = engine.evaluate()
        latencies.append((time.perf_counter() - t0) * 1000)
        if result['is_clone']:
            detected += 1

    return {
        'category': 'Clone Attack (Impossible Velocity)',
        'total': n,
        'flagged': detected,
        'detection_rate': round(detected / n * 100, 2),
        'false_positive_rate': 0.0,
        'avg_latency_ms': round(statistics.mean(latencies), 2),
        'p95_latency_ms': round(sorted(latencies)[int(len(latencies) * 0.95)], 2),
    }

def simulate_nearby_location_attacks(unit_codes, n=200):
    """Simulate nearby scans that should NOT be flagged (< 5km apart, < 800km/h)."""
    print(f"\n[C] Simulating {n} nearby-location scans (should not be flagged)…")
    false_positives = 0
    latencies = []
    attack_codes = random.sample(unit_codes, min(n, len(unit_codes)))

    for uc in attack_codes[:n]:
        reset_unit_code(uc)
        base_lat, base_lon = -1.286389, 36.817223
        # First scan
        VerificationScan.objects.create(
            unit_code=uc, raw_code=uc.secure_code, channel='WEB_QR',
            result_status='GENUINE',
            latitude=base_lat, longitude=base_lon,
            ip_address='197.237.10.2',
            scanned_at=timezone.now() - timedelta(minutes=30)
        )
        uc.scan_count = 1; uc.save()

        # Second scan: ~3km away after 30 min (very slow speed)
        t0 = time.perf_counter()
        nearby_lat = base_lat + random.uniform(0.01, 0.03)  # ~1-3km
        nearby_lon = base_lon + random.uniform(0.01, 0.03)
        engine = CloneDetectionEngine(uc, current_lat=nearby_lat, current_lon=nearby_lon, current_ip='197.237.10.3')
        result = engine.evaluate()
        latencies.append((time.perf_counter() - t0) * 1000)
        if result['is_clone']:
            false_positives += 1

    return {
        'category': 'Nearby Location (Should NOT flag)',
        'total': n,
        'flagged': false_positives,
        'detection_rate': 0.0,
        'false_positive_rate': round(false_positives / n * 100, 2),
        'avg_latency_ms': round(statistics.mean(latencies), 2) if latencies else 0,
        'p95_latency_ms': round(sorted(latencies)[int(len(latencies) * 0.95)], 2) if latencies else 0,
    }

def print_markdown_table(results):
    header = "| Test Category | Total | Detected | Detection Rate | False Positive Rate | Avg Latency (ms) | P95 Latency (ms) |"
    sep    = "| :------------ | ----: | -------: | -------------: | ------------------: | ---------------: | ---------------: |"
    rows = []
    for r in results:
        dr = f"{r['detection_rate']:.1f}%" if r['detection_rate'] > 0 else "N/A"
        fpr = f"**{r['false_positive_rate']:.1f}%**" if r['false_positive_rate'] > 0 else "0.0%"
        row = f"| {r['category']} | {r['total']:,} | {r['flagged']:,} | {dr} | {fpr} | {r['avg_latency_ms']:.1f} | {r['p95_latency_ms']:.1f} |"
        rows.append(row)
    return "\n".join([header, sep] + rows)

def main():
    parser = argparse.ArgumentParser(description='MediVerify Evaluation Benchmark')
    parser.add_argument('--genuine-n', type=int, default=500, help='Number of genuine scans (default 500 for speed; use 10000 for full report)')
    parser.add_argument('--clone-n', type=int, default=100, help='Number of clone attack scenarios')
    parser.add_argument('--nearby-n', type=int, default=100, help='Number of nearby location scenarios')
    args = parser.parse_args()

    print("=" * 65)
    print("  MediVerify Cloned-Code Detection Evaluation Benchmark")
    print("  Phase 10 Evaluation Toolkit")
    print("=" * 65)

    print("\nSetting up test batch and unit codes…")
    batch = get_or_create_test_batch()
    needed = max(args.genuine_n, args.clone_n, args.nearby_n, 200)
    unit_codes = create_unit_codes(batch, needed)
    print(f"  Created/found {len(unit_codes)} test unit codes.")

    results = []
    start = time.time()

    results.append(simulate_genuine_scans(unit_codes, n=args.genuine_n))
    results.append(simulate_clone_attacks_high_frequency(unit_codes, n=args.clone_n))
    results.append(simulate_velocity_attacks(unit_codes, n=min(args.clone_n, 50)))
    results.append(simulate_nearby_location_attacks(unit_codes, n=args.nearby_n))

    elapsed = time.time() - start

    print("\n\n" + "=" * 65)
    print("  EVALUATION RESULTS (Paste into Final Report)")
    print("=" * 65)
    table = print_markdown_table(results)
    print("\n" + table)

    # Save to file
    out_dir = Path(__file__).parent
    report_path = out_dir / f"evaluation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_path, 'w') as f:
        f.write(f"# MediVerify Evaluation Benchmark Results\n\n")
        f.write(f"**Run Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Total Runtime:** {elapsed:.1f}s\n\n")
        f.write("## Results Summary\n\n")
        f.write(table)
        f.write("\n\n## Interpretation\n\n")
        f.write("- **Detection Rate** = TP / (TP + FN) — how many attacks were caught\n")
        f.write("- **False Positive Rate** = FP / (FP + TN) — how many genuine scans wrongly flagged\n")
        f.write("- **Target:** Detection Rate ≥ 95%, False Positive Rate ≤ 2%, P95 Latency ≤ 200ms\n")

    print(f"\n✓ Report saved to: {report_path}")
    print(f"✓ Total benchmark time: {elapsed:.1f}s\n")

if __name__ == '__main__':
    main()
