import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def set_admin():
    engine = create_async_engine('postgresql+asyncpg://postgres:localdev@localhost:5433/auth_db')
    async with engine.begin() as conn:
        res = await conn.execute(text("UPDATE users SET is_admin=true, is_active=true WHERE username='gautam' OR email='gautamsachdeva201@gmail.com'"))
        print(f"Update rowcount: {res.rowcount}")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(set_admin())
