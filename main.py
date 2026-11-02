from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime, date, timedelta
import hashlib
import os  # ВАЖНО ДЛЯ RENDER

# Настройка базы данных. Если на Render задана переменная DATABASE_URL, она будет использована.
# В противном случае (локально) создастся файл slotly.db в текущей папке.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./slotly.db")
SQLALCHEMY_DATABASE_URL = DATABASE_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

CITIES = [
    "Абакан", "Адлер", "Анапа", "Ангарск", "Армавир", "Архангельск", "Астрахань", "Ачинск",
    "Балаково", "Балашиха", "Барнаул", "Белгород", "Березники", "Бийск", "Благовещенск", "Брянск",
    "Великий Новгород", "Владимир", "Владикавказ", "Владивосток", "Волгоград", "Волжский", "Вологда", "Воронеж",
    "Грозный", "Дербент", "Дзержинск", "Евпатория", "Екатеринбург", "Елец", "Иваново", "Ижевск",
    "Иркутск", "Йошкар-Ола", "Казань", "Калининград", "Калуга", "Каменск-Уральский", "Петропавловск-Камчатский", "Канск",
    "Кемерово", "Кинешма", "Киров", "Кисловодск", "Коломна", "Комсомольск-на-Амуре", "Кострома", "Краснодар",
    "Красноярск", "Курган", "Курск", "Кызыл", "Липецк", "Люберцы", "Магнитогорск", "Махачкала",
    "Миасс", "Москва", "Мурманск", "Муром", "Набережные Челны", "Нальчик", "Находка", "Невинномысск",
    "Нефтекамск", "Нефтеюганск", "Нижнекамск", "Нижний Новгород", "Нижний Тагил", "Новороссийск", "Новосибирск", "Новочебоксарск",
    "Новошахтинск", "Новокузнецк", "Норильск", "Обнинск", "Омск", "Оренбург", "Орел", "Орск",
    "Пенза", "Пермь", "Петрозаводск", "Подольск", "Псков", "Пятигорск", "Ростов-на-Дону", "Рязань",
    "Салават", "Самара", "Санкт-Петербург", "Саранск", "Саратов", "Севастополь", "Серпухов", "Смоленск",
    "Сочи", "Ставрополь", "Старый Оскол", "Стерлитамак", "Сугрут", "Сыктывкар", "Таганрог", "Тамбов",
    "Тверь", "Тольятти", "Томск", "Тула", "Тюмень", "Улан-Удэ", "Ульяновск", "Уссурийск",
    "Уфа", "Хабаровск", "Чебоксары", "Челябинск", "Череповец", "Черкесск", "Чита", "Шахты",
    "Энгельс", "Южно-Сахалинск", "Якутск", "Ярославль"
]

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    slug = Column(String, unique=True)
    city = Column(String)
    is_admin = Column(Integer, default=0)
    is_active = Column(Integer, default=1) # Для блокировки
    plan = Column(String, default="FREE")  # Для тарифов
    work_start = Column(String, default="10:00")
    work_end = Column(String, default="18:00")
    break_start = Column(String, default="14:00")
    break_end = Column(String, default="15:00")
    slot_duration = Column(Integer, default=60)
    telegram_id = Column(String, default="")

class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    price = Column(Integer)

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    client_name = Column(String)
    client_phone = Column(String)
    client_email = Column(String)
    client_comment = Column(String)
    service_name = Column(String)
    price = Column(Integer)
    date = Column(String)
    time = Column(String)

class Waitlist(Base):
    __tablename__ = "waitlist"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    client_name = Column(String)
    client_phone = Column(String)
    date = Column(String)

class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    client_name = Column(String)
    rating = Column(Integer)
    text = Column(String)
    created_at = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d"))

class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id = Column(Integer, primary_key=True)
    sender_name = Column(String)
    sender_role = Column(String)
    message = Column(String)
    status = Column(String, default="open")
    created_at = Column(String, default=lambda: datetime.now().strftime("%d.%m.%Y %H:%M"))

Base.metadata.create_all(bind=engine)
app = FastAPI()

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def hash_pass(p): return hashlib.sha256(p.encode()).hexdigest()

def get_all_cities(db: Session):
    db_cities = [u.city for u in db.query(User).all() if u.city]
    return sorted(list(set(CITIES + db_cities)))

def init_admin():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@slotly.ru").first()
        if not admin:
            new_admin = User(name="Администратор", email="admin@slotly.ru", password=hash_pass("admin"), slug="admin", city="Москва", is_admin=1)
            db.add(new_admin)
            db.commit()
    finally:
        db.close()
init_admin()

def generate_slots(start_str, end_str, b_start_str, b_end_str, duration_mins):
    slots = []
    try:
        start_time = datetime.strptime(start_str, "%H:%M")
        end_time = datetime.strptime(end_str, "%H:%M")
        duration = int(duration_mins)
        b_start = datetime.strptime(b_start_str, "%H:%M") if b_start_str else None
        b_end = datetime.strptime(b_end_str, "%H:%M") if b_end_str else None
        
        current = start_time
        while current + timedelta(minutes=duration) <= end_time:
            slot_end = current + timedelta(minutes=duration)
            in_break = False
            if b_start and b_end:
                if (current >= b_start and current < b_end) or (slot_end > b_start and slot_end <= b_end):
                    in_break = True
            if not in_break:
                slots.append(current.strftime("%H:%M"))
            current += timedelta(minutes=duration)
    except Exception:
        pass 
    return slots

