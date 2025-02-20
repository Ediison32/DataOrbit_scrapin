import os
import logging
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pymongo import UpdateOne

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
actions_collection = db["acciones"]  # Nueva colección para registrar acciones

async def obtener_abogado(telegram_id):
    """ Obtiene la información de un abogado por su ID de Telegram. """
    return await lawyer_collection.find_one({"telegram_id": telegram_id})


async def obtener_info_guardada(abogado_id, cliente_nombre):
    """
    Obtiene todos los radicados y actuaciones almacenados en MongoDB para un cliente específico.
    """
    resultado = await lawyer_collection.find_one(
        {"telegram_id": abogado_id, "clientes.nombre": cliente_nombre},
        {"clientes.$": 1}  # Solo trae la info del cliente específico
    )

    if resultado and "clientes" in resultado and resultado["clientes"]:
        return resultado["clientes"][0]["radicados"]  # 📌 Devuelve solo los radicados del cliente encontrado
    
    return []  # 📌 Si no se encontró el cliente, retorna una lista vacía

async def agregar_cliente(telegram_id, cliente_id, cliente_nombre, tipo_persona, departamento, radicados_list):
    """
    Agrega un nuevo cliente a la lista de supervisión de un abogado si no existe,
    y permite agregar radicados si están disponibles.
    """
    if radicados_list is None:
        radicados_list = []

    # Verificar si el cliente ya existe
    resultado = await lawyer_collection.find_one(
        #{"telegram_id": telegram_id, "clientes.cliente_id": cliente_id}
        {"telegram_id ": telegram_id, "clientes.nombre":cliente_nombre}
    )

    if resultado:
        logging.warning(f"⚠️ El cliente '{cliente_nombre}' ya está registrado para este abogado.")
        return False  # No se agrega porque ya existía

    # Definir la estructura del cliente
    logging.warning(f"⚠️ {type(radicados_list)}*********************************************** '{radicados_list}' ******************************.")
    return True
""" 
    nuevo_cliente = {
        "cliente_id": cliente_id,
        "nombre": cliente_nombre,
        "tipo_persona": tipo_persona,
        "departamento": departamento,
        "radicados": radicados_list  # 🔥 Agregar radicados directamente si existen
    }

    # Agregar el cliente a la base de datos
    await lawyer_collection.update_one(
        {"telegram_id": telegram_id},
        {"$push": {"clientes": nuevo_cliente}}
    )

"""
    #logging.info(f"✅ Cliente '{cliente_nombre}' agregado con {len(radicados_list)} radicados.")
    


async def obtener_clientes(telegram_id):
    """ Obtiene los clientes supervisados por un abogado. """
    abogado = await lawyer_collection.find_one({"telegram_id": telegram_id}, {"clientes": 1})
    return abogado.get("clientes", []) if abogado else []


async def registrar_abogado(telegram_id, username, nombre, correo, telefono):
    """ Registra un nuevo abogado en la base de datos. """
    nuevo_abogado = {
        "telegram_id": telegram_id,
        "username": username,
        "nombre_completo": nombre,
        "correo": correo,
        "telefono": telefono,
        "permiso": True,  # Requiere aprobación del admin
        "cuenta_activa": True,
        "monitoreo_activo": True,
        "clientes": [],
        "fecha_inscripcion": datetime.utcnow()
    }
    await lawyer_collection.insert_one(nuevo_abogado)
    logging.info(f"✅ Nuevo abogado registrado: {nombre}")

