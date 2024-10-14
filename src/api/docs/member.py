from src.api.docs.responses import response


get__member = {
    **response(
        status=200,
        description='member found',
        example={
            'name': 'steve',
            'avatar': '67018b9074900a4cd323555c',
            'proxy_tags': [
                {
                    'prefix': 's;',
                    'suffix': '',
                    'regex': False
                },
                {
                    'prefix': '',
                    'suffix': '--steve',
                    'regex': False
                },
                {
                    'prefix': 'steve:',
                    'suffix': '',
                    'regex': False
                }
            ]
        }
    ),
    **response(
        status=404,
        description='member not found',
        example={
            'detail': 'member not found'
        }
    )
}

patch__member = {
    **response(
        status=200,
        description='member updated, returns updated member',
        example={
            'name': 'steve2',
            'avatar': '67018b9074900a4cd323555c',
            'proxy_tags': [
                {
                    'prefix': '',
                    'suffix': '--steve',
                    'regex': False
                }
            ]
        }
    ),
    **response(
        status=404,
        description='member not found',
        example={
            'detail': 'member not found'
        }
    ),
    **response(
        status=400,
        description='invalid field',
        example={
            'detail': 'invalid field: invalid_field'
        }
    )
}
