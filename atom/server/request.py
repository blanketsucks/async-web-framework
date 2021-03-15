from atom.datastructures import URL, HTTPHeaders
import typing

class ClientRequest:
    def __init__(self, data: bytes):
        self.__data = data.decode()

        self.method: str = None
        self._path: str = None
        self.version: str = None

        self._url = None
        self._headers = None

        self._parse()

    @property
    def url(self):
        return self._parse_url() if not self._url else self._url

    @property
    def headers(self):
        return self._parse_headers() if not self._headers else self._headers

    def _parse(self) -> typing.Dict:
        self._get_data()

        method, path, version = self._parse_request()
        url = self._parse_url()
        headers = self._parse_headers()

        return {
            'method': method,
            'path': path,
            'version': version,
            'url': url,
            'headers': headers
        }

    def _get_data(self):
        self.__items = items = self.__data.split('\r\n')
        return items

    def _parse_request(self):
        string = self.__items[0]
        items = string.split(' ')

        self.method = items[0]
        self._path = items[1]
        self.version = items[2]

        self.__items.remove(string)
        return self.method, self._path, self.version

    def _parse_url(self):
        if not self._path:
            self._parse_request()

        string = self.__items[1]
        _, self._hostname = string.split(': ')

        if _ == 'User-Agent':
            string = self.__items[0]
            _, self._hostname = string.split(': ')

        full = 'http://' + self._hostname + self._path
        self._url = URL(full)

        self.__items.remove(string)
        return self._url

    def _parse_headers(self):
        if not self.method:
            self._parse_request()

        self._headers = headers = HTTPHeaders()

        for item in self.__items[1:]:
            if len(item) < 1:
                continue

            parts = item.split(': ')
            if len(parts) < 2:
                continue
                
            headers[parts[0]] = parts[1]

        return headers







