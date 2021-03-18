from pathlib import Path
from typing import MutableSequence, Callable

from bs4 import BeautifulSoup

from .commands import ICommand
from .models import MailContainer, User, Mail


class MailComposer(MutableSequence, Callable):
    def __init__(self):
        self._cmds: MutableSequence[ICommand] = []

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

    def compose(self, recipient: User, mail: Mail, body: str, root: Path) -> str:
        soup = BeautifulSoup(body, 'lxml')
        container = MailContainer(recipient, mail, soup, root)

        for c in self._cmds:
            c.execute(container)

        return container.body.decode()

    def __call__(self, recipient: User, mail: Mail, body: str, root: Path) -> str:
        return self.compose(recipient, mail, body, root)
