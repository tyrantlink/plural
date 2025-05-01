from dataclasses import dataclass

from plural.missing import MISSING, Optional, is_not_missing


@dataclass
class Example:
    name: str
    value: dict | list
    mimetype: str = 'application/json'
    summary: Optional[str] = MISSING
    description: Optional[str] = MISSING


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

            detail = {
                'value': example.value
            }

            if is_not_missing(example.summary):
                detail['summary'] = example.summary

            out['content'
                ][example.mimetype
                  ]['examples'][
                example.name
            ] = detail

    return out


def request(
    examples: list[Example]
) -> dict:
    return {
        example.name: {'value': example.value} |
        ({'summary': example.summary}
         if is_not_missing(example.summary) else {}) |
        ({'description': example.description}
         if is_not_missing(example.description) else {})
        for example in examples
    }
