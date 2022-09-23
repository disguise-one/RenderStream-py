from ctypes import c_uint, Structure, Union
_CData = Structure.__base__ # private type, but needed to detect ctypes fields


class AnnotatedStructureType(type(Structure)):
    def __new__(cls, name, bases, namespace):
        annotations = namespace.get('__annotations__', {})
        if annotations:
            namespace["_fields_"] = [(name, declared_type) for name, declared_type in annotations.items() if issubclass(declared_type, _CData)]
        return type(Structure).__new__(cls, name, bases, namespace)


class AnnotatedStructure(Structure, metaclass=AnnotatedStructureType):
    pass


class AnnotatedUnionType(type(Union)):
    def __new__(cls, name, bases, namespace):
        annotations = namespace.get('__annotations__', {})
        if annotations:
            namespace["_fields_"] = [(name, declared_type) for name, declared_type in annotations.items() if issubclass(declared_type, _CData)]
        return type(Union).__new__(cls, name, bases, namespace)


class AnnotatedUnion(Union, metaclass=AnnotatedUnionType):
    pass


class EnumerationType(type(c_uint)):
    def __new__(metacls, name, bases, dict):
        _members_ = {}
        for key, value in dict.items():
            if not key.startswith("_") and isinstance(value, int):
                _members_[key] = value
        dict["_members_"] = _members_
        dict["_value_map"] = {}
        cls = type(c_uint).__new__(metacls, name, bases, dict)

        # Now the enum class is created, we can override the int
        # values with the enum instances instead.
        for key, value in dict['_members_'].items():
            cls._value_map[value] = key
            setattr(cls, key, cls(value))
        return cls

    def __contains__(self, value):
        return value in self._members_.values()

    def __repr__(self):
        return "<Enumeration %s>" % self.__name__


class Enumeration(c_uint, metaclass=EnumerationType):
    def __init__(self, value):
        c_uint.__init__(self, value)

    @classmethod
    def from_param(cls, param):
        if isinstance(param, Enumeration):
            if param.__class__ != cls:
                raise ValueError("Cannot mix enumeration members")
            else:
                return param
        else:
            return cls(param)

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.value == other.value

    def __repr__(self):
        return f"<{self.__class__.__name__} value {self.__class__._value_map[self.value]} ({self.value})>"
