class DataType: ...

class Field:
    name: str
    type: DataType

class Schema:
    names: list[str]
    def field(self, name: str) -> Field: ...

class _Types:
    def is_floating(self, data_type: DataType) -> bool: ...

types: _Types
