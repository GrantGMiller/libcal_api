'''
Based on LibCal API Docs at: https://<your_domain>.libcal.com/admin/api/1.1

License: https://grant-miller.mit-license.org/
'''
import datetime
import requests
from copy import copy


class _TokenManager:
    def __init__(self, clientID, clientSecret, apiURL, debug=False):
        self.clientID = clientID
        self.clientSecret = clientSecret
        self.apiURL = apiURL
        self.debug = debug

        #
        self.dtExpiresAt = None
        self.access_token = None
        self.dtExpiresAt = datetime.datetime.now()
        self.scope = []
        #
        self.GetAccessToken()

    def print(self, *a, **k):
        if self.debug:
            print(*a, **k)

    def GetAccessToken(self):
        if self.access_token is None or datetime.datetime.now() > self.dtExpiresAt:
            # get a new token
            resp = requests.post(
                url='{}1.1/oauth/token'.format(self.apiURL),
                data={
                    'client_id': self.clientID,
                    'client_secret': self.clientSecret,
                    'grant_type': 'client_credentials',
                }
            )
            self.print('resp=', resp.text)

            if 'error' in resp.json():
                raise PermissionError(str(resp.json()))

            elif resp.json().get('access_token', None):
                self.access_token = resp.json()['access_token']
                self.dtExpiresAt = datetime.datetime.now() + datetime.timedelta(seconds=resp.json()['expires_in'])
                self.scope = resp.json()['scope']

        return self.access_token


class _BaseAPI:
    def __init__(self, baseURL, tokenCallback, debug=False):
        self.baseURL = baseURL
        self.tokenCallback = tokenCallback
        self.debug = debug

        #

    def print(self, *a, **k):
        if self.debug:
            print(*a, **k)

    def send_request(self, method, url, params=None, json=None):
        if params is None and json is not None:
            params = json

        for k, v in params.items():
            if isinstance(v, bool):
                params[k] = int(v)  # booleans are passed as int 0/1
            if isinstance(v, (datetime.datetime, datetime.date)):
                params[k] = v.isoformat()

        self.print('send_request(', method, url, params, json)

        resp = requests.request(
            method=method,
            url=url,
            params=params,
            json=json,
            headers={
                'Authorization': 'Bearer {}'.format(self.tokenCallback())
            }
        )
        return resp

    def _add_endpoint(
            self,
            endpoint,
            method='GET',
            defaultParams={},
            attribute_name=None,
            endpointCallback=None,
            requiredParams=[],
    ):
        '''

        :param endpoint: str like '/space/locations'
        :param methods: list like ['GET", 'POST']
        :param defaultParams: dict like {'admin_only': 'defaultvalue'}
        :return:
        '''
        if attribute_name is None:
            attribute_name = endpoint.split('/')[-1]
            for ch in copy(attribute_name):
                if not ch.isalnum():
                    if ch == '_':
                        pass
                    else:
                        attribute_name = attribute_name.replace(ch, '')

        self.print('attribute_name=', attribute_name)

        def new_method(endpoint=endpoint, method=method, defaultParams=defaultParams, endpointCallback=endpointCallback,
                       attribute_name=attribute_name, requiredParams=requiredParams, **kwargs):

            method = method.upper()

            if endpointCallback:
                endpoint = endpointCallback(endpoint, **kwargs)

            params = defaultParams.copy()
            for k, v in params.copy().items():
                if v is None:
                    params.pop(k, None)
                if isinstance(v, (datetime.date,)):
                    params[k] = v.isoformat()
                elif isinstance(v, list):
                    params[k] = ','.join(a for a in v)

            params.update(kwargs)

            for req in requiredParams:
                if req not in kwargs:
                    raise ValueError('Missing required keyword "{}"'.format(req))
                else:
                    params[req] = kwargs[req]

            if method == 'GET':
                resp = self.send_request(
                    url='{}{}'.format(self.baseURL, endpoint),
                    method=method,
                    params=params,
                )

            elif method == 'POST':
                resp = self.send_request(
                    url='{}{}'.format(self.baseURL, endpoint),
                    method=method,
                    json=params,
                )

            if resp.ok:
                self.print(attribute_name, 'resp.json()=', resp.json())
                self.print()
                return resp.json()
            else:
                raise Exception('{} {}: {}'.format(
                    resp.status_code,
                    resp.reason,
                    resp.text
                ))

        setattr(self, attribute_name, new_method)


