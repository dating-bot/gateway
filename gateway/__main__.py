import asyncio

from gateway.app.server import server

if __name__ == "__main__":
    asyncio.run(server.main())
