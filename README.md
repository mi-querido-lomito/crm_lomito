# CRM Mi Querido Lomito

Sistema web de gestión para una clínica y tienda de mascotas. Desarrollado con Flask y MySQL, reúne la administración de clientes y mascotas, agenda de citas, punto de venta, inventario y control de caja en una sola aplicación.

La aplicación entrega sus pantallas con Flask y Jinja. También incluye rutas JSON para funciones puntuales de la interfaz; no es una API REST pública con una especificación OpenAPI.

## Funcionalidades

- **Clientes y mascotas:** altas, edición, historial de atención, fotografías y revisión de registros duplicados.
- **Agenda:** gestión de citas, búsqueda de servicios y consulta de la agenda diaria.
- **Punto de venta:** ventas de productos y servicios, tickets imprimibles y operación con contexto de venta independiente.
- **Inventario:** productos, insumos, proveedores, entradas de inventario, códigos de barras y etiquetas.
- **Caja y reportes:** apertura y cierre de caja, gastos, cortes y reportes de ventas.
- **Acceso:** inicio de sesión, sesiones autenticadas y control de acceso por rol.
- **Archivos:** almacenamiento opcional de fotografías en Google Drive.
- **Clientes de escritorio y móvil:** los proyectos de `desktop_app/` y `mobile_app/` envuelven el sitio web desplegado; el servidor sigue ejecutando Flask y MySQL.

## Tecnologías

- Python 3.12 (ver `runtime.txt`)
- Flask, Flask-Login y Flask-MySQLdb
- MySQL
- Jinja y plantillas HTML
- Gunicorn para despliegue
- Google Drive API opcional para fotografías

## Requisitos

- Python 3.12
- MySQL con una base de datos preparada para el CRM
- `pip` y un entorno virtual de Python

En Windows, los comandos siguientes se ejecutan desde la carpeta del repositorio. En macOS o Linux, activa el entorno con `source .venv/bin/activate`.

## Instalación local

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Configura las variables de entorno descritas abajo y ejecuta la aplicación en modo de desarrollo:

```powershell
flask --app app run --debug
```

Abre `http://127.0.0.1:5000` en el navegador. El modo `--debug` es solo para desarrollo local; no lo uses en producción.

## Configuración

La aplicación carga variables desde el entorno o desde un archivo `.env` en la raíz. Crea ese archivo localmente y **no incluyas secretos ni credenciales reales en Git**.

| Variable | Requerida | Descripción |
| --- | --- | --- |
| `DB_HOST` | Sí | Host del servidor MySQL. |
| `DB_PORT` | No | Puerto MySQL; por defecto `3306`. |
| `DB_USER` | Sí | Usuario de MySQL. |
| `DB_PASSWORD` | Sí | Contraseña de MySQL. |
| `DB_NAME` | Sí | Nombre de la base de datos. |
| `FLASK_SECRET_KEY` | Sí | Clave larga, aleatoria y privada para proteger las sesiones de Flask. |
| `GOOGLE_DRIVE_FOLDER_ID` | No | Carpeta destino de imágenes en Google Drive. |
| `GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON` | No | Credenciales de cuenta de servicio en formato JSON. |
| `GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON_B64` | No | Alternativa: credenciales JSON codificadas en Base64. |
| `GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE` | No | Ruta a un archivo de credenciales de cuenta de servicio. |
| `GOOGLE_DRIVE_OAUTH_CLIENT_ID` | No | ID OAuth para acceso a Google Drive. |
| `GOOGLE_DRIVE_OAUTH_CLIENT_SECRET` | No | Secreto OAuth para acceso a Google Drive. |
| `GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN` | No | Token de actualización OAuth. |
| `GOOGLE_DRIVE_OAUTH_TOKEN_URI` | No | URL de token OAuth; por defecto la de Google. |
| `MASCOTAS_FOTO_MAX_BYTES` | No | Límite de tamaño de foto de mascota; por defecto 8 MiB. |
| `MAX_CONTENT_LENGTH` | No | Tamaño máximo de solicitud; por defecto 16 MiB. |

