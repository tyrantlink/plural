from inspect import getsource
from typing import Any

from fastapi.openapi.utils import get_openapi


def _patched_get_openapi() -> dict[str, Any]:
    new_source = getsource(get_openapi).replace(
        '    return jsonable_encoder(OpenAPI(**output), by_alias=True, exclude_none=True)',
        """
    value = jsonable_encoder(OpenAPI(**output), by_alias=True,
                             exclude_unset=True, exclude_none=False)  # type: ignore
    for endpoint in value['paths']:
        for method in value['paths'][endpoint]:
            for status_code in value['paths'][endpoint][method]['responses']:
                if value['paths'][endpoint][method]['responses'][status_code].get('content') == None:
                    value['paths'][endpoint][method]['responses'][status_code].pop(
                        'content', None)
    return value
        """
    )

    namespace = {}
    exec(new_source, get_openapi.__globals__, namespace)

    return namespace['get_openapi']


patched_get_openapi = _patched_get_openapi()


def patched_openapi(self) -> dict[str, Any]:  # noqa: ANN001
    if not self.openapi_schema:
        self.openapi_schema = patched_get_openapi(
            title=self.title,
            version=self.version,
            openapi_version=self.openapi_version,
            summary=self.summary,
            description=self.description,
            terms_of_service=self.terms_of_service,
            contact=self.contact,
            license_info=self.license_info,
            routes=self.routes,
            webhooks=self.webhooks.routes,
            tags=self.openapi_tags,
            servers=self.servers,
            separate_input_output_schemas=self.separate_input_output_schemas,
        )

    return self.openapi_schema