HTML_HEAD = '''
<!DOCTYPE html><html lang="ru" data-theme="light"><head><meta charset="UTF-8"><title>Slotly</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400&family=Inter:wght@300;400;500&display=swap" rel="stylesheet">
<style>
:root {
    --bg: #F7F5F0; --surface: #FFFFFF; --text: #1A1A1A; --text-muted: #666666;
    --border: #E5E0D8; --input-border: #D1CCC2; --btn-bg: #1A1A1A; --btn-text: #FFFFFF;
    --btn-hover-bg: #FFFFFF; --btn-hover-text: #1A1A1A; --qr-bg: #FFFFFF;
}
[data-theme="dark"] {
    --bg: #121212; --surface: #1A1A1A; --text: #F7F5F0; --text-muted: #999999;
    --border: #333333; --input-border: #444444; --btn-bg: #F7F5F0; --btn-text: #1A1A1A;
    --btn-hover-bg: #1A1A1A; --btn-hover-text: #F7F5F0; --qr-bg: #FFFFFF;
}
body { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); padding: 20px; margin: 0; font-weight: 300; transition: background 0.3s, color 0.3s; }
h1, h2, h3 { font-family: 'Cormorant Garamond', serif; font-weight: 400; margin-top: 0; letter-spacing: 0.02em; }
.box { max-width: 480px; margin: 80px auto; background: var(--surface); padding: 50px 40px; border: 1px solid var(--border); transition: background 0.3s, border-color 0.3s; }
input, select, button, textarea { width: 100%; padding: 16px; margin-bottom: 20px; background: transparent; border: none; border-bottom: 1px solid var(--input-border); color: var(--text); box-sizing: border-box; font-size: 15px; font-family: 'Inter', sans-serif; font-weight: 300; border-radius: 0; transition: border-color 0.3s; }
input:focus, select:focus, textarea:focus { outline: none; border-bottom-color: var(--text); }
select option { background: var(--surface); color: var(--text); }
button { background: var(--btn-bg); color: var(--btn-text); cursor: pointer; border: 1px solid var(--btn-bg); font-weight: 400; font-size: 13px; text-transform: uppercase; letter-spacing: 0.1em; transition: 0.3s; margin-top: 20px; padding: 18px; }
button:hover { background: var(--btn-hover-bg); color: var(--btn-hover-text); }
button:disabled { background: var(--border); color: var(--text-muted); border-color: var(--border); cursor: not-allowed; }
.nav { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 25px; margin-bottom: 50px; max-width: 1100px; margin-inline: auto; position: relative; z-index: 10; transition: border-color 0.3s; }
.nav h2 { font-family: 'Cormorant Garamond', serif; font-size: 28px; font-weight: 600; margin: 0; letter-spacing: 0.05em; color: var(--text); }
.nav a { font-size: 13px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text); text-decoration: none; margin-left: 20px; transition: color 0.3s; }
.nav a:hover { color: var(--text-muted); }
.theme-btn { background: transparent; border: 1px solid var(--border); color: var(--text); width: auto; padding: 8px 12px; margin: 0 0 0 20px; font-size: 14px; cursor: pointer; border-radius: 50%; width: 36px; height: 36px; display: inline-flex; align-items: center; justify-content: center; }
.theme-btn:hover { background: transparent; color: var(--text); border-color: var(--text); }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; max-width: 1000px; margin: 0 auto; }
.card { background: var(--surface); padding: 30px; border: 1px solid var(--border); margin-bottom: 20px; transition: background 0.3s, border-color 0.3s; }
a { color: var(--text); text-decoration: underline; text-underline-offset: 4px; }
.btn-red { background: var(--btn-bg); border-color: var(--btn-bg); color: var(--btn-text); } .btn-red:hover { background: #cc0000; border-color: #cc0000; color: white; }
.btn-green { background: var(--btn-bg); border-color: var(--btn-bg); color: var(--btn-text); } .btn-green:hover { background: #178a52; border-color: #178a52; color: white; }
.time-slots { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 30px; }
.time-slot { background: transparent; border: 1px solid var(--border); color: var(--text); text-align: center; padding: 15px; cursor: pointer; font-weight: 400; transition: 0.3s; }
.time-slot:hover { border-color: var(--text); }
.time-slot.active { background: var(--text); color: var(--bg); border-color: var(--text); }
.time-slot.disabled { opacity: 0.3; cursor: not-allowed; background: var(--bg); text-decoration: line-through; }
.link-box { background: var(--bg); padding: 20px; border: 1px solid var(--border); margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; transition: background 0.3s; }
.link-box span { font-family: monospace; font-size: 14px; word-break: break-all; }
.qr { background: var(--qr-bg); padding: 10px; border: 1px solid var(--border); display: inline-block; }
.market-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 30px; max-width: 1100px; margin: 0 auto; }
.master-card { background: var(--surface); border: 1px solid var(--border); text-align: center; transition: 0.3s; padding: 40px 30px; }
.master-card:hover { border-color: var(--text); transform: translateY(-5px); }
.master-avatar { width: 80px; height: 80px; background: var(--bg); border: 1px solid var(--border); border-radius: 50%; display: grid; place-items: center; font-size: 32px; font-family: 'Cormorant Garamond', serif; color: var(--text); margin: 0 auto 20px auto; transition: background 0.3s; }
.search-bar { max-width: 700px; margin: 0 auto 60px auto; display: flex; gap: 20px; }
.search-bar input, .search-bar select { margin: 0; flex: 1; border: 1px solid var(--border); padding: 16px; border-bottom: 1px solid var(--text); }
.schedule-form { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.stars { color: var(--text); font-size: 18px; letter-spacing: 2px; margin-bottom: 10px; }
.footer { text-align: center; padding: 60px 0 40px 0; color: var(--text-muted); font-size: 13px; border-top: 1px solid var(--border); margin-top: 80px; letter-spacing: 0.05em; transition: border-color 0.3s; }
.hero-section { text-align: center; margin: 100px 0 80px 0; }
.hero-section h1 { font-size: 72px; margin-bottom: 25px; line-height: 1.1; }
.hero-section p { color: var(--text-muted); font-size: 18px; max-width: 600px; margin: 0 auto; font-weight: 300; }
.services-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0; max-width: 1100px; margin: 0 auto 80px auto; border-top: 1px solid var(--border); border-left: 1px solid var(--border); transition: border-color 0.3s; }
.service-category { padding: 40px; border-right: 1px solid var(--border); border-bottom: 1px solid var(--border); transition: 0.3s; background: var(--surface); position: relative; }
.service-category:hover { background: var(--bg); }
.service-num { font-family: 'Cormorant Garamond', serif; font-size: 64px; font-weight: 300; color: var(--border); position: absolute; top: 20px; right: 30px; line-height: 1; }
.service-category h3 { margin-bottom: 15px; font-size: 24px; margin-top: 40px; color: var(--text); }
.service-category p { color: var(--text-muted); font-size: 14px; line-height: 1.6; margin: 0; position: relative; z-index: 2; }
.features-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 40px; max-width: 1100px; margin: 80px auto; text-align: center; }
.feature { padding: 20px; }
.feature h3 { font-size: 22px; margin-bottom: 15px; color: var(--text); }
.feature p { color: var(--text-muted); font-size: 15px; line-height: 1.6; }
.table { width: 100%; border-collapse: collapse; margin-top: 20px; }
.table th, .table td { padding: 16px; text-align: left; border-bottom: 1px solid var(--border); font-size: 14px; color: var(--text); }
.table th { font-family: 'Cormorant Garamond', serif; font-size: 18px; font-weight: 600; }

/* СТИЛИ ДЛЯ НОВОЙ АДМИНКИ */
.admin-layout { display: flex; min-height: 100vh; background: #121212; color: #F7F5F0; margin: -20px; }
.admin-sidebar { width: 260px; background: #1A1A1A; border-right: 1px solid #333; padding: 40px 20px; display: flex; flex-direction: column; }
.admin-sidebar h2 { color: #F7F5F0; font-family: 'Cormorant Garamond', serif; font-size: 28px; margin-bottom: 40px; letter-spacing: 0.1em; }
.admin-sidebar a { display: block; color: #999; text-decoration: none; padding: 15px; font-size: 14px; text-transform: uppercase; letter-spacing: 0.1em; border-bottom: 1px solid #2a2a2a; transition: 0.3s; }
.admin-sidebar a:hover, .admin-sidebar a.active { color: #F7F5F0; background: #2a2a2a; padding-left: 20px; }
.admin-main { flex: 1; padding: 50px; overflow-y: auto; background: #121212; }
.admin-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; border-bottom: 1px solid #333; padding-bottom: 20px; }
.admin-header h1 { font-size: 36px; color: #F7F5F0; margin: 0; }
.admin-card { background: #1A1A1A; border: 1px solid #333; padding: 30px; margin-bottom: 20px; }
.admin-card h3 { color: #F7F5F0; font-size: 24px; margin-bottom: 20px; }
.admin-table { width: 100%; border-collapse: collapse; }
.admin-table th, .admin-table td { padding: 15px; text-align: left; border-bottom: 1px solid #333; color: #F7F5F0; font-size: 14px; }
.admin-table th { color: #999; text-transform: uppercase; font-size: 12px; letter-spacing: 0.1em; }
.badge { padding: 5px 10px; border-radius: 4px; font-size: 11px; font-weight: 600; text-transform: uppercase; }
.badge-free { background: #333; color: #999; }
.badge-pro { background: #B8860B; color: #fff; }
.badge-active { background: #178a52; color: #fff; }
.badge-blocked { background: #cc0000; color: #fff; }
</style>
<script>
    (function() {
        const theme = localStorage.getItem('slotly-theme') || 'light';
        document.documentElement.setAttribute('data-theme', theme);
    })();
</script>
</head><body>
'''
HTML_TAIL = """
<script>
    function toggleTheme() {
        const html = document.documentElement;
        const current = html.getAttribute('data-theme');
        const next = current === 'light' ? 'dark' : 'light';
        html.setAttribute('data-theme', next);
        localStorage.setItem('slotly-theme', next);
        updateThemeBtn();
    }
    function updateThemeBtn() {
        const theme = document.documentElement.getAttribute('data-theme');
        const btns = document.querySelectorAll('.theme-btn');
        btns.forEach(b => b.innerText = theme === 'light' ? '☾' : '☀');
    }
    document.addEventListener('DOMContentLoaded', updateThemeBtn);
</script>
</body></html>
"""

