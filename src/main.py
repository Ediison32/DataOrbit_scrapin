import asyncio
import logging
#import database.database as db
#from .database.database import obtener_clientes, comparar_y_actualizar
from .database.database import obtener_info_guardada, comparar_y_guardar
#from database.database import obtener_clientes, comparar_y_actualizar
from src.scraper.scraper import scrape_actuaciones
from src.services.alerts import notificar_cambios
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
async def ejecutar_proceso(abogado_id, username, cliente_id, cliente_nombre, tipo_persona, departamento):
    """
    Ejecuta el proceso de scraping y comparación de radicados.
    """
    logging.info(f"🚀 Iniciando proceso para {cliente_nombre} ({abogado_id})")

    # 🔍 Obtener radicados existentes en la BD
    radicados_guardados = await obtener_info_guardada(abogado_id, cliente_id)

    # 🔍 Ejecutar scraping para obtener radicados actualizados
    nuevos_radicados = await scrape_actuaciones(
        abogado_id, username, cliente_nombre, tipo_persona, departamento, radicados_guardados)
#abogado_id: str, abogado_nombre: str, cliente_nombre: str, tipo_persona: str, departamento: str, radicados_guardados

    # ✅ Comparar y guardar cambios
    cambios = await comparar_y_guardar(
        abogado_id, username, cliente_id, cliente_nombre, tipo_persona, departamento, nuevos_radicados
    )

    # 📢 Enviar notificaciones si hay cambios
    if cambios:
        await notificar_cambios(abogado_id, cliente_nombre, cambios)

"""
async def ejecutar_proceso(abogado_id, abogado_nombre, cliente_nombre, tipo_persona, departamento):
    # Obtener clientes registrados en la base de datos
    radicados_guardados = await obtener_info_guardada(abogado_id, cliente_nombre)
    
    logging.info(f"🔍 Consultando radicados para {cliente_nombre} ({abogado_id})")
    nuevos_radicados = await scrape_actuaciones(abogado_id, abogado_nombre, cliente_nombre, tipo_persona, departamento, radicados_guardados)
    
    if nuevos_radicados:
        
        cambios = await comparar_y_guardar(abogado_id, cliente_nombre, tipo_persona, departamento, nuevos_radicados)
        # 4️⃣ Si hubo cambios, enviamos la notificación por Telegram
        if cambios:
            await notificar_cambios(abogado_id, cliente_nombre, cambios)
            logging.info("📢 Notificación de cambios enviada.")
        else:
            logging.info("✅ No hubo cambios detectados, no se envió notificación.")
 
if __name__ == "__main__":
    # 🔹 Datos de prueba
    abogado_id = "5367863816"
    abogado_nombre = "abogado_juan"
    cliente_nombre = "Ruben dario rave cano "#"Alba irene rave cano"
    tipo_persona = "Natural"
    departamento = "Antioquia"
    
    # 🔹 Ejecutamos el proceso de manera asíncrona
    asyncio.run(ejecutar_proceso(abogado_id, abogado_nombre, cliente_nombre, tipo_persona, departamento))

"""



if __name__ == "__main__":
    # 🔹 Datos de prueba para dos clientes diferentes
    abogado_id = "5367863816"
    username = "abogado_juan"
    
    clientes = [
        {
            "cliente_id": "c12345",
            "cliente_nombre": "Ruben dario rave cano",
            "tipo_persona": "Natural",
            "departamento": "Antioquia",
        },
        {
            "cliente_id": "c67890",
            "cliente_nombre": "Alba irene rave cano",
            "tipo_persona": "Natural",
            "departamento": "Antioquia",
        }
    ]

    async def ejecutar_multiples_procesos():
        """
        Ejecuta en paralelo las consultas para diferentes clientes usando asyncio.gather()
        """
        tareas = [
            ejecutar_proceso(
                abogado_id, 
                username, 
                cliente["cliente_id"], 
                cliente["cliente_nombre"], 
                cliente["tipo_persona"], 
                cliente["departamento"]
            ) for cliente in clientes
        ]
        await asyncio.gather(*tareas)

    # 🔥 Lanzar las consultas en paralelo
    asyncio.run(ejecutar_multiples_procesos())
