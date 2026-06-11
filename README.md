# Multi-Brand Product Dashboard

Dashboard สำหรับสรุปข้อมูลสินค้าสาธารณะจาก:

- `us.strauss.com`
- `rhone.com`
- `arcteryx.com/us/en`

เทคโนโลยีที่ใช้:

- Python + FastAPI สำหรับ scraping, cache และ API
- React + Vite สำหรับ dashboard
- Recharts สำหรับ donut chart และ treemap

## ความสามารถ

- เลือกกรองข้อมูลตาม Brand/Website
- ดึงข้อมูลจาก Shopify collection JSON endpoint และ public catalog API
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

## Deploy บน Render

โปรเจกต์มี `render.yaml` สำหรับสร้าง FastAPI และ React เป็น Web Service เดียว:

1. Push โปรเจกต์ขึ้น GitHub
2. เปิด Render Dashboard และเลือก `New > Blueprint`
3. เชื่อมต่อ repository `PatcharaV/strauss-dashboard-nic`
4. ตรวจชื่อ service แล้วกด `Apply`

Render จะติดตั้ง Python dependencies และเปิด React production bundle ผ่าน URL
`https://strauss-dashboard-nic.onrender.com` หรือ URL ที่ Render กำหนดให้

ข้อมูลใน `backend/data/products.json` เป็นข้อมูลตั้งต้นล่าสุด ส่วนปุ่ม
`Scrape latest data` จะอัปเดต cache ของ instance ที่กำลังทำงานอยู่

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
