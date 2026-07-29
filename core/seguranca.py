import os
from dotenv import load_dotenv
load_dotenv()
SERVIDOR_PERMITIDO = int(os.getenv("SERVIDOR_PERMITIDO"))
ID_DONO = int(os.getenv("ID_DONO"))
RENDER_TOKEN = os.getenv("RENDER_API_TOKEN")
RENDER_API = os.getenv("RENDER_API")
API_KEY = os.getenv("CHAVE_API")

def servidor_valido(id_serv:int) -> bool: return id_serv == SERVIDOR_PERMITIDO
def eh_dono(id_user:int) -> bool: return id_user == ID_DONO
