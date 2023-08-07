import enum


class NotSet(enum.Enum):
    "A type to include in a union where `None` is a valid value and needs to be differentiated from 'not present'."

    Value = 0
