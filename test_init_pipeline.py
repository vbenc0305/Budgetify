import asyncio
import traceback
from importlib import import_module

async def main():
    try:
        mod = import_module("api.routes.transactions")
        print("Imported module api.routes.transactions")
        p = await mod._get_pipeline()
        print("Pipeline type:", type(p))
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