class _Spaces(_BaseAPI):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._add_endpoint(
            endpoint='1.1/space/locations',
            method='GET',
            defaultParams={'details': False, 'admin_only': False},
        )
        self._add_endpoint(
            attribute_name='form',
            endpoint='1.1/space/form/{ids}',
            method='GET',
            endpointCallback=lambda endpoint, ids: endpoint.format(ids=','.join(str(i) for i in ids)),
        )
        self._add_endpoint(
            attribute_name='question',
            endpoint='1.1/space/question/{ids}',
            method='GET',
            endpointCallback=lambda endpoint, ids: endpoint.format(ids=','.join(str(i) for i in ids)),
        )
        self._add_endpoint(
            attribute_name='categories',
            endpoint='1.1/space/categories/{ids}',
            method='GET',
            endpointCallback=lambda endpoint, ids: endpoint.format(
                ids=','.join(str(i) for i in ids) if isinstance(ids, list) else ids),
            defaultParams={'admin_only': False}
        )
        self._add_endpoint(
            attribute_name='category',
            endpoint='1.1/space/category/{cid}',
            method='GET',
            endpointCallback=lambda endp, **kw: endp.format(**kw),
            requiredParams=['cid'],
            defaultParams={
                'details': False,
                'availability': datetime.date.today(),
            }
        )
        self._add_endpoint(
            attribute_name='item',
            endpoint='1.1/space/item/{ids}',
            method='GET',
            endpointCallback=lambda endp, **kw: endp.format(
                ids=kw['ids'] if isinstance(kw['ids'], (int, str)) else ','.join(str(i) for i in kw['ids']),
            ),
            requiredParams=['ids'],
            defaultParams={
                'availability': datetime.date.today(),
            }
        )
        self._add_endpoint(
            attribute_name='items',
            endpoint='1.1/space/items/{location_id}',
            method='GET',
            endpointCallback=lambda endp, **kw: endp.format(
                location_id=kw['location_id'],
            ),
            requiredParams=['location_id'],
            defaultParams={
                'category': None,
                'zoneId': None,
                'accessibleOnly': None,
                'bookable': None,
                'powered': None,
                'availability': None,
                'pageIndex': None,
                'pageSize': None,
            }
        )

        self._add_endpoint(
            attribute_name='reserve',
            method='POST',
            endpoint='1.1/space/reserve',
            requiredParams=[
                'start',
                'fname',
                'lname',
                'email',
                'bookings',
            ],
            defaultParams={
                'nickname': None,
                'adminbooking': False,
                'test': False,
            }
        )
        self._add_endpoint(
            attribute_name='booking',
            endpoint='1.1/space/booking/{ids}',
            endpointCallback=lambda endp, **kw: endp.format(
                ids=kw['ids'] if isinstance(kw['ids'], (int, str)) else ','.join(str(i) for i in kw['ids']),
            ),
            method='GET',
            requiredParams=['ids'],
            defaultParams={
                'formAnswers': None,  # bool
            }
        )
        self._add_endpoint(
            endpoint='1.1/space/bookings',
            method='GET',
            defaultParams={
                'eid': None,
                'seat_id': None,
                'cid': None,
                'lid': None,
                'email': None,
                'date': datetime.date.today(),
                'days': 1,
                'limit': 20,
                'page': 1,
                'formAnswers': False,
            }
        )
        self._add_endpoint(
            attribute_name='cancel',
            method='POST',
            endpoint='1.1/space/cancel/{ids}',
            endpointCallback=lambda endp, **kw: endp.format(
                ids=kw['ids'] if isinstance(kw['ids'], (int, str)) else ','.join(str(i) for i in kw['ids']),
            ),
        )

        self._add_endpoint(
            attribute_name='seat',
            endpoint='api/1.1/space/seat/{seat_id}',
            endpointCallback=lambda endp, **kw: endp.format(**kw),
            requiredParams=['seat_id'],
            defaultParams={
                'availability': None,
            }
        )

        self._add_endpoint(
            attribute_name='seats',
            endpoint='api/1.1/space/seats/{location_id}',
            endpointCallback=lambda endp, **kw: endp.format(**kw),
            requiredParams=['location_id'],
            defaultParams={
                'spaceId': None,
                'categoryId': None,
                'seatId': None,
                'zoneId': None,
                'accessibleOnly': False,
                'powered': False,
                'availability': datetime.date.today(),
                'pageIndex': 0,
                'pageSize': 20,
            }
        )

        self._add_endpoint(
            attribute_name='zone',
            endpoint='api/1.1/space/zone/{zone_id}',
            endpointCallback=lambda endp, **kw: endp.format(**kw),
            requiredParams=['zone_id'],
        )

        self._add_endpoint(
            attribute_name='zones',
            endpoint='api/1.1/space/zones/{location_id}',
            endpointCallback=lambda endp, **kw: endp.format(**kw),
            requiredParams=['location_id'],
        )

    # helper functions
    def is_available_at(self, location_id=None, space_id=None, seat_id=None, dt=None):
        dt = dt or datetime.datetime.now().astimezone()

        seats = self.seats(
            location_id=location_id,
            spaceId=space_id,
        )
        if seat_id:
            for item in seats:

                for fromTo in item['availability']:
                    from_ = datetime.datetime.fromisoformat(
                        fromTo['from']
                    )
                    to = datetime.datetime.fromisoformat(
                        fromTo['to']
                    )
                    if from_ < dt < to:
                        return True
            return False

        else:
            availability = self.item(
                ids=space_id,
            )
            for result in availability:
                for fromTo in result['availability']:
                    from_ = datetime.datetime.fromisoformat(fromTo['from'])
                    to = datetime.datetime.fromisoformat(fromTo['to'])
                    if from_ < dt < to:
                        return True
            return False


