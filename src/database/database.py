import os
import logging
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

# Cargar variables de entorno
load_dotenv()

# Conectar con MongoDB
mongo_client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
db = mongo_client["DataOrbit"]
lawyer_collection = db["lawyer"]

async def obtener_info_guardada(abogado_id, cliente_nombre):
    """
    Obtiene todos los radicados y actuaciones ya almacenados en MongoDB.
    """
    resultado = await lawyer_collection.find_one(
        {"telegram_id": abogado_id, "clientes.nombre": cliente_nombre},
        {"clientes.$": 1}  # Solo trae la info del cliente específico
    )

    if resultado and "clientes" in resultado and resultado["clientes"]:
        return resultado["clientes"][0]["radicados"]
    return []
""" 
async def comparar_y_guardar(abogado_id, cliente_nombre, tipo_persona, departamento, nuevos_radicados):

    radicados_guardados = await obtener_info_guardada(abogado_id, cliente_nombre)

    cambios_detectados = []

    # 📌 Diccionario de radicados guardados
    lista_radicados_completo = {r["radicado_id"]: r for r in radicados_guardados}
    lista_radicados_a_monitorear = {r["radicado_id"] for r in radicados_guardados if r["monitoreo_activo"]}

    logging.info(f"📌 Radicados en BD (completo): {list(lista_radicados_completo.keys())}")
    logging.info(f"📌 Radicados a monitorear: {list(lista_radicados_a_monitorear)}")

    for nuevo_radicado in nuevos_radicados:
        radicado_id = nuevo_radicado.get("radicado_id")

        if not radicado_id:
            logging.error(f"❌ ERROR: No se encontró 'radicado_id' en {nuevo_radicado}")
            continue  # Saltamos este radicado

        # ✅ Si el radicado NO está en la BD, se guarda como nuevo
        if radicado_id not in lista_radicados_completo:
            nuevo_radicado["monitoreo_activo"] = True
            await lawyer_collection.update_one(
                {"telegram_id": abogado_id, "clientes.nombre": cliente_nombre},
                {"$push": {"clientes.$.radicados": nuevo_radicado}}
            )
            logging.info(f"🆕 Nuevo radicado guardado: {radicado_id} y puesto en monitoreo activo.")
            cambios_detectados.append({"tipo": "nuevo_radicado", "radicado_id": radicado_id})
            continue  # Pasamos al siguiente radicado

        # ✅ Si el radicado YA existe y está en monitoreo, comparar actuaciones
        radicado_existente = lista_radicados_completo[radicado_id]

        # 🔍 Filtrar actuaciones nuevas
        actuaciones_guardadas = {a["fecha_registro"] for a in radicado_existente["actuaciones"]}
        actuaciones_nuevas = [
            a for a in nuevo_radicado["actuaciones"] if a["fecha_registro"] not in actuaciones_guardadas
        ]

        if actuaciones_nuevas:
            await lawyer_collection.update_one(
                {
                    "telegram_id": abogado_id,
                    "clientes.nombre": cliente_nombre,
                    "clientes.radicados.radicado_id": radicado_id
                },
                {
                    "$push": {
                        "clientes.$.radicados.$[radicado].actuaciones": {"$each": actuaciones_nuevas}
                    }
                },
                array_filters=[{"radicado.radicado_id": radicado_id}]
            )
            logging.info(f"✅ {len(actuaciones_nuevas)} actuaciones nuevas agregadas al radicado {radicado_id}")
            cambios_detectados.append({"tipo": "nuevas_actuaciones", "radicado_id": radicado_id, "cantidad": len(actuaciones_nuevas)})

    # 🔥 Si no hubo cambios, devolvemos una lista vacía
    return cambios_detectados

async def comparar_y_guardar(abogado_id, cliente_nombre, tipo_persona, departamento, nuevos_radicados):
    

    # 🔍 Obtener los radicados guardados en la base de datos
    radicados_guardados = await obtener_info_guardada(abogado_id, cliente_nombre)

    if not radicados_guardados:
        # 📌 Si es la PRIMERA VEZ, se guardan todos los radicados nuevos
        await guardar_en_mongo(abogado_id, cliente_nombre, tipo_persona, departamento, nuevos_radicados)
        logging.info(f"✅ Se guardaron {len(nuevos_radicados)} radicados nuevos.")
        return True  # Se hicieron cambios

    logging.info(f"📌 Lista de radicados en la base de datos: {radicados_guardados}")

    cambios_detectados = False

    # 🔍 1️⃣ Obtener los IDs de los radicados guardados en la BD
    radicados_guardados_ids = {r["radicado_id"] for r in radicados_guardados}

    # 🔍 2️⃣ Revisar cada nuevo radicado obtenido en el scraping
    for nuevo_radicado in nuevos_radicados:

        if "radicado_id" not in nuevo_radicado:
            logging.error(f"❌ ERROR: No se encontró 'radicado_id' en {nuevo_radicado}")
            continue  # Saltar este radicado

        radicado_id = nuevo_radicado["radicado_id"]
        actuaciones_nuevas = nuevo_radicado["actuaciones"]

        # 🔥 3️⃣ Si el radicado NO existe en la base de datos, se guarda como nuevo
        if radicado_id not in radicados_guardados_ids:
            await lawyer_collection.update_one(
                {"telegram_id": abogado_id, "clientes.nombre": cliente_nombre},
                {"$push": {"clientes.$.radicados": nuevo_radicado}}
            )
            logging.info(f"🆕 Nuevo radicado guardado: {radicado_id}")
            cambios_detectados = True
            continue  # Pasamos al siguiente radicado

        # ✅ 4️⃣ Si el radicado YA existe, comparar actuaciones
        radicado_existente = next(r for r in radicados_guardados if r["radicado_id"] == radicado_id)
        
        # Filtrar actuaciones nuevas
        actuaciones_guardadas = {a["fecha_registro"] for a in radicado_existente["actuaciones"]}
        actuaciones_filtradas = [
            a for a in actuaciones_nuevas if a["fecha_registro"] not in actuaciones_guardadas
        ]

        if actuaciones_filtradas:
            await lawyer_collection.update_one(
                {
                    "telegram_id": abogado_id,
                    "clientes.nombre": cliente_nombre,
                    "clientes.radicados.radicado_id": radicado_id
                },
                {
                    "$push": {
                        "clientes.$.radicados.$[radicado].actuaciones": {"$each": actuaciones_filtradas}
                    }
                },
                array_filters=[{"radicado.radicado_id": radicado_id}]
            )
            logging.info(f"✅ {len(actuaciones_filtradas)} actuaciones nuevas agregadas al radicado {radicado_id}")
            cambios_detectados = True

    # 🔥 5️⃣ Eliminar radicados que ya NO están en el scraping
    radicados_nuevos_ids = {r["radicado_id"] for r in nuevos_radicados}
 

    
    if not cambios_detectados:
        logging.info(f"✅ No hubo cambios en los radicados del cliente {cliente_nombre}, no se guardó nada.")

    return cambios_detectados  # Devuelve True si hubo cambios, False si no.


"""

