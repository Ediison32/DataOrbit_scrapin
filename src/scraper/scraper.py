# dataorbit/src/scraper/scraper.py
import os
import asyncio
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

#from services.utils import setup_driver

from src.services.utils import setup_driver  # ✅ Correcto

#from services.utils import setup_driver
#import services.utils as st
from src.database.database import guardar_en_mongo,obtener_info_guardada, comparar_y_guardar
#from database.database import obtener_de_mongo
#import sys


#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# Configuración de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


async def scrape_actuaciones(abogado_id: str, abogado_nombre: str, cliente_nombre: str, tipo_persona: str, departamento: str, radicados_guardados):
    """
    Realiza scraping en la página web y obtiene las actuaciones de los radicados en monitoreo activo.
    """
    # 🔍 Extraemos listas de radicados guardados y en monitoreo
    lista_radicados_completo = {r["radicado_id"]: r for r in radicados_guardados}
    lista_radicados_a_monitorear = {r["radicado_id"] for r in radicados_guardados if r["monitoreo_activo"]}

    logging.info(f"📌 Radicados en BD (completo): {list(lista_radicados_completo.keys())}")
    logging.info(f"📌 Radicados a monitorear: {list(lista_radicados_a_monitorear)}")

    driver = setup_driver()
    url = os.getenv("url")
    radicados_list = []

    try:
        logging.info(f"Iniciando scraping para: {cliente_nombre} - {tipo_persona}")
        driver.get(url)
        await asyncio.sleep(3)

        # 📌 Seleccionamos opciones en la web
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="mainContent"]/div/div/div/div[1]/div/div[2]/div/div[1]/div/div/div/div/div[1]/div/div[2]'))
        ).click()
        logging.info("✅ Opción 'Todos los Procesos' seleccionada")

        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="mainContent"]/div/div/div/div[1]/div/div[2]/div/div[2]/div/div[1]/div[1]/div[1]'))
        ).click()

        persona_xpath = '//*[@id="list-item-121-0"]/div' if tipo_persona.lower() == "natural" else '//*[@id="list-item-121-1"]/div'
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, persona_xpath))
        ).click()
        logging.info(f"✅ Tipo de persona seleccionado: {tipo_persona}")

        driver.find_element(By.XPATH, '//*[@id="input-78"]').send_keys(cliente_nombre)
        logging.info("✅ Nombre ingresado")
        await asyncio.sleep(3)

        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="mainContent"]/div/div/div/div[1]/div/div[2]/div/div[5]/button[1]'))
        ).click()
        await asyncio.sleep(3)

        try:
            boton_confirmar = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div[4]/div/div/div[2]/div/button'))
            )
            boton_confirmar.click()
            logging.info("✅ Se hizo clic en el botón de confirmación")
        except Exception:
            logging.warning("❌ No se encontró el botón de confirmación, continuando...")
        await asyncio.sleep(3)

        # 🔥 Capturar lista de radicados obtenidos
        tablas_info_1 = driver.find_elements(By.XPATH, '//*[@id="mainContent"]/div/div/div/div[2]/div/div/div[2]/div/table/tbody/tr')

        for i in range(1, len(tablas_info_1) + 1):
            try:
                # 📌 Recargar la lista antes de procesar
                tablas_info_1 = driver.find_elements(By.XPATH, '//*[@id="mainContent"]/div/div/div/div[2]/div/div/div[2]/div/table/tbody/tr')

                # 📌 Extraer ID del radicado
                celdas = tablas_info_1[i - 1].find_elements(By.TAG_NAME, "td")
                if not celdas or len(celdas) < 2:
                    logging.warning(f"⚠ No se pudo obtener el ID del radicado en la fila {i}")
                    continue  

                radicado_id = celdas[1].text.strip()
                logging.info(f"📌 Radicado ID obtenido: {radicado_id}")

                # 🔍 Aquí se decide si procesar o ignorar el radicado
                if radicado_id not in lista_radicados_completo:
                    logging.info(f"🆕 Radicado {radicado_id} es completamente nuevo. Procesando...")

                elif radicado_id not in lista_radicados_a_monitorear:
                    logging.info(f"⚠ Radicado {radicado_id} no está en monitoreo activo. Saltando...")
                    continue  # No monitoreado, se ignora

                # ✅ Acceder a detalles del radicado
                detalle_radicado = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, f'//*[@id="mainContent"]/div/div/div/div[2]/div/div/div[2]/div/table/tbody/tr[{i}]/td[2]/button'))
                )
                detalle_radicado.click()
                await asyncio.sleep(3)

                logging.info(f"✅ Accedido a detalles de radicado {i} - ID: {radicado_id}")

                # ✅ Ir a la pestaña de 'Actuaciones'
                actuaciones_tab = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//div[contains(text(), "Actuaciones")]'))
                )
                actuaciones_tab.click()
                await asyncio.sleep(3)

                # ✅ Extraer las actuaciones
                actuaciones_list = []
                actuaciones_tabla = driver.find_elements(By.XPATH, '//*[@id="mainContent"]/div/div/div/div[2]/div/div/div[2]/div[2]/div[2]/div/div/div[2]/div/div[1]/div[2]/div/table/tbody/tr')

                for actuacion in actuaciones_tabla:
                    celdas_actuacion = actuacion.find_elements(By.TAG_NAME, "td")
                    if len(celdas_actuacion) < 6:
                        continue

                    actuacion_data = {
                        "fecha_actuacion": celdas_actuacion[0].text.strip(),
                        "actuacion": celdas_actuacion[1].text.strip(),
                        "anotacion": celdas_actuacion[2].text.strip(),
                        "fecha_inicio": celdas_actuacion[3].text.strip(),
                        "fecha_final": celdas_actuacion[4].text.strip(),
                        "fecha_registro": celdas_actuacion[5].text.strip()
                    }
                    actuaciones_list.append(actuacion_data)

                logging.info(f"📌 Radicado {radicado_id} guardado con {len(actuaciones_list)} actuaciones")

                # ✅ Guardamos el radicado en la lista general
                radicados_list.append({
                    "radicado_id": radicado_id,
                    "monitoreo_activo": radicado_id in lista_radicados_a_monitorear,
                    "actuaciones": actuaciones_list
                })

                # ✅ Regresar a la lista de radicados
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="mainContent"]/div/div/div/div[2]/div/div/div[2]/div[1]/button'))
                ).click()
                await asyncio.sleep(3)

            except Exception as e:
                logging.warning(f"⚠ No se pudo acceder a detalles del radicado {i}: {e}")

        return radicados_list  

    except Exception as e:
        logging.error(f"❌ Error en la consulta: {e}")
    finally:
        driver.quit()

    return None