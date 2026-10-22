# Reporte de pruebas e incidencias

Fecha: 21 de octubre de 2026

## Incidencias corregidas

1. **El carrito no ejecutaba finalizar, quitar o vaciar.** El indicador global de carga deshabilitaba el botón que originó el envío antes de que el navegador serializara el formulario. Al quedar fuera del POST el nombre del botón (`finalizar`, `eliminar` o `vaciar`), Flask no reconocía la acción. El indicador ahora conserva habilitado ese botón; el formulario ya bloquea reenvíos repetidos.
2. **Dos ventanas compartían el carrito y el vínculo de cita.** Cada contexto de punto de venta ahora guarda carrito, mascota y cita por separado. La ventana general conserva el carrito anterior para compatibilidad con sesiones existentes. Los formularios y el regreso desde el ticket conservan el contexto de su ventana.
3. **Las dos ventanas del ejecutable pedían iniciar sesión por separado.** El `.exe` abre la ventana general; al completar el login, esta llama al puente local y abre el POS. WebView2 comparte un perfil persistente de cookies. En navegador se conserva el acceso manual **Abrir venta aparte**, evitando popups automáticos y aperturas inesperadas en móviles.
4. **El cierre de caja incluía ventas con tarjeta y transferencia en el efectivo esperado.** Ahora el efectivo esperado es monto inicial + ventas en efectivo − gastos pagados en efectivo.
5. **Los gastos no guardaban el medio de pago.** Los nuevos gastos requieren Efectivo, Tarjeta o Transferencia. Se agregó **Capital** con los saldos netos y el historial de ventas y gastos por medio.
   Los gastos históricos no tienen medio de pago en sus datos y aparecen como “Sin especificar”; no se asignan a una cuenta por suposición.
6. **Capital mostraba “Ocurrió un error inesperado” en producción.** Se reemplazó la consulta combinada `UNION ALL` por lecturas separadas de ventas y gastos para evitar incompatibilidades entre las columnas de ambas tablas; además, el cursor se cierra aunque falle una lectura.

## Pruebas ejecutadas

Todas las pruebas siguientes se hicieron localmente con una conexión MySQL simulada; no escribieron datos en la base de producción.

- `python -m compileall -q app.py desktop_app\main.py` — correcto.
- `python -m py_compile app.py desktop_app\main.py` tras los cambios de caja, capital y sesión — correcto.
- Flujo POS simulado: agregar un servicio, quitarlo, agregarlo de nuevo y finalizarlo — correcto; se generaron las operaciones esperadas para encabezado y detalle de venta.
- Contexto POS — correcto; el POST y la URL del ticket conservaron el identificador de ventana.
- Impresión HTML — ambas copias del ticket se renderizaron y regresaron a la ventana de venta correcta.
- Búsqueda de servicios — precio exacto y rechazo de un rango mínimo/máximo invertido — correctos.
- Importación de `app.py` — correcta; Flask registró 61 rutas.
- Dependencias de escritorio instaladas en `desktop_app/venv`: pywebview 6.2.1 y PyInstaller 6.21.0.
- Ejecutable recompilado en `desktop_app/dist/MiQueridoLomitoCRM.exe` (12,882,473 bytes; compilación PyInstaller 6.21.0 correcta). En la prueba de arranque el proceso siguió activo durante 8 segundos y se detectaron 24 procesos de WebView2; el título de la ventana no quedó accesible a la consulta automatizada.
- Smoke check posterior: importación de Flask y compilación Jinja de las cinco plantillas modificadas — correctos; rutas `/desktop_session`, `/capital`, `/cerrar_caja` y `/gastos` registradas.
- Prueba aislada de `/capital` con ventas, gastos con medio y gastos históricos sin medio: saldos netos e historial renderizados correctamente. No se conectó ni escribió en la base de producción.
- Revisión general tras el cambio: las 63 rutas Flask registradas, todas las plantillas Jinja compiladas, `py_compile` y `git diff --check` — correctos.
- Instalador de Windows: NSIS 3.13 generó `desktop_app/dist/MiQueridoLomitoCRM_Setup.exe` (versión 1.1.0). La variante aislada instaló el ejecutable, icono y desinstalador en una carpeta temporal; el desinstalador terminó con código 0. La prueba omitió accesos directos y registro de usuario. El instalador no contiene ni modifica la API.
- Arranque desde la copia instalada: el proceso permaneció activo y generó procesos WebView2. No se completó login ni se ejecutaron operaciones contra la API.
- WebView2 Runtime detectado en Windows, versión `155.0.4283.62`.
- Prueba de solo lectura desde dos WebViews conectados al servidor desplegado: la ventana general recibió `302` en `/` y `200` en `/login`; la ventana POS recibió `302` en `/ventas/ventana` y `200` en `/login`. El redireccionamiento al login confirma que el POS está desplegado y exige autenticación.
- En una prueba anterior, el ejecutable creó dos ventanas y lanzó procesos `msedgewebview2.exe`; esa compilación anterior todavía solicitaba login en cada ventana. La compilación actual cambia el flujo para abrir el POS tras autenticarse.

## Verificación pendiente en el entorno instalado

- Completar una venta y cobrar una cita contra la base real, usando una cuenta de prueba y verificando la venta y sus detalles en el historial.
- Imprimir físicamente una copia de cliente y otra de negocio. La impresión automática depende del navegador/WebView y de la impresora configurada.
- Iniciar sesión en las ventanas del `.exe` y comprobar que ambas conservan la autenticación. La petición sin sesión se verificó, pero no se usaron credenciales reales.
- Confirmar el callback de login y la sesión compartida con credenciales reales. La prueba actual no puede completarse sin acceso de usuario.
- Desplegar los cambios actuales de `app.py` y sus templates en el servidor para habilitar `/desktop_session`, medio de pago de gastos, `/capital` y el nuevo cálculo de caja. El `.exe` solo es el contenedor de escritorio; estos cambios de API no están dentro del binario.
- Desplegar también la corrección más reciente de Capital en `app.py` para que sustituya la versión que está generando el error en producción.
- Validar con importes conocidos el cierre físico (apertura + ventas efectivo − gastos efectivo) y los saldos por cuenta. No se escribieron transacciones de producción.
- Completar una venta de prueba autenticada y comprobar su ticket desde el ejecutable. No se creó una transacción de producción durante esta verificación.
- En navegador, pulsar **Abrir venta aparte** y comprobar que se abre la segunda pestaña. El servidor web no puede forzar una ventana emergente al arrancar; el navegador la bloquearía sin una acción del usuario.

La ejecución de WebView2 dentro del sandbox restringido dio errores de inicialización; al repetir el arranque y la prueba HTTP fuera del sandbox, WebView2 inició y recibió las respuestas de producción descritas arriba.

## Registro para próximas incidencias

Añade cada caso con este formato:

| Fecha | Pantalla/acción | Pasos para reproducir | Resultado esperado | Resultado obtenido | Error o captura | Estado |
|---|---|---|---|---|---|---|
| | | | | | | Pendiente |
