from src.api.docs.responses import response, multi_response


get__member = {
    **response(
        status=200,
        description='member found',
        example={
            'id': '67018b8f74900a4cd3235558',
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
            'id': '67018b8f74900a4cd3235558',
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
    **multi_response(
        status=404,
        description='member or group not found',
        examples={
            'member not found': {
                'detail': 'member not found'
            },
            'group not found': {
                'detail': 'group not found'
            }
        }
    ),
    **multi_response(
        status=400,
        description='invalid field, member already exists, name with tag over character limit',
        examples={
            'invalid field': {
                'detail': 'invalid field: invalid_field'
            },
            'member already exists': {
                'detail': 'member steve already exists'
            },
            'name with tag over character limit': {
                'detail': 'name and group tag combined must be less than 80 characters (85/80)'
            }
        },
    )
}


delete__member = {
    **response(
        status=200,
        description='member deleted',
        example={
            'message': f'member steve of group default successfully deleted'
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
