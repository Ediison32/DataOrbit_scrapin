import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Cargar variables de entorno
load_dotenv()

# Configuración de Selenium
def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1440,909")
    service = Service(os.getenv("CHROMEDRIVER_PATH"))
    return webdriver.Chrome(service=service, options=chrome_options)

# Función auxiliar para formatear datos obtenidos de scraping
def formatear_actuacion(celdas):
    return {
        "fecha_actuacion": celdas[0].text.strip(),
        "actuacion": celdas[1].text.strip(),
        "anotacion": celdas[2].text.strip(),
        "fecha_inicio": celdas[3].text.strip(),
        "fecha_final": celdas[4].text.strip(),
        "fecha_registro": celdas[5].text.strip()
    }

# Función para obtener radicado_id de una fila de la tabla de radicados
def obtener_radicado_id(tabla):
    return tabla.find_elements_by_tag_name("td")[1].text.strip()
