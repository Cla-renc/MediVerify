"""
Inventory signals — automatically recalculate pharmacy trust score
whenever inventory items or suspicious reports change.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone


def _recalculate_trust(pharmacy):
    """Compute and persist the latest trust score for a pharmacy."""
    today = timezone.now().date()
    items = pharmacy.inventory_items.all()

    expired_count = items.filter(batch__expiry_date__lt=today).count()
    recalled_count = items.filter(batch__is_recalled=True).count()
    suspicious_count = pharmacy.suspicious_reports.filter(
        status__in=['PENDING', 'INVESTIGATING']
    ).count()

    pharmacy.update_trust_score(expired_count, recalled_count, suspicious_count)


# ── Trigger on InventoryItem save / delete ──────────────────────────────────
@receiver(post_save, sender='inventory.InventoryItem')
def on_inventory_item_save(sender, instance, **kwargs):
    _recalculate_trust(instance.pharmacy)


@receiver(post_delete, sender='inventory.InventoryItem')
def on_inventory_item_delete(sender, instance, **kwargs):
    _recalculate_trust(instance.pharmacy)


# ── Trigger on SuspiciousReport status change ────────────────────────────────
@receiver(post_save, sender='reports.SuspiciousReport')
def on_suspicious_report_save(sender, instance, **kwargs):
    if instance.pharmacy:
        _recalculate_trust(instance.pharmacy)