def nav_bar(user_name=None, is_admin=False):
    admin_link = "<a href='/admin' style='color:#B8860B;'>Админка</a>" if is_admin else ""
    support_link = "<a href='/support'>Поддержка</a>"
    auth_links = f"<span style='margin-left:20px; color:var(--text-muted); font-size:13px;'>{user_name}</span><a href='/logout'>Выйти</a>" if user_name else "<a href='/my-bookings'>Мои записи</a><a href='/login'>Войти</a><a href='/register'>Регистрация</a>"
    theme_btn = "<button class='theme-btn' onclick='toggleTheme()'>☾</button>"
    return f"<div class='nav'><a href='/' style='text-decoration:none;'><h2>SLOTLY</h2></a><div>{admin_link}{support_link}{auth_links}{theme_btn}</div></div>"

def footer():
    return "<div class='footer'>© 2026 SLOTLY. Искусство управления временем.</div>"

# --- ГЛАВНАЯ ---
@app.get("/", response_class=HTMLResponse)
def index(request: Request, city: str = None, db: Session = Depends(get_db)):
    uid = request.cookies.get("uid")
    current_user = db.query(User).filter(User.id == int(uid)).first() if uid else None
    user_name = current_user.name if current_user else None
    is_admin = current_user.is_admin if current_user else False

    all_masters = db.query(User).filter(User.is_admin == 0, User.is_active == 1).all()
    masters = [m for m in all_masters if m.city == city] if city else all_masters
    total_bookings_count = db.query(Booking).count()

    masters_html = ""
    for m in masters:
        initial = m.name[0].upper() if m.name else "M"
        revs = db.query(Review).filter(Review.user_id == m.id).all()
        avg_rating = round(sum([r.rating for r in revs]) / len(revs), 1) if revs else 0
        rating_html = f"<div class='stars'>{'★' * int(avg_rating)}</div><p style='color:var(--text-muted); font-size:13px; margin-bottom:20px;'>{avg_rating} из 5 ({len(revs)} отзывов)</p>" if revs else "<p style='color:var(--text-muted); font-size:13px; margin-bottom:20px;'>Нет отзывов</p>"
        
        masters_html += f"""
        <div class='master-card'>
            <div class='master-avatar'>{initial}</div>
            <h3 style='font-size:26px; margin-bottom:5px;'>{m.name}</h3>
            <p style='color:var(--text-muted); font-size:13px; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:20px;'>📍 {m.city}</p>
            {rating_html}
            <a href='/m/{m.slug}' style='display:block; padding:16px; border:1px solid var(--text); text-decoration:none; text-transform:uppercase; letter-spacing:0.1em; font-size:12px; transition:0.3s; color:var(--text);' onmouseover="this.style.background='var(--text)';this.style.color='var(--bg)'" onmouseout="this.style.background='transparent';this.style.color='var(--text)'">Записаться</a>
        </div>
        """

    if city and not masters:
        masters_html = f"<div style='text-align:center; padding:60px; border:1px solid var(--border); grid-column:1/-1;'><h2 style='font-size:32px;'>В городе {city} пока нет мастеров</h2><p style='color:var(--text-muted);'>Станьте первым, кто присоединится к платформе.</p></div>"

    all_cities = get_all_cities(db)
    city_options = "".join([f"<option value='{c}' {'selected' if c == city else ''}>{c}</option>" for c in all_cities])

    return HTML_HEAD + nav_bar(user_name, is_admin) + f"""
    <div class='hero-section'>
        <h1>Искусство <br>управления временем</h1>
        <p>Премиальная платформа онлайн-записи для мастеров красоты. Минимализм, удобство и безупречный сервис.</p>
    </div>

    <form method='GET' action='/' class='search-bar'>
        <select name='city'><option value=''>Выберите город</option>{city_options}</select>
        <button type='submit' style='width:180px;'>Найти</button>
    </form>

    <div class='market-grid'>{masters_html}</div>

    <div style='text-align:center; margin: 100px 0 60px 0;'>
        <h2 style='font-size: 48px;'>Сферы экспертизы</h2>
        <p style='color: var(--text-muted); font-size: 16px;'>Мы работаем только с профессионалами индустрии красоты</p>
    </div>
    <div class='services-grid'>
        <div class='service-category'><div class='service-num'>01</div><h3>Маникюр и педикюр</h3><p>Классический, аппаратный, гель-лак, дизайн, укрепление и наращивание ногтей.</p></div>
        <div class='service-category'><div class='service-num'>02</div><h3>Наращивание ресниц</h3><p>Классическое наращивание, 2D/3D/5D объемы, ламинирование, ботокс и окрашивание.</p></div>
        <div class='service-category'><div class='service-num'>03</div><h3>Оформление бровей</h3><p>Коррекция и окрашивание, долговременная укладка, ламинирование, ботокс бровей.</p></div>
        <div class='service-category'><div class='service-num'>04</div><h3>Парикмахерские услуги</h3><p>Женские и мужские стрижки, укладка, окрашивание, уход и восстановление волос.</p></div>
        <div class='service-category'><div class='service-num'>05</div><h3>Косметология</h3><p>Чистки лица, пилинги, уходовые процедуры, массаж лица и инъекции красоты.</p></div>
        <div class='service-category'><div class='service-num'>06</div><h3>Макияж и образ</h3><p>Дневной и вечерний макияж, свадебный образ, прическа и сборы под ключ.</p></div>
    </div>

    <div class='features-grid'>
        <div class='feature'><h3>Скорость</h3><p>Клиенту не нужно ждать ответа. Выбрал время и записался за 30 секунд.</p></div>
        <div class='feature'><h3>Эстетика</h3><p>Сайт отлично выглядит на любых устройствах, создавая премиум-впечатление.</p></div>
        <div class='feature'><h3>Надежность</h3><p>Умный лист ожидания заполнит освободившееся время без вашего участия.</p></div>
    </div>

    <div style='text-align:center; margin-top:80px; border-top:1px solid var(--border); padding-top:60px;'>
        <h2 style='font-size:32px;'>Присоединяйтесь к сообществу</h2>
        <p style='color:var(--text-muted); font-size:18px;'>{len(all_masters)} мастеров и {total_bookings_count} довольных клиентов</p>
    </div>
    """ + footer() + HTML_TAIL

