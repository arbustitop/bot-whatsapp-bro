"""
Bot de WhatsApp para Bro Sublimados
Flask + Twilio + Google Sheets
Servicio 24/7 de sublimación y DTF
"""

import os
import logging
from datetime import datetime
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Importar templates de mensajes
from templates.mensajes import (
    MENU_PRINCIPAL,
    SUBLIMACION_INFO,
    DTF_INFO,
    CONSULTA_PEDIDO,
    HABLAR_HUMANO,
    PEDIDO_CONFIRMADO,
    ESTADO_PEDIDO,
    PEDIDO_NO_ENCONTRADO,
    MENSAJE_NO_ENTENDIDO
)

# Inicializar Flask
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'bro-sublimados-secret-key')

# Configuración del negocio
BUSINESS_NAME = os.getenv('BUSINESS_NAME', 'Bro Sublimados')
BUSINESS_PHONE = os.getenv('BUSINESS_PHONE', '+5491112345678')
BUSINESS_HOURS = os.getenv('BUSINESS_HOURS', 'Lunes a Viernes 9:00 - 18:00, Sábados 9:00 - 13:00')

# Constantes
MIN_ORDER_DESCRIPTION_LENGTH = 5

# Estados posibles del usuario
class UserState:
    MENU = 'menu'
    SUBLIMACION = 'sublimacion'
    DTF = 'dtf'
    CONSULTA = 'consulta'
    HUMANO = 'humano'
    ESPERANDO_PEDIDO_SUBLIMACION = 'esperando_pedido_sublimacion'
    ESPERANDO_PEDIDO_DTF = 'esperando_pedido_dtf'
    ESPERANDO_CONSULTA = 'esperando_consulta'

# Diccionario para mantener el estado de cada usuario (por número de teléfono)
# NOTA: Para producción con múltiples instancias, considerar usar Redis o una base de datos
# Este almacenamiento en memoria no persiste entre reinicios del servidor
user_states = {}

# Google Sheets integration
sheets_client = None


def normalize_phone_number(phone):
    """
    Normaliza un número de teléfono eliminando caracteres no numéricos
    excepto el signo + al inicio
    """
    if not phone:
        return ""
    # Eliminar espacios, guiones, paréntesis y otros caracteres
    import re
    # Mantener solo dígitos y el + inicial si existe
    normalized = re.sub(r'[^\d+]', '', phone)
    # Asegurar que solo haya un + al inicio
    if normalized.startswith('+'):
        normalized = '+' + normalized[1:].replace('+', '')
    else:
        normalized = normalized.replace('+', '')
    return normalized

def init_google_sheets():
    """Inicializa la conexión con Google Sheets"""
    global sheets_client
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        
        credentials_file = os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE', 'credentials.json')
        
        if not os.path.exists(credentials_file):
            logger.warning(f"Archivo de credenciales '{credentials_file}' no encontrado. Google Sheets deshabilitado.")
            return None
        
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        credentials = Credentials.from_service_account_file(credentials_file, scopes=scopes)
        sheets_client = gspread.authorize(credentials)
        
        spreadsheet_name = os.getenv('GOOGLE_SHEETS_SPREADSHEET_NAME', 'Pedidos_Bro_Sublimados')
        
        try:
            spreadsheet = sheets_client.open(spreadsheet_name)
        except gspread.SpreadsheetNotFound:
            logger.warning(f"Spreadsheet '{spreadsheet_name}' no encontrada. Creando una nueva...")
            spreadsheet = sheets_client.create(spreadsheet_name)
            # Crear encabezados
            worksheet = spreadsheet.sheet1
            worksheet.update('A1:F1', [['Fecha', 'Cliente', 'Teléfono', 'Tipo', 'Detalles', 'Estado']])
        
        logger.info(f"Google Sheets conectado: {spreadsheet_name}")
        return spreadsheet
    except ImportError:
        logger.warning("gspread no instalado. Google Sheets deshabilitado.")
        return None
    except Exception as e:
        logger.error(f"Error al conectar con Google Sheets: {e}")
        return None

def get_spreadsheet():
    """Obtiene o crea la conexión con Google Sheets"""
    global sheets_client
    if sheets_client is None:
        return init_google_sheets()
    try:
        spreadsheet_name = os.getenv('GOOGLE_SHEETS_SPREADSHEET_NAME', 'Pedidos_Bro_Sublimados')
        return sheets_client.open(spreadsheet_name)
    except Exception as e:
        logger.error(f"Error al obtener spreadsheet: {e}")
        return init_google_sheets()

