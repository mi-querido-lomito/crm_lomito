from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import Image as RLImage
from reportlab.graphics.shapes import Drawing
from reportlab.platypus import KeepTogether
from reportlab.lib.units import mm
from reportlab.graphics.barcode import code128
from openpyxl import Workbook
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mysqldb import MySQL
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from werkzeug.security import check_password_hash
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.platypus import Table
import io
from flask import send_file
from flask import session
import csv
from config import Config
import MySQLdb.cursors
from functools import wraps
from flask import abort
from datetime import datetime, time, timedelta

def actualizar_citas_perdidas():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        UPDATE citas
        SET estado='Cancelada'
        WHERE estado='Pendiente'
        AND fecha < NOW()
    """)
    mysql.connection.commit()
    cursor.close()


def rol_requerido(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "rol" not in session:
                abort(403)

            if session["rol"] not in roles:
                abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator

app = Flask(__name__)
app.config.from_object(Config)

app.secret_key = "SistemasRacks.23"
schema_checked = False


mysql = MySQL()
mysql.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

BARCODE_ENTITIES = {
    "productos": "PROD",
    "servicios": "SERV",
    "insumos": "INS",
}


def generar_codigo_barra(prefijo):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    codigo = generar_codigo_barra_cursor(cursor, prefijo)
    cursor.close()
    return codigo


def generar_codigo_barra_cursor(cursor, prefijo):
    cursor.execute("""
        SELECT MAX(CAST(SUBSTRING_INDEX(codigo_barras, '-', -1) AS UNSIGNED)) AS ultimo
        FROM (
            SELECT codigo_barras FROM productos
            UNION ALL SELECT codigo_barras FROM servicios
            UNION ALL SELECT codigo_barras FROM insumos
        ) AS codigos
        WHERE codigo_barras REGEXP %s
    """, (f"^{prefijo}-[0-9]+$",))

    row = cursor.fetchone()

    ultimo = int(row["ultimo"]) if row and row.get("ultimo") else 1000
    return f"{prefijo}-{ultimo + 1}"


def asegurar_codigo_barra_actual(tabla, registro_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(f"SELECT codigo_barras FROM {tabla} WHERE id=%s", (registro_id,))
    registro = cursor.fetchone()

    if not registro:
        cursor.close()
        return None

    codigo = (registro.get("codigo_barras") or "").strip()
    if not codigo:
        codigo = generar_codigo_barra_cursor(cursor, BARCODE_ENTITIES[tabla])
        cursor.execute(
            f"UPDATE {tabla} SET codigo_barras=%s WHERE id=%s",
            (codigo, registro_id)
        )
        mysql.connection.commit()

    cursor.close()
    return codigo


def rellenar_codigos_barras_faltantes(tabla):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(f"""
        SELECT id
        FROM {tabla}
        WHERE codigo_barras IS NULL OR TRIM(codigo_barras) = ''
        ORDER BY id
    """)
    registros = cursor.fetchall()
    for registro in registros:
        codigo = generar_codigo_barra_cursor(cursor, BARCODE_ENTITIES[tabla])
        cursor.execute(
            f"UPDATE {tabla} SET codigo_barras=%s WHERE id=%s",
            (codigo, registro["id"])
        )

    if registros:
        mysql.connection.commit()

    cursor.close()


def columna_existe(cursor, tabla, columna):
    cursor.execute(f"SHOW COLUMNS FROM {tabla} LIKE %s", (columna,))
    return cursor.fetchone() is not None


def asegurar_columna(cursor, tabla, columna, definicion):
    if not columna_existe(cursor, tabla, columna):
        cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}")


def asegurar_tabla_proveedores(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS proveedores (
            id INT NOT NULL AUTO_INCREMENT,
            nombre VARCHAR(150) NOT NULL,
            direccion_contacto TEXT NULL,
            telefono VARCHAR(50) NULL,
            observaciones TEXT NULL,
            PRIMARY KEY (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_spanish2_ci
    """)


def asegurar_schema_crm():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    asegurar_tabla_proveedores(cursor)

    columnas = {
        "clientes": {
            "direccion": "TEXT NULL",
        },
        "productos": {
            "proveedor_id": "INT NULL",
        },
        "insumos": {
            "proveedor_id": "INT NULL",
        },
        "mascotas": {
            "raza": "VARCHAR(100) NULL",
            "edad": "INT NULL",
            "fecha_especial": "DATE NULL",
            "alergias": "TEXT NULL",
            "genero": "VARCHAR(20) NULL",
            "talla": "VARCHAR(50) NULL",
            "color": "VARCHAR(80) NULL",
            "notas": "TEXT NULL",
        },
        "citas": {
            "servicio_id": "INT NULL",
            "observaciones": "TEXT NULL",
            "tiempo_servicio_min": "INT NULL",
        },
        "ventas": {
            "mascota_id": "INT NULL",
            "cita_id": "INT NULL",
        },
    }

    for tabla, definiciones in columnas.items():
        for columna, definicion in definiciones.items():
            asegurar_columna(cursor, tabla, columna, definicion)

    mysql.connection.commit()
    cursor.close()


def estimar_tiempo_servicio(cursor, servicio_id):
    if not servicio_id:
        return 60

    cursor.execute("""
        SELECT AVG(tiempo_servicio_min) AS promedio
        FROM citas
        WHERE servicio_id=%s
        AND estado='Completada'
        AND tiempo_servicio_min IS NOT NULL
        AND tiempo_servicio_min > 0
    """, (servicio_id,))
    promedio = cursor.fetchone()

    if promedio and promedio.get("promedio"):
        return int(round(float(promedio["promedio"])))

    cursor.execute("SELECT duracion_min FROM servicios WHERE id=%s", (servicio_id,))
    servicio = cursor.fetchone()

    if servicio and servicio.get("duracion_min"):
        return int(servicio["duracion_min"])

    return 60


def resumen_agenda_dia(cursor, fecha, servicio_id=None):
    inicio = datetime.combine(fecha.date(), time(10, 0))
    fin = datetime.combine(fecha.date(), time(17, 0))
    jornada_min = int((fin - inicio).total_seconds() / 60)
    nuevo_min = estimar_tiempo_servicio(cursor, servicio_id)

    cursor.execute("""
        SELECT servicio_id
        FROM citas
        WHERE DATE(fecha)=DATE(%s)
        AND estado='Pendiente'
    """, (fecha,))
    citas_dia = cursor.fetchall()

    ocupado = sum(estimar_tiempo_servicio(cursor, cita.get("servicio_id")) for cita in citas_dia)

    return {
        "inicio": inicio,
        "fin": fin,
        "jornada_min": jornada_min,
        "ocupado_min": ocupado,
        "disponible_min": max(jornada_min - ocupado, 0),
        "nuevo_min": nuevo_min,
        "cabe": ocupado + nuevo_min <= jornada_min and inicio <= fecha < fin,
    }


@app.before_request
def verificar_schema_crm():
    global schema_checked
    if schema_checked or request.endpoint in ("static", "login", "home"):
        return

    asegurar_schema_crm()
    schema_checked = True

# -------------------
# USER MODEL
# -------------------

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data["id"])
        self.username = user_data["username"]

