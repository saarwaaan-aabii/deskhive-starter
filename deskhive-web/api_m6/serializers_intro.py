"""M6 Lab 1 — complete this plain DRF Serializer (no database writing).

Use the existing Space fields and the M6-EXERCISES.md instructions.
Keep it a regular serializers.Serializer, not ModelSerializer.
"""
from decimal import Decimal

from rest_framework import serializers


class SpaceSnapshotSerializer(serializers.Serializer):
    # Explicit data contract mirroring the Space model constraints.
    code = serializers.SlugField(max_length=30)
    name = serializers.CharField(max_length=100)
    kind = serializers.ChoiceField(choices=[('desk', 'Desk'), ('meeting_room', 'Meeting room')])
    capacity = serializers.IntegerField(min_value=1)
    hourly_rate = serializers.DecimalField(max_digits=7, decimal_places=2, min_value=Decimal('0.01'))
