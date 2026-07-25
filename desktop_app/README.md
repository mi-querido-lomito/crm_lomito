# CRM Mi Querido Lomito - App de Escritorio (Windows)

Ventana nativa que carga el CRM (ya desplegado en tu servidor) usando WebView2.
No corre Flask ni MySQL en la PC del usuario; solo muestra el sitio en una
ventana sin barra de navegador, como una app instalada.

## Compilar el .exe

```
pip install -r requirements-desktop.txt
pyinstaller --onefile --windowed --name "MiQueridoLomitoCRM" --icon icon.ico main.py
```

El ejecutable queda en `dist/MiQueridoLomitoCRM.exe`.

## Configurar la URL del servidor

Al ejecutarlo por primera vez, se crea un archivo `lomito_config.json`
junto al .exe con este contenido:

```json
{ "url": "https://CAMBIA-ESTA-URL-POR-LA-DE-TU-SERVIDOR.com" }
```

Edita ese archivo y coloca la URL real de tu backend desplegado, luego
vuelve a abrir la app. También puedes fijarla con la variable de entorno
`LOMITO_APP_URL` antes de lanzar el ejecutable.

## Requisitos del equipo donde se instale

Windows 10/11 con el runtime "WebView2" (viene preinstalado en Windows 10/11
actualizados; si falta, Windows lo descarga automáticamente o se instala
desde https://developer.microsoft.com/microsoft-edge/webview2/).
