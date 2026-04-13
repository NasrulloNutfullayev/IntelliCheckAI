# IntelliCheck AI

`sqlite3` asosidagi yozma imtihon tizimi. O'qituvchi guruh, fan va savollarni yaratadi; o'quvchi login qiladi, o'z guruhiga mos fanni tanlaydi va o'sha fandagi savollardan bittasini random oladi.

## Hozirgi imkoniyatlar

- Login va logout sessiya bilan saqlanadi
- Sessiya frontendda saqlanib, qayta kirganda `me` orqali tiklanadi
- Ma'lumotlar `intellicheck.db` SQLite bazasida saqlanadi
- Har bir guruhga bir nechta fan, har bir fanga bir nechta savol biriktiriladi
- O'quvchi guruhiga mos fanlardan birini tanlaydi
- Savol aynan tanlangan fan havzasidan random tanlanadi
- Natijada AI copy risk foizi ko'rsatiladi
- Risk threshold oshsa tekshiruv to'xtab, AI dan ko'chirilgan deb belgilanadi
- O'qituvchi natijalarni guruh va fan bo'yicha filtrlab, har bir o'quvchi kesimida ko'radi
- Statistika uchun alohida reset endpoint bor

## Tuzilma

- `backend/` - FastAPI va SQLite logikasi
- `ai/` - semantic evaluator va AI-copy risk heuristikasi
- `frontend/` - React interfeys
- `docs/anti-cheat-plan.md` - keyingi anti-cheat roadmap

## Backend ishga tushirish

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Birinci ishga tushishda `intellicheck.db` avtomatik yaratiladi.

## Frontend ishga tushirish

```powershell
cd frontend
npm install
npm run dev
```

## Asosiy endpointlar

- `POST /login`
- `POST /logout`
- `GET /me`
- `GET /groups`
- `GET /student/subjects`
- `GET /questions/random?subject_id=...`
- `POST /submit-answer`
- `GET /teacher/dashboard`
- `POST /teacher/groups`
- `POST /teacher/subjects`
- `POST /teacher/questions`
- `POST /teacher/reset-statistics`

## Eslatma

Semantic baholash ichkarida Hugging Face modelidan foydalanishga tayyorlangan, lekin model/provider ma'lumoti end-user natija sahifasiga chiqarilmaydi.
