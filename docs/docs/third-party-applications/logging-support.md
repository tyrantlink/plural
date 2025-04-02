# Adding Logging Support

This page is intended for developers who want to integrate with /plu/ral.

If you're a user looking to clean the logs of a bot that doesn't have native support, see the [Log Clean Config](/server-guide/config.md#log-clean) page.

#### Instructions
Checking if a message exists (`HEAD /messages/:channel_id/:message_id`) does not *require* authentication, however the unauthenticated rate limit is very low, so if your bot anything more than an in-house bot for a small server, you should create an application with the `/api` command.

You can check either the id of the message that was deleted OR the id of the proxied message.

See the [API Documentation](https://api.plural.gg) for all endpoints and response examples.

#### Basic Example
::: tabs
@tab cURL
```sh
curl -X HEAD 'https://api.plural.gg/messages/{message_id}' \
  -H 'Authorization: your_token_here'
```

@tab Python (aiohttp)
```sh
pip install aiohttp
```
```python
from aiohttp import ClientSession

async def check_plural(message_id: int | str) -> bool:
    async with ClientSession(
        base_url='https://api.plural.gg',
        headers={'Authorization': 'your_token_here'}
    ) as session, session.head(
        f'/messages/{message_id}'
    ) as response:
        return response.status == 200

async def on_message_delete(message: Message) -> None:
    if await check_plural(message.id):
        print(f'message {message.id} was deleted by /plu/ral; skipping')
        return
    ...
```
@tab Python (requests)
```sh
pip install requests
```
```python
# ! requests uses blocking i/o, use aiohttp instead
# ! this code is only here for demonstration purposes
import requests

def check_plural(message_id: int | str) -> bool:
    response = requests.get(
        f'https://api.plural.gg/messages/{message_id}',
        headers={'Authorization': 'your_token_here'}
    )

    return response.status_code == 200

async def on_message_delete(message: Message) -> None:
    if await check_plural(message.id):
        print(f'message {message.id} was deleted by /plu/ral; skipping')
        return
    ...
```
:::
