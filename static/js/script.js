// This code runs as soon as the page's HTML has finished loading.
// It selects every element on the page with class "seat" and stores them in a list.
const seats = document.querySelectorAll('.seat');

// Only run the seat-selection logic if this page actually HAS seats on it
// (i.e., we're on booking.html, not some other page like the home page).
if (seats.length > 0) {

    // This will keep track of which seats the user has selected, and their prices.
    let selectedSeats = [];

    // Loop through every seat element on the page, one by one.
    seats.forEach(function (seat) {

        seat.addEventListener('click', function () {

    if (seat.classList.contains('booked')) {
        return;
    }

    const seatName = seat.dataset.seat;
    const seatPrice = Number(seat.dataset.price);
    const seatId = Number(seat.dataset.seatId); // NEW: reading the seat's database ID

    if (seat.classList.contains('selected')) {
        seat.classList.remove('selected');

        selectedSeats = selectedSeats.filter(function (s) {
            return s.name !== seatName;
        });

    } else {
        seat.classList.add('selected');
        selectedSeats.push({ id: seatId, name: seatName, price: seatPrice }); // NEW: storing id too
    }

    updateSummary();
});
    });


    // This function updates the text in the "Booking Summary" box.
    function updateSummary() {

        const selectedSeatsText = document.getElementById('selected-seats-text');
        const pricePerSeatText = document.getElementById('price-per-seat-text');
        const totalPriceText = document.getElementById('total-price-text');

        if (selectedSeats.length === 0) {
            selectedSeatsText.textContent = 'None';
            pricePerSeatText.textContent = '₹3000 × 0';
            totalPriceText.textContent = '₹0';
            return;
        }

        const seatNames = selectedSeats.map(function (s) {
            return s.name;
        }).join(', ');

        let total = 0;
        for (let i = 0; i < selectedSeats.length; i++) {
            total = total + selectedSeats[i].price;
        }

        const pricePerSeat = selectedSeats[0].price;

        selectedSeatsText.textContent = seatNames;
        pricePerSeatText.textContent = `₹${pricePerSeat} × ${selectedSeats.length}`;
        totalPriceText.textContent = `₹${total}`;
    }


    // Handle the "Book Now" button click.
    const bookBtn = document.getElementById('book-btn');

bookBtn.addEventListener('click', function () {
    if (selectedSeats.length === 0) {
        alert('Please select at least one seat before booking.');
        return;
    }

    const concertId = document.getElementById('concert-id').value;

    // Collect just the seat IDs (not names/prices) to send to the server.
    const seatIds = selectedSeats.map(function (s) {
        return s.id;
    });

    // fetch() sends a network request without reloading the page.
    fetch('/book-seats', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            concert_id: concertId,
            seat_ids: seatIds
        })
    })
    .then(function (response) {
        return response.json(); // parse Flask's response as JSON
    })
    .then(function (data) {
        if (data.success) {
            alert('Booking confirmed! Booking ID: ' + data.booking_id);
            window.location.href = '/my-bookings'; // redirect after confirming
        } else {
            alert('Booking failed: ' + data.message);
            window.location.reload(); // refresh to show updated seat availability
        }
    })
    .catch(function (error) {
        alert('Something went wrong. Please try again.');
        console.error(error);
    });
});

} // end of "if (seats.length > 0)"