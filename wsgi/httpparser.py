

class HTTPParserMixin:
    def on_body(self, body):
        self._body = body

    def on_url(self, url):
        self._url = url

    def on_header(self, header, value):
        header = header.decode(self._encoding)
        self._headers[header] = value.decode(self._encoding)

    def on_status(self, status):
        status = status.decode(self._encoding)
        self._status = status

    def on_message_complete(self):
        self._request = self._request_cls(
            version=self._request_parser.get_http_version(),
            method=self._request_parser.get_method(),
            url=self._url,
            headers=self._headers,
            body=self._body,
            status_code=self._status
        )
        
        self._request_handler_task = self._loop.create_task(
            self._request_handler(self._request, self.response_writer)
        )
        self._loop.create_task(
            self._app.dispatch('on_request', self._request)
        )