@login_manager.user_loader
def load_user(user_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM usuarios WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    if user:
        return User(user)
    return None


# -------------------
# LOGIN
# -------------------
@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM usuarios WHERE username=%s", (username,))
        user = cursor.fetchone()
        cursor.close()

        password_hash = user.get("PASSWORD") if user else None

        if password_hash and check_password_hash(password_hash, password):
            login_user(User(user))
            session["rol"] = user["rol"]
            return redirect(url_for("dashboard"))
        else:
            flash("Credenciales incorrectas")

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# -------------------
# DASHBOARD
# -------------------
@app.route("/dashboard")
@login_required
def dashboard():

    actualizar_citas_perdidas()

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    rol = session.get("rol")

    # ==========================
    # MÉTRICAS SOLO ADMIN
    # ==========================
    if rol == "admin":

        cursor.execute("SELECT COUNT(*) as total FROM clientes")
        clientes = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) as total FROM mascotas")
        mascotas = cursor.fetchone()["total"]

        # Ventas hoy
        cursor.execute("""
            SELECT IFNULL(SUM(total),0) as total_hoy
            FROM ventas
            WHERE DATE(fecha)=CURDATE()
            AND estado='activa'
        """)
        total_hoy = cursor.fetchone()["total_hoy"]

        # Ventas últimos 7 días
        cursor.execute("""
            SELECT DATE(fecha) as dia, SUM(total) as total
            FROM ventas
            WHERE fecha >= CURDATE() - INTERVAL 7 DAY
            AND estado='activa'
            GROUP BY DATE(fecha)
            ORDER BY dia
        """)
        ventas_7_dias = cursor.fetchall()

    else:
        # Empleado no necesita estas métricas
        clientes = None
        mascotas = None
        total_hoy = None
        ventas_7_dias = []

    # ==========================
    # MÉTRICAS GENERALES (TODOS)
    # ==========================

    cursor.execute("SELECT COUNT(*) as total FROM productos")
    productos = cursor.fetchone()["total"]

    # Citas de hoy
    cursor.execute("""
        SELECT estado, COUNT(*) as total
        FROM citas
        WHERE DATE(fecha) = CURDATE()
        GROUP BY estado
    """)
    resumen_citas = cursor.fetchall()

    # Inventario bajo
    cursor.execute("SELECT nombre, stock FROM productos WHERE stock <= 2")
    bajo_stock = cursor.fetchall()

    # Estado de caja
    cursor.execute("SELECT * FROM caja WHERE estado='abierta'")
    caja_abierta = cursor.fetchone()

    # Citas próximas
    cursor.execute("""
        SELECT c.id, c.fecha, m.nombre as mascota
        FROM citas c
        JOIN mascotas m ON c.mascota_id = m.id
        WHERE c.estado='Pendiente'
        AND c.fecha BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 24 HOUR)
        ORDER BY c.fecha ASC
    """)
    citas_proximas = cursor.fetchall()

    cursor.close()

    return render_template(
        "dashboard.html",
        clientes=clientes,
        mascotas=mascotas,
        productos=productos,
        total_hoy=total_hoy,
        resumen_citas=resumen_citas,
        ventas_7_dias=ventas_7_dias,
        bajo_stock=bajo_stock,
        caja_abierta=caja_abierta,
        citas_proximas=citas_proximas
    )


# -------------------
# CLIENTES
# -------------------

@app.route("/clientes", methods=["GET", "POST"])
@login_required
def clientes():

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == "POST":

        nombre = request.form.get("nombre")
        telefono = request.form.get("telefono")
        direccion = request.form.get("direccion")

        if not nombre:
            flash("El nombre es obligatorio")
            return redirect(url_for("clientes"))

        cursor.execute("""
            INSERT INTO clientes (nombre, telefono, direccion)
            VALUES (%s, %s, %s)
        """, (nombre, telefono, direccion))

        mysql.connection.commit()
        flash("Cliente agregado correctamente")

        return redirect(url_for("clientes"))

    cursor.execute("SELECT * FROM clientes ORDER BY id DESC")
    data = cursor.fetchall()
    cursor.close()

    return render_template("clientes.html", clientes=data)


# -------------------
# EDITAR CLIENTE
# -------------------

@app.route("/editar_cliente/<int:id>", methods=["GET", "POST"])
@login_required
def editar_cliente(id):

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT * FROM clientes WHERE id=%s", (id,))
    cliente = cursor.fetchone()

    if not cliente:
        cursor.close()
        flash("Cliente no encontrado")
        return redirect(url_for("clientes"))

    if request.method == "POST":

        nombre = request.form.get("nombre")
        telefono = request.form.get("telefono")
        direccion = request.form.get("direccion")

        cursor.execute("""
            UPDATE clientes
            SET nombre=%s,
                telefono=%s,
                direccion=%s
            WHERE id=%s
        """, (nombre, telefono, direccion, id))

        mysql.connection.commit()
        cursor.close()

        flash("Cliente actualizado correctamente")
        return redirect(url_for("clientes"))

    cursor.close()
    return render_template("editar_cliente.html", cliente=cliente)


# -------------------
# ELIMINAR CLIENTE (SOLO ADMIN)
# -------------------

@app.route("/eliminar_cliente/<int:id>")
@login_required
@rol_requerido(["admin"])
def eliminar_cliente(id):

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Verificar si tiene mascotas asociadas
    cursor.execute("SELECT COUNT(*) as total FROM mascotas WHERE cliente_id=%s", (id,))
    mascotas = cursor.fetchone()["total"]

    if mascotas > 0:
        cursor.close()
        flash("No puedes eliminar un cliente con mascotas registradas")
        return redirect(url_for("clientes"))

    cursor.execute("DELETE FROM clientes WHERE id=%s", (id,))
    mysql.connection.commit()
    cursor.close()

    flash("Cliente eliminado correctamente")
    return redirect(url_for("clientes"))


# -------------------
# EXPORTAR CLIENTES A PDF (SOLO ADMIN)
# -------------------

@app.route("/clientes/pdf")
@login_required
@rol_requerido(["admin"])
def export_clientes_pdf():

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    elements = []
    styles = getSampleStyleSheet()

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT nombre, telefono, direccion FROM clientes")
    data = cursor.fetchall()
    cursor.close()

    table_data = [["Nombre", "Teléfono", "Dirección"]]

    for c in data:
        table_data.append([
            c["nombre"],
            c["telefono"] if c["telefono"] else "",
            c["direccion"] if c["direccion"] else ""
        ])

    table = Table(table_data)
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="clientes.pdf",
        mimetype="application/pdf"
    )

# -------------------
# MASCOTAS
# -------------------