# --- НОВАЯ АДМИНКА ---
@app.get("/admin", response_class=HTMLResponse)
def admin_panel(request: Request, tab: str = "dashboard", db: Session = Depends(get_db)):
    uid = request.cookies.get("uid")
    if not uid: return RedirectResponse("/login")
    u = db.query(User).filter(User.id == int(uid)).first()
    if not u or not u.is_admin: return RedirectResponse("/app")

    masters = db.query(User).filter(User.is_admin == 0).all()
    total_bookings = db.query(Booking).count()
    total_money = sum([b.price for b in db.query(Booking).all()])
    tickets = db.query(SupportTicket).order_by(SupportTicket.id.desc()).all()

    sidebar = f"""
    <div class='admin-sidebar'>
        <h2>SLOTLY ADMIN</h2>
        <a href='/admin?tab=dashboard' class="{'active' if tab=='dashboard' else ''}">Обзор</a>
        <a href='/admin?tab=masters' class="{'active' if tab=='masters' else ''}">Мастера</a>
        <a href='/admin?tab=tickets' class="{'active' if tab=='tickets' else ''}">Обращения ({len([t for t in tickets if t.status=='open'])})</a>
        <div style='margin-top:auto;'>
            <a href='/'>← На сайт</a>
            <a href='/logout' style='color:#cc0000;'>Выйти</a>
        </div>
    </div>
    """

    content = ""
    if tab == "dashboard":
        content = f"""
        <div class='admin-header'><h1>Обзор платформы</h1></div>
        <div style='display:grid; grid-template-columns: repeat(4, 1fr); gap:20px; margin-bottom:40px;'>
            <div class='admin-card' style='text-align:center;'><h3 style='font-size:40px; margin:0; color:#F7F5F0;'>{len(masters)}</h3><p style='color:#999; font-size:12px; text-transform:uppercase; letter-spacing:0.1em;'>Мастеров</p></div>
            <div class='admin-card' style='text-align:center;'><h3 style='font-size:40px; margin:0; color:#F7F5F0;'>{total_bookings}</h3><p style='color:#999; font-size:12px; text-transform:uppercase; letter-spacing:0.1em;'>Записей</p></div>
            <div class='admin-card' style='text-align:center;'><h3 style='font-size:40px; margin:0; color:#F7F5F0;'>{total_money} ₽</h3><p style='color:#999; font-size:12px; text-transform:uppercase; letter-spacing:0.1em;'>Оборот</p></div>
            <div class='admin-card' style='text-align:center;'><h3 style='font-size:40px; margin:0; color:#F7F5F0;'>{len([t for t in tickets if t.status=='open'])}</h3><p style='color:#999; font-size:12px; text-transform:uppercase; letter-spacing:0.1em;'>Тикетов</p></div>
        </div>
        <div class='admin-card'>
            <h3>Последние записи на платформе</h3>
            <table class='admin-table'>
                <tr><th>Клиент</th><th>Мастер</th><th>Услуга</th><th>Дата</th><th>Сумма</th></tr>
                {''.join([f"<tr><td>{b.client_name}</td><td>{db.query(User).get(b.user_id).name}</td><td>{b.service_name}</td><td>{b.date} {b.time}</td><td>{b.price} ₽</td></tr>" for b in db.query(Booking).order_by(Booking.id.desc()).limit(10).all()]) or '<tr><td colspan="5">Нет записей</td></tr>'}
            </table>
        </div>
        """
    elif tab == "masters":
        masters_html = ""
        for m in masters:
            m_bookings = db.query(Booking).filter(Booking.user_id == m.id).count()
            status_badge = "<span class='badge badge-active'>Активен</span>" if m.is_active else "<span class='badge badge-blocked'>Заблокирован</span>"
            plan_badge = f"<span class='badge badge-pro'>PRO</span>" if m.plan == "PRO" else "<span class='badge badge-free'>FREE</span>"
            
            block_btn = f"<form method='POST' action='/admin/toggle-block/{m.id}' style='display:inline;'><button style='padding:8px 12px; margin:0; font-size:10px; width:auto; background:{'#cc0000' if m.is_active else '#178a52'}; border-color:{'#cc0000' if m.is_active else '#178a52'};'>{'Заблокировать' if m.is_active else 'Разблокировать'}</button></form>"
            pro_btn = f"<form method='POST' action='/admin/make-pro/{m.id}' style='display:inline;'><button style='padding:8px 12px; margin:0; font-size:10px; width:auto; background:#B8860B; border-color:#B8860B;'>Сделать PRO</button></form>" if m.plan == "FREE" else ""

            masters_html += f"<tr><td><b>{m.name}</b></td><td>{m.city}</td><td>{m.email}</td><td><a href='/m/{m.slug}' target='_blank' style='color:#3b82f6;'>/m/{m.slug}</a></td><td>{plan_badge}</td><td>{m_bookings}</td><td>{status_badge}</td><td style='display:flex; gap:5px;'>{pro_btn} {block_btn}</td></tr>"

        content = f"""
        <div class='admin-header'><h1>Управление мастерами</h1></div>
        <div class='admin-card'>
            <table class='admin-table'>
                <tr><th>Имя</th><th>Город</th><th>Email</th><th>Ссылка</th><th>Тариф</th><th>Записей</th><th>Статус</th><th>Действия</th></tr>
                {masters_html or '<tr><td colspan="8">Нет мастеров</td></tr>'}
            </table>
        </div>
        """
    elif tab == "tickets":
        tickets_html = ""
        for t in tickets:
            status_color = "#178a52" if t.status == "resolved" else "#B8860B"
            btn = f"<form method='POST' action='/admin/resolve/{t.id}' style='margin-top:10px;'><button class='btn-green' style='padding:8px 15px; margin:0; font-size:10px; width:auto;'>Пометить решённым</button></form>" if t.status == "open" else ""
            tickets_html += f"""
            <div class='admin-card' style='border-left: 4px solid {status_color};'>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <h3 style='margin:0; font-size:20px;'>{t.sender_name} <span style='font-size:12px; color:#999; font-weight:normal;'>/{t.sender_role}</span></h3>
                    <span style='color:{status_color}; font-size:12px; letter-spacing:0.1em;'>{t.status.upper()}</span>
                </div>
                <p style='color:#999; font-size:12px; margin:5px 0 15px 0;'>{t.created_at}</p>
                <p style='font-size:15px; margin-bottom:15px;'>{t.message}</p>
                {btn}
            </div>
            """
        content = f"""
        <div class='admin-header'><h1>Обращения в поддержку</h1></div>
        {tickets_html or '<p style="color:#999;">Нет обращений</p>'}
        """

    return HTML_HEAD + f"""
    <div class='admin-layout'>
        {sidebar}
        <div class='admin-main'>
            {content}
        </div>
    </div>
    """ + HTML_TAIL

