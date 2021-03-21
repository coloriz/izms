from abc import ABC, abstractmethod
from typing import Any, MutableMapping, MutableSet, Iterator, Optional, TypeVar, Callable

VT = TypeVar('VT', int, float, str, dict, type(None))


class PureOption(ABC):
    def __init__(self, name: str, default: Any, type_: type, required: bool):
        if not isinstance(name, str):
            raise TypeError(f"'name' must be str, not {type(name).__name__}")
        self._name = name
        self._default = default
        if not isinstance(type_, type):
            raise TypeError(f"'type_' must be type, not {type(type_).__name__}")
        self._type = type_
        if not isinstance(required, bool):
            raise TypeError(f"'required' must be bool, not {type(required).__name__}")
        self._required = required
        self._parent: Optional[PureOption] = None

    @property
    def name(self):
        return self._name

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        cls_name = type(self).__name__
        parent = self._parent.name if self._parent else None
        return f"{cls_name}(name={repr(self.name)}, default={repr(self._default)}, type={self._type.__name__}, " \
               f"required={self._required}, parent={repr(parent)})"

    @abstractmethod
    def parse_options(self, opts: MutableMapping[str, VT]):
        pass


class Option(PureOption):
    def __init__(self, name: str, default: Any = None, type: type = str, required: bool = False,
                 validator: Callable[[Any], bool] = None):
        super(Option, self).__init__(name, default, type, required)
        self._validator = validator
        if self._validator is None:
            self._validator = lambda _: True

    def parse_options(self, opts: MutableMapping[str, VT]):
        if self.name in opts:
            value = opts[self.name]
            if not isinstance(value, self._type):
                raise TypeError(f"'{self.name}' must be {self._type.__name__}, not {type(value).__name__}")
            if not self._validator(value):
                raise ValueError(f"'{self.name}' cannot be {repr(value)}")
        else:
            if self._required:
                msg = f"Missing required key '{self.name}'"
                if self._parent:
                    msg += f" in '{self._parent.name}'"
                raise KeyError(msg)
            opts[self.name] = self._default


class Options(PureOption, MutableSet[PureOption]):
    def __init__(self, name, default=None, required=False):
        super(Options, self).__init__(name, default, dict, required)
        self._children: MutableSet[PureOption] = set()

    def __contains__(self, opt: PureOption) -> bool:
        return opt in self._children

    def __iter__(self) -> Iterator[PureOption]:
        return iter(self._children)

    def __len__(self) -> int:
        return len(self._children)

    def add(self, opt: PureOption) -> None:
        self._children.add(opt)
        opt._parent = self

    def discard(self, opt: PureOption) -> None:
        self._children.discard(opt)
        opt._parent = None

    def parse_options(self, opts: MutableMapping[str, VT]):
        if self._parent:
            if self.name not in opts:
                if self._required:
                    raise KeyError(f"Missing required key '{self.name}' in '{self._parent.name}'")
                opts[self.name] = self._default
                return
            opts = opts[self.name]
        if not isinstance(opts, self._type):
            raise TypeError(f"'{self.name}' must be {self._type.__name__}, not {type(opts).__name__}")

        known_keys = frozenset(map(lambda e: e.name, self))
        for k in opts:
            if k not in known_keys:
                msg = f"Unknown key '{k}'"
                if self._parent:
                    msg += f" in '{self._parent.name}'"
                raise KeyError(msg)
        for opt in self:
            opt.parse_options(opts)
