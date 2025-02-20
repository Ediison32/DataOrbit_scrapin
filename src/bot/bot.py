
""" 
import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from motor.motor_asyncio import AsyncIOMotorClient

from dotenv import load_dotenv
from datetime import datetime
# Cargar variables de entorno
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

# Configurar logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Conectar a MongoDB
client = AsyncIOMotorClient(MONGO_URI)
db = client["data_orbit"]
lawyer_collection = db["lawyers"]
actions_collection = db["acciones"]  # Nueva colección para registrar acciones

async def start(update: Update, context):
 
    user_id = update.effective_user.id
    user = await lawyer_collection.find_one({"telegram_id": str(user_id)})

    message = f"👋 ¡Hola {update.effective_user.first_name}! Bienvenido a *DataOrbit* 📡\n\n" \
              "Elige una opción para continuar:" \
              "\n\n📝 Inscribirme en DataOrbit\n" \
              "📋 Inscribir Monitoreo"

    keyboard = [[InlineKeyboardButton("📝 Inscribirme", callback_data="inscribirse")],
                [InlineKeyboardButton("📋 Inscribir Monitoreo", callback_data="menu_monitoreo")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")


async def menu_monitoreo(update: Update, context):
   
    query = update.callback_query
    keyboard = [[InlineKeyboardButton("🔍 Consultar Estado de Cuenta", callback_data="estado_cuenta")],
                [InlineKeyboardButton("📄 Consultar Radicados", callback_data="consultar_radicados")],
                [InlineKeyboardButton("✅ Activar/Desactivar Monitoreo", callback_data="monitoreo")],
                [InlineKeyboardButton("🗣️ Hablar con un Asesor", callback_data="hablar_asesor")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("📋 *Menú de Monitoreo:*", reply_markup=reply_markup, parse_mode="Markdown")

async def handle_text_messages(update: Update, context):

    await start(update, context)

async def registrar_accion(admin_id, usuario_id, accion):
   
    await actions_collection.insert_one({
        "admin_id": str(admin_id),
        "usuario_id": str(usuario_id),
        "accion": accion,
        "fecha": datetime.utcnow()
    })

async def consultar_radicados(update: Update, context):
    
    query = update.callback_query
    user_id = str(query.from_user.id)
    user = await lawyer_collection.find_one({"telegram_id": user_id})

    if not user or "clientes" not in user or not user["clientes"]:
        await query.answer("No tienes radicados registrados.")
        return

    mensaje = "📌 *Tus radicados:*\n\n"
    for cliente in user["clientes"]:
        mensaje += f"👤 Cliente: {cliente['nombre']}\n"
        for radicado in cliente["radicados"]:
            estado = "✅ Activo" if radicado["monitoreo_activo"] else "❌ Inactivo"
            mensaje += f"   📄 `{radicado['radicado_id']}` - {estado}\n"
        mensaje += "\n"

    await query.message.reply_text(mensaje, parse_mode="Markdown")

async def estado_cuenta(update: Update, context):
    
    query = update.callback_query
    user_id = str(query.from_user.id)
    user = await lawyer_collection.find_one({"telegram_id": user_id})

    if not user:
        await query.answer("No tienes información de cuenta registrada.")
        return

    cuenta_activa = "✅ Activa" if user.get("cuenta_activa", False) else "❌ Inactiva"
    permiso = "✅ Permitido" if user.get("permiso", False) else "❌ No permitido"
    mensaje = f"📊 *Estado de tu cuenta:*\n\n🔹 *Cuenta:* {cuenta_activa}\n🔹 *Permiso:* {permiso}"
    
    await query.message.reply_text(mensaje, parse_mode="Markdown")


#app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
app.add_handler(CallbackQueryHandler(menu_monitoreo, pattern="^menu_monitoreo"))
app.add_handler(CallbackQueryHandler(consultar_radicados, pattern="^consultar_radicados"))
app.add_handler(CallbackQueryHandler(estado_cuenta, pattern="^estado_cuenta"))

logging.info("🤖 Bot de Telegram en ejecución...")


app.run_polling(poll_interval=3, timeout=10)

"""
import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from datetime import datetime
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.database.database import  comparar_y_guardar, registrar_abogado, agregar_cliente, verificar_cliente_existente
from src.main import ejecutar_proceso

