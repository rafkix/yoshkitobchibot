# """Foydalanuvchi ma‘lumotlarini bazaga qo‘shish skripti.

# Ushbu skript quyidagi ma‘lumotlarni kirita oladi:
# - To‘liq ism (F.I.Sh.)
# - Tug‘ilgan sana
# - Yashash joyi (viloyat, tuman, mahalla)
# - Ish/ta‘lim joyi
# - Telefon raqami

# Ma‘lumotlar uzbek tilida kiritiladi.
# """
# import asyncio

# from database.database import session_maker, init_db
# from database.services.user_service import UserService
# from datetime import datetime

# # Example data – replace with actual values as needed
# USER_ID = 123456789  # Telegram user ID placeholder
# FULL_NAME = "Abdumutalibov Diyorbek Elmurod o‘g‘li"
# BIRTH_DATE_STR = "29.07.2006"  # DD.MM.YYYY format
# REGION = "Farg‘ona"
# DISTRICT = "Qo‘shtepa"
# NEIGHBORHOOD = "Xo‘jaqishloq"
# WORKPLACE = "Dasturchi"
# PHONE_NUMBER = "+998883298811"
# # Contest and direction can be left as None if not applicable
# CONTEST = None
# DIRECTION = None

# def parse_date(date_str: str):
#     return datetime.strptime(date_str, "%d.%m.%Y").date()

# async def main():
#     await init_db()
#     async with session_maker() as session:
#         user_service = UserService(session)
#         # Ensure the user exists (creates if missing)
#         await user_service.create_user(user_id=USER_ID)
#         # Complete registration with provided data
#         await user_service.complete_registration(
#             user_id=USER_ID,
#             full_name=FULL_NAME,
#             birth_date=parse_date(BIRTH_DATE_STR),
#             phone_number=PHONE_NUMBER,
#             region=REGION,
#             district=DISTRICT,
#             neighborhood=NEIGHBORHOOD,
#             workplace=WORKPLACE,
#             contest=CONTEST,
#             direction=DIRECTION,
#         )
#         print(f"Foydalanuvchi {USER_ID} muvaffaqiyatli qo‘shildi/yangi ma‘lumotlar kiritildi.")

# if __name__ == "__main__":
#     asyncio.run(main())
