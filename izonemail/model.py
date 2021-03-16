from datetime import datetime
from typing import Sequence


class User:
    def __init__(self, id: str, access_token: str, nickname: str, gender: str,
                 country_code: str, prefecture_id: int, birthday: str, member_id: int):
        self.id = id
        self.access_token = access_token
        self.nickname = nickname
        self.gender = gender
        self.country_code = country_code
        self.prefecture_id = prefecture_id
        self.birthday = birthday
        self.member_id = member_id

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, User):
            return NotImplemented
        return self.id == other.id


class Member:
    def __init__(self, id: int, name: str, image_url: str):
        self.id = id
        self.name = name
        self.image_url = image_url

    def __hash__(self):
        return self.id

    def __eq__(self, other):
        if not isinstance(other, Member):
            return NotImplemented
        return self.id == other.id


class Team(Sequence):
    def __init__(self, name: str, members: Sequence[Member]):
        self.name = name
        self.members = members

    def __len__(self):
        return len(self.members)

    def __getitem__(self, i):
        return self.members[i]


class Group(Sequence):
    def __init__(self, id: int, name: str, teams: Sequence[Team]):
        self.id = id
        self.name = name
        self.teams = teams

    def __hash__(self):
        return self.id

    def __eq__(self, other):
        if not isinstance(other, Group):
            return NotImplemented
        return self.id == other.id

    def __len__(self):
        return len(self.teams)

    def __getitem__(self, i):
        return self.teams[i]


class Mail:
    def __init__(self, member: Member, id: str, subject: str, content: str, received: datetime, detail_url: str):
        self.member = member
        self.id = id
        self.subject = subject
        self.content = content
        self.received = received
        self.detail_url = detail_url

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, Mail):
            return NotImplemented
        return self.id == other.id


class Inbox(Sequence):
    def __init__(self, page: int, has_next_page: bool, mails: Sequence[Mail]):
        self.page = page
        self.has_next_page = has_next_page
        self.mails = mails

    def __len__(self):
        return len(self.mails)

    def __getitem__(self, i):
        return self.mails[i]