class _RoomBookings(_BaseAPI):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)

        self._add_endpoint(
            method='GET',
            endpoint='1.1/room_groups',
        )


class _Appointments(_BaseAPI):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)

        self._add_endpoint(
            method='GET',
            endpoint='1.1/appointments',
            requiredParams=['user_id'],
            defaultParams={
                'location_id': None,
                'group_id': None,
                'category_id': None,
                'limit': 20,
            }
        )


class _Equipment(_BaseAPI):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)

        self._add_endpoint(
            method='GET',
            endpoint='1.1/equipment/locations',
            defaultParams={'details': False, 'admin_only': False},
        )


class _Events(_BaseAPI):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)

        self._add_endpoint(
            method='GET',
            endpoint='1.1/events',
            requiredParams=['cal_id'],
            defaultParams={
                'date': datetime.date.today(),
                'days': 30,
                'limit': 20,
                'campus': None,
                'category': None,
                'audience': None,
                'tag': None,
            }
        )


class _Calendars(_BaseAPI):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)

        self._add_endpoint(
            method='GET',
            endpoint='1.1/calendars',
        )


class _Hours(_BaseAPI):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)

        self._add_endpoint(
            attribute_name='hours',
            method='GET',
            endpoint='api/1.1/hours/{ids}',
            requiredParams=['ids'],
            endpointCallback=lambda endp, **kw: endp.format(
                ids=kw['ids'] if isinstance(kw['ids'], (int, str)) else ','.join(str(i) for i in kw['ids'])),
            defaultParams={
                'from': datetime.date.today(),
                'to': datetime.date.today(),
            }
        )


class Location(dict):
    @property
    def categories(self):
        ret = []
        categoryResults = self['parent'].spaces.categories(ids=self['lid'])
        for result in categoryResults:
            if result['lid'] == self['lid']:
                for cat in result['categories']:
                    ret.append(Category(
                        parent=self['parent'],
                        location_name=self['name'],
                        **cat
                    ))
        return ret

    @property
    def spaces(self):
        ret = []
        for cat in self.categories:
            spacesResults = self['parent'].spaces.category(cid=cat['cid'])
            for result in spacesResults:
                for space in result['items']:
                    ret.append(Space(
                        parent=self['parent'],
                        lid=self.id,
                        location_name=self['name'],
                        **space
                    ))
        return ret

    @property
    def id(self):
        return self['lid']

    def __str__(self):
        return '<{}: name={}, id={}>'.format(type(self).__name__, self['name'], self.id)

    def __repr__(self):
        return str(self)


class Category(dict):

    @property
    def id(self):
        return self['cid']

    def __str__(self):
        return '<{}: name={}, id={}, location_name={}>'.format(
            type(self).__name__,
            self['name'],
            self.id,
            self['location_name'],
        )

    def __repr__(self):
        return str(self)


