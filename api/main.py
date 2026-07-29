from fastapi import FastAPI, Header, HTTPException
import aiohttp, os, sqlite3
from dotenv import load_dotenv
load_dotenv()
app = FastAPI(title="👑 MONARCH API V8")
CHAVE = os.getenv("CHAVE_API")
RENDER_API = os.getenv("RENDER_API")
RENDER_TOKEN = os.getenv("RENDER_API_TOKEN")

def verificar(chave:str=Header(None)):
    if chave != CHAVE: raise HTTPException(403,"Chave inválida")

@app.get("/")
def raiz(): return {"status":"ONLINE","sistema":"MONARCH2026©"}

@app.post("/criar-servico",dependencies=[verificar])
async def criar(nome:str,plano:str):
    async with aiohttp.ClientSession() as s:
        r = await s.post(f"{RENDER_API}/services",headers={"Authorization":f"Bearer {RENDER_TOKEN}","Content-Type":"application/json"},
            json={"name":nome,"repo":"https://github.com/SEU_USUARIO/MONARCH-BOTS.git","branch":"main","startCommand":f"python bot_{plano}.py"})
        return await r.json()

@app.post("/ligar-servico/{sid}",dependencies=[verificar])
async def ligar(sid:str):
    async with aiohttp.ClientSession() as s:
        await s.post(f"{RENDER_API}/services/{sid}/resume",headers={"Authorization":f"Bearer {RENDER_TOKEN}"})
        return {"status":"LIGADO"}

@app.post("/desligar-servico/{sid}",dependencies=[verificar])
async def desligar(sid:str):
    async with aiohttp.ClientSession() as s:
        await s.post(f"{RENDER_API}/services/{sid}/suspend",headers={"Authorization":f"Bearer {RENDER_TOKEN}"})
        return {"status":"DESLIGADO"}