@app.route("/mascotas", methods=["GET", "POST"])
@login_required
def mascotas():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == "POST":
        nombre = request.form["nombre"]
        especie = request.form["especie"]
        cliente_id = request.form.get("cliente_id")
        nuevo_cliente = request.form.get("nuevo_cliente")

        if nuevo_cliente == "1":
            cliente_nombre = request.form.get("cliente_nombre")
            cliente_telefono = request.form.get("cliente_telefono")
            cliente_direccion = request.form.get("cliente_direccion")

            if not cliente_nombre:
                flash("El nombre del nuevo cliente es obligatorio")
                cursor.close()
                return redirect(url_for("mascotas"))

            cursor.execute("""
                INSERT INTO clientes (nombre, telefono, direccion)
                VALUES (%s, %s, %s)
            """, (cliente_nombre, cliente_telefono, cliente_direccion))
            mysql.connection.commit()
            cliente_id = cursor.lastrowid

        if not cliente_id:
            flash("Selecciona un dueño o registra un cliente nuevo")
            cursor.close()
            return redirect(url_for("mascotas"))

        datos = (
            nombre,
            especie,
            cliente_id,
            request.form.get("raza"),
            request.form.get("edad") or None,
            request.form.get("fecha_especial") or None,
            request.form.get("alergias"),
            request.form.get("genero"),
            request.form.get("talla"),
            request.form.get("color"),
            request.form.get("notas"),
        )

        cursor.execute("""
            INSERT INTO mascotas
            (nombre, especie, cliente_id, raza, edad, fecha_especial, alergias, genero, talla, color, notas)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, datos)
        mysql.connection.commit()

    cursor.execute("""
        SELECT mascotas.*, clientes.nombre as dueno
        FROM mascotas
        JOIN clientes ON mascotas.cliente_id = clientes.id
        ORDER BY mascotas.id DESC
    """)
    data = cursor.fetchall()

    cursor.execute("SELECT * FROM clientes")
    clientes = cursor.fetchall()

    cursor.close()

    return render_template("mascotas.html", mascotas=data, clientes=clientes)


# -------------------
# EDITAR MASCOTA
@app.route("/editar_mascota/<int:id>", methods=["GET", "POST"])
@login_required
def editar_mascota(id):

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT * FROM mascotas WHERE id=%s", (id,))
    mascota = cursor.fetchone()

    if not mascota:
        cursor.close()
        flash("Mascota no encontrada")
        return redirect(url_for("mascotas"))

    # necesitamos lista de clientes para el select
    cursor.execute("SELECT * FROM clientes")
    clientes = cursor.fetchall()

    if request.method == "POST":

        nombre = request.form["nombre"]
        especie = request.form["especie"]
        cliente_id = request.form["cliente_id"]
        raza = request.form.get("raza")
        edad = request.form.get("edad") or None
        fecha_especial = request.form.get("fecha_especial") or None
        alergias = request.form.get("alergias")
        genero = request.form.get("genero")
        talla = request.form.get("talla")
        color = request.form.get("color")
        notas = request.form.get("notas")

        cursor.execute("""
            UPDATE mascotas
            SET nombre=%s,
                especie=%s,
                cliente_id=%s,
                raza=%s,
                edad=%s,
                fecha_especial=%s,
                alergias=%s,
                genero=%s,
                talla=%s,
                color=%s,
                notas=%s
            WHERE id=%s
        """, (nombre, especie, cliente_id, raza, edad, fecha_especial, alergias, genero, talla, color, notas, id))

        mysql.connection.commit()
        flash("Mascota actualizada correctamente")
        return redirect(url_for("mascotas"))

    cursor.close()
    return render_template("editar_mascota.html",
                           mascota=mascota,
                           clientes=clientes)

# ELIMINAR MASCOTA
# -------------------
@app.route("/eliminar_mascota/<int:id>")
@login_required
@rol_requerido(["admin"])
def eliminar_mascota(id):

    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM mascotas WHERE id=%s", (id,))
    mysql.connection.commit()
    cursor.close()

    flash("Mascota eliminada correctamente")
    return redirect(url_for("mascotas"))


@app.route("/mascota/<int:id>/historial")
@login_required
def historial_mascota(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT mascotas.*, clientes.nombre as dueno, clientes.telefono, clientes.direccion
        FROM mascotas
        JOIN clientes ON mascotas.cliente_id = clientes.id
        WHERE mascotas.id=%s
    """, (id,))
    mascota = cursor.fetchone()

    if not mascota:
        cursor.close()
        flash("Mascota no encontrada")
        return redirect(url_for("mascotas"))

    cursor.execute("""
        SELECT c.*, s.nombre as servicio, s.precio
        FROM citas c
        LEFT JOIN servicios s ON c.servicio_id = s.id
        WHERE c.mascota_id=%s
        ORDER BY c.fecha DESC
    """, (id,))
    citas = cursor.fetchall()

    cursor.execute("""
        SELECT v.id as venta_id, v.fecha, v.total, v.metodo_pago,
               d.tipo, d.cantidad, d.precio_unitario, d.subtotal,
               s.nombre as servicio, p.nombre as producto
        FROM ventas v
        JOIN detalle_venta d ON d.venta_id = v.id
        LEFT JOIN servicios s ON d.servicio_id = s.id
        LEFT JOIN productos p ON d.producto_id = p.id
        WHERE v.mascota_id=%s
        AND v.estado='activa'
        ORDER BY v.fecha DESC
    """, (id,))
    ventas = cursor.fetchall()

    cursor.execute("""
        SELECT s.nombre as servicio, AVG(c.tiempo_servicio_min) as promedio_min, COUNT(*) as total
        FROM citas c
        LEFT JOIN servicios s ON c.servicio_id = s.id
        WHERE c.mascota_id=%s
        AND c.estado='Completada'
        AND c.tiempo_servicio_min IS NOT NULL
        GROUP BY c.servicio_id, s.nombre
        ORDER BY s.nombre
    """, (id,))
    promedios = cursor.fetchall()

    cursor.close()

    return render_template(
        "historial_mascota.html",
        mascota=mascota,
        citas=citas,
        ventas=ventas,
        promedios=promedios
    )


# -------------------
# PRODUCTOS
# -------------------

@app.route("/productos", methods=["GET", "POST"])
@login_required
@rol_requerido(["admin"])
def productos():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == "POST":
        nombre = request.form["nombre"]
        stock = request.form["stock"]
        precio = request.form["precio"]
        proveedor_id = request.form.get("proveedor_id") or None
        codigo = generar_codigo_barra("PROD")

        cursor.execute(
            "INSERT INTO productos (nombre, stock, precio, proveedor_id, codigo_barras) VALUES (%s,%s,%s,%s,%s)",
            (nombre, stock, precio, proveedor_id, codigo)
        )
        mysql.connection.commit()

    rellenar_codigos_barras_faltantes("productos")
    cursor.execute("""
        SELECT productos.*, proveedores.nombre AS proveedor_nombre
        FROM productos
        LEFT JOIN proveedores ON productos.proveedor_id = proveedores.id
        ORDER BY productos.id DESC
    """)
    data = cursor.fetchall()
    cursor.execute("SELECT * FROM proveedores ORDER BY nombre")
    proveedores = cursor.fetchall()
    cursor.close()

    return render_template("productos.html", productos=data, proveedores=proveedores)

# EDITAR PRODUCTO
# -------------------
@app.route("/editar_producto/<int:id>", methods=["GET", "POST"])
@login_required
@rol_requerido(["admin"])
def editar_producto(id):

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT * FROM productos WHERE id=%s", (id,))
    producto = cursor.fetchone()

    if request.method == "POST":

        nombre = request.form["nombre"]
        precio = request.form["precio"]
        stock = request.form["stock"]
        proveedor_id = request.form.get("proveedor_id") or None
        codigo = (producto.get("codigo_barras") or "").strip()
        if not codigo:
            codigo = generar_codigo_barra("PROD")

        cursor.execute("""
            UPDATE productos
            SET nombre=%s,
                precio=%s,
                stock=%s,
                proveedor_id=%s,
                codigo_barras=%s
            WHERE id=%s
        """, (nombre, precio, stock, proveedor_id, codigo, id))

        mysql.connection.commit()
        flash("Producto actualizado correctamente")
        return redirect(url_for("productos"))

    cursor.execute("SELECT * FROM proveedores ORDER BY nombre")
    proveedores = cursor.fetchall()
    cursor.close()
    return render_template("editar_producto.html", producto=producto, proveedores=proveedores)

