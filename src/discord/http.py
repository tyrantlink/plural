from src.core.session import session
from src.models import project


BASE_URL = 'https://discord.com/api/v10'


async def _request(
    method: str,
    url: str,
    token: str | None = None,
    **kwargs
) -> dict | None:
    resp = await session.request(
        method,
        url,
        headers={
            'Authorization': f'Bot {token or project.bot_token}'
        }
    )

    try:
        return await resp.json()
    except Exception:
        return None
