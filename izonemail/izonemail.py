from datetime import datetime
from typing import Dict, List

from easydict import EasyDict
from requests import Response

from .factory import SessionFactory
from .models import API_HOST, Profile, User, Member, Team, Group, Mail, Inbox


def create_member(m):
    return Member(m.id, m.name, m.image_url)


def create_team(t):
    return Team(t.team_name, [create_member(m) for m in t.members])


def create_mail(m):
    received = datetime.fromisoformat(m.receive_datetime)
    return Mail(create_member(m.member), m.id, m.subject, m.content, received, m.detail_url)


class IZONEMail:
    def __init__(self, profile: Profile):
        self._s = SessionFactory.instance()
        self._profile = profile

    def _get(self, url, **kwargs) -> Response:
        r = self._s.get(url, headers=self._profile, **kwargs)
        r.raise_for_status()
        return r

    def _get_json(self, url, **kwargs) -> Dict:
        r = self._get(url, **kwargs)
        return EasyDict(r.json())

    def get_members(self) -> List[Group]:
        r = self._get_json(f'{API_HOST}/v1/members')

        groups = []
        for g in r.all_members:
            group = Group(g.group.id, g.group.name, [create_team(t) for t in g.team_members])
            groups.append(group)

        return groups

    def get_user(self) -> User:
        r = self._get_json(f'{API_HOST}/v1/users')
        u = r.user
        user = User(u.id, u.access_token, u.nickname, u.gender,
                    u.country_code, u.prefecture_id, u.birthday, u.member_id)
        return user

    def get_application_settings(self) -> Dict:
        r = self._get_json(f'{API_HOST}/v1/application_settings')
        return r.application_settings

    def get_informations(self) -> List[Dict]:
        r = self._get_json(f'{API_HOST}/v1/informations')
        return r.informations

    def get_inbox(self, page: int = 1) -> Inbox:
        r = self._get_json(f'{API_HOST}/v1/inbox', params={
            'is_star': 0,
            'is_unread': 0,
            'page': page
        })

        return Inbox(r.page, r.has_next_page, [create_mail(m) for m in r.mails])

    def get_mail_detail(self, mail: Mail) -> str:
        r = self._get(mail.detail_url)
        return r.text