# EXPORTAR PRODUCTO A EXCEL
# -------------------
@app.route("/exportar_productos")
@login_required
@rol_requerido(["admin"])
def exportar_productos():

    rellenar_codigos_barras_faltantes("productos")
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT productos.*, proveedores.nombre AS proveedor_nombre
        FROM productos
        LEFT JOIN proveedores ON productos.proveedor_id = proveedores.id
    """)
    productos = cursor.fetchall()
    cursor.close()

    wb = Workbook()
    ws = wb.active
    ws.title = "Productos"

    ws.append(["ID", "Nombre", "Stock", "Precio", "Proveedor", "Código Barras"])

    for p in productos:
        ws.append([
            p["id"],
            p["nombre"],
            p["stock"],
            float(p["precio"]),
            p.get("proveedor_nombre", ""),
            p.get("codigo_barras", "")
        ])

    file = io.BytesIO()
    wb.save(file)
    file.seek(0)

    return send_file(
        file,
        download_name="productos.xlsx",
        as_attachment=True
    )

# ETIQUETAS DE PRODUCTOS EN PDF
# -------------------
@app.route("/etiquetas_productos_carta")
@login_required
@rol_requerido(["admin"])
def etiquetas_productos_carta():

    rellenar_codigos_barras_faltantes("productos")
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=10,
        leftMargin=10,
        topMargin=10,
        bottomMargin=10
    )

    elements = []
    styles = getSampleStyleSheet()

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT nombre, precio, codigo_barras FROM productos")
    productos = cursor.fetchall()
    cursor.close()

    etiquetas = []
    fila = []

    for p in productos:

        contenido = []

        contenido.append(Paragraph(f"<b>{p['nombre']}</b>", styles["Normal"]))
        contenido.append(Spacer(1, 3))
        contenido.append(Paragraph(f"${p['precio']}", styles["Normal"]))
        contenido.append(Spacer(1, 4))

        if p["codigo_barras"]:
            barcode = code128.Code128(
                str(p["codigo_barras"]),
                barHeight=15*mm,
                barWidth=1.0
            )
            contenido.append(barcode)
            contenido.append(Spacer(1, 3))
            contenido.append(Paragraph(str(p["codigo_barras"]), styles["Normal"]))

        etiqueta = Table([[contenido]],
                         colWidths=60*mm,
                         rowHeights=38*mm)

        etiqueta.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ]))

        fila.append(etiqueta)

        if len(fila) == 3:
            etiquetas.append(fila)
            fila = []

    if fila:
        while len(fila) < 3:
            fila.append("")
        etiquetas.append(fila)

    tabla_final = Table(etiquetas, colWidths=[65*mm]*3)
    elements.append(tabla_final)

    doc.build(elements)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="etiquetas_productos_carta.pdf",
        mimetype="application/pdf"
    )

# -------------------
# CITAS
# -------------------

@app.route("/citas", methods=["GET", "POST"])
@login_required
def citas():

    actualizar_citas_perdidas()
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == "POST":
        mascota_id = request.form["mascota_id"]
        fecha = request.form["fecha"]
        servicio_id = request.form.get("servicio_id") or None
        notas = request.form.get("notas")
        fecha_convertida = datetime.strptime(fecha, "%Y-%m-%dT%H:%M")

        agenda = resumen_agenda_dia(cursor, fecha_convertida, servicio_id)

        if not agenda["cabe"]:
            flash("La cita no cabe en la jornada laboral de 10:00 a 17:00 con el tiempo estimado actual")
            cursor.close()
            return redirect(url_for("citas"))

        cursor.execute("""
            INSERT INTO citas (mascota_id, servicio_id, fecha, estado, notas)
            VALUES (%s, %s, %s, 'Pendiente', %s)
        """, (mascota_id, servicio_id, fecha_convertida, notas))
        mysql.connection.commit()

    cursor.execute("""
        SELECT citas.*, mascotas.nombre as mascota, servicios.nombre as servicio
        FROM citas
        JOIN mascotas ON citas.mascota_id = mascotas.id
        LEFT JOIN servicios ON citas.servicio_id = servicios.id
        ORDER BY citas.fecha DESC
    """)
    data = cursor.fetchall()

    cursor.execute("SELECT * FROM mascotas")
    mascotas = cursor.fetchall()

    cursor.execute("SELECT * FROM servicios ORDER BY nombre")
    servicios = cursor.fetchall()

    agenda_hoy = resumen_agenda_dia(cursor, datetime.now())

    cursor.close()

    return render_template("citas.html", citas=data, mascotas=mascotas, servicios=servicios, agenda_hoy=agenda_hoy)


@app.route("/api/agenda_dia")
@login_required
def api_agenda_dia():
    fecha_raw = request.args.get("fecha")
    servicio_id = request.args.get("servicio_id") or None

    if not fecha_raw:
        return {"ok": False, "error": "Fecha requerida"}

    try:
        fecha = datetime.strptime(fecha_raw, "%Y-%m-%dT%H:%M")
    except ValueError:
        return {"ok": False, "error": "Formato de fecha inválido"}

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    agenda = resumen_agenda_dia(cursor, fecha, servicio_id)
    cursor.close()

    return {
        "ok": True,
        "ocupado_min": agenda["ocupado_min"],
        "disponible_min": agenda["disponible_min"],
        "nuevo_min": agenda["nuevo_min"],
        "cabe": agenda["cabe"],
    }

# EDITAR CITA
# -------------------
@app.route("/editar_cita/<int:id>", methods=["GET", "POST"])
@login_required
@rol_requerido(["admin", "empleado"])
def editar_cita(id):

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT * FROM citas WHERE id=%s", (id,))
    cita = cursor.fetchone()

    if not cita:
        cursor.close()
        flash("Cita no encontrada")
        return redirect(url_for("citas"))

    if request.method == "POST":

        fecha_raw = request.form["fecha"]
        servicio_id = request.form.get("servicio_id") or None
        notas = request.form.get("notas")
        observaciones = request.form.get("observaciones")
        tiempo_servicio_min = request.form.get("tiempo_servicio_min") or None

        # convertir formato HTML a formato MySQL
        fecha_convertida = datetime.strptime(
            fecha_raw, "%Y-%m-%dT%H:%M"
        )

        estado = request.form["estado"]

        cursor.execute("""
            UPDATE citas
            SET fecha=%s,
                servicio_id=%s,
                estado=%s,
                notas=%s,
                observaciones=%s,
                tiempo_servicio_min=%s
            WHERE id=%s
        """, (fecha_convertida, servicio_id, estado, notas, observaciones, tiempo_servicio_min, id))

        mysql.connection.commit()
        flash("Cita actualizada correctamente")
        return redirect(url_for("citas"))

    cursor.close()

    # convertir fecha MySQL a formato HTML datetime-local
    fecha_html = cita["fecha"].strftime("%Y-%m-%dT%H:%M")

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM servicios ORDER BY nombre")
    servicios = cursor.fetchall()
    cursor.close()

    return render_template("editar_cita.html",
                           cita=cita,
                           fecha_html=fecha_html,
                           servicios=servicios)

# CANCELAR CITA
# -------------------
@app.route("/cancelar_cita/<int:id>")
@login_required
def cancelar_cita(id):

    cursor = mysql.connection.cursor()

    cursor.execute("""
        UPDATE citas
        SET estado='Cancelada'
        WHERE id=%s
    """, (id,))

    mysql.connection.commit()
    cursor.close()

    flash("Cita cancelada correctamente")
    return redirect(url_for("citas"))

# CONVERTIR CITA A VENTA
# -------------------
@app.route("/convertir_cita/<int:id>", methods=["GET", "POST"])
@login_required
def convertir_cita(id):

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT citas.*, mascotas.nombre as mascota, servicios.nombre as servicio, servicios.precio
        FROM citas
        JOIN mascotas ON citas.mascota_id = mascotas.id
        LEFT JOIN servicios ON citas.servicio_id = servicios.id
        WHERE citas.id=%s
    """, (id,))
    cita = cursor.fetchone()

    if not cita:
        cursor.close()
        flash("Cita no encontrada")
        return redirect(url_for("citas"))

    if request.method == "POST":
        observaciones = request.form.get("observaciones")
        tiempo = request.form.get("tiempo_servicio_min") or None

        cursor.execute("""
            UPDATE citas
            SET estado='Completada',
                observaciones=%s,
                tiempo_servicio_min=%s
            WHERE id=%s
        """, (observaciones, tiempo, id))

        mysql.connection.commit()

        session["venta_mascota_id"] = cita["mascota_id"]
        session["venta_cita_id"] = cita["id"]

        if cita.get("servicio_id"):
            if "carrito" not in session:
                session["carrito"] = []

            session["carrito"].append({
                "tipo": "servicio",
                "id": cita["servicio_id"],
                "nombre": cita["servicio"],
                "precio": float(cita["precio"] or 0),
                "cantidad": 1,
                "subtotal": float(cita["precio"] or 0),
            })
            session.modified = True

        flash("Cita completada. Revisa el carrito y finaliza el cobro.")
        cursor.close()
        return redirect(url_for("ventas"))

    cursor.close()
    return render_template("finalizar_cita.html", cita=cita)