class Space(dict):

    def is_available_at(self, dt=None):
        dt = dt or datetime.datetime.now().astimezone()

        for fromTo in self['availability']:
            from_ = datetime.datetime.fromisoformat(
                fromTo['from']
            )
            to = datetime.datetime.fromisoformat(
                fromTo['to']
            )
            if from_ < dt < to:
                return True

        return False

    @property
    def seats(self):
        if self['isBookableAsWhole'] is True:
            return []

        ret = []
        seats = self['parent'].spaces.seats(
            location_id=self['lid'],
            spaceId=self['id'],
        )
        for seat in seats:
            ret.append(Seat(
                parent=self['parent'],
                space_id=self.id,
                space_name=self['name'],
                location_name=self['location_name'],
                **seat
            ))

        return ret

    @property
    def id(self):
        return self['id']

    def reserve(self, fname, lname, email, startDT=None, endDT=None, ):
        '''
        The start/end time has be match one of the availability slots.
        :param startDT: datetime
        :param endDT: endtime
        :param fname:
        :param lname:
        :param email:
        :return:
        '''

        assert self.is_available_at(), 'This space is not currently available'

        startDT = startDT or datetime.datetime.now().astimezone()

        # the startDT must match one of the availability slots
        for fromTo in self['availability']:
            from_ = datetime.datetime.fromisoformat(
                fromTo['from']
            )
            to = datetime.datetime.fromisoformat(
                fromTo['to']
            )
            if from_ <= startDT < to:
                startDT = from_
                break

        # the endDT must match one of the availability slots
        endDT = endDT or startDT
        for fromTo in self['availability']:
            from_ = datetime.datetime.fromisoformat(
                fromTo['from']
            )
            to = datetime.datetime.fromisoformat(
                fromTo['to']
            )
            if from_ <= endDT <= to:
                endDT = to
                break

        # make the booking
        booking = {
            'id': self.id,
            'to': endDT.isoformat(),
        }

        resp = self['parent'].spaces.reserve(
            start=startDT,
            fname=fname,
            lname=lname,
            email=email,
            bookings=[booking],
        )

        return Booking(
            parent=self['parent'],
            **resp,
        )

    @property
    def bookings(self):
        ret = []
        for booking in self['parent'].spaces.bookings(
                eid=self.id,
        ):
            ret.append(Booking(
                parent=self['parent'],
                **booking,
            ))
        return ret

    def __str__(self):
        return '<{}: name={}, id={}, isAvailableNow={}, location_name={}>'.format(
            type(self).__name__,
            self['name'],
            self.id,
            self.is_available_at(),
            self['location_name'],
        )

    def __repr__(self):
        return str(self)


class Seat(dict):
    def is_available_at(self, dt=None):
        dt = dt or datetime.datetime.now().astimezone()
        if dt.tzname() is None:
            dt = dt.astimezone()

        for fromTo in self['availability']:
            from_ = datetime.datetime.fromisoformat(
                fromTo['from']
            )
            to = datetime.datetime.fromisoformat(
                fromTo['to']
            )
            if from_ <= dt <= to:
                return True

        return False

    @property
    def id(self):
        return self['id']

    def reserve(self, fname, lname, email, startDT=None, endDT=None, ):
        '''
        The start/end time has be match one of the availability slots.
        :param startDT: datetime
        :param endDT: endtime
        :param fname:
        :param lname:
        :param email:
        :return:
        '''

        startDT = startDT or datetime.datetime.now().astimezone()
        if startDT.tzname() is None:
            startDT = startDT.astimezone()

        assert self.is_available_at(startDT), 'This seat is not available at startDT={}'.format(startDT)

        # the startDT must match one of the availability slots
        for fromTo in self['availability']:
            from_ = datetime.datetime.fromisoformat(
                fromTo['from']
            )
            to = datetime.datetime.fromisoformat(
                fromTo['to']
            )
            if from_ <= startDT < to:
                startDT = from_
                break

        # the endDT must match one of the availability slots
        endDT = endDT or startDT
        if endDT.tzname() is None:
            endDT = endDT.astimezone()

        assert self.is_available_at(endDT), 'This seat is not available at endDT={}'.format(endDT)

        for fromTo in self['availability']:
            from_ = datetime.datetime.fromisoformat(
                fromTo['from']
            )
            to = datetime.datetime.fromisoformat(
                fromTo['to']
            )
            if from_ <= endDT <= to and to > startDT:
                endDT = to
                break

        # make the booking
        booking = {
            'id': self['space_id'],
            'to': endDT.isoformat(),
            'seat_id': self.id
        }

        resp = self['parent'].spaces.reserve(
            start=startDT,
            fname=fname,
            lname=lname,
            email=email,
            bookings=[booking],
        )

        return Booking(
            parent=self['parent'],
            **resp,
        )

    @property
    def bookings(self):
        ret = []
        for booking in self['parent'].spaces.bookings(
                seat_id=self.id,
        ):
            ret.append(Booking(
                parent=self['parent'],
                **booking,
            ))
        return ret

    def __str__(self):
        return '<{}: name={}, id={}, isAvailableNow={}, space_name={}, location_name={}>'.format(
            type(self).__name__,
            self['name'],
            self.id,
            self.is_available_at(),
            self['space_name'],
            self['location_name'],
        )

    def __repr__(self):
        return str(self)


