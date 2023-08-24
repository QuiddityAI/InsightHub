from django.db import models
from django.utils import timezone

from simple_history.models import HistoricalRecords


class Organization(models.Model):
    name = models.CharField(
        verbose_name="Name",
        max_length=200,
        blank=False,
        null=False)
    created_at = models.DateTimeField(
        verbose_name='Created at',
        default=timezone.now,
        blank=True,
        null=True)
    changed_at = models.DateTimeField(
        verbose_name='Changed at',
        auto_now=True,
        editable=False,
        blank=False,
        null=False)

    history = HistoricalRecords()

    def __str__(self):
        return f"SDK Delivery: {self.name}"

    class Meta:
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"
