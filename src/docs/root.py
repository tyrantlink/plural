from src.docs.responses import response


get__root = {
    **response(
        status=200,
        description='success!',
        example={
            'message': 'this is very basic i\'ll work on it later',
            'version': '2.0.0'
        }
    )
}
