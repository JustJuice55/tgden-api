"""Offline acceptance coverage; deliberately never calls an external endpoint."""
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from tgden_tools import TOOLS, SourceError, normalize_username, run_tool
from tgden_tools.channel_html import parse_channel_page


class PublicToolTests(unittest.TestCase):
    def setUp(self):
        self.no_network = patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('Tests must be offline'))
        self.no_network.start()
        self.addCleanup(self.no_network.stop)

    def test_each_catalog_mode_selects_its_kind_and_bounded_rows(self):
        for mode, kind in [('groups', 'chat'), ('channels', 'channel'), ('bots', 'bot')]:
            calls = []
            def fetch(url):
                calls.append(url)
                return {'items': [{'username': 'Public_Name', 'entity_type': kind, 'title': 'Title',
                                   'verified': True, 'categories': ['tech', {'secret': 'hidden'}],
                                   'raw': {'secret': 'hidden'}, 'sender_id': 'hidden'}] * 3, 'total': 100}
            with self.subTest(mode=mode):
                result = run_tool(mode, query='python', limit=2, fetch_json=fetch)
                self.assertEqual(len(calls), 1)
                self.assertEqual(parse_qs(urlsplit(calls[0]).query)['type'], [kind])
                self.assertEqual(result['count'], 2)
                self.assertEqual(result['source_total'], 100)
                self.assertEqual(result['items'][0]['categories'], ['tech'])
                expected_route = '/en/bots?q=public_name&' if kind == 'bot' else '/en/%s/public_name?' % kind
                self.assertIn(expected_route, result['items'][0]['catalog_url'])
                self.assertNotIn('hidden', str(result))
                self.assertNotIn('sender_id', str(result))
                self.assertTrue(result['items'][0]['verified'])

    def test_bot_catalog_link_uses_existing_filtered_bot_directory(self):
        result = run_tool('bots', query='moderation', fetch_json=lambda url: {'items': [
            {'username': 'SomeBot', 'entity_type': 'bot', 'title': 'Some Bot'}]})
        item = result['items'][0]
        self.assertEqual(item['telegram_url'], 'https://t.me/somebot')
        self.assertEqual(item['catalog_url'], 'https://tgden.com/en/bots?q=somebot&utm_source=github&utm_medium=free_tools&utm_campaign=telegram_tools')
        self.assertNotIn('/en/bot/', item['catalog_url'])

    def test_language_array_is_retained_with_only_string_values(self):
        result = run_tool('groups', query='python', fetch_json=lambda url: {'items': [
            {'username': 'somegroup', 'entity_type': 'chat', 'language': ['en', 'ru', {'secret': 'hidden'}, 7]}]})
        self.assertEqual(result['items'][0]['language'], ['en', 'ru'])
        self.assertNotIn('hidden', str(result))

    def test_skips_private_missing_username_and_wrong_entity_type(self):
        rows = [{'username': 'public_name', 'entity_type': 'chat'},
                {'username': 'private_one', 'entity_type': 'chat', 'private': True},
                {'username': 'private_two', 'entity_type': 'chat', 'is_private': True},
                {'username': 'private_str', 'entity_type': 'chat', 'is_private': 'true'},
                {'entity_type': 'chat', 'title': 'Private'},
                {'username': 'wrong_kind', 'entity_type': 'channel'},
                {'username': 'https://bad.example', 'entity_type': 'chat'}]
        result = run_tool('groups', query='test', fetch_json=lambda url: {'items': rows})
        self.assertEqual([item['username'] for item in result['items']], ['public_name'])

    def test_lookup_exact_only_deduplicates_and_reports_catalog_absence(self):
        calls = []
        def fetch(url):
            calls.append(url)
            name = parse_qs(urlsplit(url).query)['q'][0]
            return {'items': [
                {'username': 'telegram', 'entity_type': 'channel', 'title': 'Telegram'},
                {'username': name + '_fan', 'entity_type': 'chat'},
            ], 'total': 2}
        result = run_tool('lookup', username='@Telegram,https://t.me/s/telegram,missing_name', fetch_json=fetch)
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(parse_qs(urlsplit(url).query)['type'] == ['all'] for url in calls))
        self.assertEqual([i['lookup_status'] for i in result['items']], ['catalog_match', 'not_found'])
        self.assertEqual(result['items'][1]['username'], 'missing_name')
        self.assertIn('not a claim about Telegram', result['scope'])

    def test_lookup_rejects_more_than_ten_or_a_too_small_limit_before_fetch(self):
        fetch = lambda url: self.fail('Invalid input must not fetch')
        with self.assertRaises(ValueError):
            run_tool('lookup', username=','.join('handle_%s' % i for i in range(11)), fetch_json=fetch)
        with self.assertRaises(ValueError):
            run_tool('lookup', username='hello,world', limit=1, fetch_json=fetch)

    def test_lookup_failure_is_never_not_found(self):
        for response in ({}, {'items': None}, {'items': ['bad']}, {'items': [{'username': 'telegram'}]}, {'items': [{'entity_type': {}, 'username': 'telegram'}]}, {'error': 'rate limited'}):
            with self.subTest(response=response), self.assertRaises(SourceError):
                run_tool('lookup', username='telegram', fetch_json=lambda url: response)
        with self.assertRaises(SourceError):
            run_tool('lookup', username='telegram', fetch_json=lambda url: (_ for _ in ()).throw(OSError()))

    def test_classifieds_projects_listing_fields_and_builds_valid_source_link(self):
        calls = []
        def fetch(url):
            calls.append(url)
            return {'items': [{'id': 'abc-123', 'country': 'th', 'type': 'rent', 'direction': 'offer',
                    'title': '=formula', 'category': 'real-estate', 'price_amount': 12000,
                    'price_currency': 'THB', 'location': 'Bangkok', 'lang': 'en', 'suspicious': False,
                    'source_chat_username': 'Rental_Chat', 'source_msg_id': 123,
                    'seller_since_year': 'hidden', 'photos': ['hidden'], 'author': 'hidden',
                    'sender_id': 'hidden', 'raw': 'hidden'}], 'total': 12, 'next_cursor': 'hidden'}
        result = run_tool('classifieds', country='TH', category='real-estate', limit=3, fetch_json=fetch)
        item = result['items'][0]
        self.assertEqual(item['price_amount'], 12000)
        self.assertEqual(item['title'], '=formula')
        self.assertEqual(item['source_message_url'], 'https://t.me/rental_chat/123')
        self.assertTrue(item['market_url'].startswith('https://tgden.com/en/market/abc-123?'))
        self.assertNotIn('hidden', str(result))
        self.assertEqual(parse_qs(urlsplit(calls[0]).query), {'limit': ['3'], 'country': ['th'], 'category': ['real-estate']})

    def test_malicious_listing_urls_are_not_exported(self):
        result = run_tool('classifieds', fetch_json=lambda url: {'items': [
            {'id': '../evil', 'source_chat_username': 'https://evil.example', 'source_msg_id': 10},
            {'id': 12, 'source_chat_username': 'public_chat', 'source_msg_id': '4/../../evil'},
        ]})
        self.assertNotIn('source_message_url', result['items'][0])
        self.assertNotIn('market_url', result['items'][0])
        self.assertNotIn('source_message_url', result['items'][1])
        self.assertIn('/market/12?', result['items'][1]['market_url'])

    def test_buyer_preview_preserves_masked_scope_and_more_without_identities(self):
        calls = []
        def fetch(url):
            calls.append(url)
            return {'preview': [{'chat_username': 'Public_Group', 'chat_title': 'Group',
                    'snippet': 'Need help; contact ***', 'posted_at_ts': 123, 'posted_at': '2026-10-26',
                    'has_contact': True, 'tg_link': 'https://t.me/Public_Group/25',
                    'intent': 'buy', 'country': 'vn', 'category': 'real-estate',
                    'sender_id': 'hidden', 'phone': 'hidden', 'contact': 'hidden', 'raw': 'hidden'}],
                    'total': 200, 'more': True, 'contract': {'secret': 'hidden'}}
        result = run_tool('buyer-preview', country='vn', category='real-estate', days=30, limit=2, fetch_json=fetch)
        self.assertEqual(len(calls), 1)
        self.assertTrue(result['more'])
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['limits']['public_rate_limit'], '60 requests/hour/IP')
        self.assertEqual(result['items'][0]['tg_link'], 'https://t.me/public_group/25')
        self.assertNotIn('hidden', str(result))
        self.assertEqual(parse_qs(urlsplit(calls[0]).query)['days'], ['30'])

    def test_preview_never_follows_or_exports_arbitrary_supplied_links(self):
        result = run_tool('buyer-preview', query='housing', fetch_json=lambda url: {'preview': [
            {'chat_username': 'public_chat', 'snippet': 'Example', 'tg_link': 'https://evil.example/secret'}], 'more': False})
        self.assertNotIn('tg_link', result['items'][0])
        with self.assertRaises(SourceError):
            run_tool('buyer-preview', query='housing', fetch_json=lambda url: {'preview': [], 'more': 'yes'})

    def test_post_search_uses_channel_index_and_generated_message_url(self):
        calls = []
        def fetch(url):
            calls.append(url)
            return {'items': [{'channel_username': 'Telegram', 'telegram_msg_id': 123,
                    'snippet': 'Hello', 'posted_at': '2026-10-26', 'views': 300,
                    'source': {'secret': 'hidden'}, 'tme_url': 'https://evil.example',
                    'raw': 'hidden', 'sender_id': 'hidden'}], 'total': 1}
        result = run_tool('post-search', query='telegram', limit=1, fetch_json=fetch)
        self.assertEqual(result['items'][0]['tme_url'], 'https://t.me/telegram/123')
        self.assertNotIn('evil', str(result))
        self.assertNotIn('hidden', str(result))
        params = parse_qs(urlsplit(calls[0]).query)
        self.assertEqual(params['kind'], ['channel'])
        self.assertEqual(params['min_views'], ['0'])

    def test_valid_empty_results_are_distinct_from_bad_schema(self):
        for tool in ('groups', 'channels', 'bots', 'classifieds', 'post-search'):
            kwargs = {'query': 'example'} if tool != 'classifieds' else {}
            with self.subTest(tool=tool):
                result = run_tool(tool, fetch_json=lambda url: {'items': [], 'total': 0}, **kwargs)
                self.assertEqual(result['count'], 0)
                with self.assertRaises(SourceError):
                    run_tool(tool, fetch_json=lambda url: {'error': 'unavailable'}, **kwargs)

    def test_validation_rejects_unsupported_or_unbounded_inputs_without_network(self):
        cases = [('missing', {}), ('groups', {}), ('groups', {'query': 'x' * 201}),
                 ('groups', {'query': 'python', 'country': 'vn'}),
                 ('groups', {'query': 'x', 'limit': 51}), ('groups', {'query': 'x', 'limit': True}),
                 ('groups', {'query': 'x', 'days': 8}), ('groups', {'query': 'x', 'username': 'abc'}),
                 ('classifieds', {'query': 'rent'}), ('classifieds', {'country': '../'}),
                 ('buyer-preview', {}), ('buyer-preview', {'query': 'x', 'limit': 11}),
                 ('buyer-preview', {'country': 'vn', 'days': 31}),
                 ('buyer-preview', {'country': 'vn', 'category': 'x&raw=1'}),
                 ('channel-posts', {'username': 'telegram', 'limit': 21}),
                 ('lookup', {'query': 'telegram'}), ('lookup', {'username': 'abc,,def'})]
        for mode, kwargs in cases:
            with self.subTest(mode=mode, kwargs=kwargs), self.assertRaises(ValueError):
                run_tool(mode, fetch_json=lambda url: self.fail('must not fetch'), fetch_text=lambda url: self.fail('must not fetch'), **kwargs)

    def test_username_url_boundary(self):
        for value in ('@Telegram', 'telegram', 'https://t.me/Telegram/', 'https://t.me/s/Telegram'):
            self.assertEqual(normalize_username(value), 'telegram')
        for value in ('https://127.0.0.1/telegram', 'https://t.me.evil.test/telegram',
                      'https://t.me:443/telegram', 'https://user@t.me/telegram', 'http://t.me/telegram',
                      'https://t.me/telegram#x', 'https://t.me/telegram?x=1', 'https://t.me/+hash',
                      'https://t.me/joinchat/hash', 'https://t.me/telegram/12', 'https://t.me/%74elegram',
                      '//t.me/telegram', 'тест', 'ab', 'x' * 33, 'telegram\nmore'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_username(value)


class ChannelParserTests(unittest.TestCase):
    def feed(self, content):
        return '<div class="tgme_channel_history">%s</div>' % content

    def message(self, number, content):
        return '<div class="tgme_widget_message js-widget_message" data-post="Telegram/%s">%s</div>' % (number, content)

    def test_nested_text_breaks_entities_time_and_view_text(self):
        body = self.feed(self.message(1, '<div class="tgme_widget_message_text">A &amp; <b>B</b><br>C<p>D</p>'
                    '<script>secret()</script><style>hidden</style><a href="https://example.com">E</a></div>'
                    '<time datetime="2026-10-26T00:00:00+00:00"></time><span class="tgme_widget_message_views">12K</span>'))
        item = parse_channel_page(body, 'telegram', 10)[0]
        self.assertEqual(item['text'], 'A & B\nC\nD\nE')
        self.assertEqual(item['views'], '12K')
        self.assertEqual(item['message_url'], 'https://t.me/telegram/1')
        self.assertEqual(item['posted_at'], '2026-10-26T00:00:00+00:00')

    def test_limits_latest_visible_posts_without_fetching_older_pages(self):
        body = self.feed(''.join(self.message(i, '<div class="tgme_widget_message_text">Post</div>') for i in range(1, 5)))
        result = parse_channel_page(body, 'telegram', 2)
        self.assertEqual([item['message_url'] for item in result], ['https://t.me/telegram/3', 'https://t.me/telegram/4'])

    def test_empty_public_history_can_succeed(self):
        self.assertEqual(parse_channel_page(self.feed(''), 'telegram', 10), [])

    def test_contact_challenge_unsupported_and_incomplete_pages_fail(self):
        for body in ('<html>Contact @telegram</html>', '<form>Captcha challenge</form>', '', '<div class="tgme_channel_history">',
                     '<div class="tgme_channel_history"><div class="tgme_widget_message" data-post="telegram/1">',
                     self.feed(self.message(1, '').replace('Telegram/1', 'another/1')),
                     self.feed(self.message(1, '').replace('Telegram/1', 'telegram/../bad'))):
            with self.subTest(body=body), self.assertRaises(SourceError):
                parse_channel_page(body, 'telegram', 10)

    def test_injected_html_also_obeys_size_bound(self):
        with self.assertRaises(SourceError):
            parse_channel_page('x' * (2 * 1024 * 1024 + 1), 'telegram', 10)

    def test_direct_mode_does_not_call_tgden(self):
        calls = []
        result = run_tool('channel-posts', username='@Telegram',
                          fetch_text=lambda url: calls.append(url) or self.feed(self.message(1, '')),
                          fetch_json=lambda url: self.fail('Telegram export must not use TGDen'))
        self.assertEqual(calls, ['https://t.me/s/telegram'])
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['limits']['preview_pages'], 1)


if __name__ == '__main__':
    unittest.main()
