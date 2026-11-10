/* M5 lab 3: use the supplied local jQuery full build. */
$(function () {
    // Details: each button controls only the block named by its aria-controls.
    $('.toggle-details').on('click', function () {
        var $button = $(this);
        var target = document.getElementById($button.attr('aria-controls'));
        if (!target) {
            return;
        }
        target.hidden = !target.hidden;
        var open = !target.hidden;
        $button.attr('aria-expanded', open ? 'true' : 'false');
        $button.text(open ? 'Hide details' : 'Show details');
    });

    // Availability: only on the booking form.
    var $form = $('#booking-form');
    var $check = $('#check-availability');
    var $status = $('#availability');
    if (!$form.length || !$check.length) {
        return;
    }

    var generation = 0;   // bumped on every input change and every new check
    var pending = null;   // the jqXHR of the request in flight, if any

    function abortPending() {
        if (pending) {
            pending.abort();
            pending = null;
        }
    }

    // Any change makes earlier results (finished or not) obsolete.
    $('#id_space, #id_start, #id_end').on('input change', function () {
        generation += 1;
        abortPending();
        $status.text('Values changed. Check availability again.');
        $check.prop('disabled', false);
    });

    $check.on('click', function () {
        generation += 1;
        abortPending();
        var requestGeneration = generation;
        $check.prop('disabled', true);
        $status.text('Checking…');

        var request = $.ajax({
            url: $form.data('availability-url'),
            method: 'GET',
            data: {
                space: $('#id_space').val(),
                start: $('#id_start').val(),
                end: $('#id_end').val()
            },
            dataType: 'json',
            timeout: 10000
        });
        pending = request;

        request.done(function (data) {
            if (requestGeneration !== generation) {
                return;   // stale response: a newer check or change owns the feedback
            }
            $status.text(data.available === true
                ? 'Available — saving checks again.'
                : 'Already booked');
        });

        request.fail(function (xhr, textStatus) {
            if (textStatus === 'abort' || requestGeneration !== generation) {
                return;   // deliberately aborted or stale: no error message
            }
            if (xhr.status === 400) {
                $status.text('Choose a space and a valid interval of at most 12 hours.');
            } else {
                $status.text('Could not check availability. Please retry.');
            }
        });

        request.always(function () {
            if (requestGeneration !== generation) {
                return;   // only the current request may restore the button
            }
            pending = null;
            $check.prop('disabled', false);
        });
    });
});
