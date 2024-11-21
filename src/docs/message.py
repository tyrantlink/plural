from src.docs.responses import json_response


get__message = {
    **json_response(
        status=200,
        description='message found or only_check_existence = true',
        examples={
            'only_check_existence = false': {
                'original_id': 1309185110070923304,
                'proxy_id': 1309185113774489671,
                'author_id': 250797109022818305,
                'reason': 'matched from member proxy tags:\ntext--steve',
                'ts': '2024-10-13T03:19:08.984000'
            },
            'only_check_existence = true': True
        }
    ),
    **json_response(
        status=404,
        description='message not found',
        examples={
            'message not found': {
                'detail': 'message not found'
            }
        }
    )
}

post__message = {
    **json_response(
        status=200,
        description='message sent',
        examples={
            'message sent': {
                'original_id': None,
                'proxy_id': 1294861961028309093,
                'author_id': 250797109022818305,
                'ts': '2024-10-13T03:19:08.984000'
            }
        }
    ),
    **json_response(
        status=403,
        description='missing permissions',
        examples={
            'missing permissions': {
                'detail': 'you do not have permission to send messages to this channel\nif the server has auto moderation enabled, you must have the manage server permission, otherwise you must have the send messages and view channel permissions'
            }
        }
    ),
    **json_response(
        status=404,
        description='channel or proxy member not found',
        examples={
            'channel not found': {
                'detail': 'channel not found'
            },
            'member not found': {
                'detail': 'member not found'
            }
        }
    ),
    **json_response(
        status=500,
        description='failed to send message',
        examples={
            'failed to send message': {
                'detail': 'failed to send message'
            }
        }
    )
}
