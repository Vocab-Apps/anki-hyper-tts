import typing as t

import typing_extensions as te

from databind.core.converter import Converter, DelegateToClassmethodConverter
from databind.core.settings import ClassDecoratorSetting


class ConverterSupplier(te.Protocol):
    def __call__(self) -> Converter:
        ...


class JsonConverter(ClassDecoratorSetting):
    """Use this setting to decorate a class or to annotate a type hint to inform the JSON module to use the
    specified convert when deserialize the type instead of any converter that would otherwise match the type.

    Example:

    ```py
    from databind.json.settings import JsonConverter



    class MyCustomConverter(Converter):
        def __init__(self, direction: Direction) -> None:
            self.direction = direction
        def convert(self, ctx: Context) -> Any:
            ...

    @JsonConverter.using_classmethods(serialize="__str__", deserialize="of")
    class MyCustomType:

        def __str__(self) -> str:
            ...

        @staticmethod
        def of(s: str) -> MyCustomType:
            ...
    ```

    The same override can also be achieved by attaching the setting to an `Annotated` type hint:


    ```py
    Annotated[MyCustomType, JsonConverter(MyCustomConverter)]
    ```
    """

    supplier: ConverterSupplier

    def __init__(self, supplier: t.Union[ConverterSupplier, Converter]) -> None:
        super().__init__()
        if isinstance(supplier, Converter):
            self.supplier = lambda: supplier
        else:
            self.supplier = supplier

    @staticmethod
    def using_classmethods(
        serialized_type: t.Union[t.Type[t.Any], t.Tuple[t.Type[t.Any], ...], None] = None,
        *,
        serialize: "str | None" = None,
        deserialize: "str | None" = None
    ) -> "JsonConverter":
        return JsonConverter(
            DelegateToClassmethodConverter(serialized_type, serialize=serialize, deserialize=deserialize)
        )
