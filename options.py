from abc import ABC, abstractmethod
from typing import Any, MutableMapping, MutableSet, Iterator, Optional, TypeVar, Callable, Tuple, Union

TT = TypeVar('TT', type, Tuple[Union[type, Tuple[Any, ...]], ...])
VT = TypeVar('VT', int, float, str, dict, type(None))


class PureOption(ABC):
    def __init__(self, name: str, default: Any, type_: TT, required: bool):
        if not isinstance(name, str):
            raise TypeError(f"'name' must be str, not {type(name).__name__}")
        self._name = name
        self._default = default
        if not isinstance(type_, (type, tuple)):
            raise TypeError(f"'type_' must be type or tuple, not {type(type_).__name__}")
        self._type = type_ if isinstance(type_, tuple) else (type_,)
        if not len(self._type):
            raise ValueError(f"'type_' cannot be empty")
        if not isinstance(required, bool):
            raise TypeError(f"'required' must be bool, not {type(required).__name__}")
        self._required = required
        self._parent: Optional[PureOption] = None

    @property
    def name(self):
        return self._name

    @property
    def default(self):
        return self._default

    @property
    def type(self):
        return self._type

    @property
    def type_str(self):
        if len(self.type) == 1:
            return self.type[0].__name__
        return '(' + ', '.join(t.__name__ for t in self.type) + ')'

    @property
    def required(self):
        return self._required

    @property
    def parent(self):
        return self._parent

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        cls_name = type(self).__name__
        parent = self.parent.name if self.parent else None
        return f"{cls_name}(name={repr(self.name)}, default={repr(self.default)}, type={self.type_str}, " \
               f"required={self.required}, parent={repr(parent)})"

    @abstractmethod
    def parse_options(self, opts: MutableMapping[str, VT]):
        pass


class Option(PureOption):
    def __init__(self, name: str, default: Any = None, type: TT = str, required: bool = False,
                 validator: Callable[[str, Any], None] = None):
        super(Option, self).__init__(name, default, type, required)
        self._validator = validator

    def parse_options(self, opts: MutableMapping[str, VT]):
        if self.name in opts:
            value = opts[self.name]
            if not isinstance(value, self.type):
                raise TypeError(f"'{self.name}' must be {self.type_str}, not {type(value).__name__}")
            if self._validator:
                self._validator(self.name, value)
        else:
            if self.required:
                msg = f"Missing required key '{self.name}'"
                if self.parent:
                    msg += f" in '{self.parent.name}'"
                raise KeyError(msg)
            opts[self.name] = self.default


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
                if self.required:
                    raise KeyError(f"Missing required key '{self.name}' in '{self.parent.name}'")
                opts[self.name] = self.default
                return
            opts = opts[self.name]
        if not isinstance(opts, self.type):
            raise TypeError(f"'{self.name}' must be {self.type_str}, not {type(opts).__name__}")

        known_keys = frozenset(map(lambda e: e.name, self))
        for k in opts:
            if k not in known_keys:
                msg = f"Unknown key '{k}'"
                if self._parent:
                    msg += f" in '{self.parent.name}'"
                raise KeyError(msg)
        for opt in self:
            opt.parse_options(opts)
