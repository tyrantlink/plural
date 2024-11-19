from typing import TypeVar, Type, Optional
from beanie import Document
from pydantic import create_model, BaseModel
from pydantic import BaseModel
from typing import Any


# class BaseUpdateModel(BaseModel):
#     def to_update_dict(self, prefix: str = '') -> dict[str, Any]:
#         update_dict = {}
#         model_dump = self.model_dump(exclude_unset=True)

#         for field, value in model_dump.items():
#             field_path = f"{prefix}{field}" if prefix else field

#             if isinstance(value, BaseUpdateModel):
#                 nested_updates = value.to_update_dict(f"{field_path}.")
#                 update_dict.update(nested_updates)
#             elif value is not None:
#                 update_dict[field_path] = value

#         return update_dict


class Responses(BaseModel):
    class Example(BaseModel):
        title: str
        example: dict[str, Any] | str | bool

    status: int


T = TypeVar('T', bound=Document)


def excluded_model(
    original_model: Type[T],
    exclude_fields: list[str],
    responses: list[Responses] | None = None
) -> Type[BaseModel]:
    model = create_model(
        original_model.__name__,
        __config__=getattr(original_model, '__config__', None),
        __doc__=original_model.__doc__,
        __base__=None,
        __module__=__name__,
        __validators__=getattr(original_model, '__validators__', None),
        __cls_kwargs__=getattr(original_model, '__cls_kwargs__', None),
        **{
            field_name: (
                field_info.annotation, ... if field_info.is_required() else None)
            for field_name, field_info in original_model.model_fields.copy().items()
            if field_name not in exclude_fields
        }
    )
    return model


def patch_model(
    original_model: Type[T],
    include_fields: list[str]
) -> Type[BaseModel]:
    return create_model(
        original_model.__name__,
        __config__=getattr(original_model, '__config__', None),
        __doc__=original_model.__doc__,
        __base__=None,
        __module__=__name__,
        __validators__=getattr(original_model, '__validators__', None),
        __cls_kwargs__=getattr(original_model, '__cls_kwargs__', None),
        **{
            field_name: (Optional[field_info.annotation], None)
            for field_name, field_info in original_model.model_fields.copy().items()
            if field_name in include_fields
        }
    )