# --- ДЕЙСТВИЯ АДМИНА ---
@app.post("/admin/toggle-block/{user_id}")
def admin_toggle_block(user_id: int, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if u:
        u.is_active = 0 if u.is_active else 1
        db.commit()
    return RedirectResponse("/admin?tab=masters", status_code=303)

@app.post("/admin/make-pro/{user_id}")
def admin_make_pro(user_id: int, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if u:
        u.plan = "PRO"
        db.commit()
    return RedirectResponse("/admin?tab=masters", status_code=303)

@app.post("/admin/resolve/{ticket_id}")
def resolve_ticket(ticket_id: int, db: Session = Depends(get_db)):
    t = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if t: t.status = "resolved"; db.commit()
    return RedirectResponse("/admin?tab=tickets", status_code=303)

# --- ОСТАЛЬНЫЕ РОУТЫ ---
@app.get("/support", response_class=HTMLResponse)
def support_page(request: Request):
    return HTML_HEAD + nav_bar() + f"""
    <div class='box'>
        <h2 style='text-align:center; font-size:32px;'>Служба поддержки</h2>
        <p style='text-align:center; color:var(--text-muted); margin-bottom:30px;'>Опишите вашу проблему, и мы обязательно поможем.</p>
        <form method='POST' action='/support'>
            <input name='sender_name' placeholder='Ваше имя' required>
            <select name='sender_role'><option value='Клиент'>Я клиент</option><option value='Мастер'>Я мастер</option></select>
            <textarea name='message' placeholder='Опишите вашу проблему...' rows='4' required></textarea>
            <button type='submit'>Отправить</button>
        </form>
    </div>
    """ + footer() + HTML_TAIL

@app.post("/support")
def support_submit(sender_name: str = Form(...), sender_role: str = Form(...), message: str = Form(...), db: Session = Depends(get_db)):
    db.add(SupportTicket(sender_name=sender_name, sender_role=sender_role, message=message))
    db.commit()
    return HTML_HEAD + nav_bar() + f"""
    <div class='box' style='text-align:center'>
        <h2 style='font-size:32px;'>Сообщение отправлено</h2>
        <p style='color:var(--text-muted);'>Администратор свяжется с вами в ближайшее время.</p>
        <a href='/' style='display:block; margin-top:30px; padding:16px; border:1px solid var(--text); text-decoration:none; text-transform:uppercase; letter-spacing:0.1em; font-size:12px;'>Вернуться</a>
    </div>
    """ + footer() + HTML_TAIL

@app.get("/my-bookings", response_class=HTMLResponse)
def client_bookings_get(request: Request):
    return HTML_HEAD + nav_bar() + f"""
    <div class='box'>
        <h2 style='text-align:center; font-size:32px;'>Мои записи</h2>
        <p style='text-align:center; color:var(--text-muted); margin-bottom:30px;'>Введите номер телефона, чтобы найти ваши визиты.</p>
        <form method='POST' action='/my-bookings'><input name='phone' type='tel' placeholder='+7 (999) 123-45-67' required pattern='[\+0-9\s\-\(\)]+'><button type='submit'>Найти</button></form>
    </div>
    """ + footer() + HTML_TAIL

@app.post("/my-bookings", response_class=HTMLResponse)
def client_bookings_post(request: Request, phone: str = Form(...), db: Session = Depends(get_db)):
    clean_phone = ''.join(filter(str.isdigit, phone))
    all_bookings = db.query(Booking).all()
    my_bookings = [b for b in all_bookings if clean_phone in ''.join(filter(str.isdigit, b.client_phone))]

    if not my_bookings:
        return HTML_HEAD + nav_bar() + f"""<div class='box' style='text-align:center'><h2 style='font-size:32px;'>Записей не найдено</h2><p style='color:var(--text-muted);'>На номер {phone} нет активных визитов.</p><a href='/my-bookings' style='display:block; margin-top:30px; padding:16px; border:1px solid var(--text); text-decoration:none; text-transform:uppercase; letter-spacing:0.1em; font-size:12px;'>Попробовать снова</a></div>""" + footer() + HTML_TAIL

    bookings_html = ""
    for b in my_bookings:
        master = db.query(User).filter(User.id == b.user_id).first()
        d = datetime.strptime(b.date, '%Y-%m-%d').strftime('%d.%m.%Y')
        bookings_html += f"""<div class='card' style='display:flex; justify-content:space-between; align-items:center;'><div><h3 style='margin-bottom:5px;'>{b.service_name}</h3><span style='color:var(--text-muted); font-size:13px; text-transform:uppercase;'>Мастер: {master.name}</span><br><span style='color:var(--text); font-size:14px; font-weight:500;'>{d} в {b.time}</span></div><form method='POST' action='/client-cancel/{b.id}'><button class='btn-red' style='padding:10px 15px; margin:0; font-size:10px;'>Отменить</button></form></div>"""
    return HTML_HEAD + nav_bar() + f"""<div class='box' style='max-width:600px;'><h2 style='text-align:center; font-size:32px;'>Ваши визиты</h2>{bookings_html}<a href='/' style='display:block; text-align:center; margin-top:30px; font-size:13px; text-transform:uppercase; letter-spacing:0.1em;'>На главную</a></div>""" + footer() + HTML_TAIL

@app.post("/client-cancel/{booking_id}")
def client_cancel(booking_id: int, db: Session = Depends(get_db)):
    b = db.query(Booking).filter(Booking.id == booking_id).first()
    if b: db.delete(b); db.commit()
    return RedirectResponse("/my-bookings", status_code=303)

@app.get("/register", response_class=HTMLResponse)
def reg_page(db: Session = Depends(get_db)):
    all_cities = get_all_cities(db)
    city_options = "".join([f"<option value='{c}'>" for c in all_cities])
    return HTML_HEAD + f"""<div class='box'><h2 style='font-size:32px;'>Регистрация</h2><form method='POST' action='/register'><input name='name' placeholder='Ваше имя' required><input name='city' list='city-list' placeholder='Ваш город' required><datalist id='city-list'>{city_options}</datalist><input name='email' type='email' placeholder='Email' required><input name='slug' placeholder='Ссылка (например, anna)' required pattern='[a-z0-9-]+'><input name='password' type='password' placeholder='Пароль' required><button type='submit'>Создать аккаунт</button></form><p style='text-align:center; margin-top:30px; font-size:13px;'><a href='/'>На главную</a></p></div>""" + footer() + HTML_TAIL

@app.post("/register")
def reg(name: str = Form(...), city: str = Form(...), email: str = Form(...), slug: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    if db.query(User).filter((User.email == email) | (User.slug == slug)).first():
        return RedirectResponse("/register?error=1", status_code=303)
    u = User(name=name, city=city, email=email, slug=slug, password=hash_pass(password), is_admin=0)
    db.add(u); db.commit()
    resp = RedirectResponse("/app", status_code=303)
    resp.set_cookie("uid", str(u.id))
    return resp

@app.get("/login", response_class=HTMLResponse)
def login_page():
    return HTML_HEAD + """<div class='box'><h2 style='font-size:32px;'>Вход</h2><form method='POST' action='/login'><input name='email' placeholder='Email' required><input name='password' type='password' placeholder='Пароль' required><button type='submit'>Войти</button></form><p style='text-align:center; margin-top:30px; font-size:13px;'><a href='/'>На главную</a></p></div>""" + footer() + HTML_TAIL

@app.post("/login")
def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.email == email, User.password == hash_pass(password)).first()
    if not u: return RedirectResponse("/login?error=1", status_code=303)
    if not u.is_active: return RedirectResponse("/login?error=blocked", status_code=303) # Проверка на блокировку
    resp = RedirectResponse("/admin" if u.is_admin else "/app", status_code=303)
    resp.set_cookie("uid", str(u.id))
    return resp

@app.get("/logout")
def logout():
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie("uid")
    return resp

@app.post("/update-slug")
def update_slug(request: Request, new_slug: str = Form(...), db: Session = Depends(get_db)):
    uid = request.cookies.get("uid")
    u = db.query(User).filter(User.id == int(uid)).first()
    if db.query(User).filter(User.slug == new_slug, User.id != u.id).first():
        return RedirectResponse("/app?error=slug_taken", status_code=303)
    u.slug = new_slug
    db.commit()
    return RedirectResponse("/app?success=slug_updated", status_code=303)

@app.post("/update-schedule")
def update_schedule(request: Request, work_start: str = Form(...), work_end: str = Form(...), break_start: str = Form(None), break_end: str = Form(None), slot_duration: int = Form(...), telegram_id: str = Form(None), db: Session = Depends(get_db)):
    uid = request.cookies.get("uid")
    u = db.query(User).filter(User.id == int(uid)).first()
    u.work_start = work_start; u.work_end = work_end; u.break_start = break_start; u.break_end = break_end; u.slot_duration = slot_duration; u.telegram_id = telegram_id or ""
    db.commit()
    return RedirectResponse("/app?success=schedule_updated", status_code=303)

@app.get("/app", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    uid = request.cookies.get("uid")
    if not uid: return RedirectResponse("/login")
    u = db.query(User).filter(User.id == int(uid)).first()
    if u.is_admin: return RedirectResponse("/admin")
    
    services = db.query(Service).filter(Service.user_id == u.id).all()
    bookings = db.query(Booking).filter(Booking.user_id == u.id).order_by(Booking.date).all()
    waitlist = db.query(Waitlist).filter(Waitlist.user_id == u.id).all()
    reviews = db.query(Review).filter(Review.user_id == u.id).order_by(Review.id.desc()).all()

    total_revenue = sum([b.price for b in bookings])
    serv_html = "".join([f"<div class='card' style='padding:20px;'><b style='font-size:18px;'>{s.name}</b><br><span style='color:var(--text); font-weight:500;'>{s.price} ₽</span></div>" for s in services])
    
    book_html = ""
    for b in bookings:
        d = datetime.strptime(b.date, '%Y-%m-%d').strftime('%d.%m')
        comment_html = f"<br><span style='color:#B8860B; font-size:12px; font-style:italic;'>«{b.client_comment}»</span>" if b.client_comment else ""
        book_html += f"""<div class='card' style='display:flex; justify-content:space-between; align-items:center; padding:20px;'><div><b style='font-size:18px;'>{b.client_name}</b><br><span style='color:var(--text-muted); font-size:13px;'>{b.client_phone}</span> • <span style='color:var(--text-muted); font-size:12px;'>{b.client_email}</span><br><span style='color:var(--text); font-size:13px;'>{b.service_name} • {d} в {b.time}</span>{comment_html}</div><form method='POST' action='/cancel-booking/{b.id}'><button class='btn-red' style='padding:8px 12px; margin:0; font-size:10px;'>Отменить</button></form></div>"""

    wait_html = "".join([f"<div class='card' style='border-left: 3px solid #B8860B; padding:20px;'><b style='font-size:18px;'>{w.client_name}</b> ждет на {w.date}<br><span style='color:var(--text-muted); font-size:13px;'>{w.client_phone}</span></div>" for w in waitlist])
    reviews_html = "".join([f"<div class='card' style='padding:20px;'><div class='stars'>{'★' * r.rating + '☆' * (5 - r.rating)}</div><b style='font-size:18px;'>{r.client_name}</b><br><span style='color:var(--text-muted); font-size:14px;'>{r.text}</span></div>" for r in reviews]) or "<p style='color:var(--text-muted)'>Пока нет отзывов</p>"

    # ИСПРАВЛЕНИЕ ССЫЛКИ ДЛЯ RENDER:
    base_url = str(request.base_url).rstrip('/')
    full_link = f"{base_url}/m/{u.slug}"
    
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=120x120&data={full_link}"
    link_widget = f"""<div style='margin-top:30px; padding:30px; border:1px solid var(--border);'><h3 style='margin-top:0;'>Ваша персональная ссылка</h3><div class='link-box'><span>{full_link}</span><button onclick="navigator.clipboard.writeText('{full_link}'); alert('Ссылка скопирована!')" style='width:auto; padding:10px 15px; margin:0; font-size:10px;'>Копировать</button></div><div style='display:flex; gap:20px; align-items:center;'><div class='qr'><img src='{qr_url}' width='100' height='100'></div><div><p style='color:var(--text-muted); font-size:13px; margin:0;'>Покажите этот QR-код клиенту для мгновенной записи.</p></div></div><details style='margin-top:20px;'><summary style='cursor:pointer; font-size:13px; text-transform:uppercase; letter-spacing:0.1em;'>Изменить адрес</summary><form method='POST' action='/update-slug' style='margin-top:15px; display:flex; gap:10px;'><input name='new_slug' value='{u.slug}' required pattern='[a-z0-9-]+' style='margin:0;'><button type='submit' style='width:120px; margin:0;'>Сохранить</button></form></details></div>"""
    
    schedule_widget = f"""<div style='margin-top:30px; padding:30px; border:1px solid var(--border);'><h3 style='margin-top:0;'>Расписание и уведомления</h3><form method='POST' action='/update-schedule'><div class='schedule-form'><div><label style='font-size:11px; color:var(--text-muted); text-transform:uppercase;'>Начало</label><input type='time' name='work_start' value='{u.work_start}' required></div><div><label style='font-size:11px; color:var(--text-muted); text-transform:uppercase;'>Конец</label><input type='time' name='work_end' value='{u.work_end}' required></div><div><label style='font-size:11px; color:var(--text-muted); text-transform:uppercase;'>Обед с</label><input type='time' name='break_start' value='{u.break_start or ""}'></div><div><label style='font-size:11px; color:var(--text-muted); text-transform:uppercase;'>Обед до</label><input type='time' name='break_end' value='{u.break_end or ""}'></div></div><label style='font-size:11px; color:var(--text-muted); text-transform:uppercase; margin-top:15px; display:block;'>Длительность</label><select name='slot_duration'><option value='30' {'selected' if u.slot_duration == 30 else ''}>30 минут</option><option value='60' {'selected' if u.slot_duration == 60 else ''}>1 час</option><option value='90' {'selected' if u.slot_duration == 90 else ''}>1.5 часа</option><option value='120' {'selected' if u.slot_duration == 120 else ''}>2 часа</option></select><label style='font-size:11px; color:var(--text-muted); text-transform:uppercase; margin-top:15px; display:block;'>Telegram ID</label><input name='telegram_id' value='{u.telegram_id or ""}' placeholder='Например: 123456789'><button type='submit'>Сохранить</button></form></div>"""

    return HTML_HEAD + nav_bar(u.name) + f"""
    <div class='grid'>
        <div>
            <div class='card' style='padding:40px;'><h3 style='margin:0; color:var(--text-muted); font-size:12px; text-transform:uppercase; letter-spacing:0.1em;'>Общая выручка</h3><h1 style='margin:10px 0 0 0; font-size:56px;'>{total_revenue} ₽</h1><p style='color:var(--text-muted); font-size:13px; margin-top:5px;'>Всего записей: {len(bookings)}</p></div>
            <h3 style='margin-top:40px; font-size:28px;'>Мои услуги</h3><form method='POST' action='/add-service' style='display:flex; gap:15px;'><input name='name' placeholder='Название услуги' required style='margin:0;'><input name='price' type='number' placeholder='Цена' required style='width:100px; margin:0;'><button type='submit' style='width:120px; margin:0;'>Добавить</button></form><div style='margin-top:20px;'>{serv_html or '<p style="color:var(--text-muted)">Нет услуг</p>'}</div>
            <h3 style='margin-top:40px; font-size:28px;'>Отзывы</h3>{reviews_html}<h3 style='margin-top:40px; font-size:28px;'>Лист ожидания</h3>{wait_html or '<p style="color:var(--text-muted)">Пусто</p>'}
        </div>
        <div><h3 style='font-size:28px;'>Записи клиентов</h3>{book_html or '<p style="color:var(--text-muted)">Пока нет записей</p>'}{schedule_widget}{link_widget}</div>
    </div>
    """ + footer() + HTML_TAIL

@app.post("/add-service")
def add_service(request: Request, name: str = Form(...), price: int = Form(...), db: Session = Depends(get_db)):
    uid = request.cookies.get("uid")
    db.add(Service(user_id=int(uid), name=name, price=price)); db.commit()
    return RedirectResponse("/app", status_code=303)

@app.post("/cancel-booking/{booking_id}")
def cancel_booking(booking_id: int, db: Session = Depends(get_db)):
    b = db.query(Booking).filter(Booking.id == booking_id).first()
    if b: db.delete(b); db.commit()
    return RedirectResponse("/app", status_code=303)

@app.get("/m/{slug}", response_class=HTMLResponse)
def public_page(slug: str, date_str: str = None, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.slug == slug).first()
    if not u or not u.is_active: return HTML_HEAD + nav_bar() + "<div class='box'><h2>Мастер не найден или заблокирован</h2><a href='/'>На главную</a></div>" + footer() + HTML_TAIL
    
    services = db.query(Service).filter(Service.user_id == u.id).all()
    reviews = db.query(Review).filter(Review.user_id == u.id).order_by(Review.id.desc()).all()
    reviews_html = "".join([f"<div class='card' style='background:transparent; padding:20px;'><div class='stars'>{'★' * r.rating + '☆' * (5 - r.rating)}</div><b style='font-size:18px;'>{r.client_name}</b><br><span style='color:var(--text-muted); font-size:14px;'>{r.text}</span></div>" for r in reviews])
    review_form = f"""<hr style='border:none; border-top:1px solid var(--border); margin:40px 0;'><h3 style='text-align:center; font-size:28px;'>Оставить отзыв</h3><form method='POST' action='/m/{slug}/review'><input name='client_name' placeholder='Ваше имя' required><select name='rating' required><option value='5'>★★★★★ (Отлично)</option><option value='4'>★★★★☆ (Хорошо)</option><option value='3'>★★★☆☆ (Нормально)</option><option value='2'>★★☆☆☆ (Плохо)</option><option value='1'>★☆☆☆☆ (Ужасно)</option></select><textarea name='text' placeholder='Текст отзыва...' rows='2' required></textarea><button type='submit'>Отправить</button></form>"""

    if not services: return HTML_HEAD + nav_bar() + f"<div class='box'><h2>{u.name}</h2><p>Пока нет услуг.</p>{reviews_html}{review_form}<a href='/'>На главную</a></div>" + footer() + HTML_TAIL

    serv_options = "".join([f"<option value='{s.id}'>{s.name} — {s.price} ₽</option>" for s in services])

    if not date_str:
        return HTML_HEAD + nav_bar() + f"""<div class='box'><h2 style='text-align:center; font-size:40px;'>{u.name}</h2><p style='text-align:center; color:var(--text-muted); margin-bottom:40px; text-transform:uppercase; letter-spacing:0.1em; font-size:12px;'>📍 {u.city}</p><form method='GET' action='/m/{slug}'><input type='date' name='date_str' required min='{date.today().isoformat()}'><button type='submit'>Выбрать время</button></form><h3 style='margin-top:50px; font-size:28px;'>Отзывы</h3>{reviews_html or '<p style="color:var(--text-muted); text-align:center;">Пока нет отзывов</p>'}{review_form}</div>""" + footer() + HTML_TAIL

    all_times = generate_slots(u.work_start, u.work_end, u.break_start, u.break_end, u.slot_duration)
    busy_bookings = db.query(Booking).filter(Booking.user_id == u.id, Booking.date == date_str).all()
    busy_times = [b.time for b in busy_bookings]

    slots_html = ""
    for t in all_times:
        if t in busy_times: slots_html += f"<div class='time-slot disabled'> {t} </div>"
        else: slots_html += f"<div class='time-slot' onclick='selectTime(this, \"{t}\")'> {t} </div>"
    if not all_times: slots_html = "<p style='color:#cc0000; grid-column:1/-1; text-align:center;'>Нет слотов.</p>"

    display_date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%d.%m.%Y')
    waitlist_btn = f"""<div style='margin-top:30px; text-align:center;'><p style='color:var(--text-muted); font-size:13px;'>Нет подходящего времени?</p><form method='POST' action='/m/{slug}/waitlist'><input type='hidden' name='date' value='{date_str}'><input name='client_name' placeholder='Имя' required style='margin-bottom:10px;'><input name='client_phone' placeholder='Телефон' required style='margin-bottom:10px;'><button type='submit' style='background:transparent; color:var(--text); border:1px solid var(--text);'>Встать в лист ожидания</button></form></div>"""

    return HTML_HEAD + nav_bar() + f"""<div class='box'><a href='/m/{slug}' style='font-size:12px; text-transform:uppercase; letter-spacing:0.1em;'>← Назад</a><h2 style='text-align:center; margin-top:20px; font-size:36px;'>Запись на {display_date}</h2><div class='time-slots'>{slots_html}</div><form method='POST' action='/m/{slug}/book'><input type='hidden' name='date' value='{date_str}'><input type='hidden' name='time' id='selected-time' required><select name='service_id' required>{serv_options}</select><input name='client_name' placeholder='Ваше имя' required><input name='client_phone' type='tel' placeholder='Телефон (+7...)' required pattern='[\+0-9\s\-\(\)]+'><input name='client_email' type='email' placeholder='Email' required><textarea name='client_comment' placeholder='Комментарий (пожелания)' rows='2'></textarea><button type='submit' id='submit-btn' disabled>Подтвердить запись</button></form>{waitlist_btn}</div><script>function selectTime(el, time) {{document.querySelectorAll('.time-slot').forEach(s => s.classList.remove('active'));el.classList.add('active');document.getElementById('selected-time').value = time;document.getElementById('submit-btn').disabled = false;}}</script>""" + footer() + HTML_TAIL

@app.post("/m/{slug}/review")
def add_review(slug: str, client_name: str = Form(...), rating: int = Form(...), text: str = Form(...), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.slug == slug).first()
    db.add(Review(user_id=u.id, client_name=client_name, rating=rating, text=text)); db.commit()
    return RedirectResponse(f"/m/{slug}", status_code=303)

@app.post("/m/{slug}/book", response_class=HTMLResponse)
def book(slug: str, service_id: int = Form(...), client_name: str = Form(...), client_phone: str = Form(...), client_email: str = Form(...), client_comment: str = Form(None), date: str = Form(...), time: str = Form(...), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.slug == slug).first()
    serv = db.query(Service).filter(Service.id == service_id).first()
    existing = db.query(Booking).filter(Booking.user_id == u.id, Booking.date == date, Booking.time == time).first()
    if existing: return HTML_HEAD + nav_bar() + f"<div class='box' style='text-align:center;'><h2 style='font-size:32px;'>Это время уже занято</h2><p style='color:var(--text-muted)'>К сожалению, кто-то оказался быстрее.</p><a href='/m/{slug}?date_str={date}' style='display:block; margin-top:30px; padding:16px; border:1px solid var(--text); text-decoration:none; text-transform:uppercase; letter-spacing:0.1em; font-size:12px;'>Выбрать другое время</a></div>" + footer() + HTML_TAIL
    db.add(Booking(user_id=u.id, client_name=client_name, client_phone=client_phone, client_email=client_email, client_comment=client_comment, service_name=serv.name, price=serv.price, date=date, time=time)); db.commit()
    return HTML_HEAD + nav_bar() + f"""<div class='box' style='text-align:center'><h2 style='font-size:36px;'>Успешно!</h2><p style='font-size:18px; margin-bottom:10px;'>{client_name}, вы записаны к мастеру {u.name}</p><p style='color:var(--text-muted); margin-bottom:30px;'>{serv.name} • {date} в {time}</p><p style='font-size:13px; color:var(--text-muted);'>Подтверждение отправлено на {client_email}.</p><a href='/my-bookings' style='display:block; margin-top:30px; padding:16px; border:1px solid var(--text); text-decoration:none; text-transform:uppercase; letter-spacing:0.1em; font-size:12px;'>Мои записи</a></div>""" + footer() + HTML_TAIL

@app.post("/m/{slug}/waitlist", response_class=HTMLResponse)
def add_waitlist(slug: str, client_name: str = Form(...), client_phone: str = Form(...), date: str = Form(...), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.slug == slug).first()
    db.add(Waitlist(user_id=u.id, client_name=client_name, client_phone=client_phone, date=date)); db.commit()
    return HTML_HEAD + nav_bar() + f"""<div class='box' style='text-align:center'><h2 style='font-size:32px;'>Вы в листе ожидания</h2><p style='color:var(--text-muted)'>Мы свяжемся с вами, если на {date} освободится время.</p><a href='/' style='display:block; margin-top:30px; padding:16px; border:1px solid var(--text); text-decoration:none; text-transform:uppercase; letter-spacing:0.1em; font-size:12px;'>На главную</a></div>""" + footer() + HTML_TAIL
