'''
Based on LibCal API Docs at:

License: https://grant-miller.mit-license.org/
'''
import datetime
from copy import copy
from urllib.parse import urlparse

import requests


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

    def send_request(self, method, url, params=None):
        for k, v in params.items():
            if isinstance(v, bool):
                params[k] = int(v)  # booleans are passed as int 0/1

        self.print('send_request(', method, url, params)

        resp = requests.request(
            method=method,
            url=url,
            params=params,
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
            endpointCallback=lambda endpoint, ids: endpoint.format(ids=','.join(str(i) for i in ids)),
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
            endpoint='1.1/space/booking',
            method='GET',
            requiredParams=['book_ids'],
            defaultParams={
                'formAnswers': False,
            }
        )
        self._add_endpoint(
            endpoint='1.1/space/items/bookings',
            method='GET',
            defaultParams={
                'eid': None,
                'seat_id': None,
                'cid': None,
                'lid': None,
                'email': None,
                'date': datetime.date.today(),
                'days': 0,
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
