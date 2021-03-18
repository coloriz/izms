from typing import MutableSequence, Callable

from .commands import ICommand
from .models import MailContainer


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

    def compose(self, mail: MailContainer):
        for c in self._cmds:
            c.execute(mail)

    def __call__(self, mail: MailContainer):
        self.compose(mail)