# -------------------
# VENTAS
# -------------------
@app.route("/ventas", methods=["GET", "POST"])
@login_required
def ventas():

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    def cerrar_y_redirigir(endpoint, **kwargs):
        cursor.close()
        return redirect(url_for(endpoint, **kwargs))

    if "carrito" not in session:
        session["carrito"] = []

    # ==========================
    # AGREGAR AL CARRITO
    # ==========================
    if request.method == "POST" and "agregar" in request.form:

        codigo = request.form.get("codigo_barras")
        cantidad = int(request.form.get("cantidad", 1))

        if not codigo:
            flash("Código no proporcionado")
            return cerrar_y_redirigir("ventas")

        # Buscar en productos
        cursor.execute("SELECT * FROM productos WHERE codigo_barras=%s", (codigo,))
        item = cursor.fetchone()

        if item:
            tipo = "producto"

            if item["stock"] < cantidad:
                flash("Stock insuficiente")
                return cerrar_y_redirigir("ventas")

        else:
            # Buscar en servicios
            cursor.execute("SELECT * FROM servicios WHERE codigo_barras=%s", (codigo,))
            item = cursor.fetchone()

            if item:
                tipo = "servicio"
            else:
                flash("Código no encontrado")
                return cerrar_y_redirigir("ventas")

        carrito_item = {
            "tipo": tipo,
            "id": item["id"],
            "nombre": item["nombre"],
            "precio": float(item["precio"]),
            "cantidad": cantidad,
            "subtotal": float(item["precio"]) * cantidad
        }

        session["carrito"].append(carrito_item)
        session.modified = True

        return cerrar_y_redirigir("ventas")

    # ==========================
    # ELIMINAR ITEM
    # ==========================
    if request.method == "POST" and "eliminar" in request.form:

        index = int(request.form.get("index"))
        session["carrito"].pop(index)
        session.modified = True

        return cerrar_y_redirigir("ventas")

    # ==========================
    # VACIAR CARRITO
    # ==========================
    if request.method == "POST" and "vaciar" in request.form:

        session["carrito"] = []
        session.modified = True

        return cerrar_y_redirigir("ventas")

    # ==========================
    # FINALIZAR VENTA
    # ==========================
    if request.method == "POST" and "finalizar" in request.form:

        carrito = session.get("carrito", [])

        if not carrito:
            flash("Carrito vacío")
            return cerrar_y_redirigir("ventas")

        metodo_pago = request.form.get("metodo_pago")
        cliente_id = request.form.get("cliente_id")
        mascota_id = request.form.get("mascota_id") or session.get("venta_mascota_id")
        mascota_opcion = request.form.get("mascota_opcion")
        cita_id = session.get("venta_cita_id")

        if mascota_opcion == "nueva":
            mascota_nombre = request.form.get("mascota_nombre")

            if not mascota_nombre:
                flash("El nombre de la mascota nueva es obligatorio")
                return cerrar_y_redirigir("ventas")

            cursor.execute("""
                INSERT INTO mascotas
                (nombre, especie, cliente_id, raza, edad, genero, talla, color, alergias, notas)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                mascota_nombre,
                request.form.get("mascota_especie") or "Perro",
                cliente_id if cliente_id else None,
                request.form.get("mascota_raza"),
                request.form.get("mascota_edad") or None,
                request.form.get("mascota_genero"),
                request.form.get("mascota_talla"),
                request.form.get("mascota_color"),
                request.form.get("mascota_alergias"),
                request.form.get("mascota_notas"),
            ))
            mysql.connection.commit()
            mascota_id = cursor.lastrowid

        if mascota_id and not cliente_id:
            cursor.execute("SELECT cliente_id FROM mascotas WHERE id=%s", (mascota_id,))
            mascota_venta = cursor.fetchone()
            if mascota_venta and mascota_venta.get("cliente_id"):
                cliente_id = mascota_venta["cliente_id"]

        if cliente_id and mascota_id and mascota_opcion != "nueva":
            cursor.execute(
                "SELECT id FROM mascotas WHERE id=%s AND cliente_id=%s",
                (mascota_id, cliente_id)
            )
            if not cursor.fetchone():
                flash("La mascota seleccionada no pertenece al cliente elegido")
                return cerrar_y_redirigir("ventas")

        total = sum(item["subtotal"] for item in carrito)

        cursor.execute(
            "INSERT INTO ventas (total, metodo_pago, cliente_id, mascota_id, cita_id) VALUES (%s, %s, %s, %s, %s)",
            (total, metodo_pago, cliente_id if cliente_id else None, mascota_id if mascota_id else None, cita_id)
        )

        mysql.connection.commit()
        venta_id = cursor.lastrowid

        for item in carrito:

            if item["tipo"] == "producto":

                cursor.execute("""
                    INSERT INTO detalle_venta
                    (venta_id, tipo, producto_id, servicio_id, cantidad, precio_unitario, subtotal)
                    VALUES (%s, %s, %s, NULL, %s, %s, %s)
                """, (
                    venta_id,
                    "producto",
                    item["id"],
                    item["cantidad"],
                    item["precio"],
                    item["subtotal"]
                ))

                cursor.execute("""
                    UPDATE productos
                    SET stock = stock - %s
                    WHERE id = %s
                """, (item["cantidad"], item["id"]))

            elif item["tipo"] == "servicio":

                cursor.execute("""
                    INSERT INTO detalle_venta
                    (venta_id, tipo, producto_id, servicio_id, cantidad, precio_unitario, subtotal)
                    VALUES (%s, %s, NULL, %s, %s, %s, %s)
                """, (
                    venta_id,
                    "servicio",
                    item["id"],
                    item["cantidad"],
                    item["precio"],
                    item["subtotal"]
                ))

        mysql.connection.commit()

        session["carrito"] = []
        session.pop("venta_mascota_id", None)
        session.pop("venta_cita_id", None)
        flash("Venta completada correctamente")

        return cerrar_y_redirigir("ticket_html", venta_id=venta_id)

    # ==========================
    # CARGAR DATOS
    # ==========================
    rellenar_codigos_barras_faltantes("productos")
    rellenar_codigos_barras_faltantes("servicios")

    cursor.execute("SELECT * FROM productos")
    productos = cursor.fetchall()

    cursor.execute("SELECT * FROM servicios")
    servicios = cursor.fetchall()

    cursor.execute("SELECT * FROM clientes")
    clientes = cursor.fetchall()

    cursor.execute("""
        SELECT mascotas.*, clientes.nombre as dueno
        FROM mascotas
        JOIN clientes ON mascotas.cliente_id = clientes.id
        ORDER BY mascotas.nombre
    """)
    mascotas = cursor.fetchall()

    venta_cliente_id = None
    if session.get("venta_mascota_id"):
        for mascota in mascotas:
            if mascota["id"] == session.get("venta_mascota_id"):
                venta_cliente_id = mascota.get("cliente_id")
                break

    cursor.close()

    return render_template(
        "ventas.html",
        productos=productos,
        servicios=servicios,
        clientes=clientes,
        mascotas=mascotas,
        venta_cliente_id=venta_cliente_id,
        carrito=session.get("carrito", [])
    )

# -------------------
# Cancelar Venta y Devolver Stock
# -------------------
@app.route("/cancelar_venta/<int:venta_id>")
@login_required
@rol_requerido(["admin"])
def cancelar_venta(venta_id):

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # verificar venta
    cursor.execute("""
        SELECT v.*, c.nombre as cliente, m.nombre as mascota
        FROM ventas v
        LEFT JOIN clientes c ON v.cliente_id = c.id
        LEFT JOIN mascotas m ON v.mascota_id = m.id
        WHERE v.id=%s
    """, (venta_id,))
    venta = cursor.fetchone()

    if not venta:
        flash("Venta no encontrada")
        return redirect(url_for("ventas_lista"))

    if venta["estado"] == "cancelada":
        flash("La venta ya está cancelada")
        return redirect(url_for("ventas_lista"))

    # obtener detalle
    cursor.execute("""
        SELECT *
        FROM detalle_venta
        WHERE venta_id=%s
    """, (venta_id,))

    detalles = cursor.fetchall()

    # devolver inventario solo productos
    for d in detalles:

        if d["tipo"] == "producto":

            cursor.execute("""
                UPDATE productos
                SET stock = stock + %s
                WHERE id = %s
            """, (d["cantidad"], d["producto_id"]))

    # actualizar estado venta
    cursor.execute("""
        UPDATE ventas
        SET estado='cancelada'
        WHERE id=%s
    """, (venta_id,))

    mysql.connection.commit()
    cursor.close()

    flash("Venta cancelada y stock devuelto correctamente")

    return redirect(url_for("ventas_lista"))

# -------------------
# Ticket de venta
# -------------------
@app.route("/ticket/<int:venta_id>")
@login_required
def generar_ticket(venta_id):

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    elements = []
    styles = getSampleStyleSheet()

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT v.*, c.nombre as cliente, m.nombre as mascota
        FROM ventas v
        LEFT JOIN clientes c ON v.cliente_id = c.id
        LEFT JOIN mascotas m ON v.mascota_id = m.id
        WHERE v.id=%s
    """, (venta_id,))
    venta = cursor.fetchone()

    cursor.execute("""
    SELECT 
        d.tipo,
        d.cantidad,
        d.subtotal,
        COALESCE(p.nombre, s.nombre) as nombre
    FROM detalle_venta d
    LEFT JOIN productos p ON d.producto_id = p.id
    LEFT JOIN servicios s ON d.servicio_id = s.id
    WHERE d.venta_id = %s
""", (venta_id,))

    detalles = cursor.fetchall()
    cursor.close()

    elements.append(Paragraph(f"Ticket Venta #{venta_id}", styles["Title"]))
    elements.append(Spacer(1, 12))

    for d in detalles:
        elements.append(Paragraph(
            f"{d['nombre']} x{d['cantidad']} - ${d['subtotal']}",
            styles["Normal"]
        ))

    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Total: ${venta['total']}", styles["Heading2"]))

    doc.build(elements)
    buffer.seek(0)

    return send_file(buffer,
                     as_attachment=True,
                     download_name=f"ticket_{venta_id}.pdf",
                     mimetype="application/pdf")

