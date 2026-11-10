from django.core.exceptions import ValidationError
from django.db import OperationalError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_safe, require_POST
from django.views.decorators.cache import never_cache
from spaces.models import Space
from .forms_m5 import AvailabilityForm, PersistentBookingForm
from .models import Booking
from .services import save_booking, delete_booking, is_available

OWNED = 'm5_booking_ids'

@require_safe
def booking_list(request):
    bookings = Booking.objects.filter(pk__in=request.session.get(OWNED, [])).select_related('space', 'member')
    return render(request, 'bookings/manage.html', {'bookings': bookings, 'spaces': Space.objects.select_related('location')})

@require_http_methods(['GET', 'HEAD', 'POST'])
def booking_edit(request, pk=None):
    booking = None
    initial = {}
    if pk is not None:
        booking = get_object_or_404(Booking, pk=pk, pk__in=request.session.get(OWNED, []))
        initial = {'space': booking.space.code, 'full_name': booking.member.full_name, 'email': booking.member.email,
                   'start': booking.start, 'end': booking.end}
    form = PersistentBookingForm(request.POST if request.method == 'POST' else None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        try:
            saved = save_booking(**form.cleaned_data, booking=booking)
        except ValidationError as exc:
            form.add_error(None, '; '.join(exc.messages))
        except OperationalError:
            form.add_error(None, 'The database is busy. Please try again.')
        else:
            request.session[OWNED] = list(set(request.session.get(OWNED, []) + [saved.pk]))
            return redirect('bookings:manage')
    return render(request, 'bookings/edit.html', {'form': form, 'booking': booking})

@require_POST
def booking_delete(request, pk):
    booking = get_object_or_404(Booking, pk=pk, pk__in=request.session.get(OWNED, []))
    try:
        delete_booking(booking)
    except ValidationError:
        return render(request, 'bookings/incomplete.html', status=501)
    request.session[OWNED] = [item for item in request.session.get(OWNED, []) if item != pk]
    return redirect('bookings:manage')

@never_cache
@require_safe
def availability(request):
    form = AvailabilityForm(request.GET)
    if not form.is_valid():
        return JsonResponse({'errors': form.errors.get_json_data()}, status=400)
    # Read-only lookup: reports availability, never creates or reserves a booking.
    return JsonResponse({'available': is_available(**form.cleaned_data)})
