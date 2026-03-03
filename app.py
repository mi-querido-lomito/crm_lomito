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
from datetime import datetime

def actualizar_citas_perdidas():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        UPDATE citas
        SET estado='perdida'
        WHERE estado='pendiente'
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


mysql = MySQL()
mysql.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

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
        cursor.execute("SELECT * FROM usuarios WHERE username=%s AND password=%s", (username, password))
        user = cursor.fetchone()
        cursor.close()

        if user:
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

    # Totales generales
    cursor.execute("SELECT COUNT(*) as total FROM clientes")
    clientes = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM mascotas")
    mascotas = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM productos")
    productos = cursor.fetchone()["total"]

    # Ventas hoy
    cursor.execute("""
        SELECT IFNULL(SUM(total),0) as total_hoy
        FROM ventas
        WHERE DATE(fecha)=CURDATE()
        AND estado='activa'
    """)
    total_hoy = cursor.fetchone()["total_hoy"]

    #Citas de hoy
    cursor.execute("""
        SELECT estado, COUNT(*) as total
        FROM citas
        WHERE fecha = CURDATE()
        GROUP BY estado
    """)
    resumen_citas = cursor.fetchall()

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

    # Inventario bajo
    cursor.execute("SELECT nombre, stock FROM productos WHERE stock <= 5")
    bajo_stock = cursor.fetchall()

    # Estado de caja
    cursor.execute("SELECT * FROM caja WHERE estado='abierta'")
    caja_abierta = cursor.fetchone()

    cursor.execute("""
        SELECT c.id, c.fecha, m.nombre as mascota
        FROM citas c
        JOIN mascotas m ON c.mascota_id = m.id
        WHERE c.estado='pendiente'
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
        nombre = request.form["nombre"]
        telefono = request.form["telefono"]
        email = request.form["email"]

        cursor.execute("INSERT INTO clientes (nombre, telefono, email) VALUES (%s,%s,%s)",
                       (nombre, telefono, email))
        mysql.connection.commit()

    cursor.execute("SELECT * FROM clientes")
    data = cursor.fetchall()
    cursor.close()

    return render_template("clientes.html", clientes=data)

# -------------------
# EDITAR CLIENTE
@app.route("/editar_cliente/<int:id>", methods=["GET", "POST"])
@login_required
def editar_cliente(id):

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT * FROM clientes WHERE id=%s", (id,))
    cliente = cursor.fetchone()

    if not cliente:
        flash("Cliente no encontrado")
        return redirect(url_for("clientes"))

    if request.method == "POST":

        nombre = request.form["nombre"]
        telefono = request.form["telefono"]
        email = request.form["email"]

        cursor.execute("""
            UPDATE clientes
            SET nombre=%s,
                telefono=%s,
                email=%s
            WHERE id=%s
        """, (nombre, telefono, email, id))

        mysql.connection.commit()
        flash("Cliente actualizado correctamente")
        return redirect(url_for("clientes"))

    cursor.close()
    return render_template("editar_cliente.html", cliente=cliente)

# Botón de ELIMINAR CLIENTE
# -------------------  
@app.route("/eliminar_cliente/<int:id>")
@login_required
@rol_requerido(["admin"])
def eliminar_cliente(id):

    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM clientes WHERE id=%s", (id,))
    mysql.connection.commit()
    cursor.close()

    flash("Cliente eliminado correctamente")
    return redirect(url_for("clientes"))

# -------------------
# EXPORTAR CLIENTES A PDF  
@app.route("/clientes/pdf")
@login_required
def export_clientes_pdf():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    elements = []

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT nombre, telefono, email FROM clientes")
    data = cursor.fetchall()
    cursor.close()

    table_data = [("Nombre", "Teléfono", "Email")]
    table_data.extend(data)

    table = Table(table_data)
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    return send_file(buffer, as_attachment=True,
                     download_name="clientes.pdf",
                     mimetype='application/pdf')

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
        cliente_id = request.form["cliente_id"]

        cursor.execute("INSERT INTO mascotas (nombre, especie, cliente_id) VALUES (%s,%s,%s)",
                       (nombre, especie, cliente_id))
        mysql.connection.commit()

    cursor.execute("SELECT mascotas.*, clientes.nombre as dueno FROM mascotas JOIN clientes ON mascotas.cliente_id = clientes.id")
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
        flash("Mascota no encontrada")
        return redirect(url_for("mascotas"))

    # necesitamos lista de clientes para el select
    cursor.execute("SELECT * FROM clientes")
    clientes = cursor.fetchall()

    if request.method == "POST":

        nombre = request.form["nombre"]
        especie = request.form["especie"]
        cliente_id = request.form["cliente_id"]

        cursor.execute("""
            UPDATE mascotas
            SET nombre=%s,
                especie=%s,
                cliente_id=%s
            WHERE id=%s
        """, (nombre, especie, cliente_id, id))

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


# -------------------
# PRODUCTOS
# -------------------

@app.route("/productos", methods=["GET", "POST"])
@login_required
def productos():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == "POST":
        nombre = request.form["nombre"]
        stock = request.form["stock"]
        precio = request.form["precio"]
        codigo = request.form["codigo_barras"]

        cursor.execute(
    "INSERT INTO productos (nombre, stock, precio, codigo_barras) VALUES (%s,%s,%s,%s)",
    (nombre, stock, precio, codigo))
        mysql.connection.commit()

    cursor.execute("SELECT * FROM productos")
    data = cursor.fetchall()
    cursor.close()

    return render_template("productos.html", productos=data)

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
        codigo = request.form["codigo_barras"]

        cursor.execute("""
            UPDATE productos
            SET nombre=%s,
                precio=%s,
                stock=%s,
                codigo_barras=%s
            WHERE id=%s
        """, (nombre, precio, stock, codigo, id))

        mysql.connection.commit()
        flash("Producto actualizado correctamente")
        return redirect(url_for("productos"))

    cursor.close()
    return render_template("editar_producto.html", producto=producto)

# EXPORTAR PRODUCTO A EXCEL
# -------------------
@app.route("/exportar_productos")
@login_required
@rol_requerido(["admin"])
def exportar_productos():

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM productos")
    productos = cursor.fetchall()
    cursor.close()

    wb = Workbook()
    ws = wb.active
    ws.title = "Productos"

    ws.append(["ID", "Nombre", "Stock", "Precio", "Código Barras"])

    for p in productos:
        ws.append([
            p["id"],
            p["nombre"],
            p["stock"],
            float(p["precio"]),
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

        cursor.execute("INSERT INTO citas (mascota_id, fecha, estado) VALUES (%s,%s,'Pendiente')",
                       (mascota_id, fecha))
        mysql.connection.commit()

    cursor.execute("SELECT citas.*, mascotas.nombre as mascota FROM citas JOIN mascotas ON citas.mascota_id = mascotas.id")
    data = cursor.fetchall()

    cursor.execute("SELECT * FROM mascotas")
    mascotas = cursor.fetchall()

    cursor.close()

    return render_template("citas.html", citas=data, mascotas=mascotas)

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
        flash("Cita no encontrada")
        return redirect(url_for("citas"))

    if request.method == "POST":

        fecha_raw = request.form["fecha"]

        # convertir formato HTML a formato MySQL
        fecha_convertida = datetime.strptime(
            fecha_raw, "%Y-%m-%dT%H:%M"
        )

        estado = request.form["estado"]

        cursor.execute("""
            UPDATE citas
            SET fecha=%s,
                estado=%s
            WHERE id=%s
        """, (fecha_convertida, estado, id))

        mysql.connection.commit()
        flash("Cita actualizada correctamente")
        return redirect(url_for("citas"))

    cursor.close()

    # convertir fecha MySQL a formato HTML datetime-local
    fecha_html = cita["fecha"].strftime("%Y-%m-%dT%H:%M")

    return render_template("editar_cita.html",
                           cita=cita,
                           fecha_html=fecha_html)

# CANCELAR CITA
# -------------------
@app.route("/cancelar_cita/<int:id>")
@login_required
def cancelar_cita(id):

    cursor = mysql.connection.cursor()

    cursor.execute("""
        UPDATE citas
        SET estado='cancelada'
        WHERE id=%s
    """, (id,))

    mysql.connection.commit()
    cursor.close()

    flash("Cita cancelada correctamente")
    return redirect(url_for("citas"))

# CONVERTIR CITA A VENTA
# -------------------
@app.route("/convertir_cita/<int:id>")
@login_required
def convertir_cita(id):

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT * FROM citas WHERE id=%s", (id,))
    cita = cursor.fetchone()

    if not cita:
        flash("Cita no encontrada")
        return redirect(url_for("citas"))

    # marcar como completada
    cursor.execute("""
        UPDATE citas
        SET estado='completada'
        WHERE id=%s
    """, (id,))

    mysql.connection.commit()

    flash("Cita marcada como completada. Ahora registra la venta.")

    return redirect(url_for("ventas"))

# -------------------
# VENTAS
# -------------------
@app.route("/ventas", methods=["GET", "POST"])
@login_required
def ventas():

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if "carrito" not in session:
        session["carrito"] = []


    # -------------------
# AGREGAR AL CARRITO
# -------------------
if request.method == "POST" and "agregar" in request.form:

    codigo = request.form.get("codigo_barras")
    cantidad = int(request.form.get("cantidad", 1))

    if not codigo:
        flash("Código no proporcionado")
        return redirect(url_for("ventas"))

    # Buscar primero en productos
    cursor.execute("SELECT * FROM productos WHERE codigo_barras=%s", (codigo,))
    item = cursor.fetchone()

    if item:
        tipo = "producto"

        if item["stock"] < cantidad:
            flash("Stock insuficiente")
            return redirect(url_for("ventas"))

    else:
        # Buscar en servicios
        cursor.execute("SELECT * FROM servicios WHERE codigo_barras=%s", (codigo,))
        item = cursor.fetchone()

        if item:
            tipo = "servicio"
        else:
            flash("Código no encontrado")
            return redirect(url_for("ventas"))

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

    return redirect(url_for("ventas"))

    # ELIMINAR ITEM
    # -------------------
    if request.method == "POST" and "eliminar" in request.form:

        index = int(request.form.get("index"))
        session["carrito"].pop(index)
        session.modified = True

        return redirect(url_for("ventas"))

    # VACIAR CARRITO
    # -------------------
    if request.method == "POST" and "vaciar" in request.form:

        session["carrito"] = []
        session.modified = True

        return redirect(url_for("ventas"))

    # FINALIZAR VENTA
    # -------------------
    if request.method == "POST" and "finalizar" in request.form:

    carrito = session.get("carrito", [])

    if not carrito:
        flash("Carrito vacío")
        return redirect(url_for("ventas"))

    metodo_pago = request.form.get("metodo_pago")
    cliente_id = request.form.get("cliente_id")

    total = sum(item["subtotal"] for item in carrito)

    cursor.execute(
        "INSERT INTO ventas (total, metodo_pago, cliente_id) VALUES (%s, %s, %s)",
        (total, metodo_pago, cliente_id if cliente_id else None)
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
    flash("Venta completada correctamente")

    return redirect(url_for("ticket_html", venta_id=venta_id))

    # CARGAR DATOS
    # -------------------
    cursor.execute("SELECT * FROM productos")
    productos = cursor.fetchall()

    cursor.execute("SELECT * FROM servicios")
    servicios = cursor.fetchall()

    cursor.execute("SELECT * FROM clientes")
    clientes = cursor.fetchall()

    cursor.close()

    return render_template(
        "ventas.html",
        productos=productos,
        servicios=servicios,
        clientes=clientes,
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
    cursor.execute("SELECT * FROM ventas WHERE id=%s", (venta_id,))
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

    cursor.execute("SELECT * FROM ventas WHERE id=%s", (venta_id,))
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
        codigo = request.form.get("codigo_barras")

        cursor.execute("""
            INSERT INTO servicios (nombre, precio, descripcion, codigo_barras)
            VALUES (%s, %s, %s, %s)
        """, (nombre, precio, descripcion, codigo))

        mysql.connection.commit()
        flash("Servicio agregado correctamente")

        return redirect(url_for("servicios"))

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
        codigo = request.form.get("codigo_barras")

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
        proveedor = request.form["proveedor"]

        cursor.execute("""
            INSERT INTO insumos (nombre, stock, costo, proveedor)
            VALUES (%s, %s, %s, %s)
        """, (nombre, stock, costo, proveedor))

        mysql.connection.commit()
        flash("Insumo agregado")
        return redirect(url_for("insumos"))

    cursor.execute("SELECT * FROM insumos ORDER BY fecha DESC")
    insumos = cursor.fetchall()
    cursor.close()

    return render_template("insumos.html", insumos=insumos)


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
        proveedor = request.form["proveedor"]
        codigo = request.form.get("codigo_barras")

        cursor.execute("""
            UPDATE insumos
            SET nombre=%s,
                stock=%s,
                costo=%s,
                proveedor=%s,
                codigo_barras=%s
            WHERE id=%s
        """, (nombre, stock, costo, proveedor, codigo, id))

        mysql.connection.commit()
        flash("Insumo actualizado correctamente")
        return redirect(url_for("insumos"))

    cursor.close()
    return render_template("editar_insumo.html", insumo=insumo)


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

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM insumos")
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
            i.get("proveedor", ""),
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
    app.run(host="0.0.0.0", port=3306)

