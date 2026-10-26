"""Protected consumer contracts for the free runnable tool suite."""
import unittest
from tgden_tools import run_tool


class FreeToolsContract(unittest.TestCase):
    def test_bot_result_links_to_the_real_search_page_and_keeps_languages(self):
        from urllib.parse import parse_qs, urlsplit
        payload={'items':[{'entity_type':'bot','username':'BotFather','title':'BotFather','language':['en'],'is_private':False}]}
        result=run_tool('bots',query='botfather',fetch_json=lambda u:payload)
        item=result['items'][0]
        self.assertEqual(item['language'],['en'])
        link=urlsplit(item['catalog_url'])
        self.assertEqual(link.path,'/en/bots')
        self.assertEqual(parse_qs(link.query)['q'],['botfather'])
        self.assertEqual(parse_qs(link.query)['utm_campaign'],['telegram_tools'])

    def test_group_search_is_keyless_and_drops_raw_private_fields(self):
        calls=[]
        def fetch(url):
            calls.append(url)
            return {'items':[
                {'entity_type':'chat','username':'Python_ru','title':'Python RU','is_private':False,'members_count':100,'raw':{'access_hash':'do-not-export'},'invite_hash':'do-not-export'},
                {'entity_type':'chat','username':'private_group','title':'Private','is_private':True},
            ],'total':2}
        result=run_tool('groups',query='python',limit=10,fetch_json=fetch)
        self.assertEqual(len(result['items']),1)
        self.assertEqual(result['items'][0]['username'],'python_ru')
        self.assertEqual(result['items'][0]['telegram_url'],'https://t.me/python_ru')
        self.assertIn('https://tgden.com/api/v1/search?',calls[0])
        self.assertIn('type=chat',calls[0])
        self.assertNotIn('do-not-export',str(result))
        self.assertNotIn('partner',calls[0])

    def test_source_failure_is_not_successful_empty_dataset(self):
        def fail(url): raise OSError('network failure')
        with self.assertRaises(Exception):
            run_tool('groups',query='python',fetch_json=fail)

    def test_buyer_preview_obeys_existing_public_limit(self):
        calls=[]
        def fetch(url):
            calls.append(url)
            return {'preview':[{'snippet':'Need a tutor','chat_title':'Public group','chat_username':'groupname','tg_link':'https://t.me/groupname/1','posted_at_ts':1,'sender_id':123,'invite_hash':'secret'}], 'total':1,'more':True}
        result=run_tool('buyer-preview',query='tutor',country='vn',limit=10,fetch_json=fetch)
        self.assertEqual(len(result['items']),1)
        self.assertIn('/api/v1/intent/preview?',calls[0])
        self.assertIn('limit=10',calls[0])
        self.assertNotIn('sender_id',str(result))
        self.assertNotIn('invite_hash',str(result))
        self.assertTrue(result['more'])
        with self.assertRaises(ValueError): run_tool('buyer-preview',query='tutor',limit=11,fetch_json=fetch)

    def test_direct_channel_export_needs_no_tgden_or_apify(self):
        calls=[]
        body='''<div class="tgme_channel_history"><div class="tgme_widget_message" data-post="telegram/123">
        <div class="tgme_widget_message_text js-message_text">Hello<br>public world</div>
        <a class="tgme_widget_message_date" href="https://t.me/telegram/123"><time datetime="2026-10-26T00:00:00+00:00"></time></a>
        <span class="tgme_widget_message_views">12K</span></div></div>'''
        def fetch(url): calls.append(url); return body
        result=run_tool('channel-posts',username='https://t.me/telegram',limit=10,fetch_text=fetch)
        self.assertEqual(calls,['https://t.me/s/telegram'])
        self.assertEqual(result['items'][0]['message_url'],'https://t.me/telegram/123')
        self.assertIn('Hello',result['items'][0]['text'])
        self.assertNotIn('<br>',result['items'][0]['text'])

    def test_username_target_is_not_an_arbitrary_url(self):
        for target in ('https://127.0.0.1/x','https://t.me.evil.test/telegram','https://t.me/+privatehash'):
            with self.subTest(target=target),self.assertRaises(ValueError):
                run_tool('channel-posts',username=target,fetch_text=lambda u:'bad')


if __name__=='__main__': unittest.main()
