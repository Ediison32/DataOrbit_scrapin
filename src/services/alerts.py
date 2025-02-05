import os
import logging
import aiohttp
from dotenv import load_dotenv
import asyncio
# Cargar variables de entorno
load_dotenv()

TELEGRAM_BOT = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("chat_admin")  # ✅ Tu ID para recibir alertas si algo falla

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

async def enviar_mensaje_telegram(mensaje, chat_id):
    """
    Envía un mensaje a un usuario específico por Telegram.
    Si falla, envía una notificación al administrador.

    """
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": mensaje,
        "parse_mode": "Markdown"
    }

    async with aiohttp.ClientSession() as session:
        for intento in range(3):  # 🔄 Intentamos hasta 3 veces
            async with session.post(url, json=payload) as response:
                respuesta_texto = await response.text()
                if response.status == 200:
                    logging.info(f"✅ Notificación enviada a {chat_id}.")
                    return True  # Mensaje enviado correctamente
                else:
                    logging.error(f"❌ Error al enviar notificación a {chat_id}: {response.status} - {respuesta_texto}")
                    
                    # 🔥 Si es un error crítico (ej. usuario bloqueó el bot), notificamos al admin
                    if response.status in [403, 404]:  # 403 = usuario bloqueó, 404 = chat_id no válido
                        admin_alerta = f"🚨 *Error de envío de mensaje*\nUsuario: `{chat_id}`\nError: `{response.status}` - {respuesta_texto}"
                        await session.post(url, json={"chat_id": ADMIN_CHAT_ID, "text": admin_alerta, "parse_mode": "Markdown"})
                        return False  # No seguir intentando, usuario bloqueó o chat_id no existe

            await asyncio.sleep(2)  # 🔄 Esperar 2 segundos antes de reintentar

    return False  # Si después de 3 intentos falla, retornamos False

async def notificar_cambios(abogado_id, abogado_nombre, cambios):
    """
    Envía notificaciones por Telegram en función de los cambios detectados en los radicados.
    """
    if not cambios:
        logging.info("✅ No hubo cambios detectados, no se envió notificación.")
        return

    mensajes = []
        
    for cambio in cambios:
        if cambio["tipo"] == "nuevo_radicado":
            mensajes.append(f"🆕 *Nuevo radicado agregado para {abogado_nombre}:*\n📌 `{cambio['radicado_id']}`")
        elif cambio["tipo"] == "nuevas_actuaciones":
            mensajes.append(f"📌 *{cambio['cantidad']} nuevas actuaciones en el radicado de {abogado_nombre}:*\n📄 `{cambio['radicado_id']}`")

    if mensajes:
        mensaje_final = "\n".join(mensajes)
        envio_exitoso = await enviar_mensaje_telegram(mensaje_final, abogado_id)

        if not envio_exitoso:
            logging.warning(f"❌ No se pudo enviar la notificación a {abogado_id}. Se notificó al administrador.")
        else:
            logging.info("📢 Notificación de cambios enviada.")

""" 
async def prueba_envio():
    chat_id = input("📢 Ingresa tu chat ID de Telegram: ")  # Puedes poner tu chat_id aquí fijo si quieres
    mensaje = "🔔 *Prueba de notificación*\nEste es un mensaje de prueba desde tu bot."
    
    resultado = await enviar_mensaje_telegram(mensaje, chat_id)
    if resultado:
        print("✅ Mensaje enviado correctamente.")
    else:
        print("❌ Error al enviar el mensaje.")

# Ejecutamos la prueba
asyncio.run(prueba_envio())
"""