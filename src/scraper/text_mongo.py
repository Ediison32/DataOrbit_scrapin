import os
from pymongo import MongoClient
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options



# Cargar variables de entornopy
load_dotenv()
mongo_uri = os.getenv("MONGO_URI")

try:
    client = MongoClient(mongo_uri)
    db = client["DataOrbit"]  # Nombre de la base de datos
    print("✅ Conexión exitosa a MongoDB")
    print("📂 Bases de datos disponibles:", client.list_database_names())
except Exception as e:
    print("❌ Error al conectar con MongoDB:", e)


# Cargar el chromedriver desde el .env
chromedriver_path = os.getenv("CHROMEDRIVER_PATH")

# Configuración de Selenium
chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# Iniciar el navegador
try:
    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get("https://www.google.com")
    print("✅ Selenium funciona correctamente")
    driver.quit()
except Exception as e:
    print(f"❌ Error en Selenium: {e}")

