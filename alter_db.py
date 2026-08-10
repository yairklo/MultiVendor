import asyncio
import aiomysql

async def alter_table():
    conn = await aiomysql.connect(host='127.0.0.1', port=3306,
                                  user='root', password='rootpassword',
                                  db='multivendor_dev', autocommit=True)
    async with conn.cursor() as cur:
        await cur.execute("ALTER TABLE orders MODIFY COLUMN status ENUM('pending', 'pending_payment', 'processing', 'completed', 'cancelled', 'expired') DEFAULT 'pending';")
    conn.close()

asyncio.run(alter_table())
