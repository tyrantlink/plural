from src.docs.responses import json_response
from src.version import VERSION


get__root = {
    **json_response(
        status=200,
        description='success!',
        examples={
            'success!': {
                'message': 'this is very basic i\'ll work on it later',
                'version': VERSION
            }
        }
    )
}
