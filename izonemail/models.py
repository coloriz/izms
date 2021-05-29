from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Sequence, MutableMapping, Mapping, Optional, Iterator, MutableSequence

from bs4 import BeautifulSoup


@dataclass
class Policy:
    bundle_id: str
    api_host: str
    app_host: str
    mail_header: str
    css: str
    genesis: datetime


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


@dataclass(frozen=True)
class User:
    id: str
    access_token: str = field(compare=False)
    nickname: str = field(compare=False)
    gender: str = field(compare=False)
    country_code: str = field(compare=False)
    prefecture_id: int = field(compare=False)
    birthday: str = field(compare=False)
    member_id: int = field(compare=False)


@dataclass(frozen=True)
class Member:
    id: int
    name: str = field(compare=False)
    image_url: str = field(compare=False)


@dataclass(frozen=True)
class Team(Sequence):
    name: str
    members: Sequence[Member] = field(compare=False)

    def __len__(self):
        return len(self.members)

    def __getitem__(self, i):
        return self.members[i]


@dataclass(frozen=True)
class Group(Sequence):
    id: int
    name: str = field(compare=False)
    teams: Sequence[Team] = field(compare=False)

    def __len__(self):
        return len(self.teams)

    def __getitem__(self, i):
        return self.teams[i]


@dataclass(frozen=True)
class Mail:
    member: Member = field(compare=False)
    id: str
    subject: str = field(compare=False)
    content: str = field(compare=False)
    received: datetime = field(compare=False)
    detail_url: str = field(compare=False)


@dataclass(frozen=True)
class Inbox(Sequence):
    page: int
    has_next_page: bool
    mails: Sequence[Mail]

    def __len__(self):
        return len(self.mails)

    def __getitem__(self, i):
        return self.mails[i]


@dataclass(frozen=True)
class Artifact:
    path: Path
    data: bytes


@dataclass(frozen=True)
class ComposerPayload:
    recipient: User
    header: Mail
    body: BeautifulSoup
    path: Path
    artifacts: MutableSequence[Artifact] = field(default_factory=list)
