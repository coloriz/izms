from datetime import datetime
from typing import Dict, NamedTuple, List
import json

import requests


with open('izonemail_settings.json') as f:
    settings = json.load(f)


class User(NamedTuple):
    nickname: str
    gender: str
    country_code: str
    prefecture_id: int
    birthday: str
    member_id: int


class Member(NamedTuple):
    id: int
    name: str
    image_url: str


class Team(NamedTuple):
    name: str
    members: List[Member]


class Group(NamedTuple):
    id: int
    name: str
    teams: List[Team]


class Mail(NamedTuple):
    member: Member
    id: str
    pure_id: int
    subject: str
    received: datetime


class Inbox(NamedTuple):
    page: int
    has_next_page: bool
    mails: List[Mail]


class IZONEMail:
    __API_HOST = settings['api_host']
    __APP_HOST = settings['app_host']

    def __init__(self, user_id: str, access_token: str):
        self.__sess = requests.Session()
        self.__sess.headers['application-version'] = settings['application-version']
        self.__sess.headers['terms-version'] = settings['terms-version']
        self.__sess.headers['os-type'] = settings['os-type']
        self.__sess.headers['user-id'] = user_id
        self.__sess.headers['access-token'] = access_token

    def _get(self, url, **kwargs) -> Dict:
        res = self.__sess.get(url, **kwargs)
        res.raise_for_status()
        return res.json()

    def get_members(self) -> Group:
        res = self._get(f'{self.__API_HOST}/v1/members')
        # this api always responses with one group.
        group = res['all_members'][0]

        def make_member(m):
            return Member(m['id'], m['name'], m['image_url'])

        def make_team(t):
            return Team(t['team_name'], [make_member(m) for m in t['members']])

        return Group(group['group']['id'], group['group']['name'], [make_team(t) for t in group['team_members']])

    def get_user(self) -> User:
        res = self._get(f'{self.__API_HOST}/v1/users')
        res = res['user']
        user = User(res['nickname'], res['gender'], res['country_code'],
                    res['prefecture_id'], res['birthday'], res['member_id'])
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
            # in case of birthday mail, ignore pure_id
            pure_id = int(m['id'][1:]) if m['id'][0] != 'b' else 0
            return Mail(make_member(m['member']), m['id'], pure_id, m['subject'], received)

        return Inbox(res['page'], res['has_next_page'], [make_mail(m) for m in res['mails']])

    def get_mail_detail(self, mail_id: str) -> bytes:
        res = self.__sess.get(f'{self.__APP_HOST}/mail/{mail_id}')
        res.raise_for_status()
        return res.content