#from database.database import guardar_en_mongo, obtener_info_guardada, comparar_y_guardar
#from src.database.database import guardar_en_mongo,obtener_info_guardada, comparar_y_guardar
# Cargar variables de entorno
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

# Configurar logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Conectar a MongoDB
client = AsyncIOMotorClient(MONGO_URI)
db = client["DataOrbit"]
lawyer_collection = db["lawyer"]
actions_collection = db["acciones"]  

# conversación
NOMBRE, CORREO, TELEFONO = range(3)
CLIENTE_NOMBRE, TIPO_PERSONA, DEPARTAMENTO = range(3, 6)


async def start(update: Update, context):
    """Mensaje de bienvenida y menú inicial."""
    user_id = str(update.effective_user.id)
    
    user = await lawyer_collection.find_one({"telegram_id": user_id})
    
    message = f"👋 ¡Hola {update.effective_user.first_name}! Bienvenido a *DataOrbit* 📡\n\n user "

    if not user:
        message += "Parece que aún no te has registrado. Inscríbete para comenzar.\n"
        keyboard = [[InlineKeyboardButton("📝 Inscribirme en DataOrbit", callback_data="inscribirse")],
                    [InlineKeyboardButton("🗣️ Hablar con un Asesor", callback_data="hablar_asesor")]]
    else:
        message += "Elige una opción para continuar:"
        keyboard = [[InlineKeyboardButton("📋 Inscribir Monitoreo", callback_data="menu_monitoreo")],
                    [InlineKeyboardButton("🗣️ Hablar con un Asesor", callback_data="hablar_asesor")]]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")



async def inscribirse(update: Update, context):
    """Inicia el proceso de inscripción del abogado en DataOrbit."""
    query = update.callback_query
    await query.message.reply_text("📝 *Registro en DataOrbit*\n\nPor favor, envía tu *nombre completo*.")
    return NOMBRE


async def obtener_nombre(update: Update, context):
    """Guarda el nombre del usuario y solicita el correo."""
    context.user_data["nombre"] = update.message.text
    await update.message.reply_text("📧 Ahora envía tu *correo electrónico* (opcional, puedes escribir 'N/A').")
    return CORREO


async def obtener_correo(update: Update, context):
    """Guarda el correo y solicita el teléfono."""
    context.user_data["correo"] = update.message.text
    await update.message.reply_text("📱 Ingresa tu *número de teléfono* (opcional, puedes escribir 'N/A').")
    return TELEFONO


async def obtener_telefono(update: Update, context):
    """Finaliza el registro y guarda en la base de datos."""
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or "No tiene username"
    nombre = context.user_data["nombre"]
    correo = context.user_data["correo"]
    telefono = update.message.text

    await registrar_abogado(user_id, username, nombre, correo, telefono)

    await update.message.reply_text(f"✅ *Registro completado*\n\nGracias {nombre}, tu inscripción ha sido enviada para aprobación.")
    
    return ConversationHandler.END  # Finaliza la conversación


inscripcion_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(inscribirse, pattern="^inscribirse")],
    states={
        NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, obtener_nombre)],
        CORREO: [MessageHandler(filters.TEXT & ~filters.COMMAND, obtener_correo)],
        TELEFONO: [MessageHandler(filters.TEXT & ~filters.COMMAND, obtener_telefono)]
    },
    fallbacks=[]
)

