import csv
import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.ai.ocr import read_pack_image


class Command(BaseCommand):
    help = 'Evaluate OCR batch and expiry exact-match accuracy on labelled pack images.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--images',
            default=str(settings.BASE_DIR / 'tests' / 'fixtures' / 'ocr'),
            help='Folder with images named BATCH__YYYY-MM-DD.png (or jpg/webp).',
        )
        parser.add_argument(
            '--output-dir',
            default=str(Path(settings.BASE_DIR).parent / 'evaluation'),
        )

    def handle(self, *args, **options):
        folder = Path(options['images'])
        if not folder.is_dir():
            raise CommandError(f'Image folder does not exist: {folder}')
        image_paths = sorted(
            path for path in folder.iterdir()
            if path.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp')
        )
        if not image_paths:
            raise CommandError('No supported labelled images were found.')
        batch_correct = 0
        expiry_correct = 0
        total_time = 0.0
        rows = []
        for path in image_paths:
            try:
                expected_batch, expected_expiry = path.stem.rsplit('__', 1)
            except ValueError as exc:
                raise CommandError(f'Expected filename BATCH__YYYY-MM-DD.ext, got {path.name}.') from exc
            start = time.perf_counter()
            result = read_pack_image(path.read_bytes())
            duration = (time.perf_counter() - start) * 1000
            total_time += duration
            actual_batch = result['batch_number']['value']
            actual_expiry = result['expiry_date']['value']
            batch_match = actual_batch == expected_batch
            expiry_match = actual_expiry == expected_expiry
            batch_correct += batch_match
            expiry_correct += expiry_match
            rows.append((path.name, expected_batch, actual_batch, expected_expiry, actual_expiry, duration))

        count = len(image_paths)
        output_dir = Path(options['output_dir'])
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / 'ocr_evaluation_results.csv'
        with csv_path.open('w', newline='', encoding='utf-8') as output:
            writer = csv.writer(output)
            writer.writerow(('image', 'expected_batch', 'actual_batch', 'expected_expiry', 'actual_expiry', 'processing_ms'))
            writer.writerows(rows)
        self.stdout.write(f'Images evaluated: {count}')
        self.stdout.write(f'Batch number exact-match accuracy: {batch_correct / count:.3f} ({batch_correct}/{count})')
        self.stdout.write(f'Expiry date exact-match accuracy: {expiry_correct / count:.3f} ({expiry_correct}/{count})')
        self.stdout.write(f'Average processing time: {total_time / count:.1f} ms')
        self.stdout.write(f'Per-image results: {csv_path}')