Ejemplo de `.env` sin valores reales:

```dotenv
DB_HOST=localhost
DB_PORT=3306
DB_USER=usuario_local
DB_PASSWORD=contraseña_local
DB_NAME=crm_lomito
FLASK_SECRET_KEY=reemplaza-por-una-clave-aleatoria-larga
```

Si no configuras Google Drive, la integración de fotografías en Drive no estará disponible. Las credenciales deben mantenerse privadas y fuera del repositorio.

## Base de datos

La aplicación requiere una base MySQL con tablas para usuarios, clientes, mascotas, citas, productos, servicios, ventas, inventario y caja, entre otras. El código verifica y prepara algunos elementos del esquema al iniciar, pero no sustituye la configuración inicial de la base ni las migraciones de datos.

Los respaldos SQL y scripts de migración que se encuentran en este repositorio pueden contener datos o cambios específicos del entorno. Revisa su contenido y haz un respaldo antes de aplicar cualquier SQL. No los ejecutes automáticamente en una base de producción.

## Rutas principales

Las pantallas principales están protegidas por inicio de sesión. El acceso a ciertas operaciones también depende del rol del usuario.

| Ruta | Uso |
| --- | --- |
| `/login` | Inicio de sesión. |
| `/dashboard` | Resumen principal. |
| `/clientes` | Gestión de clientes. |
| `/mascotas` | Gestión de mascotas. |
| `/citas` | Agenda de citas. |
| `/productos` | Catálogo de productos. |
| `/servicios` | Catálogo de servicios. |
| `/insumos` | Inventario de insumos. |
| `/proveedores` | Proveedores. |
| `/ventas` | Punto de venta. |
| `/abrir_caja` y `/cerrar_caja` | Operación de caja. |
| `/gastos` y `/capital` | Gastos y saldos. |

Rutas JSON utilizadas por la interfaz:

| Ruta | Uso |
| --- | --- |
| `GET /api/servicios/buscar` | Busca servicios para la agenda o el flujo de atención. |
| `GET /api/agenda_dia` | Consulta información de la agenda diaria. |

Estas rutas forman parte de la aplicación web y requieren la sesión y los permisos correspondientes. Para conocer parámetros y formatos exactos, consulta sus implementaciones en `app.py`.

## Despliegue

El repositorio incluye un `Procfile` para plataformas compatibles con procesos web:

```text
gunicorn app:app --workers=1 --worker-class=gthread --threads=4 --timeout=120
```

Configura en la plataforma las mismas variables de entorno, habilita conexión segura a MySQL y mantén `FLASK_SECRET_KEY` y las credenciales de base de datos en el almacén privado de secretos del proveedor. No uses el servidor de desarrollo de Flask en producción.

## Estructura del repositorio

```text
app.py          Aplicación Flask, rutas y lógica de negocio
config.py       Configuración desde variables de entorno
templates/      Plantillas de la interfaz
static/         Recursos estáticos
desktop_app/    Contenedor de escritorio para Windows
mobile_app/     Aplicación móvil basada en Capacitor
```

## Aplicaciones complementarias

`desktop_app/README.md` documenta la compilación del cliente de escritorio para Windows. `mobile_app/README.md` contiene instrucciones para compilar los clientes Android e iOS. Ambos muestran la aplicación web alojada y requieren configurar la URL del servidor correspondiente.

## Seguridad

- `.env`, archivos de credenciales y archivos SQL están excluidos del control de versiones mediante `.gitignore`.
- No publiques archivos con contraseñas, tokens, datos personales ni respaldos de producción.
- Si un secreto se expuso o se versionó, rótalo en el servicio correspondiente; borrar el archivo en un commit posterior no lo elimina del historial de Git.
- Usa HTTPS en el despliegue y contraseñas robustas para las cuentas de aplicación y base de datos.

## Licencia

No se especifica una licencia en este repositorio. Añade un archivo `LICENSE` para indicar los permisos de uso y distribución.
