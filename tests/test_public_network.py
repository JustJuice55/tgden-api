"""No network access: exercise the HTTP boundary using fake responses."""
import io
import json
import unittest
import urllib.error
import urllib.request
from unittest.mock import Mock, patch
from tgden_tools.network import MAX_BYTES, PublicClient, PublicRedirectHandler, SourceError, USER_AGENT, validate_source_url


class Response(io.BytesIO):
    status = 200
    headers = {}

    def __init__(self, content=b'{}', url='https://tgden.com/api/v1/search?q=test'):
        super().__init__(content)
        self.url = url

    def geturl(self):
        return self.url


class NetworkTests(unittest.TestCase):
    def test_fetch_sends_signed_agent_and_no_auth_and_reads_json(self):
        opener = Mock()
        opener.open.return_value = Response(b'{"items": []}')
        with patch('urllib.request.build_opener', return_value=opener):
            self.assertEqual(PublicClient().fetch_json('https://tgden.com/api/v1/search?q=test'), {'items': []})
        request = opener.open.call_args.args[0]
        self.assertEqual(request.get_header('User-agent'), USER_AGENT)
        self.assertEqual(request.get_header('Accept-encoding'), 'identity')
        self.assertIsNone(request.get_header('Authorization'))
        self.assertIsNone(request.get_header('Cookie'))
        self.assertLessEqual(opener.open.call_args.kwargs['timeout'], 15)

    def test_exact_https_host_only(self):
        for url in ('http://tgden.com/x', 'https://tgden.com.evil.test/x', 'https://localhost/x',
                    'https://127.0.0.1/x', 'https://tgden.com:443/x', 'https://user@tgden.com/x',
                    'https://tgden.com/x#frag', 'https://TGDen.com/x'):
            with self.subTest(url=url), self.assertRaises(SourceError):
                validate_source_url(url, 'tgden.com')
        validate_source_url('https://tgden.com/api/v1/search?q=test', 'tgden.com')

    def test_cross_host_and_non_https_redirects_are_blocked(self):
        handler = PublicRedirectHandler('t.me')
        request = urllib.request.Request('https://t.me/s/telegram')
        for destination in ('https://evil.example/x', 'http://t.me/s/telegram', 'https://t.me:443/x', 'https://user@t.me/x'):
            with self.subTest(destination=destination), self.assertRaises(SourceError):
                handler.redirect_request(request, None, 302, 'Found', {}, destination)
        redirected = handler.redirect_request(request, None, 302, 'Found', {}, 'https://t.me/s/telegram?before=1')
        self.assertEqual(redirected.full_url, 'https://t.me/s/telegram?before=1')

    def test_oversized_body_fails_with_or_without_content_length(self):
        for with_header in (False, True):
            response = Response(b'x' * (MAX_BYTES + 1))
            response.headers = {'Content-Length': str(MAX_BYTES + 1)} if with_header else {}
            opener = Mock()
            opener.open.return_value = response
            with self.subTest(header=with_header), patch('urllib.request.build_opener', return_value=opener), self.assertRaises(SourceError):
                PublicClient().fetch_json('https://tgden.com/api/v1/search?q=test')

    def test_429_does_not_retry(self):
        opener = Mock()
        opener.open.side_effect = urllib.error.HTTPError('https://tgden.com/x', 429, 'Rate limit', {}, None)
        with patch('urllib.request.build_opener', return_value=opener), self.assertRaisesRegex(SourceError, '429'):
            PublicClient().fetch_json('https://tgden.com/api/v1/search?q=test')
        self.assertEqual(opener.open.call_count, 1)

    def test_non_json_response_is_source_error(self):
        opener = Mock()
        opener.open.return_value = Response(b'<html>challenge</html>')
        with patch('urllib.request.build_opener', return_value=opener), self.assertRaisesRegex(SourceError, 'valid JSON'):
            PublicClient().fetch_json('https://tgden.com/api/v1/search?q=test')

    def test_final_response_url_is_validated(self):
        opener = Mock()
        opener.open.return_value = Response(b'{}', 'https://evil.example/leak')
        with patch('urllib.request.build_opener', return_value=opener), self.assertRaises(SourceError):
            PublicClient().fetch_json('https://tgden.com/api/v1/search?q=test')

    def test_request_budget_is_enforced(self):
        client = PublicClient()
        client.calls = 10
        with patch('urllib.request.build_opener') as build, self.assertRaises(SourceError):
            client.fetch_json('https://tgden.com/api/v1/search?q=test')
        build.assert_not_called()


if __name__ == '__main__':
    unittest.main()
