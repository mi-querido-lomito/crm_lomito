# CRM Mi Querido Lomito - App Movil (Capacitor)

Este proyecto NO reescribe el CRM: envuelve tu app web ya desplegada
(Flask + Jinja + Bootstrap) en un WebView nativo usando Capacitor.
El celular no corre Flask ni MySQL; solo muestra tu sitio dentro de una
app con icono propio, sin la barra del navegador.

## 1. Configurar la URL real antes de compilar

Edita `capacitor.config.json` y reemplaza `server.url` por la URL pública
de tu backend ya desplegado:

```json
"server": {
  "url": "https://tu-dominio-real.com",
  "androidScheme": "https"
}
```

Despues de cambiarla, sincroniza los proyectos nativos:

```
npx cap sync
```

## 2. Requisitos para compilar

- Node.js 18+ y npm
- Para Android: JDK 17 y Android SDK (platform 34, build-tools 34.0.0,
  platform-tools). Se puede usar Android Studio, o solo las
  "command-line tools" de Android sin instalar el IDE completo.
- Para iOS: una Mac con Xcode y CocoaPods (ver seccion 4).

> Nota Windows: si la ruta del proyecto tiene espacios (como
> `...CRM_Lomito_CLONE REPO...`), los scripts `sdkmanager.bat` y
> `gradlew.bat` de Android pueden fallar con errores raros de "no se
> reconoce como comando" o de sintaxis de nombre de archivo. Si eso pasa,
> mapea una unidad sin espacios antes de compilar y trabaja desde ahi:
> ```
> subst L: "C:\ruta\con espacios\crm_lomito"
> cd L:\mobile_app\android
> ```

## 3. Compilar el APK de Android

```
npm install
npx cap sync android
cd android
./gradlew.bat assembleDebug
```

El APK queda en `android/app/build/outputs/apk/debug/app-debug.apk`.
Ese APK debug ya es instalable en un celular real (activa "Instalar apps
de origenes desconocidos" en Android y copia el archivo, o usa
`adb install app-debug.apk`).

### Para publicarla en Play Store (release firmado)

1. Genera un keystore propio (guardalo, no lo pierdas ni lo subas a git):
   ```
   keytool -genkey -v -keystore lomito-release.keystore -alias lomito -keyalg RSA -keysize 2048 -validity 10000
   ```
2. Configura `android/key.properties` (no versionado) y referencialo en
   `android/app/build.gradle` en `signingConfigs` (ver guia oficial de
   Capacitor: https://capacitorjs.com/docs/android/deploying-to-google-play).
3. Ejecuta `./gradlew.bat assembleRelease` o `bundleRelease` (para .aab).

## 4. iOS (.ipa) - requiere Mac

Apple exige compilar y firmar con Xcode en macOS con una cuenta de Apple
Developer (de pago, $99/año) para instalar en un iPhone real. Esta
carpeta ya incluye el proyecto Xcode generado (`ios/App`), listo para
abrir en una Mac:

```
npm install
npx cap sync ios
cd ios/App
pod install
open App.xcworkspace
```

Desde Xcode: selecciona tu equipo de firma (Signing & Capabilities) y
compila/archiva para tu iPhone o para TestFlight.

Si no tienes Mac, alternativas sin comprar una:

- **PWA (ya activado en el CRM):** en iPhone, abre la URL del CRM en
  Safari y usa "Compartir" -> "Agregar a pantalla de inicio". Queda con
  icono propio y pantalla completa, sin instalar nada de App Store, y
  sin costo. Es la opcion mas rapida mientras no haya Mac disponible.
- **Runner macOS en la nube:** servicios como Codemagic o un workflow de
  GitHub Actions con `runs-on: macos-latest` pueden compilar este mismo
  proyecto Xcode sin que tengas una Mac fisica. Aun asi, para instalar en
  un iPhone real necesitas una cuenta de Apple Developer para firmar el
  build (TestFlight o instalacion ad-hoc); sin cuenta solo se puede
  compilar para el Simulador de iOS, no para un dispositivo real.
