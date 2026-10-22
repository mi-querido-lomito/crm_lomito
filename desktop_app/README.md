# CRM Mi Querido Lomito - App de Escritorio (Windows)

Ventana nativa que carga el CRM (ya desplegado en tu servidor) usando WebView2.
Primero abre la ventana general; después de iniciar sesión abre automáticamente
otra ventana dedicada al punto de venta. Ambas usan la misma sesión del servidor,
y cada ventana conserva su propio carrito. No corre Flask ni MySQL en la PC del
usuario; solo muestra el sitio en una ventana sin barra de navegador.
El perfil WebView2 compartido se guarda en `%LOCALAPPDATA%\MiQueridoLomitoCRM\WebView2`
para conservar la sesión entre las dos ventanas.

## Compilar el .exe

```
pip install -r requirements-desktop.txt
pyinstaller --onefile --windowed --name "MiQueridoLomitoCRM" --icon icon.ico main.py
```

El ejecutable queda en `dist/MiQueridoLomitoCRM.exe`. El icono (`icon.ico`)
esta generado a partir de `static/img/icon-512.png`; si cambias el logo,
regenera el .ico con Pillow:

```
python -c "from PIL import Image; Image.open('../static/img/icon-512.png').save('icon.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])"
```

## Compilar el instalador (NSIS)

El .exe de arriba es portable (no se "instala"). Para generar un instalador
real con accesos directos, icono y desinstalador desde "Agregar o quitar
programas", usa NSIS (https://nsis.sourceforge.io/):

```
makensis installer.nsi
```

Genera `dist/MiQueridoLomitoCRM_Setup.exe`. Requiere que ya exista
`dist/MiQueridoLomitoCRM.exe` (compilalo primero con PyInstaller, ver
arriba). El instalador:

- No requiere permisos de administrador (instala en
  `%LOCALAPPDATA%\MiQueridoLomitoCRM`, por usuario).
- Crea accesos directos en el Menu Inicio y en el Escritorio.
- Registra un desinstalador visible en "Agregar o quitar programas".

La versión del instalador es 1.1.0. Para validar el paquete sin crear accesos
directos ni tocar el registro del usuario, puede compilarse una variante de
prueba y darle un destino aislado:

```
makensis /DINSTALLER_TEST_MODE installer.nsi
dist\MiQueridoLomitoCRM_Setup_Test.exe /S /D=%TEMP%\LomitoCRM-Test
```

La variante de prueba conserva los mismos archivos de aplicación, icono y
desinstalador, pero omite accesos directos y claves de desinstalación del
registro.

## Configurar la URL del servidor

Al ejecutarlo por primera vez, se crea un archivo `lomito_config.json`
junto al .exe con este contenido:

```json
{ "url": "https://CAMBIA-ESTA-URL-POR-LA-DE-TU-SERVIDOR.com" }
```

Si necesitas apuntar a otra URL, edita `main.py` (constante `DEFAULT_URL`)
antes de compilar, o edita `lomito_config.json` despues de instalar y
vuelve a abrir la app. También puedes fijarla con la variable de entorno
`LOMITO_APP_URL` antes de lanzar el ejecutable.

## Requisitos del equipo donde se instale

Windows 10/11 con el runtime "WebView2" (viene preinstalado en Windows 10/11
actualizados; si falta, Windows lo descarga automáticamente o se instala
desde https://developer.microsoft.com/microsoft-edge/webview2/).

En la versión web, usa **Abrir venta aparte** en la barra superior para abrir
el punto de venta en otra pestaña con un carrito independiente. La apertura
automática del segundo espacio se reserva al ejecutable para evitar popups y
no abrir ventanas inesperadas en Android o iOS.