async def comparar_y_guardar(abogado_id, cliente_nombre, tipo_persona, departamento, nuevos_radicados):
    """
    Compara los nuevos radicados con los existentes y solo guarda los cambios necesarios.
    """
    logging.info(f"🔍 Iniciando comparación de radicados para {cliente_nombre} ({abogado_id})")

    # 🔍 Obtener los radicados guardados en la base de datos
    radicados_guardados = await obtener_info_guardada(abogado_id, cliente_nombre)

    # 📌 Si no hay radicados en la BD, usar `guardar_en_mongo()` directamente
    if not radicados_guardados:
        logging.info(f"🆕 Cliente {cliente_nombre} no tiene radicados en la BD. Guardando todos...")
        
        # 🔥 Asegurar que todos los radicados nuevos queden en `monitoreo_activo=True`
        for radicado in nuevos_radicados:
            radicado["monitoreo_activo"] = True

        await guardar_en_mongo(abogado_id, cliente_nombre, tipo_persona, departamento, nuevos_radicados)
        logging.info(f"✅ Se guardaron {len(nuevos_radicados)} radicados nuevos en MongoDB.")
        return [{"tipo": "nuevo_radicado", "radicado_id": r["radicado_id"]} for r in nuevos_radicados]

    # 📌 Crear diccionarios para acceso rápido
    lista_radicados_completo = {r["radicado_id"]: r for r in radicados_guardados}
    lista_radicados_a_monitorear = {r["radicado_id"] for r in radicados_guardados if r.get("monitoreo_activo", False)}

    logging.info(f"📌 Radicados en BD (completo): {list(lista_radicados_completo.keys())}")
    logging.info(f"📌 Radicados a monitorear: {list(lista_radicados_a_monitorear)}")

    cambios_detectados = []

    for nuevo_radicado in nuevos_radicados:
        radicado_id = nuevo_radicado.get("radicado_id")

        if not radicado_id:
            logging.error(f"❌ ERROR: No se encontró 'radicado_id' en {nuevo_radicado}")
            continue  # Saltamos este radicado

        # ✅ Si el radicado NO está en la BD, se guarda como nuevo y se activa monitoreo
        if radicado_id not in lista_radicados_completo:
            nuevo_radicado["monitoreo_activo"] = True  # 🔥 Se activa monitoreo SIEMPRE para nuevos radicados
            
            logging.info(f"🆕 Guardando nuevo radicado en MongoDB: {radicado_id}")

            resultado = await lawyer_collection.update_one(
                {"telegram_id": abogado_id, "clientes.nombre": cliente_nombre},
                {"$push": {"clientes.$.radicados": nuevo_radicado}}
            )

            if resultado.modified_count == 0:
                logging.warning(f"⚠ Radicado {radicado_id} no se pudo guardar con `update_one()`. Usando `guardar_en_mongo()`.")
                await guardar_en_mongo(abogado_id, cliente_nombre, tipo_persona, departamento, [nuevo_radicado])  # Guardar con `guardar_en_mongo()`
            else:
                logging.info(f"✅ Nuevo radicado guardado exitosamente: {radicado_id}")
                cambios_detectados.append({"tipo": "nuevo_radicado", "radicado_id": radicado_id})
            
            continue  # Pasamos al siguiente radicado

        # ✅ Si el radicado YA existe y está en monitoreo, comparar actuaciones
        radicado_existente = lista_radicados_completo[radicado_id]

        # 🔥 Conservar el estado de `monitoreo_activo`
        nuevo_radicado["monitoreo_activo"] = radicado_existente.get("monitoreo_activo", True)

        # 🔍 Filtrar actuaciones nuevas
        actuaciones_guardadas = {a["fecha_registro"] for a in radicado_existente["actuaciones"]}
        actuaciones_nuevas = [
            a for a in nuevo_radicado["actuaciones"] if a["fecha_registro"] not in actuaciones_guardadas
        ]

        if actuaciones_nuevas:
            logging.info(f"📌 Se encontraron {len(actuaciones_nuevas)} actuaciones nuevas en {radicado_id}")

            resultado = await lawyer_collection.update_one(
                {
                    "telegram_id": abogado_id,
                    "clientes.nombre": cliente_nombre,
                    "clientes.radicados.radicado_id": radicado_id
                },
                {
                    "$push": {
                        "clientes.$.radicados.$[radicado].actuaciones": {"$each": actuaciones_nuevas}
                    }
                },
                array_filters=[{"radicado.radicado_id": radicado_id}]
            )

            if resultado.modified_count == 0:
                logging.error(f"❌ ERROR: No se pudieron guardar las actuaciones en {radicado_id}")
            else:
                logging.info(f"✅ {len(actuaciones_nuevas)} actuaciones nuevas guardadas en {radicado_id}")
                cambios_detectados.append({
                    "tipo": "nuevas_actuaciones",
                    "radicado_id": radicado_id,
                    "cantidad": len(actuaciones_nuevas)
                })

    if not cambios_detectados:
        logging.info(f"✅ No hubo cambios en los radicados del cliente {cliente_nombre}, no se guardó nada.")

    return cambios_detectados  # Devuelve una lista de cambios detectados


async def guardar_en_mongo(abogado_id, cliente_nombre, tipo_persona, departamento, radicados_list):
    """
    Guarda nuevos radicados en la base de datos.
    """
    resultado = await lawyer_collection.find_one({"telegram_id": abogado_id, "clientes.nombre": cliente_nombre})

    if not resultado:
        # Si el cliente no existe, se crea un nuevo documento en la base de datos
        nuevo_cliente = {
            "telegram_id": abogado_id,
            "clientes": [
                {
                    "nombre": cliente_nombre,
                    "tipo_persona": tipo_persona,
                    "departamento": departamento,
                    "radicados": radicados_list  # ✅ Guardamos toda la lista de radicados
                }
            ]
        }
        await lawyer_collection.insert_one(nuevo_cliente)
    else:
        # Si el cliente ya existe, agregamos nuevos radicados en UNA sola operación
        await lawyer_collection.update_one(
            {
                "telegram_id": abogado_id,
                "clientes.nombre": cliente_nombre
            },
            {"$push": {
                "clientes.$.radicados": {"$each": radicados_list}  # ✅ Agrega todos los radicados a la vez
            }}
        )