# -------------------
# Impresión de Ticket 58mm / 80mm
# -------------------
@app.route("/ticket_html/<int:venta_id>")
@login_required
def ticket_html(venta_id):

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT v.*,
               c.nombre AS cliente,
               m.nombre AS mascota
        FROM ventas v
        LEFT JOIN clientes c ON v.cliente_id = c.id
        LEFT JOIN mascotas m ON v.mascota_id = m.id
        WHERE v.id=%s
    """, (venta_id,))
    venta = cursor.fetchone()

    cursor.execute("""
        SELECT 
            d.tipo,
            d.cantidad,
            d.subtotal,
            COALESCE(p.nombre, s.nombre) as nombre
        FROM detalle_venta d
        LEFT JOIN productos p ON d.producto_id=p.id
        LEFT JOIN servicios s ON d.servicio_id=s.id
        WHERE venta_id=%s
    """, (venta_id,))

    detalles = cursor.fetchall()
    cursor.close()

    return render_template("ticket_print.html",
                           venta=venta,
                           detalles=detalles)

# -------------------
# REPORTE DE VENTAS DIARIO
# -------------------
@app.route("/reporte_diario")
@login_required
@rol_requerido(["admin"])
def reporte_diario():

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT 
            IFNULL(SUM(total),0) as total_dia,
            COUNT(*) as ventas
        FROM ventas
        WHERE DATE(fecha)=CURDATE()
        AND estado='activa'
    """)

    data = cursor.fetchone()
    cursor.close()

    return render_template("reporte.html", data=data)


# -------------------
# CORTE DE CAJA
# -------------------
@app.route("/corte")
@login_required
def corte():

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT SUM(total) as total,
               COUNT(*) as ventas
        FROM ventas
        WHERE DATE(fecha) = CURDATE()
    """)

    datos = cursor.fetchone()

    cursor.execute("""
        INSERT INTO corte_caja (total_ventas, cantidad_ventas)
        VALUES (%s, %s)
    """, (datos["total"] or 0, datos["ventas"] or 0))

    mysql.connection.commit()
    cursor.close()

    flash("Corte realizado correctamente")
    return redirect(url_for("dashboard"))


# Abrir caja con monto inicial 
# -------------------
@app.route("/abrir_caja", methods=["GET", "POST"])
@login_required
def abrir_caja():

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT * FROM caja WHERE estado='abierta'")
    caja_abierta = cursor.fetchone()

    if caja_abierta:
        flash("Ya existe una caja abierta")
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        monto = float(request.form.get("monto_inicial"))

        cursor.execute("""
            INSERT INTO caja (monto_inicial)
            VALUES (%s)
        """, (monto,))

        mysql.connection.commit()
        flash("Caja abierta correctamente")
        return redirect(url_for("dashboard"))

    cursor.close()
    return render_template("abrir_caja.html")


# Cerrar caja con monto final y diferencias
# -------------------
@app.route("/cerrar_caja", methods=["GET", "POST"])
@login_required
def cerrar_caja():

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Buscar caja abierta
    cursor.execute("SELECT * FROM caja WHERE estado='abierta'")
    caja = cursor.fetchone()

    if not caja:
        flash("No hay caja abierta")
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        try:
            monto_final = float(request.form.get("monto_final"))

            # Calcular ventas desde apertura hasta ahora
            cursor.execute("""
                SELECT IFNULL(SUM(total),0) as total_ventas
                FROM ventas
                WHERE estado='activa'
                AND fecha BETWEEN %s AND NOW()
            """, (caja["fecha_apertura"],))

            resultado = cursor.fetchone()
            total_ventas = resultado["total_ventas"] if resultado else 0

            diferencia = monto_final - (float(caja["monto_inicial"]) + float(total_ventas))

            cursor.execute("""
                UPDATE caja
                SET fecha_cierre=NOW(),
                    monto_final=%s,
                    diferencia=%s,
                    estado='cerrada'
                WHERE id=%s
            """, (monto_final, diferencia, caja["id"]))

            mysql.connection.commit()

            flash(f"Caja cerrada correctamente. Diferencia: ${diferencia}")

        except Exception as e:
            mysql.connection.rollback()
            flash(f"Error al cerrar caja: {str(e)}")

        return redirect(url_for("dashboard"))

    cursor.close()
    return render_template("cerrar_caja.html", caja=caja)

# -------------------
# LISTA DE VENTAS
# -------------------
@app.route("/ventas_lista")
@login_required
def ventas_lista():

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
    SELECT id, fecha, total, metodo_pago, estado
    FROM ventas
    ORDER BY fecha DESC
""")

    ventas = cursor.fetchall()
    cursor.close()

    return render_template("ventas_lista.html", ventas=ventas)

# -------------------
# DETALLES DE CADA VENTA
@app.route("/venta/<int:venta_id>")
@login_required
def ver_venta(venta_id):

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT * FROM ventas WHERE id=%s", (venta_id,))
    venta = cursor.fetchone()

    cursor.execute("""
        SELECT 
            d.tipo,
            d.cantidad,
            d.subtotal,
            COALESCE(p.nombre, s.nombre) as nombre
        FROM detalle_venta d
        LEFT JOIN productos p ON d.producto_id = p.id
        LEFT JOIN servicios s ON d.servicio_id = s.id
        WHERE d.venta_id = %s
    """, (venta_id,))

    detalles = cursor.fetchall()

    cursor.close()

    return render_template("ver_venta.html",
                           venta=venta,
                           detalles=detalles)