class Booking(dict):

    def __str__(self):
        return '<{}: id={}, start={}, end={}, location_name={}, space_name={}, {}{}{}email={}>'.format(
            type(self).__name__,
            self.id,
            self.start,
            self.end,
            self.location_name,
            self.space_name,
            'seat_name={}, '.format(self['seat_name']) if self.get('seat_name', None) else '',
            'cancelled={}, '.format(self['cancelled']) if self.get('cancelled', None) else '',
            'status={}, '.format(self['status']) if self.get('status', None) else '',
            self.email,
        )

    def __repr__(self):
        return str(self)

    def _update(self):
        for booking in self['parent'].spaces.booking(ids=self.id):
            if booking['bookId'] == self.id or booking['booking_id'] == self.id:
                print('777 booking=', booking)
                self.update(booking)

    @property
    def id(self):
        ID = self.get('booking_id', self.get('bookId', None))
        if ID:
            return ID
        else:
            raise KeyError('Cannot find Booking ID')

    @property
    def start(self):
        if not self.get('fromDate', None):
            self._update()
        if 'fromDate' in self:
            return datetime.datetime.fromisoformat(self['fromDate'])
        else:
            return None

    @property
    def end(self):
        if not self.get('toDate', None):
            self._update()
        if 'toDate' in self:
            return datetime.datetime.fromisoformat(self['toDate'])
        else:
            return None

    @property
    def location_name(self):
        if not self.get('fromDate', None):
            self._update()

        return self['location_name']

    @property
    def space_name(self):
        if not self.get('item_name', None):
            self._update()
        return self['item_name']

    @property
    def email(self):
        if not self.get('email', None):
            self._update()
        return self['email']

    def cancel(self):
        resp = self['parent'].spaces.cancel(ids=self.id)
        for item in resp:
            if item.get('booking_id', None) == self.id:
                self.update(item)
        return resp


class LibCal:
    def __init__(
            self,
            baseURL,
            clientID,
            clientSecret,
            apiURL='https://api2.libcal.com/',
            debug=False,
    ):
        self.baseURL = baseURL
        self.clientID = clientID
        self.clientSecret = clientSecret
        self.apiURL = apiURL
        self.debug = debug

        #
        self.tokenManager = _TokenManager(
            clientID=self.clientID,
            clientSecret=self.clientSecret,
            apiURL=self.apiURL,
            debug=self.debug,
        )

        for cls in [
            _Spaces,
            _RoomBookings,
            _Equipment,
            _Appointments,
            _Events,
            _Calendars,
            _Hours,
        ]:
            self._add_api(cls)

    def print(self, *a, **k):
        if self.debug:
            print(*a, **k)

    def _add_api(self, cls):
        setattr(
            self,
            cls.__name__.strip('_').lower(),
            cls(
                baseURL=self.baseURL,
                tokenCallback=self.tokenManager.GetAccessToken,
                debug=self.debug
            )
        )

    @property
    def locations(self):
        ret = []
        locations = self.spaces.locations()
        for loc in locations:
            ret.append(Location(parent=self, **loc))
        return ret

    def find(self, booking_ids=None, seat_ids=None):
        if booking_ids:
            resp = self.spaces.booking(ids=booking_ids)
            ret = []
            for item in resp:
                ret.append(Booking(
                    parent=self,
                    **item
                ))
            return ret

        elif seat_ids:
            ret = []
            if isinstance(seat_ids, (int, str)):
                seat_ids = [seat_ids]

            for location in self.locations:
                for space in location.spaces:
                    for seat in space.seats:
                        if seat.id in seat_ids:
                            ret.append(seat)
            return ret
