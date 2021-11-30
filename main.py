import datetime
import random
import config
import libcal

lc = libcal.LibCal(
    baseURL=config.BASE_URL,
    clientID=config.CLIENT_ID,
    clientSecret=config.CLIENT_SECRET,
    # debug=True,
)

# print out all the meeting spaces
bookableItems = []
for location in lc.locations:
    print('location=', location)

    for space in location.spaces:
        print('\tspace=', space)

        if not space.seats:
            bookings = space.bookings
            for booking in bookings:
                print('\t\tbooking=', booking)

        if len(space.seats) == 0 and space.is_available_at():
            bookableItems.append(space)
            pass

        for seat in space.seats:
            print('\t\tseat=', seat)
            if seat.is_available_at():
                bookableItems.append(seat)
                pass
            for booking in seat.bookings:
                print('\t\t\tbooking=', booking)

item = random.choice(bookableItems)
print('Creating a new booking for', item)
booking = item.reserve(
    startDT=datetime.datetime.now() + datetime.timedelta(hours=1),
    fname=config.fname,
    lname=config.lname,
    email=config.email,
)
print('new booking=', booking)

booking_id = booking.id
print('looking up a booking by its id "{}"'.format(booking_id))
bookings = lc.find(booking_ids=booking_id)
for booking in bookings:
    print('found booking=', booking)

# cancel a booking
booking.cancel()
