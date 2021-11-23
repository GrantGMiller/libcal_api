import config
import libcal
import datetime

lc = libcal.LibCal(
    baseURL=config.BASE_URL,
    clientID=config.CLIENT_ID,
    clientSecret=config.CLIENT_SECRET,
    # debug=True,
)

locations = lc.spaces.locations()

print('There {} {} location{}.'.format(
    len(locations),
    'are' if len(locations) > 1 else 'is',
    's' if len(locations) > 1 else '',
))
for loc in locations:
    print('Location Name: {}, ID: {}'.format(loc['name'], loc['lid']))

    res = lc.spaces.categories(ids=[d['lid'] for d in locations])
    for item in res:
        if item['lid'] == loc['lid']:
            print('\tThis location has {} categor{}'.format(
                len(item['categories']),
                'ies' if len(item['categories']) > 1 else 'y',
            ))

            for cat in item['categories']:
                print('\tCategory Name: {}, ID: {}'.format(
                    cat['name'],
                    cat['cid'],
                ))

                categoryResults = lc.spaces.category(cid=cat['cid'])
                for categoryResult in categoryResults:
                    if categoryResult['cid'] == cat['cid']:
                        print('\t\tThis category has {} instance{}'.format(
                            len(categoryResult['items']),
                            's' if len(categoryResult['items']) > 1 else '',
                        ))
                        for instance in categoryResult['items']:
                            print('\t\t\tInstance Name: {}, Seating Capacity: {}, ID: {}; {}'.format(
                                instance['name'],
                                instance['capacity'],
                                instance['id'],
                                'These seats can be booked individually.' if not instance['isBookableAsWhole'] else '',
                            ))

                            availability = lc.spaces.item(
                                ids=instance['id'],
                            )
                            isAvailableNow = False
                            nowDT = datetime.datetime.now().astimezone()
                            for result in availability:
                                for fromTo in result['availability']:
                                    from_ = datetime.datetime.fromisoformat(fromTo['from'])
                                    to = datetime.datetime.fromisoformat(fromTo['to'])
                                    if from_ < nowDT < to:
                                        isAvailableNow = True
                                        break
                            print('\t\t\t{} is {}available now.'.format(
                                instance['name'],
                                'not ' if isAvailableNow is False else '',
                            ))
                            if instance['capacity'] > 1:
                                print('\t\t\tThese are the seats.')

                                seats = lc.spaces.seats(
                                    location_id=loc['lid'],
                                    spaceId=instance['id'],
                                )
                                for item in seats:
                                    print('\t\t\t\tSeat Name: {}, ID: {}'.format(
                                        item['name'],
                                        item['id'],
                                    ))
