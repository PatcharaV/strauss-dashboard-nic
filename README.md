# Strauss Product Dashboard

Dashboard สำหรับสรุปข้อมูลสินค้าสาธารณะจาก `us.strauss.com` โดยใช้:

- Python + FastAPI สำหรับ scraping, cache และ API
- React + Vite สำหรับ dashboard
- Recharts สำหรับ donut chart และ treemap

## ความสามารถ

- ดึงข้อมูลจาก Shopify collection JSON endpoint แบบแบ่งหน้า
- รวมสินค้าที่ซ้ำกันข้าม collection ด้วย canonical product handle
- อ้างอิง product card ที่แสดงจริงบนหน้า collection และรวมสีภายใต้สินค้าหลัก
- กรองตามกลุ่มสินค้า หมวดหมู่ และช่วงราคา
- เลือกเปิด/ปิด KPI, กราฟกลุ่มสินค้า, กราฟหมวดหมู่, treemap และตารางสินค้า
- แสดง Material และป้าย Top seller ในตารางสินค้า
- บันทึก cache ไว้ใน `backend/data/products.json`
- กด `Scrape latest data` เพื่ออัปเดตข้อมูลจากเว็บไซต์

## เริ่มใช้งาน

ต้องติดตั้ง Python 3.11+ และ Node.js 20+ ก่อน

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

### Frontend

เปิด PowerShell อีกหน้าต่าง:

```powershell
cd frontend
npm install
npm run dev
```

เปิด `http://localhost:5173`

หรือใช้ `start-dashboard.ps1` หลังจากติดตั้ง dependencies ครั้งแรกแล้ว

## API

- `GET /api/health`
- `GET /api/options`
- `GET /api/dashboard`
- `GET /api/products`
- `POST /api/scrape`

ตัวอย่าง filter:

```text
/api/dashboard?audiences=men,women&categories=Shirts,Pants&min_price=20&max_price=150
```

## หมายเหตุ

โปรเจกต์ใช้เฉพาะข้อมูลสินค้าสาธารณะและตรวจ `robots.txt` ก่อน scrape ทุกครั้ง มี delay ระหว่างหน้าและ cache เพื่อลดจำนวน request ควรตรวจ Terms of Service ของเว็บไซต์ก่อนนำไปใช้เชิงพาณิชย์หรือรันด้วยความถี่สูง
