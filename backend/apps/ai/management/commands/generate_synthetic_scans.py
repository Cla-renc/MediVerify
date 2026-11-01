import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.ai.models import CloneEvaluationCase
from apps.products.models import Batch, Manufacturer, Product, UnitCode
from apps.verification.models import VerificationScan


LOCATIONS = [
    (-1.2864, 36.8172),
    (-4.0435, 39.6682),
    (-0.0917, 34.7680),
    (-0.3031, 36.0800),
    (-1.5177, 37.2634),
]


class Command(BaseCommand):
    help = 'Create reproducible synthetic genuine and cloned-code scan patterns.'

    def add_arguments(self, parser):
        parser.add_argument('--seed', type=int, default=42)
        parser.add_argument('--genuine', type=int, default=60)
        parser.add_argument('--clones-per-type', type=int, default=15)

    def handle(self, *args, **options):
        rng = random.Random(options['seed'])
        manufacturer, _ = Manufacturer.objects.get_or_create(
            license_number='MV-AI-SYNTHETIC',
            defaults={
                'name': 'MediVerify Synthetic Training Manufacturer',
                'contact_email': 'synthetic@mediverify.invalid',
                'country': 'Kenya',
                'is_verified': False,
            },
        )
        product, _ = Product.objects.get_or_create(
            manufacturer=manufacturer,
            brand_name='Training Sample Medicine',
            defaults={
                'generic_name': 'Training Sample',
                'strength': '500mg',
                'usage_instructions_en': 'Training data only.',
                'usage_instructions_sw': 'Data ya mafunzo pekee.',
                'side_effects_en': 'Training data only.',
                'side_effects_sw': 'Data ya mafunzo pekee.',
                'key_warnings_en': 'Not for clinical use.',
                'key_warnings_sw': 'Si kwa matumizi ya kliniki.',
            },
        )
        batch, _ = Batch.objects.get_or_create(
            batch_number='MV-AI-SYNTHETIC-BATCH',
            defaults={
                'product': product,
                'manufacture_date': timezone.now().date() - timedelta(days=30),
                'expiry_date': timezone.now().date() + timedelta(days=365),
                'total_quantity': 100000,
            },
        )

        created = {key: 0 for key in ('GENUINE', 'REPEATED', 'DISTANT', 'NEARBY', 'SLOW')}
        cases = [('GENUINE', options['genuine'])]
        cases.extend((attack, options['clones_per_type']) for attack in created if attack != 'GENUINE')
        for attack_type, count in cases:
            for index in range(count):
                serial = f'SYN-{options["seed"]}-{attack_type}-{index}'
                secure_code, signature = UnitCode.generate_hmac_code(str(batch.id), serial)
                unit_code, was_created = UnitCode.objects.get_or_create(
                    batch=batch,
                    serial_number=serial,
                    defaults={'secure_code': secure_code, 'hmac_signature': signature},
                )
                if not was_created:
                    continue
                CloneEvaluationCase.objects.create(unit_code=unit_code, attack_type=attack_type)
                scans = _build_pattern(attack_type, rng)
                base_time = timezone.now() - timedelta(days=rng.randint(10, 60))
                for scan_index, scan in enumerate(scans):
                    event = VerificationScan.objects.create(
                        unit_code=unit_code,
                        raw_code=secure_code,
                        channel=scan['channel'],
                        result_status='GENUINE',
                        latitude=scan['lat'],
                        longitude=scan['lon'],
                        ip_address=scan['ip'],
                        user_agent=scan['device'],
                    )
                    event.scanned_at = base_time + timedelta(minutes=scan['offset_minutes'])
                    event.save(update_fields=['scanned_at'])
                unit_code.scan_count = len(scans)
                unit_code.save(update_fields=['scan_count'])
                created[attack_type] += 1

        self.stdout.write(self.style.SUCCESS(
            f"Created {sum(created.values())} synthetic codes (seed {options['seed']}): "
            + ', '.join(f'{name.lower()}={count}' for name, count in created.items())
        ))


def _build_pattern(attack_type, rng):
    location = rng.choice(LOCATIONS)
    if attack_type == 'GENUINE':
        count = rng.choices([1, 2, 3], weights=[0.78, 0.20, 0.02])[0]
        return [
            _event(rng, location, offset=0 if i == 0 else rng.randint(2 * 24 * 60, 7 * 24 * 60),
                   device='consumer-device-1', ip='10.1.0.1')
            for i in range(count)
        ]
    if attack_type == 'REPEATED':
        return [
            _event(rng, location, offset=i * rng.randint(1, 4),
                   device=f'clone-device-{i % 5}', ip=f'10.2.0.{i % 5 + 1}')
            for i in range(9)
        ]
    if attack_type == 'DISTANT':
        first, second = LOCATIONS[0], LOCATIONS[1]
        return [
            _event(rng, first, 0, 'distant-clone-a', '10.3.0.1'),
            _event(rng, second, 20, 'distant-clone-b', '10.3.0.2'),
            _event(rng, first, 45, 'distant-clone-c', '10.3.0.3'),
        ]
    if attack_type == 'NEARBY':
        lat, lon = location
        return [
            _event(rng, (lat + i * 0.08, lon + i * 0.06), i * 18,
                   f'nearby-device-{i % 3}', f'10.4.0.{i % 3 + 1}')
            for i in range(6)
        ]
    return [
        _event(rng, (location[0] + i * 0.3, location[1] + i * 0.2), i * 3 * 24 * 60,
               f'slow-device-{i % 2}', f'10.5.0.{i % 2 + 1}')
        for i in range(5)
    ]


def _event(rng, location, offset, device, ip):
    return {
        'lat': location[0] + rng.uniform(-0.005, 0.005),
        'lon': location[1] + rng.uniform(-0.005, 0.005),
        'offset_minutes': offset,
        'device': device,
        'ip': ip,
        'channel': rng.choices(['WEB_QR', 'SMS', 'USSD'], weights=[0.75, 0.18, 0.07])[0],
    }
