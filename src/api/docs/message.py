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
