# Adding Logging Support

this page is for logging bot developers who want to add native support for /plu/ral to their bot. if you're a user looking to clean the logs of a bot that doesn't have native support, see the [logging compatibility](/server-guide/logging-compatibility) page.

#### Instructions
you must have a registered /plu/ral application (see [creating applications](/third-party-applications/creating-applications))

once you have your token, you can simply make a GET request to the `/messages/{message_id}`

see [the api reference](/third-party-applications/api-reference) for information on authentication, the response format, and query parameters

if you only want basic support, ignoring deleted messages, you can make a HEAD request instead of a GET request, which will return a response with no body, and a status code of 200 if the message exists, and 404 if it doesn't

by default, the api adds a delay of up to 10 seconds, to ensure the message is saved in the database, preventing false negatives.
you can use the `?max_wait={seconds}` query parameter to modify this delay, must be a float between 0.0 and 10.0
note that this delay means that any message that was *not* deleted by /plu/ral will take 10 seconds to respond, so if latency is a concern, consider lowering this delay, at cost of potential false negatives

#### Basic Example (just checking if a message exists)
::: tabs
@tab cURL
```sh
curl -X HEAD 'https://api.plural.gg/messages/{message_id}' \
    -H 'Authorization: Bot your_token_here'
```
@tab python (plural.py)
\*note: plural.py is currently in development, and may not be available yet
```sh
pip install plural.py
```
```python
from plural import Application

app = Application('your_token_here')

async def on_message_delete(message: Message) -> None:
    if await app.fetch_message(message.id, existence_only=True):
        print(f'message {message.id} was deleted by /plu/ral; skipping')
        return
    ...
```

@tab python (aiohttp)
```sh
pip install aiohttp
```
```python
from aiohttp import ClientSession

async def check_plural(message_id: int | str, max_wait: float = 10.0) -> bool:
    async with ClientSession(
        base_url='https://api.plural.gg',
        headers={'Authorization': f'Bot {your_token_here}'}
    ) as session:
        async with session.head(
            f'/messages/{message_id}',
            params={'max_wait': max_wait}
        ) as response:
            return response.status == 200

async def on_message_delete(message: Message) -> None:
    if await check_plural(message.id):
        print(f'message {message.id} was deleted by /plu/ral; skipping')
        return
    ...
```
@tab python (requests)
```sh
pip install requests
```
```python
# ! requests uses blocking i/o, use plural.py or aiohttp instead
# ! this code is only here for demonstration purposes
import requests

def check_plural(message_id: int | str, max_wait: float = 10.0) -> bool:
    response = requests.get(
        f'https://api.plural.gg/messages/{message_id}',
        headers={'Authorization': f'Bot {your_token_here}'},
        params={'max_wait': max_wait}
    )
    return response.status_code == 200

async def on_message_delete(message: Message) -> None:
    if await check_plural(message.id):
        print(f'message {message.id} was deleted by /plu/ral; skipping')
        return
    ...
```
:::

#### Full Example (getting the message data)
::: tabs
@tab cURL
```sh
curl 'https://api.plural.gg/messages/{message_id}' \
    -H 'Authorization: Bot your_token_here'
```
@tab python (plural.py)
\*note: plural.py is currently in development, and may not be available yet
```sh
pip install plural.py
```
```python
from plural import Application

app = Application('your_token_here')

async def on_message_delete(message: Message) -> None:
    plural_message = await app.fetch_message(message.id, with_member=True)
    print(plural_message) # Message object
    if plural_message is not None:
        print(f'message {message.id} was deleted by /plu/ral')
        # Message object has the following attributes:
        plural_message.original_id
        plural_message.proxy_id
        plural_message.author_id
        plural_message.channel_id
        plural_message.reason
        plural_message.timestamp
        # Message objects include a PartialMember object when `with_member` is True
        plural_message.member.id
        plural_message.member.name
        plural_message.member.avatar
    ...
```
@tab python (aiohttp)
```sh
pip install aiohttp
```
```python
from aiohttp import ClientSession

async def fetch_plural_message(message_id: int | str, max_wait: float = 10.0) -> dict | None:
    async with ClientSession(
        base_url='https://api.plural.gg',
        headers={'Authorization': f'Bot {your_token_here}'}
    ) as session:
        async with session.get(
            f'/messages/{message_id}',
            params={'max_wait': max_wait}
        ) as response:
            if response.status == 200:
                return await response.json()
            return None

async def on_message_delete(message: Message) -> None:
    plural_message = await fetch_plural_message(message.id)
    print(plural_message) # dict | None
    if plural_message is not None:
        print(f'message {message['id']} was deleted by /plu/ral')
    ...
```
@tab python (requests)
```sh
pip install requests
```
```python
# ! requests uses blocking i/o, use plural.py or aiohttp instead
# ! this code is only here for demonstration purposes
import requests

def fetch_plural_message(message_id: int | str, max_wait: float = 10.0) -> dict | None:
    response = requests.get(
        f'https://api.plural.gg/messages/{message_id}',
        headers={'Authorization': f'Bot {your_token_here}'},
        params={'max_wait': max_wait}
    )
    if response.status_code == 200:
        return response.json()
    return None

async def on_message_delete(message: Message) -> None:
    plural_message = await fetch_plural_message(message.id)
    print(plural_message) # dict | None
    if plural_message is not None:
        print(f'message {message['id']} was deleted by /plu/ral')
    ...
```