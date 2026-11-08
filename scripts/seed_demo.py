import asyncio
from app.services.seed_service import seed_data

if __name__ == "__main__":
    asyncio.run(seed_data())
    print("[Seed] Seed data successfully populated.")