def guardar_pedido(cliente, telefono, tipo, detalles):
    """
    Guarda un pedido en Google Sheets
    Returns: número de pedido
    """
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            logger.warning("No se pudo guardar el pedido en Google Sheets")
            return f"LOCAL-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        worksheet = spreadsheet.sheet1
        fecha = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        estado = 'Pendiente'
        
        # Obtener la siguiente fila disponible
        all_values = worksheet.get_all_values()
        next_row = len(all_values) + 1
        numero_pedido = next_row - 1  # Restamos 1 porque la primera fila son encabezados
        
        # Agregar el pedido
        worksheet.append_row([fecha, cliente, telefono, tipo, detalles, estado])
        
        logger.info(f"Pedido #{numero_pedido} guardado en Google Sheets")
        return str(numero_pedido)
    except Exception as e:
        logger.error(f"Error al guardar pedido: {e}")
        return f"ERROR-{datetime.now().strftime('%Y%m%d%H%M%S')}"

def buscar_pedido(consulta):
    """
    Busca un pedido por número de pedido o teléfono
    Returns: dict con información del pedido o None
    """
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return None
        
        worksheet = spreadsheet.sheet1
        all_values = worksheet.get_all_values()
        
        # Normalizar la consulta
        consulta_normalizada = normalize_phone_number(consulta)
        
        # Saltamos la primera fila (encabezados)
        for i, row in enumerate(all_values[1:], start=1):
            if len(row) >= 6:
                fecha, cliente, telefono, tipo, detalles, estado = row[:6]
                telefono_normalizado = normalize_phone_number(telefono)
                # Buscar por número de pedido o teléfono normalizado
                if str(i) == consulta or (telefono_normalizado and consulta_normalizada and 
                    (telefono_normalizado == consulta_normalizada or 
                     telefono_normalizado.endswith(consulta_normalizada) or 
                     consulta_normalizada.endswith(telefono_normalizado))):
                    return {
                        'numero_pedido': str(i),
                        'fecha': fecha,
                        'cliente': cliente,
                        'tipo': tipo,
                        'detalles': detalles,
                        'estado': estado
                    }
        return None
    except Exception as e:
        logger.error(f"Error al buscar pedido: {e}")
        return None

def get_user_state(phone_number):
    """Obtiene el estado actual del usuario"""
    return user_states.get(phone_number, {'state': UserState.MENU, 'data': {}})

def set_user_state(phone_number, state, data=None):
    """Establece el estado del usuario"""
    user_states[phone_number] = {
        'state': state,
        'data': data or {}
    }

def process_message(phone_number, message, sender_name='Cliente'):
    """
    Procesa el mensaje del usuario y retorna la respuesta apropiada
    """
    message = message.strip().lower()
    user_data = get_user_state(phone_number)
    current_state = user_data['state']
    
    logger.info(f"Usuario {phone_number} - Estado: {current_state} - Mensaje: {message}")
    
    # Comando para volver al menú principal
    if message == '0' or message == 'menu' or message == 'hola':
        set_user_state(phone_number, UserState.MENU)
        return MENU_PRINCIPAL.format(horario=BUSINESS_HOURS)
    
    # Procesar según el estado actual
    if current_state == UserState.MENU:
        return process_menu_option(phone_number, message)
    elif current_state == UserState.ESPERANDO_PEDIDO_SUBLIMACION:
        return process_pedido(phone_number, message, 'Sublimación', sender_name)
    elif current_state == UserState.ESPERANDO_PEDIDO_DTF:
        return process_pedido(phone_number, message, 'DTF', sender_name)
    elif current_state == UserState.ESPERANDO_CONSULTA:
        return process_consulta(phone_number, message)
    elif current_state == UserState.HUMANO:
        # En modo humano, simplemente confirmar que el mensaje fue recibido
        return "📨 Tu mensaje fue recibido. Un representante te responderá pronto.\n\nEnviá *0* para volver al menú."
    else:
        return MENSAJE_NO_ENTENDIDO

def process_menu_option(phone_number, message):
    """Procesa las opciones del menú principal"""
    if message == '1' or 'sublimacion' in message or 'sublimación' in message:
        set_user_state(phone_number, UserState.ESPERANDO_PEDIDO_SUBLIMACION)
        return SUBLIMACION_INFO
    elif message == '2' or 'dtf' in message:
        set_user_state(phone_number, UserState.ESPERANDO_PEDIDO_DTF)
        return DTF_INFO
    elif message == '3' or 'consultar' in message or 'pedido' in message:
        set_user_state(phone_number, UserState.ESPERANDO_CONSULTA)
        return CONSULTA_PEDIDO
    elif message == '4' or 'humano' in message or 'persona' in message or 'hablar' in message:
        set_user_state(phone_number, UserState.HUMANO)
        return HABLAR_HUMANO.format(telefono_negocio=BUSINESS_PHONE, horario=BUSINESS_HOURS)
    else:
        return MENSAJE_NO_ENTENDIDO

