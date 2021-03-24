from datetime import datetime
from pathlib import Path
from typing import Sequence, NamedTuple, MutableMapping, Mapping, Optional, Iterator

from bs4 import BeautifulSoup

API_HOST = r'https://app-api.izone-mail.com'
APP_HOST = r'https://app-web.izone-mail.com'


class Profile(MutableMapping):
    """A case-insensitive ``dict``-like object."""

    _http_headers = frozenset({
        'user-agent', 'accept-encoding', 'accept', 'accept-language'
    })
    _required_keys = frozenset({
        'user-id', 'access-token', 'os-type', 'application-version', 'terms-version'
    })
    _valid_keys = frozenset(
        _http_headers | _required_keys | {'application-language', 'device-version', 'os-version'}
    )

    def __init__(self, data: Optional[Mapping[str, str]] = None, **kwargs):
        self._store = {}
        if data is None:
            data = {}
        self.update(data, **kwargs)

    def __getitem__(self, key: str) -> str:
        return self._store[key.lower()]

    def __setitem__(self, key: str, value: str) -> None:
        if not self.is_valid_key(key):
            raise LookupError(key)
        self._store[key.lower()] = value

    def __delitem__(self, key: str) -> None:
        del self._store[key.lower()]

    def __iter__(self) -> Iterator[str]:
        return iter(self._store)

    def __len__(self) -> int:
        return len(self._store)

    def __repr__(self) -> str:
        return repr(self._store)

    @classmethod
    def required_keys(cls):
        return cls._required_keys

    @classmethod
    def is_required_key(cls, key: str) -> bool:
        return key.lower() in cls._required_keys

    @classmethod
    def valid_keys(cls):
        return cls._valid_keys

    @classmethod
    def is_valid_key(cls, key: str) -> bool:
        return key.lower() in cls._valid_keys


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


class MailContainer(NamedTuple):
    recipient: User
    header: Mail
    body: BeautifulSoup
    path: Path
