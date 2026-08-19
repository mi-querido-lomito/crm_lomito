package com.miqueridolomito.crm;

import android.Manifest;
import android.app.DownloadManager;
import android.content.Context;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.webkit.CookieManager;
import android.webkit.DownloadListener;
import android.webkit.MimeTypeMap;
import android.webkit.URLUtil;
import android.widget.Toast;

import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.getcapacitor.BridgeActivity;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * El WebView de Capacitor no descarga archivos por si solo: cuando el
 * servidor responde con Content-Disposition: attachment (ej. las etiquetas
 * PNG), el WebView no sabe que hacer y se queda sin reaccionar o intenta
 * navegar/renderizar los bytes crudos. Este listener intercepta esa
 * respuesta y la entrega al DownloadManager de Android para que se
 * descargue como un archivo normal, sin salir de la pagina actual.
 */
public class MainActivity extends BridgeActivity {

    private static final int STORAGE_PERMISSION_REQUEST = 9001;

    private String pendingDownloadUrl;
    private String pendingDownloadUserAgent;
    private String pendingDownloadContentDisposition;
    private String pendingDownloadMimeType;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        getBridge().getWebView().setDownloadListener(new DownloadListener() {
            @Override
            public void onDownloadStart(String url, String userAgent, String contentDisposition,
                                         String mimeType, long contentLength) {
                boolean needsLegacyPermission = Build.VERSION.SDK_INT < Build.VERSION_CODES.Q
                        && ContextCompat.checkSelfPermission(MainActivity.this,
                                Manifest.permission.WRITE_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED;

                if (needsLegacyPermission) {
                    pendingDownloadUrl = url;
                    pendingDownloadUserAgent = userAgent;
                    pendingDownloadContentDisposition = contentDisposition;
                    pendingDownloadMimeType = mimeType;

                    ActivityCompat.requestPermissions(MainActivity.this,
                            new String[]{Manifest.permission.WRITE_EXTERNAL_STORAGE},
                            STORAGE_PERMISSION_REQUEST);
                    return;
                }

                startDownload(url, userAgent, contentDisposition, mimeType);
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

        if (granted && pendingDownloadUrl != null) {
            startDownload(pendingDownloadUrl, pendingDownloadUserAgent,
                    pendingDownloadContentDisposition, pendingDownloadMimeType);
        } else {
            Toast.makeText(this,
                    "Se necesita permiso de almacenamiento para descargar el archivo",
                    Toast.LENGTH_LONG).show();
        }

        pendingDownloadUrl = null;
        pendingDownloadUserAgent = null;
        pendingDownloadContentDisposition = null;
        pendingDownloadMimeType = null;
    }

    /**
     * URLUtil.guessFileName() de Android es poco confiable cuando el header
     * Content-Disposition trae tanto filename= como filename*=UTF-8''...
     * (formato que Flask/Werkzeug genera por defecto): a menudo falla en
     * extraer el nombre y cae a una extension generica segun el mimeType
     * (.bin para application/octet-stream). Por eso se extrae el filename=
     * manualmente en vez de depender de esa funcion.
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

    /**
     * El servidor envia application/octet-stream a proposito (para forzar la
     * descarga incluso en WebViews viejos que intentan renderizar tipos
     * conocidos como image/png). Para que el archivo guardado se asocie
     * correctamente con la app de Galeria/Fotos, se deduce el mimeType real
     * a partir de la extension del archivo en vez de usar el que mando el
     * servidor.
     */
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

    private void startDownload(String url, String userAgent, String contentDisposition, String mimeType) {
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
