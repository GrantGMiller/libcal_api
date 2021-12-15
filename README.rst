Python LibCal Interface
=======================

SpringShare has many APIs including the LibCal API. Used by many libraries and universities to organize spaces and rooms.

`SpringShare <https://springshare.com/>`_

`LibCal <https://springshare.com/libcal/>`_

View your LibCal API Docs at your specific URL like "https://company.libcal.com/admin/api/1.1/"


Usage
=====

This package provides a simple interface to the LibCal API.

The spaces are organized by Location > Category > Spaces > Seats.

Spaces might not have Seats, it might just be a large room that the user can book.

Credentials
===========
You will need to create a "Client ID" and "Client Secret" through the API webpage.

https://your-company.libcal.com/admin/api/authentication

,

Example
=======

::

    import datetime
    from libcal import LibCal
    import config
    
    lc = LibCal(
        baseURL=config.BASE_URL,  # str like "https://company.libcal.com/"
        clientID=config.CLIENT_ID,  # str
        clientSecret=config.CLIENT_SECRET,  # str
        # debug=True, # if True, all HTTP request/response will be printed
    )
    
    # print out all the meeting spaces
    for location in lc.locations:
        print('location=', location)
    
        for space in location.spaces:
            print('\tspace=', space)
    
            if not space.seats:
                bookings = space.bookings
                for booking in bookings:
                    print('\t\tbooking=', booking)
    
            for seat in space.seats:  # space.seats might return an empty list
                print('\t\tseat=', seat)
    
                for booking in seat.bookings:
                    print('\t\t\tbooking=', booking)
    
    # you can look up a specific seat by its ID
    seats = lc.find(seat_ids=[98, 99, 100])
    
    # book the seat if available
    for seat in seats:
        if seat.is_available_at():  # no args means 'now'
            booking = seat.reserve(
                startDT=datetime.datetime.now() + datetime.timedelta(hours=1),
                fname='john',
                lname='smith',
                email='john_smith@email.com',
            )

Example Output
==============

::

    location= <Location: name=Nashville Office, id=15181>
        space= <Space: name=Huddle Desk 1, id=124124, isAvailableNow=True, location_name=Nashville Office>
            seat= <Seat: name=Seat 1, id=158173, isAvailableNow=True, space_name=Huddle Desk 1, location_name=Nashville Office>
            seat= <Seat: name=Seat 2, id=158174, isAvailableNow=True, space_name=Huddle Desk 1, location_name=Nashville Office>
       space= <Space: name=Huddle Desk 2, id=124151, isAvailableNow=True, location_name=Nashville Office>
            seat= <Seat: name=Seat 1, id=158179, isAvailableNow=True, space_name=Huddle Desk 2, location_name=Nashville Office>
            seat= <Seat: name=Seat 2, id=158180, isAvailableNow=True, space_name=Huddle Desk 2, location_name=Nashville Office>
        space= <Space: name=Conference Room 101, id=124152, isAvailableNow=True, location_name=Nashville Office>
    location= <Location: name=Knoxville Office, id=15194>
        space= <Space: name=Conference Room 202, id=124289, isAvailableNow=False, location_name=Knoxville Office>
        space= <Space: name=Huddle Desk 3, id=124290, isAvailableNow=False, location_name=Knoxville Office>
            seat= <Seat: name=Seat 1, id=158192, isAvailableNow=False, space_name=Huddle Desk 3, location_name=Knoxville Office>
            seat= <Seat: name=Seat 2, id=158193, isAvailableNow=False, space_name=Huddle Desk 3, location_name=Knoxville Office>
            
