from src.docs.responses import response, multi_file_response


get__image = {
    **multi_file_response(
        status=200,
        description='image found',
        content_types=['image/png', 'image/jpeg', 'image/gif', 'image/webp']
    ),
    **response(
        status=404,
        description='image not found',
        example={
            'detail': 'image not found'
        }
    )
}
