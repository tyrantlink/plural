### Adding Logging Support

this page is for logging bot developers who want to add native support for \*plu/ral\* to their bot. if you're a user looking to clean logs with a bot that doesn't have native support, see the [logging compatibility](/server-guide/logging-compatibility) page.

#### Instructions
you must have a registered /plu/ral application (see [creating applications](/third-party-applications/creating-applications))

once you have your token, you can simply make a GET request to the `/message/{message_id}`

see [the api reference](/third-party-applications/api-reference) for information on authentication, the response format, and query parameters

if you only want basic support, ignoring deleted messages, you can use the `?only_check_existence=true` query parameter, which will return a 204 status code if the message exists and a 404 status code if it doesn't

by default, the api adds a delay of up to 10 seconds, to ensure the message is saved in the database, preventing false negatives.
you can use the `?max_wait={seconds}` query parameter to modify this delay, must be a float between 0.0 and 10.0

#### Example
::: tabs
@tab cURL
```sh
curl -X GET 'https://api.plural.gg/message/{message_id}?only_check_existence=true' \
    -H 'Authorization: Bot your_token_here'
```
@tab python (aiohttp)
```python
from aiohttp import ClientSession

async def check_plural(message_id: int | str, max_wait: float = 10.0) -> bool:
    async with ClientSession(
        base_url='https://api.plural.gg',
        headers={'Authorization': f'Bot {your_token_here}'}
    ) as session:
        async with session.get(
            f'/message/{message_id}',
            params={'only_check_existence': True, 'max_wait': max_wait}
        ) as response:
            return response.status == 204
```
@tab python (requests)
```python
# ! requests uses blocking i/o, use aiohttp instead
# ! this code is only here for demonstration purposes
import requests

def check_plural(message_id: int | str, max_wait: float = 10.0) -> bool:
    response = requests.get(
        f'https://api.plural.gg/message/{message_id}',
        headers={'Authorization': f'Bot {your_token_here}'},
        params={'only_check_existence': True, 'max_wait': max_wait}
    )
    return response.status_code == 204
```