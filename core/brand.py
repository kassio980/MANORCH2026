import sqlite3, datetime
from discord import Embed, Color
DB_PATH = "dados/sistema.db"
def init():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS branding(id INTEGER PRIMARY KEY,nome TEXT,slogan TEXT,logo TEXT,banner TEXT,video TEXT,cor TEXT,rodape TEXT)")
    c.execute("INSERT OR IGNORE INTO branding VALUES(1,'MONARCH2026©','Sua tecnologia','','','','FF8C00','👑 MONARCH2026©')")
    conn.commit()
    conn.close()
init()

def get():
    c = sqlite3.connect(DB_PATH).cursor()
    c.execute("SELECT * FROM branding WHERE id=1")
    return c.fetchone()

def setar(**kw):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    d = get()
    novo = (kw.get("nome",d[1]),kw.get("slogan",d[2]),kw.get("logo",d[3]),kw.get("banner",d[4]),kw.get("video",d[5]),kw.get("cor",d[6]),kw.get("rodape",d[7]))
    c.execute("UPDATE branding SET nome=?,slogan=?,logo=?,banner=?,video=?,cor=?,rodape=? WHERE id=1",novo)
    conn.commit()
    conn.close()

def mk_embed(titulo="",desc=""):
    b = get()
    try: cor = int(b[6].replace("#",""),16)
    except: cor = 0xFF8C00
    e = Embed(title=titulo,description=desc,color=Color(cor))
    if b[3]: e.set_thumbnail(url=b[3])
    if b[4]: e.set_image(url=b[4])
    e.set_author(name=b[1])
    e.set_footer(text=b[7])
    e.timestamp = datetime.datetime.now(datetime.timezone.utc)
    return e
