import os

class Config:
    SECRET_KEY = os.environ.get("SistemasRacks.23") 
    MYSQL_HOST = os.environ.get("ns1.solucionesefectivas.com.mx")
    MYSQL_PORT = os.environ.get("3306")
    MYSQL_USER = os.environ.get("siste234_America9206")
    MYSQL_PASSWORD = os.environ.get("Lomitos.2025!")
    MYSQL_DB = os.environ.get("siste234_Mi_querido_lomito")
    
