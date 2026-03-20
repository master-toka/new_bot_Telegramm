import asyncio
from aiohttp_socks import ProxyConnector
import aiohttp

async def test_proxy():
    connector = ProxyConnector.from_url("socks5://147.125.130.70:2083")
    
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            async with session.get("https://api.telegram.org", timeout=10) as resp:
                print(f"Статус: {resp.status}")
                print(await resp.text())
        except Exception as e:
            print(f"Ошибка: {e}")

asyncio.run(test_proxy())
