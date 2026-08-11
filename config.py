import os

class Config:
    MYSQL_HOST = os.getenv('DB_HOST', 'ns1.solucionesefectivas.com.mx')
    MYSQL_PORT = int(os.getenv('DB_PORT', 3306))
    MYSQL_USER = os.getenv('DB_USER', 'siste234_America9206')
    MYSQL_PASSWORD = os.getenv('DB_PASSWORD', 'Lomitos.2025!')
    MYSQL_DB = os.getenv('DB_NAME', 'siste234_Mi_querido_lomito')
    MYSQL_UNIX_SOCKET = None
    MYSQL_CONNECT_TIMEOUT = 5
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "SistemasRacks.23")
    GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
    GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON", "")
    GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON_B64 = os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON_B64", "")
    GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE", "")
    MASCOTAS_FOTO_MAX_BYTES = int(os.getenv("MASCOTAS_FOTO_MAX_BYTES", 8 * 1024 * 1024))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))
