from os import PathLike
from pathlib import Path
from typing import MutableSequence, Union

from bs4 import BeautifulSoup

from .commands import ICommand
from .models import ComposerPayload, User, Mail
from .utils import naive_join, slugify


class MailComposer(MutableSequence):
    def __init__(self, root: Union[str, PathLike], mail_path_fmt: str):
        self._cmds: MutableSequence[ICommand] = []
        self._root = Path(root)
        self._mail_path_fmt = mail_path_fmt

    def insert(self, index: int, value: ICommand) -> None:
        self._cmds.insert(index, value)

    def __getitem__(self, i: int) -> ICommand:
        return self._cmds[i]

    def __setitem__(self, i: int, o: ICommand) -> None:
        self._cmds[i] = o

    def __delitem__(self, i: int) -> None:
        del self._cmds[i]

    def __len__(self) -> int:
        return len(self._cmds)

    def __iadd__(self, other: ICommand):
        self._cmds.append(other)
        return self

    def __isub__(self, other: ICommand):
        self._cmds.remove(other)
        return self

    def compose(self, recipient: User, mail: Mail, body: str) -> str:
        soup = BeautifulSoup(body, 'lxml')
        path = Path(self._mail_path_fmt.format_map({
            'member_id': mail.member.id,
            'member_name': mail.member.name,
            'mail_id': mail.id,
            'received': mail.received,
            'subject': slugify(mail.subject)
        }))
        payload = ComposerPayload(recipient, mail, soup, path, [])

        for c in self._cmds:
            c.execute(payload)

        # Save composing artifacts if any
        for item in payload.artifacts:
            artifact_path = naive_join(self._root, item.path)
            # Double-check presence of files due to the absence of exclusive access
            if artifact_path.is_file():
                continue
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with artifact_path.open('xb') as f:
                    f.write(item.data)
            except FileExistsError:
                pass

        return payload.body.decode()