async def volver_inicio(update: Update, context):
    """Regresa al menú principal."""
    query = update.callback_query
    keyboard = [[InlineKeyboardButton("📝 Inscribirme en DataOrbit", callback_data="inscribirse")],
                [InlineKeyboardButton("📋 Inscribir Monitoreo", callback_data="menu_monitoreo")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text("🔙 *Has vuelto al Menú Principal*. Selecciona una opción:", reply_markup=reply_markup, parse_mode="Markdown")


async def handle_text_messages(update: Update, context):
    """Si el usuario envía un mensaje desconocido, mostrar el menú."""
    await start(update, context)


async def menu_monitoreo(update: Update, context):
    """Menú para gestionar el monitoreo."""
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("📝 Inscribir Monitoreo", callback_data="inscribir_monitoreo")],
        [InlineKeyboardButton("🔍 Consultar Estado de Cuenta", callback_data="estado_cuenta")],
        [InlineKeyboardButton("📄 Consultar Radicados", callback_data="consultar_radicados")],
        [InlineKeyboardButton("✅ Activar/Desactivar Monitoreo", callback_data="monitoreo")],
        [InlineKeyboardButton("🗣️ Hablar con un Asesor", callback_data="hablar_asesor")],
        [InlineKeyboardButton("⬅️ Volver al Menú Principal", callback_data="volver_inicio")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("📋 *Menú de Monitoreo:*", reply_markup=reply_markup, parse_mode="Markdown")




async def inscribir_monitoreo(update: Update, context):
    """Inicia el proceso de inscripción para monitoreo."""
    query = update.callback_query
    await query.message.reply_text("📝 *Registro de Monitoreo*\n\nPor favor, envía el *nombre completo de la persona a monitorear*.")
    return CLIENTE_NOMBRE


async def obtener_cliente_nombre(update: Update, context):
    """Guarda el nombre del cliente y solicita el tipo de persona."""
    context.user_data["cliente_nombre"] = update.message.text
    keyboard = [[InlineKeyboardButton("Natural", callback_data="natural")],
                [InlineKeyboardButton("Jurídica", callback_data="juridica")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👥 ¿Tipo de persona?", reply_markup=reply_markup)
    return TIPO_PERSONA


async def obtener_tipo_persona(update: Update, context):
    """Guarda el tipo de persona y solicita el departamento."""
    query = update.callback_query
    context.user_data["tipo_persona"] = query.data.capitalize()
    await query.message.reply_text("📍 Ingresa el *departamento* de la persona a monitorear.")
    return DEPARTAMENTO


async def obtener_departamento(update: Update, context):
    """Finaliza la inscripción y ejecuta el monitoreo."""
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or "No tiene username"
    cliente_nombre = context.user_data["cliente_nombre"]
    tipo_persona = context.user_data["tipo_persona"]
    departamento = update.message.text
    cliente_id = datetime.utcnow()
    radicados_list = []
    cliente_nombre = cliente_nombre.strip().lower()
    # Guardar en la base de datos y ejecutar proceso
    cliente_existe = await verificar_cliente_existente(user_id, cliente_nombre)
    if cliente_existe == False: 

        await agregar_cliente(user_id, cliente_id, cliente_nombre, tipo_persona, departamento, radicados_list=None)
        #await comparar_y_guardar(user_id, username, cliente_id, cliente_nombre, tipo_persona, departamento, radicados_list)
        await update.message.reply_text(f"✅ *Monitoreo registrado*\n\nSe ha añadido a {cliente_nombre} para monitoreo. Un momento por favor")
        await ejecutar_proceso(user_id, username, cliente_id, cliente_nombre, tipo_persona, departamento)
    else:
        await update.message.reply_text(f"cliente {cliente_nombre} existente")
        await start(update, context)
    return ConversationHandler.END



app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# Conversación para inscripción de monitoreo
monitoreo_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(inscribir_monitoreo, pattern="^inscribir_monitoreo")],
    states={
        CLIENTE_NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, obtener_cliente_nombre)],
        TIPO_PERSONA: [CallbackQueryHandler(obtener_tipo_persona, pattern="^(natural|juridica)")],
        DEPARTAMENTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, obtener_departamento)]
    },
    fallbacks=[],
)

app.add_handler(monitoreo_handler)
app.add_handler(CommandHandler("start", start))
app.add_handler(inscripcion_handler)
#app.add_handler(CallbackQueryHandler(inscribirse, pattern="^inscribirse")) 
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
app.add_handler(CallbackQueryHandler(menu_monitoreo, pattern="^menu_monitoreo"))
app.add_handler(CallbackQueryHandler(volver_inicio, pattern="^volver_inicio"))

logging.info("🤖 Bot de Telegram en ejecución...")

app.run_polling(poll_interval=3, timeout=10)