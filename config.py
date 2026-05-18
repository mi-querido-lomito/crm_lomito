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
