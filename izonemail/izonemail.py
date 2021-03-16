from datetime import datetime
from pathlib import Path
from typing import Dict, List
import json

import requests

from .model import User, Member, Team, Group, Mail, Inbox

settings = json.loads((Path(__file__).resolve().parent / 'settings.json').read_text())


class IZONEMail:
    __API_HOST = settings['api_host']
    __APP_HOST = settings['app_host']

    def __init__(self, user_id: str, access_token: str):
        # get an application version from Apple server
        res = requests.get(r'https://itunes.apple.com/lookup?bundleId=com.ca-smart.izonemail&country=JP')
        res.raise_for_status()
        app_manifest = res.json()['results'][0]
        self.__sess = requests.Session()
        self.__sess.headers['application-version'] = app_manifest['version']
        self.__sess.headers['terms-version'] = settings['terms-version']
        self.__sess.headers['os-type'] = settings['os-type']
        self.__sess.headers['user-id'] = user_id
        self.__sess.headers['access-token'] = access_token

    def _get(self, url, **kwargs) -> Dict:
        res = self.__sess.get(url, **kwargs)
        res.raise_for_status()
        return res.json()

    def get_members(self) -> List[Group]:
        res = self._get(f'{self.__API_HOST}/v1/members')

        def make_member(m):
            return Member(m['id'], m['name'], m['image_url'])

        def make_team(t):
            return Team(t['team_name'], [make_member(m) for m in t['members']])

        groups = []
        for g in res['all_members']:
            group = Group(g['group']['id'], g['group']['name'], [make_team(t) for t in g['team_members']])
            groups.append(group)

        return groups

    def get_user(self) -> User:
        res = self._get(f'{self.__API_HOST}/v1/users')
        res = res['user']
        user = User(res['id'], res['access_token'], res['nickname'], res['gender'],
                    res['country_code'], res['prefecture_id'], res['birthday'], res['member_id'])
        return user

    def get_application_settings(self) -> Dict:
        res = self._get(f'{self.__API_HOST}/v1/application_settings')
        return res['application_settings']

    def get_informations(self) -> List[Dict]:
        res = self._get(f'{self.__API_HOST}/v1/informations')
        return res['informations']

    def get_inbox(self, page: int = 1) -> Inbox:
        res = self._get(f'{self.__API_HOST}/v1/inbox', params={
            'is_star': 0,
            'is_unread': 0,
            'page': page
        })

        def make_member(e):
            return Member(e['id'], e['name'], e['image_url'])

        def make_mail(m):
            received = datetime.fromisoformat(m['receive_datetime'])
            return Mail(make_member(m['member']), m['id'], m['subject'], m['content'], received, m['detail_url'])

        return Inbox(res['page'], res['has_next_page'], [make_mail(m) for m in res['mails']])

    def get_mail_detail(self, mail: Mail) -> bytes:
        res = self.__sess.get(mail.detail_url)
        res.raise_for_status()
        return res.content
