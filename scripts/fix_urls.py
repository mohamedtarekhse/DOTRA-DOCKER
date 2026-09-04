"""Fix MINIO_PUBLIC_BASE URLs in the database."""
import asyncio
import asyncpg

async def fix():
    conn = await asyncpg.connect(
        host="postgres", database="acuseek",
        user="acuseek", password="acuseek_secret"
    )
    r = await conn.execute(
        "UPDATE image_store SET image_url = REPLACE(image_url, "
        "'http://192.168.10.50/minio', 'http://89.169.112.175/minio')"
    )
    print(f"Updated image_store: {r}")
    r2 = await conn.execute(
        "UPDATE face_embeddings SET sample_image_url = REPLACE(sample_image_url, "
        "'http://192.168.10.50/minio', 'http://89.169.112.175/minio') "
        "WHERE sample_image_url IS NOT NULL"
    )
    print(f"Updated face_embeddings: {r2}")
    await conn.close()

asyncio.run(fix())
