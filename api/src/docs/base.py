from dataclasses import dataclass

from plural.missing import MISSING, Optional, is_not_missing


@dataclass
class Example:
    name: str
    value: dict
    mimetype: str = 'application/json'


def response(
    description: Optional[str] = MISSING,
    content: Optional[str] = MISSING,
    examples: Optional[list[Example]] = MISSING,
    model: Optional[type] = MISSING,
) -> dict:
    out = {}

    if is_not_missing(content) and is_not_missing(examples):
        raise ValueError('Cannot set both content and examples')

    if is_not_missing(description):
        out['description'] = description

    if is_not_missing(content):
        out['content'] = content

    if is_not_missing(model):
        out['model'] = model

    if is_not_missing(examples):
        out['content'] = {}

        for example in examples:
            if example.mimetype not in out['content']:
                out['content'][example.mimetype] = {
                    'examples': {}
                }

            out['content'
                ][example.mimetype
                  ]['examples'][
                example.name
            ] = {
                'value': example.value
            }

    return out
