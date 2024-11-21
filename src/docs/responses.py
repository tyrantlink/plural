from typing import Any


def json_response(
    status: int,
    description: str,
    examples: dict[str, Any]
) -> dict[str | int, dict]:
    """examples is a dictionary of example names and their values"""
    try:
        return {
            status:
            {
                'description': description,
                'content':
                {
                    'application/json':
                    {
                        'examples':
                        {
                            name:
                            {
                                'value': value
                            }
                            for name, value in examples.items()
                        }
                    }
                }
            }
        }
    except ValueError:
        print(examples)
        exit()


def file_response(
    status: int,
    description: str,
    content_types: list[str]
) -> dict[str | int, dict]:
    return {
        status:
        {
            'description': description,
            'content':
            {
                content_type:
                {
                    'schema':
                    {
                        'type': 'string',
                        'format': 'binary',
                        'example': 'binary file'
                    }
                }
                for content_type in content_types
            }
        }
    }
