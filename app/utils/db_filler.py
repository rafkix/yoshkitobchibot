import asyncio
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.dialects.sqlite import insert

# o‘zingizning fayllaringizdan import qiling
from database.models import Base, Calendar 

# 1. Konfiguratsiya
DB_URL = "sqlite+aiosqlite:///users.db"
engine = create_async_engine(url=DB_URL)
async_session = async_sessionmaker(engine, expire_on_commit=False)

CITIES = [
    "toshkent", "andijon", "fargona", "samarqand", "qoqon", "gazli",
    "gijduvon", "qorakol", "guliston", "sardoba", "jizzax", "zomin",
    "forish", "gallaorol", "navoiy", "zarafshon", "konimex", "nurota",
    "uchquduq", "nukus", "moynoq", "taxtakopir", "tortkol", "qongirot",
    "margilon", "ishtixon", "mirbozor", "kattaqorgon", "urgut", "termiz",
    "boysun", "denov", "sherobod", "shorchi", "qarshi", "dehqonobod",
    "muborak", "shahrisabz", "guzor", "angren", "piskent", "bekobod",
    "buxoro", "xonobod", "shahrixon", "xojaobod", "namangan", "chortoq",
    "chust", "quva", "rishton", "parkent", "gazalkent", "sirdaryo",
    "boyovut", "paxtaobod", "jondor", "dostlik", "pop1", "uchqorgon",
    "bogdod", "oltiariq", "asaka", "marhamat", "paytug", "olmaliq",
    "boka", "yangiyol", "nurafshon", "urganch", "hazorasp", "xonqa",
    "yangibozor", "shovot", "xiva", "boston", "mingbuloq"
]

WEEKDAY_MAP = {
    "Du": "Dushanba", "Se": "Seshanba", "Ch": "Chorshanba",
    "Pa": "Payshanba", "Ju": "Juma", "Sha": "Shanba", "Ya": "Yakshanba"
}

async def scrape_city(city_slug: str):
    """Saytdan ma'lumotni scrape qilish"""
    url = f"https://namozvaqti.uz/ramazon/{city_slug}"
    headers = {"User-Agent": "Mozilla/5.0"}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=15.0)
            if response.status_code != 200: return None

            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table')
            if not table: return None

            rows = table.find_all('tr')[1:] # Headerdan keyingi qatorlar
            city_data = []
            
            for i, row in enumerate(rows, 1):
                cols = row.find_all('td')
                if len(cols) >= 5:
                    short_day = cols[1].text.strip()
                    city_data.append({
                        "city_slug": city_slug,
                        "day": i,
                        "weekday": WEEKDAY_MAP.get(short_day, short_day),
                        "date": cols[2].text.strip(),
                        "morning": cols[3].text.strip(),
                        "iftorlik": cols[4].text.strip()
                    })
            return city_data
        except Exception as e:
            print(f"\n🚨 Xato ({city_slug}): {e}")
            return None

async def main():
    # Jadvallarni yaratish
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("🌙 Ramazon 2026 ma'lumotlari bazaga yuklanmoqda...")

    async with async_session() as session:
        for city in CITIES:
            print(f"📡 {city.capitalize()} yuklanmoqda...", end="\r")
            data = await scrape_city(city)

            if data:
                for item in data:
                    # INSERT OR IGNORE mantiqi (UniqueConstraint asosida)
                    stmt = insert(Calendar).values(**item).on_conflict_do_nothing()
                    await session.execute(stmt)
                
                await session.commit()
                print(f"✅ {city.capitalize()} bazaga qo‘shildi!              ")
            
            await asyncio.sleep(0.3) # Sayt bloklamasligi uchun

    print("\n✨ Barcha ma'lumotlar muvaffaqiyatli saqlandi!")

if __name__ == "__main__":
    asyncio.run(main())