import asyncio
from sqlalchemy import text
from app.core.database import engine

async def reset_logs():
    print("[*] DROPPING_TABLE: system_logs")
    async with engine.begin() as conn:
        # Drop dependent tables first if any, but SystemLog is primary here.
        # Cascade might be needed if foreign keys exist.
        await conn.execute(text("DROP TABLE IF EXISTS system_logs CASCADE;"))
        await conn.execute(text("DROP TABLE IF EXISTS anomaly_records CASCADE;"))
    print("[+] RESET_COMPLETE: Schema ready for autoincrement initialization.")

if __name__ == "__main__":
    asyncio.run(reset_logs())