async def comparar_y_guardar(abogado_id, username, cliente_id, cliente_nombre, tipo_persona, departamento, nuevos_radicados):
    """
    Compara los nuevos radicados con los existentes y solo guarda los cambios necesarios sin duplicar datos.
    """

    logging.info(f"🔍 Iniciando comparación de radicados para {cliente_nombre} ({abogado_id})")

    # 🔍 Obtener los radicados guardados en la base de datos
    radicados_guardados = await obtener_info_guardada(abogado_id, cliente_nombre)

    # 📌 Si no hay radicados en la BD, guardar todos los nuevos directamente
    if not radicados_guardados:
        logging.info(f"🆕 Cliente {cliente_nombre} no tiene radicados en la BD. Guardando todos...")

        for radicado in nuevos_radicados:
            radicado["monitoreo_activo"] = True  # 🔥 Activamos monitoreo en nuevos radicados

        await guardar_en_mongo(abogado_id, username, cliente_id, cliente_nombre, tipo_persona, departamento, nuevos_radicados)
        logging.info(f"✅ Se guardaron {len(nuevos_radicados)} radicados nuevos en MongoDB.")
        return [{"tipo": "nuevo_radicado", "radicado_id": r["radicado_id"]} for r in nuevos_radicados]

    # 📌 Crear diccionarios para acceso rápido
    lista_radicados_completo = {r["radicado_id"]: r for r in radicados_guardados}
    lista_radicados_a_monitorear = {r["radicado_id"] for r in radicados_guardados if r.get("monitoreo_activo", False)}

    logging.info(f"📌 Radicados en BD (completo): {list(lista_radicados_completo.keys())}")
    logging.info(f"📌 Radicados a monitorear: {list(lista_radicados_a_monitorear)}")

    cambios_detectados = []
    operaciones_batch = []

    # 🔍 Revisar cada radicado extraído del scraping
    for nuevo_radicado in nuevos_radicados:
        radicado_id = nuevo_radicado.get("radicado_id")

        if not radicado_id:
            logging.error(f"❌ ERROR: No se encontró 'radicado_id' en {nuevo_radicado}")
            continue  # Saltamos este radicado

        # ✅ Si el radicado NO está en la BD, lo agregamos de forma segura
        if radicado_id not in lista_radicados_completo:
            nuevo_radicado["monitoreo_activo"] = True  # 🔥 Activamos monitoreo en nuevos radicados
            
            logging.info(f"🆕 Guardando nuevo radicado en MongoDB: {radicado_id}")

            operaciones_batch.append(
                UpdateOne(
                    {
                        "telegram_id": abogado_id,
                        "clientes.cliente_id": cliente_id,
                        "clientes.radicados.radicado_id": {"$ne": radicado_id}  # ✅ Evitar duplicados
                    },
                    {"$push": {"clientes.$.radicados": nuevo_radicado}}
                )
            )
            cambios_detectados.append({"tipo": "nuevo_radicado", "radicado_id": radicado_id})
            continue  # Pasamos al siguiente radicado

        # ✅ Si el radicado YA existe y está en monitoreo, comparar actuaciones
        radicado_existente = lista_radicados_completo[radicado_id]

        # 🔥 Mantener el estado de monitoreo_activo
        nuevo_radicado["monitoreo_activo"] = radicado_existente.get("monitoreo_activo", True)

        # 🔍 Filtrar actuaciones nuevas

        #actuaciones_guardadas = {a["timestamp"] for a in radicado_existente["actuaciones"]}
        # Asegurar que "actuaciones" existe y es una lista antes de iterar
        actuaciones_guardadas = {a["fecha_registro"] for a in radicado_existente.get("actuaciones", [])}
        actuaciones_nuevas = [
            
            a for a in nuevo_radicado["actuaciones"] if a["fecha_registro"] not in actuaciones_guardadas
        ]

        if actuaciones_nuevas:
            logging.info(f"📌 Se encontraron {len(actuaciones_nuevas)} actuaciones nuevas en {radicado_id}")

            operaciones_batch.append(
                UpdateOne(
                    {
                        "telegram_id": abogado_id,
                        "clientes.cliente_id": cliente_id,
                        "clientes.radicados.radicado_id": radicado_id
                    },
                    {
                        "$push": {
                            "clientes.$.radicados.$[radicado].actuaciones": {"$each": actuaciones_nuevas}
                        }
                    },
                    array_filters=[{"radicado.radicado_id": radicado_id}]
                )
            )
            cambios_detectados.append({
                "tipo": "nuevas_actuaciones",
                "radicado_id": radicado_id,
                "cantidad": len(actuaciones_nuevas)
            })

    # 🔥 Ejecutar todas las operaciones en un solo batch para eficiencia
    if operaciones_batch:
        resultado = await lawyer_collection.bulk_write(operaciones_batch)
        logging.info(f"✅ {resultado.modified_count} documentos modificados en MongoDB.")

    if not cambios_detectados:
        logging.info(f"✅ No hubo cambios en los radicados del cliente {cliente_nombre}, no se guardó nada.")

    return cambios_detectados  # Devuelve una lista de cambios detectados




async def guardar_en_mongo(abogado_id, username, cliente_id, cliente_nombre, tipo_persona, departamento, radicados_list):
    """
    Guarda un nuevo cliente bajo un abogado existente o crea un nuevo registro si no existe.
    """
    # Verificar si el abogado ya existe
    resultado = await lawyer_collection.find_one({"telegram_id": abogado_id})

    nuevo_cliente = {
        "cliente_id": cliente_id,
        "nombre": cliente_nombre,
        "tipo_persona": tipo_persona,
        "departamento": departamento,
        "radicados": radicados_list
    }

    if resultado:
        # Si el abogado ya existe, agregamos el cliente si no existe.
        #logging.info(f"✅ ------------------------- {radicados_list} ---------------------------------------.")
        await lawyer_collection.update_one(
            {"telegram_id": abogado_id, "clientes.cliente_id": {"$ne": cliente_id}},
            {"$push": {"clientes": nuevo_cliente}}
            
        )
        logging.info(f"✅ Cliente {cliente_nombre} agregado a abogado existente.")
    else:
        # Si el abogado no existe, creamos el registro completo.
        nuevo_abogado = {
            "telegram_id": abogado_id,
            "username": username,
            "permiso": True,
            "cuenta_activa": True,
            "monitoreo_activo": True,
            "fecha_inscripcion": datetime.utcnow(),
            "clientes": [nuevo_cliente]
        }
        await lawyer_collection.insert_one(nuevo_abogado)
        logging.info(f"✅ Nuevo abogado y cliente {cliente_nombre} registrados.")

async def verificar_cliente_existente(abogado_id: str, cliente_nombre: str):
    """
    Verifica si un cliente ya está registrado bajo un abogado específico.
    """
    nombre_normalizado = cliente_nombre.strip().lower()
    cliente_existente = await lawyer_collection.find_one({
        "telegram_id": abogado_id,
        "clientes.nombre": cliente_nombre
    })

    if cliente_existente:
        return True  # El cliente ya existe
    return False  # El cliente no existe