def process_pedido(phone_number, message, tipo, sender_name):
    """Procesa un pedido de sublimación o DTF"""
    if len(message) < MIN_ORDER_DESCRIPTION_LENGTH:
        return f"📝 Por favor, describí tu pedido con más detalle.\n\nIncluí:\n• Producto\n• Cantidad\n• Descripción del diseño\n\nO enviá *0* para volver al menú."
    
    # Guardar el pedido
    numero_pedido = guardar_pedido(sender_name, phone_number, tipo, message)
    
    # Volver al estado de menú
    set_user_state(phone_number, UserState.MENU)
    
    fecha = datetime.now().strftime('%d/%m/%Y %H:%M')
    return PEDIDO_CONFIRMADO.format(
        tipo=tipo,
        detalles=message[:100] + ('...' if len(message) > 100 else ''),
        fecha=fecha,
        numero_pedido=numero_pedido,
        horario=BUSINESS_HOURS
    )

def process_consulta(phone_number, message):
    """Procesa una consulta de estado de pedido"""
    # Limpiar el mensaje para buscar
    consulta = message.replace('#', '').replace('-', '').strip()
    
    # Buscar el pedido
    pedido = buscar_pedido(consulta)
    
    if pedido:
        set_user_state(phone_number, UserState.MENU)
        return ESTADO_PEDIDO.format(**pedido)
    else:
        return PEDIDO_NO_ENCONTRADO

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Endpoint principal para recibir mensajes de WhatsApp via Twilio
    """
    try:
        # Obtener datos del mensaje
        incoming_msg = request.values.get('Body', '').strip()
        sender_phone = request.values.get('From', '')
        sender_name = request.values.get('ProfileName', 'Cliente')
        
        logger.info(f"Mensaje recibido de {sender_phone} ({sender_name}): {incoming_msg}")
        
        # Procesar el mensaje
        response_text = process_message(sender_phone, incoming_msg, sender_name)
        
        # Crear respuesta de Twilio
        resp = MessagingResponse()
        msg = resp.message()
        msg.body(response_text)
        
        return str(resp)
    except Exception as e:
        logger.error(f"Error en webhook: {e}")
        resp = MessagingResponse()
        msg = resp.message()
        msg.body("❌ Ocurrió un error. Por favor, intentá de nuevo o enviá *0* para ver el menú.")
        return str(resp)

@app.route('/health', methods=['GET'])
def health():
    """Endpoint para verificar que el servicio está activo"""
    return {
        'status': 'ok',
        'service': 'Bro Sublimados WhatsApp Bot',
        'timestamp': datetime.now().isoformat()
    }

@app.route('/', methods=['GET'])
def home():
    """Página principal"""
    return f"""
    <html>
        <head>
            <title>Bro Sublimados - WhatsApp Bot</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
                h1 {{ color: #25D366; }}
                .status {{ background: #e8f5e9; padding: 20px; border-radius: 10px; }}
                code {{ background: #f5f5f5; padding: 2px 6px; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <h1>🎨 {BUSINESS_NAME} - WhatsApp Bot</h1>
            <div class="status">
                <h2>✅ Bot Activo</h2>
                <p>El bot de WhatsApp está funcionando correctamente.</p>
                <p><strong>Webhook URL:</strong> <code>/webhook</code></p>
                <p><strong>Health Check:</strong> <code>/health</code></p>
            </div>
            <h3>📋 Servicios disponibles:</h3>
            <ul>
                <li>🌈 Sublimación</li>
                <li>🔥 DTF (Direct to Film)</li>
                <li>🔍 Consulta de pedidos</li>
                <li>🧑‍💼 Atención personalizada</li>
            </ul>
            <p><em>Horario: {BUSINESS_HOURS}</em></p>
        </body>
    </html>
    """

if __name__ == '__main__':
    # Inicializar Google Sheets al arrancar
    init_google_sheets()
    
    # Obtener puerto del entorno o usar 5000 por defecto
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Iniciando {BUSINESS_NAME} WhatsApp Bot en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
