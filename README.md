# 🎨 Bot WhatsApp - Bro Sublimados

Bot de WhatsApp 24/7 para **Bro Sublimados** - Especialistas en sublimación y DTF.

## 📋 Características

- ✅ Menú interactivo con 4 opciones principales
- ✅ Gestión de estados por número de teléfono
- ✅ Registro automático de pedidos en Google Sheets
- ✅ Respuestas rápidas con emojis
- ✅ Información de horarios y precios
- ✅ Consulta de estado de pedidos
- ✅ Opción de contacto humano

## 🛠️ Tecnologías

- **Flask** - Framework web Python
- **Twilio** - API de WhatsApp
- **gspread** - Integración con Google Sheets
- **ngrok** - Túnel para desarrollo local

## 📁 Estructura del Proyecto

```
bot-whatsapp-bro/
├── app.py                  # Aplicación principal Flask
├── requirements.txt        # Dependencias Python
├── .env.example           # Ejemplo de variables de entorno
├── credentials.json       # Credenciales de Google (NO incluir en git)
├── templates/
│   ├── __init__.py
│   └── mensajes.py        # Templates de mensajes
└── README.md
```

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/arbustitop/bot-whatsapp-bro.git
cd bot-whatsapp-bro
```

### 2. Crear entorno virtual

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus credenciales
```

## 🔐 Configuración de Credenciales

### Twilio (WhatsApp API)

1. Crear cuenta en [Twilio](https://www.twilio.com/)
2. Activar el sandbox de WhatsApp en la consola
3. Obtener `ACCOUNT_SID` y `AUTH_TOKEN`
4. Configurar en `.env`:

```env
TWILIO_ACCOUNT_SID=tu_account_sid
TWILIO_AUTH_TOKEN=tu_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

### Google Sheets (gspread)

1. Ir a [Google Cloud Console](https://console.cloud.google.com/)
2. Crear un nuevo proyecto
3. Habilitar la API de Google Sheets
4. Habilitar la API de Google Drive
5. Crear credenciales de cuenta de servicio:
   - Ir a "Credenciales" > "Crear credenciales" > "Cuenta de servicio"
   - Descargar el archivo JSON
   - Renombrarlo a `credentials.json` y colocarlo en la raíz del proyecto

6. Compartir el spreadsheet con el email de la cuenta de servicio:
   - Abrir el archivo `credentials.json`
   - Copiar el valor de `client_email`
   - Crear un Google Sheet llamado "Pedidos_Bro_Sublimados"
   - Compartirlo con ese email dándole permisos de editor

```env
GOOGLE_SHEETS_CREDENTIALS_FILE=credentials.json
GOOGLE_SHEETS_SPREADSHEET_NAME=Pedidos_Bro_Sublimados
```

## 🌐 Configuración de ngrok

ngrok permite exponer tu servidor local a internet para recibir webhooks de Twilio.

### 1. Instalar ngrok

```bash
# macOS
brew install ngrok

# Windows (con chocolatey)
choco install ngrok

# O descargar desde https://ngrok.com/download
```

### 2. Autenticar ngrok

```bash
ngrok config add-authtoken TU_AUTH_TOKEN
```

### 3. Iniciar el túnel

```bash
# En una terminal
python app.py

# En otra terminal
ngrok http 5000
```

### 4. Configurar webhook en Twilio

1. Copiar la URL de ngrok (ej: `https://abc123.ngrok.io`)
2. Ir a Twilio Console > Messaging > Settings > WhatsApp Sandbox
3. En "When a message comes in", pegar: `https://abc123.ngrok.io/webhook`
4. Método: POST

## 📱 Menú del Bot

| Opción | Descripción |
|--------|-------------|
| 1️⃣ | Sublimación - Info y pedidos de sublimación |
| 2️⃣ | DTF - Info y pedidos de DTF |
| 3️⃣ | Consultar pedido - Buscar estado de pedido |
| 4️⃣ | Hablar con humano - Contacto personalizado |
| 0️⃣ | Volver al menú principal |

## 📊 Google Sheets - Estructura

Los pedidos se guardan con las siguientes columnas:

| Columna | Descripción |
|---------|-------------|
| Fecha | Fecha y hora del pedido |
| Cliente | Nombre del cliente (ProfileName de WhatsApp) |
| Teléfono | Número de WhatsApp del cliente |
| Tipo | "Sublimación" o "DTF" |
| Detalles | Descripción del pedido |
| Estado | Estado del pedido (Pendiente, En proceso, Listo, Entregado) |

## 🖥️ Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Página de inicio con estado del bot |
| `/webhook` | POST | Webhook para recibir mensajes de WhatsApp |
| `/health` | GET | Health check para monitoreo |

## 🚀 Ejecutar en Producción

### Con Gunicorn

```bash
gunicorn app:app -w 4 -b 0.0.0.0:5000
```

### Con Docker (opcional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "app:app", "-w", "4", "-b", "0.0.0.0:5000"]
```

## 📝 Variables de Entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `TWILIO_ACCOUNT_SID` | SID de cuenta Twilio | - |
| `TWILIO_AUTH_TOKEN` | Token de autenticación Twilio | - |
| `TWILIO_WHATSAPP_NUMBER` | Número de WhatsApp Twilio | `whatsapp:+14155238886` |
| `GOOGLE_SHEETS_CREDENTIALS_FILE` | Archivo de credenciales Google | `credentials.json` |
| `GOOGLE_SHEETS_SPREADSHEET_NAME` | Nombre del spreadsheet | `Pedidos_Bro_Sublimados` |
| `FLASK_SECRET_KEY` | Clave secreta Flask | Auto-generada |
| `FLASK_DEBUG` | Modo debug | `False` |
| `BUSINESS_NAME` | Nombre del negocio | `Bro Sublimados` |
| `BUSINESS_PHONE` | Teléfono del negocio | `+5491112345678` |
| `BUSINESS_HOURS` | Horario de atención | `Lunes a Viernes 9:00 - 18:00...` |
| `PORT` | Puerto del servidor | `5000` |

## 🔧 Troubleshooting

### El bot no responde
- Verificar que ngrok esté corriendo
- Verificar que la URL del webhook en Twilio sea correcta
- Revisar los logs de Flask

### Error de Google Sheets
- Verificar que el archivo `credentials.json` existe
- Verificar que el spreadsheet está compartido con la cuenta de servicio
- Revisar que los nombres de spreadsheet coincidan

### Error de Twilio
- Verificar credenciales en `.env`
- Verificar que el sandbox esté activo
- Revisar el dashboard de Twilio para errores

## 📄 Licencia

MIT License - Bro Sublimados © 2024

## 👨‍💻 Autor

Desarrollado para **Bro Sublimados** - Tu idea, nuestra pasión ✨