# -------------------
# Entrada de Inventario con lector de codigo de barras 
# -------------------
@app.route("/entrada_inventario", methods=["GET", "POST"])
@login_required
def entrada_inventario():

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == "POST":

        codigo = request.form.get("codigo_barras")
        cantidad = int(request.form.get("cantidad", 1))

        cursor.execute("SELECT * FROM productos WHERE codigo_barras=%s", (codigo,))
        producto = cursor.fetchone()

        if not producto:
            flash("Producto no encontrado")
            return redirect(url_for("entrada_inventario"))

        # actualizar stock
        cursor.execute("""
            UPDATE productos
            SET stock = stock + %s
            WHERE id = %s
        """, (cantidad, producto["id"]))

        # registrar entrada
        cursor.execute("""
            INSERT INTO entradas_inventario (producto_id, cantidad)
            VALUES (%s, %s)
        """, (producto["id"], cantidad))

        mysql.connection.commit()

        flash("Entrada registrada correctamente")

        return redirect(url_for("entrada_inventario"))

    cursor.close()

    return render_template("entrada_inventario.html")


# -------------------
# SERVICIOS
# -------------------
@app.route("/servicios", methods=["GET", "POST"])
@login_required
def servicios():

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == "POST":

        nombre = request.form.get("nombre")
        precio = request.form.get("precio")
        descripcion = request.form.get("descripcion")
        codigo = generar_codigo_barra("SERV")

        cursor.execute("""
            INSERT INTO servicios (nombre, precio, descripcion, codigo_barras)
            VALUES (%s, %s, %s, %s)
        """, (nombre, precio, descripcion, codigo))

        mysql.connection.commit()
        flash("Servicio agregado correctamente")

        return redirect(url_for("servicios"))

    rellenar_codigos_barras_faltantes("servicios")
    cursor.execute("SELECT * FROM servicios")
    servicios = cursor.fetchall()

    cursor.close()

    return render_template("servicios.html", servicios=servicios)

# EDITAR SERVICIO
# -------------------
@app.route("/editar_servicio/<int:id>", methods=["GET", "POST"])
@login_required
@rol_requerido(["admin"])
def editar_servicio(id):

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT * FROM servicios WHERE id=%s", (id,))
    servicio = cursor.fetchone()

    if not servicio:
        flash("Servicio no encontrado")
        return redirect(url_for("servicios"))

    if request.method == "POST":

        nombre = request.form["nombre"]
        precio = request.form["precio"]
        descripcion = request.form["descripcion"]
        codigo = (servicio.get("codigo_barras") or "").strip()
        if not codigo:
            codigo = generar_codigo_barra("SERV")

        cursor.execute("""
            UPDATE servicios
            SET nombre=%s,
                precio=%s,
                descripcion=%s,
                codigo_barras=%s
            WHERE id=%s
        """, (nombre, precio, descripcion, codigo, id))

        mysql.connection.commit()
        flash("Servicio actualizado correctamente")
        return redirect(url_for("servicios"))

    cursor.close()
    return render_template("editar_servicio.html", servicio=servicio)


# ELIMINAR SERVICIO
# -------------------
@app.route("/eliminar_servicio/<int:id>")
@login_required
@rol_requerido(["admin"])
def eliminar_servicio(id):

    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM servicios WHERE id=%s", (id,))
    mysql.connection.commit()
    cursor.close()

    flash("Servicio eliminado correctamente")
    return redirect(url_for("servicios"))


# EXPORTAR SERVICIO A EXCEL
# -------------------
@app.route("/exportar_servicios")
@login_required
@rol_requerido(["admin"])
def exportar_servicios():

    rellenar_codigos_barras_faltantes("servicios")
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM servicios")
    servicios = cursor.fetchall()
    cursor.close()

    wb = Workbook()
    ws = wb.active
    ws.title = "Servicios"

    ws.append(["ID", "Nombre", "Precio", "Descripción", "Código Barras"])

    for s in servicios:
        ws.append([
            s["id"],
            s["nombre"],
            float(s["precio"]),
            s["descripcion"],
            s.get("codigo_barras", "")
        ])

    file = io.BytesIO()
    wb.save(file)
    file.seek(0)

    return send_file(
        file,
        download_name="servicios.xlsx",
        as_attachment=True
    )

# ETIQUETAS DE SERVICIOS EN PDF
# -------------------
@app.route("/etiquetas_servicios_carta")
@login_required
@rol_requerido(["admin"])
def etiquetas_servicios_carta():

    rellenar_codigos_barras_faltantes("servicios")
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=letter)

    elements = []
    styles = getSampleStyleSheet()

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT nombre, precio, codigo_barras FROM servicios")
    servicios = cursor.fetchall()
    cursor.close()

    etiquetas = []
    fila = []

    for s in servicios:

        contenido = []

        contenido.append(Paragraph(f"<b>{s['nombre']}</b>", styles["Normal"]))
        contenido.append(Spacer(1, 3))
        contenido.append(Paragraph(f"${s['precio']}", styles["Normal"]))
        contenido.append(Spacer(1, 4))

        if s["codigo_barras"]:
            barcode = code128.Code128(
                str(s["codigo_barras"]),
                barHeight=15*mm,
                barWidth=1.0
            )
            contenido.append(barcode)
            contenido.append(Spacer(1, 3))
            contenido.append(Paragraph(str(s["codigo_barras"]), styles["Normal"]))

        etiqueta = Table([[contenido]],
                         colWidths=60*mm,
                         rowHeights=38*mm)

        etiqueta.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ]))

        fila.append(etiqueta)

        if len(fila) == 3:
            etiquetas.append(fila)
            fila = []

    if fila:
        while len(fila) < 3:
            fila.append("")
        etiquetas.append(fila)

    elements.append(Table(etiquetas, colWidths=[65*mm]*3))

    doc.build(elements)
    buffer.seek(0)

    return send_file(buffer,
                     as_attachment=True,
                     download_name="etiquetas_servicios_carta.pdf",
                     mimetype="application/pdf")


# -------------------
# INSUMOS
# -------------------
@app.route("/insumos", methods=["GET", "POST"])
@login_required
@rol_requerido(["admin"])
def insumos():

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == "POST":

        nombre = request.form["nombre"]
        stock = request.form["stock"]
        costo = request.form["costo"]
        proveedor_id = request.form.get("proveedor_id") or None
        codigo = generar_codigo_barra("INS")

        cursor.execute("""
            INSERT INTO insumos (nombre, stock, costo, proveedor_id, codigo_barras)
            VALUES (%s, %s, %s, %s, %s)
        """, (nombre, stock, costo, proveedor_id, codigo))

        mysql.connection.commit()
        flash("Insumo agregado")
        return redirect(url_for("insumos"))

    rellenar_codigos_barras_faltantes("insumos")
    cursor.execute("""
        SELECT insumos.*, proveedores.nombre AS proveedor_nombre
        FROM insumos
        LEFT JOIN proveedores ON insumos.proveedor_id = proveedores.id
        ORDER BY insumos.fecha DESC
    """)
    insumos = cursor.fetchall()
    cursor.execute("SELECT * FROM proveedores ORDER BY nombre")
    proveedores = cursor.fetchall()
    cursor.close()

    return render_template("insumos.html", insumos=insumos, proveedores=proveedores)


# EDITAR INSUMO
# -------------------
@app.route("/editar_insumo/<int:id>", methods=["GET", "POST"])
@login_required
@rol_requerido(["admin"])
def editar_insumo(id):

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT * FROM insumos WHERE id=%s", (id,))
    insumo = cursor.fetchone()

    if not insumo:
        flash("Insumo no encontrado")
        return redirect(url_for("insumos"))

    if request.method == "POST":

        nombre = request.form["nombre"]
        stock = request.form["stock"]
        costo = request.form["costo"]
        proveedor_id = request.form.get("proveedor_id") or None
        codigo = (insumo.get("codigo_barras") or "").strip()
        if not codigo:
            codigo = generar_codigo_barra("INS")

        cursor.execute("""
            UPDATE insumos
            SET nombre=%s,
                stock=%s,
                costo=%s,
                proveedor_id=%s,
                codigo_barras=%s
            WHERE id=%s
        """, (nombre, stock, costo, proveedor_id, codigo, id))

        mysql.connection.commit()
        flash("Insumo actualizado correctamente")
        return redirect(url_for("insumos"))

    cursor.execute("SELECT * FROM proveedores ORDER BY nombre")
    proveedores = cursor.fetchall()
    cursor.close()
    return render_template("editar_insumo.html", insumo=insumo, proveedores=proveedores)


