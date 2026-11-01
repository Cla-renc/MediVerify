from django.core.management.base import BaseCommand, CommandError

from apps.ai.clone_model.service import train_model


class Command(BaseCommand):
    help = 'Train and persist the Isolation Forest clone detector.'

    def add_arguments(self, parser):
        parser.add_argument('--seed', type=int, default=42)
        parser.add_argument('--contamination', type=float, default=0.08)

    def handle(self, *args, **options):
        contamination = options['contamination']
        if not 0 < contamination <= 0.5:
            raise CommandError('--contamination must be greater than 0 and no more than 0.5.')
        try:
            version = train_model(seed=options['seed'], contamination=contamination)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(
            f'Trained clone model v{version.version} on {version.training_samples} codes '
            f'at {version.trained_at:%Y-%m-%d %H:%M UTC}.'
        ))
        self.stdout.write(
            f"Decision threshold: {version.training_report['score_threshold']:.4f}; "
            f"artifact: {version.model_path}"
        )
