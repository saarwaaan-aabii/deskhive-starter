"""M6 Lab 2: complete serializers using the existing M5 ORM and rules."""
from rest_framework import serializers
from spaces.models import Space

class SpaceSerializer(serializers.ModelSerializer):
    # City of the related Location, flattened into the space representation.
    location_city = serializers.CharField(source='location.city', read_only=True)

    class Meta:
        model = Space
        # Explicit public contract: only these fields, all read-only.
        fields = ('code', 'name', 'kind', 'capacity', 'hourly_rate', 'location_city')
        read_only_fields = fields

class BookingCreateSerializer(serializers.Serializer):
    # Format-level validation: DRF checks each field before any booking rule.
    space = serializers.SlugRelatedField(slug_field='code', queryset=Space.objects.all())
    full_name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    # TODO M6 Lab 2: validate interval with local_interval + validate_booking.
    # Implement create() by calling bookings.services.save_booking.
    # Translate model/service validation failures into DRF ValidationError.

class BookingReadSerializer(serializers.Serializer):
    # TODO M6 Lab 2: return id, space code, start and end (read-only).
    pass
