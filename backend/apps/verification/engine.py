import math
from datetime import timedelta
from django.utils import timezone
from apps.reports.models import SystemSettings

def haversine_distance_km(lat1, lon1, lat2, lon2):
    """
    Calculates the great-circle distance between two points on the Earth
    in kilometers using the Haversine formula.
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 0.0

    R = 6371.0  # Earth radius in kilometers

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

class CloneDetectionEngine:
    def __init__(self, unit_code, current_lat=None, current_lon=None, current_ip=None,
                 current_ua=None, channel='WEB_QR'):
        self.unit_code = unit_code
        self.current_lat = current_lat
        self.current_lon = current_lon
        self.current_ip = current_ip
        self.current_ua = current_ua
        self.channel = channel
        self.settings = SystemSettings.get_settings()

    def evaluate(self):
        """
        Evaluates the unit code against all 3 detection rules.
        Returns a dictionary:
        {
            'is_clone': bool,
            'risk_score': float (0.0 to 100.0),
            'reasons': list of str,
            'rule_scores': {'frequency': float, 'velocity': float, 'entropy': float}
        }
        """
        reasons = []
        
        # If code was already confirmed as cloned by a regulator:
        if self.unit_code.is_flagged_clone:
            confirmed_alert = self.unit_code.clone_alerts.filter(status='CONFIRMED').first()
            if confirmed_alert:
                return {
                    'is_clone': True,
                    'risk_score': 100.0,
                    'reasons': ["CONFIRMED CLONE: This medicine code was officially confirmed as counterfeit/cloned by the regulatory authority."],
                    'rule_scores': {'frequency': 100.0, 'velocity': 100.0, 'entropy': 100.0},
                    'ml_score': None,
                    'rule_risk_score': 100.0,
                }

        # Rule 1: High Frequency Scan Count
        scan_count = self.unit_code.scan_count + 1 # count current scan
        freq_threshold = self.settings.max_scan_threshold
        freq_score = min(100.0, (scan_count / max(1, freq_threshold)) * 100.0) if scan_count >= freq_threshold else 0.0
        
        if scan_count >= freq_threshold:
            reasons.append(f"High Frequency: Code scanned {scan_count} times (Threshold: {freq_threshold})")

        # Rule 2: Velocity / Impossible Travel Check
        vel_score = 0.0
        previous_scan = self.unit_code.scans.order_by('-scanned_at').first()
        
        if previous_scan and self.current_lat and self.current_lon and previous_scan.latitude and previous_scan.longitude:
            dist_km = haversine_distance_km(
                previous_scan.latitude, previous_scan.longitude,
                self.current_lat, self.current_lon
            )
            time_diff = timezone.now() - previous_scan.scanned_at
            time_hours = max(0.001, time_diff.total_seconds() / 3600.0)
            speed_kmh = dist_km / time_hours
            
            if dist_km > 5.0 and speed_kmh > self.settings.max_velocity_kmh:
                vel_score = 100.0
                mins = time_diff.total_seconds() / 60.0
                reasons.append(
                    f"Velocity Anomaly: Distance {dist_km:.1f}km traveled in {mins:.1f} mins "
                    f"(Speed: {speed_kmh:.1f} km/h > Max allowed: {self.settings.max_velocity_kmh:.1f} km/h)"
                )

        # Rule 3: IP & Device Fingerprint Entropy
        ent_score = 0.0
        window_start = timezone.now() - timedelta(minutes=self.settings.distinct_ip_window_minutes)
        recent_scans = self.unit_code.scans.filter(scanned_at__gte=window_start)
        
        distinct_ips = set(recent_scans.values_list('ip_address', flat=True))
        if self.current_ip:
            distinct_ips.add(self.current_ip)
            
        distinct_ip_count = len([ip for ip in distinct_ips if ip])
        
        if distinct_ip_count >= self.settings.distinct_ip_threshold:
            ent_score = 100.0
            reasons.append(
                f"Entropy Anomaly: {distinct_ip_count} distinct IP addresses detected within "
                f"{self.settings.distinct_ip_window_minutes} minute window"
            )

        # Composite Risk Score Calculation
        w_freq = self.settings.weight_frequency
        w_vel = self.settings.weight_velocity
        w_ent = self.settings.weight_entropy
        
        rule_score = (freq_score * w_freq) + (vel_score * w_vel) + (ent_score * w_ent)
        rule_score = round(min(100.0, max(0.0, rule_score)), 1)
        rule_is_clone = (rule_score >= 60.0) or len(reasons) > 0
        ml_result = None
        if self.settings.ml_enabled:
            from apps.ai.clone_model.service import score_code

            ml_result = score_code(
                self.unit_code,
                current_lat=self.current_lat,
                current_lon=self.current_lon,
                current_ip=self.current_ip,
                current_ua=self.current_ua,
                channel=self.channel,
            )

        risk_score = rule_score
        if ml_result is not None:
            weight_total = self.settings.rule_weight + self.settings.ml_weight
            risk_score = (
                rule_score * self.settings.rule_weight
                + ml_result['score'] * self.settings.ml_weight
            ) / max(weight_total, 1e-6)
            if ml_result['score'] >= self.settings.ml_threshold:
                reasons.extend(ml_result['reasons'])
        risk_score = round(min(100.0, max(0.0, risk_score)), 1)
        is_clone = rule_is_clone or (
            ml_result is not None and (
                ml_result['score'] >= self.settings.ml_threshold
                or risk_score >= self.settings.hybrid_threshold
            )
        )

        return {
            'is_clone': is_clone,
            'risk_score': risk_score,
            'reasons': list(dict.fromkeys(reasons)),
            'rule_scores': {
                'frequency': round(freq_score, 1),
                'velocity': round(vel_score, 1),
                'entropy': round(ent_score, 1)
            },
            'rule_risk_score': rule_score,
            'ml_score': ml_result['score'] if ml_result else None,
        }
