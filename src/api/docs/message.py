from .responses import response, multi_response


get__message = {
    **multi_response(
        status=200,
        description='image found',
        examples={
            'only check existence = false': {
                'original_id': 1294861959618891788,
                'proxy_id': 1294861961028309093,
                'author_id': 250797109022818305,
                'ts': '2024-10-13T03:19:08.984000'
            },
            'only check existence = true': True
        }
    ),
    **response(
        status=404,
        description='message not found',
        example={
            'detail': 'message not found'
        }
    )
}

post__message = {
    **response(
        status=200,
        description='message sent',
        example={
            'original_id': None,
            'proxy_id': 1294861961028309093,
            'author_id': 250797109022818305,
            'ts': '2024-10-13T03:19:08.984000'
        }
    ),
    **multi_response(
        status=404,
        description='webhook or member not found',
        examples={
            'member not found': {
                'detail': 'member not found'
            },
            'webhook not found': {
                'detail': 'webhook not found; make sure at least one message is sent via discord message before using the API'
            }
        }
    ),
    **response(
        status=400,
        description='invalid webhook url',
        example={
            'detail': 'invalid webhook url found, please send a message through the bot and try again'
        }
    )
}
