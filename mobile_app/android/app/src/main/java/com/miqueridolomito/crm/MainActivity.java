package com.miqueridolomito.crm;

import android.Manifest;
import android.app.DownloadManager;
import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Context;
import android.content.pm.PackageManager;
import android.media.MediaScannerConnection;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.util.Base64;
import android.webkit.CookieManager;
import android.webkit.DownloadListener;
import android.webkit.JavascriptInterface;
import android.webkit.MimeTypeMap;
import android.webkit.URLUtil;
import android.widget.Toast;

import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.getcapacitor.BridgeActivity;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * El WebView de Capacitor no descarga archivos por si solo. En dispositivos
 * modernos, cuando el servidor responde con Content-Disposition: attachment
 * (ej. las etiquetas PNG), se puede interceptar con setDownloadListener() y
 * mandarlo al DownloadManager del sistema. PERO en el motor WebView de
 * ciertos equipos viejos (comprobado en una tablet con Android 5.0) esa
 * deteccion simplemente no existe: el WebView navega igual hacia la
 * respuesta binaria y trata de interpretarla como una pagina, sin llamar
 * nunca a onDownloadStart(), sin importar el mimeType usado.
 *
 * Por eso el mecanismo principal es un puente JavaScript -> Java
 * (AndroidFileSaver, ver saveFromDataUrl mas abajo): la propia pagina web
 * descarga el archivo con XMLHttpRequest (la misma red que ya funciona para
 * navegar normalmente) y entrega los bytes ya en memoria a este codigo
 * nativo solo para guardarlos, sin depender de que el WebView decida
 * correctamente "esto es una descarga". El DownloadListener se deja como
 * respaldo por si algun enlace no pasa por el puente JS.
 */
public class MainActivity extends BridgeActivity {

    private static final int STORAGE_PERMISSION_REQUEST = 9001;

    private Runnable pendingPermissionAction;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        getBridge().getWebView().addJavascriptInterface(new WebAppFileSaver(), "AndroidFileSaver");

