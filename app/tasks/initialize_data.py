import asyncio

from app.core.elasticsearch import create_es_indexes, es_client
from app.tasks.fill_init_data import fill_init_data


async def main() -> None:
    try:
        await es_client.info()
        await create_es_indexes()
        await fill_init_data()
    finally:
        await es_client.close()


if __name__ == "__main__":
    asyncio.run(main())