# ELIMINAR INSUMO
# -------------------
@app.route("/eliminar_insumo/<int:id>")
@login_required
@rol_requerido(["admin"])
def eliminar_insumo(id):

    cursor = mysql.connection.cursor()

    cursor.execute("DELETE FROM insumos WHERE id=%s", (id,))
    mysql.connection.commit()
    cursor.close()

    flash("Insumo eliminado correctamente")
    return redirect(url_for("insumos"))

# EXPORTAR INSUMOS A EXCEL
# -------------------
@app.route("/exportar_insumos")
@login_required
@rol_requerido(["admin"])
def exportar_insumos():

    rellenar_codigos_barras_faltantes("insumos")
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT insumos.*, proveedores.nombre AS proveedor_nombre
        FROM insumos
        LEFT JOIN proveedores ON insumos.proveedor_id = proveedores.id
    """)
    insumos = cursor.fetchall()
    cursor.close()

    wb = Workbook()
    ws = wb.active
    ws.title = "Insumos"

    ws.append(["ID", "Nombre", "Stock", "Costo", "Proveedor", "Código Barras"])

    for i in insumos:
        ws.append([
            i["id"],
            i["nombre"],
            i["stock"],
            float(i["costo"]),
            i.get("proveedor_nombre") or i.get("proveedor", ""),
            i.get("codigo_barras", "")
        ])

    file = io.BytesIO()
    wb.save(file)
    file.seek(0)

    return send_file(
        file,
        download_name="insumos.xlsx",
        as_attachment=True
    )

# ETIQUETAS DE INSUMOS EN PDF
# -------------------
@app.route("/etiquetas_insumos_carta")
@login_required
@rol_requerido(["admin"])
def etiquetas_insumos_carta():

    rellenar_codigos_barras_faltantes("insumos")
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    elements = []
    styles = getSampleStyleSheet()

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT nombre, costo, codigo_barras FROM insumos")
    insumos = cursor.fetchall()
    cursor.close()

    etiquetas = []
    fila = []

    for i in insumos:

        contenido = []

        contenido.append(Paragraph(f"<b>{i['nombre']}</b>", styles["Normal"]))
        contenido.append(Spacer(1, 3))
        contenido.append(Paragraph(f"${i['costo']}", styles["Normal"]))
        contenido.append(Spacer(1, 4))

        if i["codigo_barras"]:
            barcode = code128.Code128(
                str(i["codigo_barras"]),
                barHeight=15*mm,
                barWidth=1.0
            )
            contenido.append(barcode)
            contenido.append(Spacer(1, 3))
            contenido.append(Paragraph(str(i["codigo_barras"]), styles["Normal"]))

        etiqueta = Table([[contenido]],
                         colWidths=60*mm,
                         rowHeights=38*mm)

        etiqueta.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ]))

        fila.append(etiqueta)

        if len(fila) == 3:
            etiquetas.append(fila)
            fila = []

    if fila:
        while len(fila) < 3:
            fila.append("")
        etiquetas.append(fila)

    elements.append(Table(etiquetas, colWidths=[65*mm]*3))

    doc.build(elements)
    buffer.seek(0)

    return send_file(buffer,
                     as_attachment=True,
                     download_name="etiquetas_insumos_carta.pdf",
                     mimetype="application/pdf")


# -------------------
# PROVEEDORES
# -------------------
@app.route("/proveedores", methods=["GET", "POST"])
@login_required
@rol_requerido(["admin"])
def proveedores():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == "POST":
        nombre = request.form["nombre"]
        direccion_contacto = request.form.get("direccion_contacto")
        telefono = request.form.get("telefono")
        observaciones = request.form.get("observaciones")

        cursor.execute("""
            INSERT INTO proveedores (nombre, direccion_contacto, telefono, observaciones)
            VALUES (%s, %s, %s, %s)
        """, (nombre, direccion_contacto, telefono, observaciones))

        mysql.connection.commit()
        cursor.close()
        flash("Proveedor agregado correctamente")
        return redirect(url_for("proveedores"))

    cursor.execute("""
        SELECT proveedores.*,
               (SELECT COUNT(*) FROM productos WHERE productos.proveedor_id = proveedores.id) AS productos_count,
               (SELECT COUNT(*) FROM insumos WHERE insumos.proveedor_id = proveedores.id) AS insumos_count
        FROM proveedores
        ORDER BY proveedores.nombre
    """)
    proveedores = cursor.fetchall()
    cursor.close()

    return render_template("proveedores.html", proveedores=proveedores)


@app.route("/editar_proveedor/<int:id>", methods=["GET", "POST"])
@login_required
@rol_requerido(["admin"])
def editar_proveedor(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT * FROM proveedores WHERE id=%s", (id,))
    proveedor = cursor.fetchone()

    if not proveedor:
        cursor.close()
        flash("Proveedor no encontrado")
        return redirect(url_for("proveedores"))

    if request.method == "POST":
        nombre = request.form["nombre"]
        direccion_contacto = request.form.get("direccion_contacto")
        telefono = request.form.get("telefono")
        observaciones = request.form.get("observaciones")

        cursor.execute("""
            UPDATE proveedores
            SET nombre=%s,
                direccion_contacto=%s,
                telefono=%s,
                observaciones=%s
            WHERE id=%s
        """, (nombre, direccion_contacto, telefono, observaciones, id))

        mysql.connection.commit()
        cursor.close()
        flash("Proveedor actualizado correctamente")
        return redirect(url_for("proveedores"))

    cursor.close()
    return render_template("editar_proveedor.html", proveedor=proveedor)


@app.route("/eliminar_proveedor/<int:id>")
@login_required
@rol_requerido(["admin"])
def eliminar_proveedor(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT
            (SELECT COUNT(*) FROM productos WHERE proveedor_id=%s) AS productos_count,
            (SELECT COUNT(*) FROM insumos WHERE proveedor_id=%s) AS insumos_count
    """, (id, id))
    uso = cursor.fetchone()

    if uso and (uso["productos_count"] or uso["insumos_count"]):
        cursor.close()
        flash("No se puede eliminar: el proveedor está ligado a productos o insumos")
        return redirect(url_for("proveedores"))

    cursor.execute("DELETE FROM proveedores WHERE id=%s", (id,))
    mysql.connection.commit()
    cursor.close()

    flash("Proveedor eliminado correctamente")
    return redirect(url_for("proveedores"))


# -------------------
# GASTOS O SERVICIOS A PAGAR
# -------------------
@app.route("/gastos", methods=["GET", "POST"])
@login_required
@rol_requerido(["admin"])
def gastos():

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == "POST":

        concepto = request.form["concepto"]
        monto = request.form["monto"]
        fecha = request.form["fecha"]
        descripcion = request.form["descripcion"]

        cursor.execute("""
            INSERT INTO gastos_fijos (concepto, monto, fecha, descripcion)
            VALUES (%s, %s, %s, %s)
        """, (concepto, monto, fecha, descripcion))

        mysql.connection.commit()
        flash("Gasto registrado")
        return redirect(url_for("gastos"))

    cursor.execute("SELECT * FROM gastos_fijos ORDER BY fecha DESC")
    gastos = cursor.fetchall()
    cursor.close()

    return render_template("gastos.html", gastos=gastos)


# -------------------FINAL DE APP-------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
