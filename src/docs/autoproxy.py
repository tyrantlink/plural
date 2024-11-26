from src.docs.responses import json_response


get__autoproxy = {
    **json_response(
        status=200,
        description='autoproxy found',
        examples={
            'guild autoproxy found': {
                'user': 250797109022818300,
                'guild': 1025541831506804900,
                'enabled': True,
                'fronting': True,
                'member': '670f500e8773629a1410d859'
            },
            'global autoproxy found': {
                'user': 250797109022818300,
                'guild': None,
                'enabled': False,
                'fronting': False,
                'member': None
            }
        }
    ),
    **json_response(
        status=404,
        description='autoproxy not found',
        examples={
            'autoproxy not found': {
                'detail': 'autoproxy not found'
            }
        }
    )
}


post__autoproxy = {
    **json_response(
        status=200,
        description='autoproxy found',
        examples={
            'guild autoproxy found': {
                'user': 250797109022818300,
                'guild': 1025541831506804900,
                'enabled': True,
                'fronting': True,
                'member': '670f500e8773629a1410d859'
            },
            'global autoproxy found': {
                'user': 250797109022818300,
                'guild': None,
                'enabled': False,
                'fronting': False,
                'member': None
            }
        }
    ),
    **json_response(
        status=404,
        description='autoproxy already exists',
        examples={
            'autoproxy already exists': {
                'detail': 'autoproxy already exists'
            }
        }
    )
}


put__autoproxy = {
    **json_response(
        status=200,
        description='autoproxy found',
        examples={
            'guild autoproxy found': {
                'user': 250797109022818300,
                'guild': 1025541831506804900,
                'enabled': True,
                'fronting': True,
                'member': '670f500e8773629a1410d859'
            },
            'global autoproxy found': {
                'user': 250797109022818300,
                'guild': None,
                'enabled': False,
                'fronting': False,
                'member': None
            }
        }
    )
}