        getBridge().getWebView().setDownloadListener(new DownloadListener() {
            @Override
            public void onDownloadStart(String url, String userAgent, String contentDisposition,
                                         String mimeType, long contentLength) {
                runWithStoragePermissionIfNeeded(() -> startDownloadFromUrl(url, userAgent, contentDisposition, mimeType));
            }
        });
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);

        if (requestCode != STORAGE_PERMISSION_REQUEST) {
            return;
        }

        boolean granted = grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED;

        if (granted && pendingPermissionAction != null) {
            pendingPermissionAction.run();
        } else if (!granted) {
            Toast.makeText(this,
                    "Se necesita permiso de almacenamiento para descargar el archivo",
                    Toast.LENGTH_LONG).show();
        }

        pendingPermissionAction = null;
    }

    private void runWithStoragePermissionIfNeeded(Runnable action) {
        boolean needsLegacyPermission = Build.VERSION.SDK_INT < Build.VERSION_CODES.Q
                && ContextCompat.checkSelfPermission(this,
                        Manifest.permission.WRITE_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED;

        if (needsLegacyPermission) {
            pendingPermissionAction = action;
            ActivityCompat.requestPermissions(this,
                    new String[]{Manifest.permission.WRITE_EXTERNAL_STORAGE},
                    STORAGE_PERMISSION_REQUEST);
            return;
        }

        action.run();
    }

    /**
     * Puente expuesto a la pagina web. La pagina hace el fetch con
     * XMLHttpRequest y llama a AndroidFileSaver.saveFromDataUrl(dataUrl,
     * fileName) con el resultado en formato "data:<mime>;base64,<datos>".
     */
    private class WebAppFileSaver {
        @JavascriptInterface
        public void saveFromDataUrl(final String dataUrl, final String fileName) {
            runOnUiThread(() -> runWithStoragePermissionIfNeeded(() -> saveDataUrl(dataUrl, fileName)));
        }
    }

    private void saveDataUrl(String dataUrl, String fileName) {
        try {
            int commaIndex = dataUrl.indexOf(',');
            if (!dataUrl.startsWith("data:") || commaIndex < 0) {
                throw new IOException("Formato de datos invalido");
            }

            String meta = dataUrl.substring(5, commaIndex);
            String mimeType = meta.contains(";") ? meta.substring(0, meta.indexOf(';')) : meta;
            String base64Data = dataUrl.substring(commaIndex + 1);
            byte[] bytes = Base64.decode(base64Data, Base64.DEFAULT);

            saveBytes(bytes, fileName, resolveMimeType(fileName, mimeType));
        } catch (Exception e) {
            Toast.makeText(this, "No se pudo guardar el archivo", Toast.LENGTH_LONG).show();
        }
    }

    private void saveBytes(byte[] bytes, String fileName, String mimeType) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                saveViaMediaStore(bytes, fileName, mimeType);
            } else {
                saveLegacy(bytes, fileName);
            }
            Toast.makeText(this, "Guardado en Descargas: " + fileName, Toast.LENGTH_LONG).show();
        } catch (Exception e) {
            Toast.makeText(this, "No se pudo guardar el archivo", Toast.LENGTH_LONG).show();
        }
    }

    private void saveViaMediaStore(byte[] bytes, String fileName, String mimeType) throws IOException {
        ContentValues values = new ContentValues();
        values.put(MediaStore.Downloads.DISPLAY_NAME, fileName);
        values.put(MediaStore.Downloads.MIME_TYPE, mimeType);
        values.put(MediaStore.Downloads.IS_PENDING, 1);

        ContentResolver resolver = getContentResolver();
        Uri item = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);

        if (item == null) {
            throw new IOException("No se pudo crear el archivo en Descargas");
        }

        try (OutputStream out = resolver.openOutputStream(item)) {
            if (out == null) {
                throw new IOException("No se pudo abrir el archivo para escritura");
            }
            out.write(bytes);
        }

        values.clear();
        values.put(MediaStore.Downloads.IS_PENDING, 0);
        resolver.update(item, values, null, null);
    }

    private void saveLegacy(byte[] bytes, String fileName) throws IOException {
        File downloadsDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS);

        if (!downloadsDir.exists()) {
            downloadsDir.mkdirs();
        }

        File outFile = new File(downloadsDir, fileName);

        try (FileOutputStream fos = new FileOutputStream(outFile)) {
            fos.write(bytes);
        }

        MediaScannerConnection.scanFile(this, new String[]{outFile.getAbsolutePath()}, null, null);
    }

    /**
     * Respaldo: si algun enlace dispara una descarga por navegacion normal
     * del WebView (Content-Disposition: attachment) en vez de pasar por el
     * puente JS, se maneja con el DownloadManager del sistema como antes.
     */
    private String extractFileName(String url, String contentDisposition, String mimeType) {
        if (contentDisposition != null) {
            Matcher matcher = Pattern
                    .compile("filename\\s*=\\s*\"?([^\";]+)\"?", Pattern.CASE_INSENSITIVE)
                    .matcher(contentDisposition);

            if (matcher.find()) {
                String name = matcher.group(1).trim();
                if (!name.isEmpty()) {
                    return name;
                }
            }
        }

        return URLUtil.guessFileName(url, contentDisposition, mimeType);
    }

    private String resolveMimeType(String fileName, String fallbackMimeType) {
        int dotIndex = fileName.lastIndexOf('.');

        if (dotIndex >= 0 && dotIndex < fileName.length() - 1) {
            String extension = fileName.substring(dotIndex + 1).toLowerCase();
            String resolved = MimeTypeMap.getSingleton().getMimeTypeFromExtension(extension);

            if (resolved != null) {
                return resolved;
            }
        }

        return fallbackMimeType;
    }

    private void startDownloadFromUrl(String url, String userAgent, String contentDisposition, String mimeType) {
        try {
            String fileName = extractFileName(url, contentDisposition, mimeType);
            String resolvedMimeType = resolveMimeType(fileName, mimeType);
            String cookies = CookieManager.getInstance().getCookie(url);

            DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url));

            if (cookies != null) {
                request.addRequestHeader("Cookie", cookies);
            }
            request.addRequestHeader("User-Agent", userAgent);
            request.setMimeType(resolvedMimeType);
            request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
            request.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, fileName);
            request.allowScanningByMediaScanner();

            DownloadManager downloadManager = (DownloadManager) getSystemService(Context.DOWNLOAD_SERVICE);

            if (downloadManager != null) {
                downloadManager.enqueue(request);
                Toast.makeText(this, "Descargando " + fileName + "…", Toast.LENGTH_LONG).show();
            }
        } catch (Exception e) {
            Toast.makeText(this, "No se pudo descargar el archivo", Toast.LENGTH_LONG).show();
        }
    }
}
