from src.docs.responses import response, multi_response


get__group = {
    **response(
        status=200,
        description='group found',
        example={
            'id': '67018b8f74900a4cd3235555',
            'name': 'test',
            'accounts': [
                250797109022818305
            ],
            'avatar': None,
            'channels': [],
            'tag': None,
            'members': [
                '67018b8f74900a4cd3235556'
            ]
        }
    ),
    **response(
        status=404,
        description='group not found',
        example={
            'detail': 'group not found'
        }
    )
}


get__groups = {
    **response(
        status=200,
        description='groups found',
        example=[
            {
                'id': '67018b8f74900a4cd3235555',
                'name': 'test',
                'accounts': [
                    250797109022818300
                ],
                'avatar': None,
                'channels': [],
                'tag': None,
                'members': [
                    '67018b8f74900a4cd3235556'
                ]
            },
            {
                'id': '67018b8f74900a4cd3235557',
                'name': 'default',
                'accounts': [
                    250797109022818300
                ],
                'avatar': None,
                'channels': [],
                'tag': None,
                'members': [
                    '67018b8f74900a4cd3235559',
                    '67018b8f74900a4cd3235558',
                    '6702ef294d6c1e6b0b903e00',
                    '67018b8f74900a4cd323555a'
                ]
            }
        ]
    )
}


patch__group = {
    **response(
        status=200,
        description='group updated, returns updated group',
        example={
            'id': '67018b8f74900a4cd3235555',
            'name': 'test2',
            'accounts': [
                250797109022818305
            ],
            'avatar': None,
            'channels': [],
            'tag': None,
            'members': [
                '67018b8f74900a4cd3235556'
            ]
        }
    ),
    **multi_response(
        status=400,
        description='group already exists or invalid field or tag with member name over character limit',
        examples={
            'group already exists': {
                'detail': 'group test2 already exists'
            },
            'invalid field': {
                'detail': 'invalid field'
            },
            'tag with member name over character limit': {
                'detail': f'member(s) steve, John, test3 have a name and tag combined that exceeds 80 characters'
            }
        }
    ),
    **multi_response(
        status=404,
        description='group or avatar not found',
        examples={
            'group not found': {
                'detail': 'group not found'
            },
            'avatar not found': {
                'detail': 'avatar not found'
            }
        }
    )
}


post__group = {
    **response(
        status=200,
        description='group created, returns created group',
        example={
            'id': '67018b8f74900a4cd3235555',
            'name': 'test',
            'accounts': [
                250797109022818305
            ],
            'avatar': None,
            'channels': [],
            'tag': None,
            'members': [
                '67018b8f74900a4cd3235556'
            ]
        }
    ),
    **response(
        status=400,
        description='group already exists',
        example={
            'detail': 'group test already exists'
        }
    )
}


delete__group = {
    **response(
        status=200,
        description='group deleted',
        example={
            'deleted_group': 'default',
            'deleted_members': [
                'steve',
                'John'
            ]
        }
    ),
    **response(
        status=400,
        description='group has members',
        example={
            'detail': 'group has members; please delete or move all members first, or set param delete_members to true'
        }
    ),
    **response(
        status=404,
        description='group not found',
        example={
            'detail': 'group not found'
        }
    )
}


get__group_members = {
    **response(
        status=200,
        description='group members found',
        example=[
            {
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
            },
            {
                'id': '67018b8f74900a4cd323555a',
                'name': 'John',
                'avatar': '67018b9074900a4cd323555d',
                'proxy_tags': [
                    {
                        'prefix': '',
                        'suffix': '--john',
                        'regex': False
                    },
                    {
                        'prefix': '',
                        'suffix': '--jm',
                        'regex': False
                    },
                    {
                        'prefix': 'j;',
                        'suffix': '',
                        'regex': False
                    }
                ]
            }
        ]
    ),
    **response(
        status=404,
        description='group not found',
        example={
            'detail': 'group not found'
        }
    )
}


get__group_member = {
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


post__group_member = {
    **response(
        status=200,
        description='member created, returns created member',
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
    **multi_response(
        status=400,
        description='member already exists or name and group tag combined must be less than 80 characters',
        examples={
            'member already exists': {
                'detail': 'member steve already exists'
            },
            'name and group tag combined must be less than 80 characters': {
                'detail': 'name and group tag combined must be less than 80 characters (81/80)'
            }
        }
    ),
    **response(
        status=404,
        description='group not found',
        example={
            'detail': 'group not found'
        }
    )
}
