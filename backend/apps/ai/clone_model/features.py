import math
from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from apps.verification.models import VerificationScan


FEATURE_NAMES = (
    'scan_total',
    'scans_1h',
    'scans_24h',
    'scans_7d',
    'distinct_devices',
    'distinct_ips',
    'distinct_locations',
    'max_speed_kmh',
    'age_days',
    'channel_web_ratio',
    'channel_sms_ratio',
    'channel_ussd_ratio',
    'batch_rate_ratio',
)

FEATURE_LABELS = {
    'scan_total': 'total scans',
    'scans_1h': 'scans in the last hour',
    'scans_24h': 'scans in the last 24 hours',
    'scans_7d': 'scans in the last 7 days',
    'distinct_devices': 'different devices',
    'distinct_ips': 'different IP addresses',
    'distinct_locations': 'distinct locations',
    'max_speed_kmh': 'maximum implied travel speed',
    'age_days': 'days since the first scan',
    'channel_web_ratio': 'web scan share',
    'channel_sms_ratio': 'SMS scan share',
    'channel_ussd_ratio': 'USSD scan share',
    'batch_rate_ratio': 'scan rate compared with the batch average',
}


def _distance_km(lat1, lon1, lat2, lon2):
    radius = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def extract_code_features(unit_code, current_lat=None, current_lon=None, current_ip=None,
                          current_ua=None, channel='WEB_QR', now=None):
    now = now or timezone.now()
    events = list(
        VerificationScan.objects.filter(unit_code=unit_code)
        .order_by('scanned_at')
        .values('scanned_at', 'latitude', 'longitude', 'ip_address', 'user_agent', 'channel', 'pharmacy_id')
    )
    events.append({
        'scanned_at': now,
        'latitude': current_lat,
        'longitude': current_lon,
        'ip_address': current_ip,
        'user_agent': current_ua,
        'channel': channel,
        'pharmacy_id': None,
    })

    scan_times = [event['scanned_at'] for event in events]
    distinct_devices = {event['user_agent'] for event in events if event['user_agent']}
    distinct_ips = {event['ip_address'] for event in events if event['ip_address']}
    locations = {
        (round(event['latitude'], 1), round(event['longitude'], 1))
        for event in events
        if event['latitude'] is not None and event['longitude'] is not None
    }
    locations.update(
        ('pharmacy', event['pharmacy_id'])
        for event in events
        if event['pharmacy_id'] and event['latitude'] is None
    )

    max_speed = 0.0
    previous = None
    for event in events:
        if event['latitude'] is None or event['longitude'] is None:
            continue
        if previous is not None:
            elapsed_hours = (event['scanned_at'] - previous['scanned_at']).total_seconds() / 3600
            if elapsed_hours > 0:
                speed = _distance_km(
                    previous['latitude'], previous['longitude'],
                    event['latitude'], event['longitude'],
                ) / elapsed_hours
                max_speed = max(max_speed, speed)
        previous = event

    event_count = len(events)
    window_counts = {
        'scans_1h': sum(event['scanned_at'] >= now - timedelta(hours=1) for event in events),
        'scans_24h': sum(event['scanned_at'] >= now - timedelta(hours=24) for event in events),
        'scans_7d': sum(event['scanned_at'] >= now - timedelta(days=7) for event in events),
    }
    channels = {
        'channel_web_ratio': sum(event['channel'].startswith('WEB') for event in events) / event_count,
        'channel_sms_ratio': sum(event['channel'] == 'SMS' for event in events) / event_count,
        'channel_ussd_ratio': sum(event['channel'] == 'USSD' for event in events) / event_count,
    }
    batch_codes = max(1, unit_code.batch.unit_codes.count())
    batch_total = (
        VerificationScan.objects.filter(unit_code__batch=unit_code.batch)
        .values('unit_code_id')
        .annotate(scan_count=Count('id'))
    )
    batch_average = sum(item['scan_count'] for item in batch_total) / batch_codes
    batch_rate_ratio = event_count / max(batch_average, 0.1)
    first_scan = min(scan_times)
    features = {
        'scan_total': event_count,
        **window_counts,
        'distinct_devices': len(distinct_devices),
        'distinct_ips': len(distinct_ips),
        'distinct_locations': len(locations),
        'max_speed_kmh': max_speed,
        'age_days': max(0.0, (now - first_scan).total_seconds() / 86400),
        **channels,
        'batch_rate_ratio': batch_rate_ratio,
    }
    return [float(features[name]) for name in FEATURE_NAMES], features
