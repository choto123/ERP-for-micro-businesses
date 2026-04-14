from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort
from werkzeug.security import generate_password_hash, check_password_hash
from database import init_db, get_db
from auth import login_required, admin_required, can_edit
from datetime import date

app = Flask(__name__)
app.secret_key = "erp-tienda-secret-2024-xK9#"

# ── Context processor: disponible en todos los templates ─────────────────────
@app.context_processor
def inject_user():
    return dict(
        current_user={
            "id":     session.get("user_id"),
            "nombre": session.get("user_nombre", ""),
            "rol":    session.get("user_rol", ""),
        },
        can_edit=can_edit()
    )

# ── LOGIN / LOGOUT ────────────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute("SELECT * FROM usuarios WHERE username=?", (username,)).fetchone()
        if not user:
            error = "Usuario no encontrado."
        elif not user["activo"]:
            error = "Esta cuenta está desactivada. Contacta al administrador."
        elif not check_password_hash(user["password"], password):
            error = "Contraseña incorrecta."
        else:
            session.clear()
            session["user_id"]     = user["id"]
            session["user_nombre"] = user["nombre"]
            session["user_rol"]    = user["rol"]
            return redirect(url_for("dashboard"))
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ── ERROR 403 ─────────────────────────────────────────────────────────────────
@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403

# ── DASHBOARD ─────────────────────────────────────────────────────────────────
@app.route("/")
@login_required
def dashboard():
    db = get_db()
    hoy = date.today().isoformat()
    mes = hoy[:7]
    ventas_hoy  = db.execute("SELECT COALESCE(SUM(total),0) as t FROM ventas WHERE fecha=?", (hoy,)).fetchone()["t"]
    ventas_mes  = db.execute("SELECT COALESCE(SUM(total),0) as t FROM ventas WHERE fecha LIKE ?", (mes+"%",)).fetchone()["t"]
    gastos_mes  = db.execute("SELECT COALESCE(SUM(monto),0) as t FROM gastos WHERE fecha LIKE ?", (mes+"%",)).fetchone()["t"]
    n_productos = db.execute("SELECT COUNT(*) as c FROM productos").fetchone()["c"]
    n_clientes  = db.execute("SELECT COUNT(*) as c FROM clientes").fetchone()["c"]
    stock_bajo  = db.execute("SELECT nombre, stock, unidad FROM productos WHERE stock <= stock_min ORDER BY stock ASC LIMIT 8").fetchall()
    ultimas_ventas = db.execute(
        "SELECT v.id, v.fecha, COALESCE(c.nombre,'Consumidor final') as cliente, v.total, v.estado "
        "FROM ventas v LEFT JOIN clientes c ON v.cliente_id=c.id ORDER BY v.id DESC LIMIT 6"
    ).fetchall()
    return render_template("dashboard.html",
        ventas_hoy=ventas_hoy, ventas_mes=ventas_mes,
        gastos_mes=gastos_mes, utilidad=ventas_mes-gastos_mes,
        n_productos=n_productos, n_clientes=n_clientes,
        stock_bajo=stock_bajo, ultimas_ventas=ultimas_ventas, hoy=hoy)

# ── VENTAS ────────────────────────────────────────────────────────────────────
@app.route("/ventas")
@login_required
def ventas():
    db = get_db()
    ventas   = db.execute("SELECT v.id, v.fecha, COALESCE(c.nombre,'Consumidor final') as cliente, v.total, v.pago, v.estado FROM ventas v LEFT JOIN clientes c ON v.cliente_id=c.id ORDER BY v.id DESC").fetchall()
    clientes  = db.execute("SELECT id, nombre FROM clientes ORDER BY nombre").fetchall()
    productos = db.execute("SELECT id, nombre, precio, stock, unidad FROM productos WHERE stock>0 ORDER BY nombre").fetchall()
    return render_template("ventas.html", ventas=ventas, clientes=clientes, productos=productos)

@app.route("/ventas/nueva", methods=["POST"])
@login_required
def nueva_venta():
    if not can_edit(): return jsonify({"error": "Sin permisos"}), 403
    db   = get_db()
    data = request.get_json()
    cliente_id = data.get("cliente_id") or None
    fecha      = data.get("fecha", date.today().isoformat())
    items      = data.get("items", [])
    if not items: return jsonify({"error": "Sin items"}), 400
    total = sum(i["precio"] * i["cant"] for i in items)
    cur   = db.execute("INSERT INTO ventas (fecha, cliente_id, total, pago, estado) VALUES (?,?,?,?,?)",
                       (fecha, cliente_id, total, data.get("pago","Efectivo"), data.get("estado","Pagado")))
    venta_id = cur.lastrowid
    for i in items:
        db.execute("INSERT INTO venta_items (venta_id, producto_id, nombre, cantidad, precio_unit) VALUES (?,?,?,?,?)",
                   (venta_id, i["pid"], i["nombre"], i["cant"], i["precio"]))
        db.execute("UPDATE productos SET stock = stock - ? WHERE id=?", (i["cant"], i["pid"]))
    if cliente_id:
        db.execute("UPDATE clientes SET total_compras=total_compras+?, ultima_compra=? WHERE id=?", (total, fecha, cliente_id))
    db.commit()
    return jsonify({"ok": True, "id": venta_id})

# ── INVENTARIO ────────────────────────────────────────────────────────────────
@app.route("/inventario")
@login_required
def inventario():
    db = get_db()
    productos   = db.execute("SELECT p.*, pr.empresa as proveedor_nombre FROM productos p LEFT JOIN proveedores pr ON p.proveedor_id=pr.id ORDER BY p.nombre").fetchall()
    proveedores = db.execute("SELECT id, empresa FROM proveedores WHERE estado='Activo' ORDER BY empresa").fetchall()
    return render_template("inventario.html", productos=productos, proveedores=proveedores)

@app.route("/inventario/guardar", methods=["POST"])
@login_required
def guardar_producto():
    if not can_edit(): return jsonify({"error": "Sin permisos"}), 403
    db = get_db(); d = request.get_json()
    pid = d.get("id")
    fields = (d["nombre"], d.get("categoria",""), d.get("proveedor_id") or None,
              float(d.get("precio",0)), float(d.get("costo",0)),
              int(d.get("stock",0)), int(d.get("stock_min",5)), d.get("unidad","und"))
    if pid: db.execute("UPDATE productos SET nombre=?,categoria=?,proveedor_id=?,precio=?,costo=?,stock=?,stock_min=?,unidad=? WHERE id=?", fields+(pid,))
    else:   db.execute("INSERT INTO productos (nombre,categoria,proveedor_id,precio,costo,stock,stock_min,unidad) VALUES (?,?,?,?,?,?,?,?)", fields)
    db.commit(); return jsonify({"ok": True})

@app.route("/inventario/eliminar/<int:pid>", methods=["DELETE"])
@login_required
def eliminar_producto(pid):
    if not can_edit(): return jsonify({"error": "Sin permisos"}), 403
    db = get_db(); db.execute("DELETE FROM productos WHERE id=?", (pid,)); db.commit()
    return jsonify({"ok": True})

# ── CLIENTES ──────────────────────────────────────────────────────────────────
@app.route("/clientes")
@login_required
def clientes():
    db = get_db()
    return render_template("clientes.html", clientes=db.execute("SELECT * FROM clientes ORDER BY nombre").fetchall())

@app.route("/clientes/guardar", methods=["POST"])
@login_required
def guardar_cliente():
    if not can_edit(): return jsonify({"error": "Sin permisos"}), 403
    db = get_db(); d = request.get_json(); cid = d.get("id")
    fields = (d["nombre"], d.get("telefono",""), d.get("email",""), d.get("direccion",""), d.get("tipo","Regular"))
    if cid: db.execute("UPDATE clientes SET nombre=?,telefono=?,email=?,direccion=?,tipo=? WHERE id=?", fields+(cid,))
    else:   db.execute("INSERT INTO clientes (nombre,telefono,email,direccion,tipo) VALUES (?,?,?,?,?)", fields)
    db.commit(); return jsonify({"ok": True})

@app.route("/clientes/eliminar/<int:cid>", methods=["DELETE"])
@login_required
def eliminar_cliente(cid):
    if not can_edit(): return jsonify({"error": "Sin permisos"}), 403
    db = get_db(); db.execute("DELETE FROM clientes WHERE id=?", (cid,)); db.commit()
    return jsonify({"ok": True})

# ── PROVEEDORES ───────────────────────────────────────────────────────────────
@app.route("/proveedores")
@login_required
def proveedores():
    db = get_db()
    return render_template("proveedores.html", proveedores=db.execute("SELECT * FROM proveedores ORDER BY empresa").fetchall())

@app.route("/proveedores/guardar", methods=["POST"])
@login_required
def guardar_proveedor():
    if not can_edit(): return jsonify({"error": "Sin permisos"}), 403
    db = get_db(); d = request.get_json(); pid = d.get("id")
    fields = (d["empresa"], d.get("contacto",""), d.get("telefono",""), d.get("email",""), d.get("categoria",""), d.get("estado","Activo"))
    if pid: db.execute("UPDATE proveedores SET empresa=?,contacto=?,telefono=?,email=?,categoria=?,estado=? WHERE id=?", fields+(pid,))
    else:   db.execute("INSERT INTO proveedores (empresa,contacto,telefono,email,categoria,estado) VALUES (?,?,?,?,?,?)", fields)
    db.commit(); return jsonify({"ok": True})

@app.route("/proveedores/eliminar/<int:pid>", methods=["DELETE"])
@login_required
def eliminar_proveedor(pid):
    if not can_edit(): return jsonify({"error": "Sin permisos"}), 403
    db = get_db(); db.execute("DELETE FROM proveedores WHERE id=?", (pid,)); db.commit()
    return jsonify({"ok": True})

# ── GASTOS ────────────────────────────────────────────────────────────────────
@app.route("/gastos")
@login_required
def gastos():
    db = get_db()
    return render_template("gastos.html", gastos=db.execute("SELECT * FROM gastos ORDER BY fecha DESC, id DESC").fetchall())

@app.route("/gastos/guardar", methods=["POST"])
@login_required
def guardar_gasto():
    if not can_edit(): return jsonify({"error": "Sin permisos"}), 403
    db = get_db(); d = request.get_json(); gid = d.get("id")
    fields = (d["descripcion"], d.get("categoria","Otros"), float(d.get("monto",0)), d.get("fecha", date.today().isoformat()), d.get("notas",""))
    if gid: db.execute("UPDATE gastos SET descripcion=?,categoria=?,monto=?,fecha=?,notas=? WHERE id=?", fields+(gid,))
    else:   db.execute("INSERT INTO gastos (descripcion,categoria,monto,fecha,notas) VALUES (?,?,?,?,?)", fields)
    db.commit(); return jsonify({"ok": True})

@app.route("/gastos/eliminar/<int:gid>", methods=["DELETE"])
@login_required
def eliminar_gasto(gid):
    if not can_edit(): return jsonify({"error": "Sin permisos"}), 403
    db = get_db(); db.execute("DELETE FROM gastos WHERE id=?", (gid,)); db.commit()
    return jsonify({"ok": True})

# ── REPORTES ──────────────────────────────────────────────────────────────────
@app.route("/reportes")
@login_required
def reportes():
    db = get_db(); mes = date.today().isoformat()[:7]
    ventas_cat    = db.execute("SELECT p.categoria, SUM(vi.cantidad*vi.precio_unit) as total FROM venta_items vi JOIN productos p ON vi.producto_id=p.id JOIN ventas v ON vi.venta_id=v.id WHERE v.fecha LIKE ? GROUP BY p.categoria ORDER BY total DESC", (mes+"%",)).fetchall()
    gastos_cat    = db.execute("SELECT categoria, SUM(monto) as total FROM gastos WHERE fecha LIKE ? GROUP BY categoria ORDER BY total DESC", (mes+"%",)).fetchall()
    top_productos = db.execute("SELECT vi.nombre, SUM(vi.cantidad) as cant, SUM(vi.cantidad*vi.precio_unit) as revenue FROM venta_items vi JOIN ventas v ON vi.venta_id=v.id WHERE v.fecha LIKE ? GROUP BY vi.nombre ORDER BY cant DESC LIMIT 8", (mes+"%",)).fetchall()
    ventas_diarias= db.execute("SELECT fecha, SUM(total) as total FROM ventas WHERE fecha LIKE ? GROUP BY fecha ORDER BY fecha", (mes+"%",)).fetchall()
    return render_template("reportes.html", ventas_cat=ventas_cat, gastos_cat=gastos_cat, top_productos=top_productos, ventas_diarias=ventas_diarias, mes=mes)

# ── USUARIOS (solo admin) ─────────────────────────────────────────────────────
@app.route("/usuarios")
@admin_required
def usuarios():
    db = get_db()
    users = db.execute("SELECT id, username, nombre, rol, activo, creado_en FROM usuarios ORDER BY id").fetchall()
    return render_template("usuarios.html", users=users)

@app.route("/usuarios/guardar", methods=["POST"])
@admin_required
def guardar_usuario():
    db = get_db(); d = request.get_json()
    uid      = d.get("id")
    username = d.get("username","").strip().lower()
    nombre   = d.get("nombre","").strip()
    rol      = d.get("rol","viewer")
    activo   = int(d.get("activo", 1))
    password = d.get("password","").strip()
    if not username or not nombre:
        return jsonify({"error": "Usuario y nombre son requeridos"}), 400
    if uid:
        # editar existente
        if password:
            db.execute("UPDATE usuarios SET username=?,nombre=?,rol=?,activo=?,password=? WHERE id=?",
                       (username, nombre, rol, activo, generate_password_hash(password), uid))
        else:
            db.execute("UPDATE usuarios SET username=?,nombre=?,rol=?,activo=? WHERE id=?",
                       (username, nombre, rol, activo, uid))
    else:
        if not password: return jsonify({"error": "La contraseña es requerida para usuarios nuevos"}), 400
        try:
            db.execute("INSERT INTO usuarios (username,nombre,password,rol,activo) VALUES (?,?,?,?,?)",
                       (username, nombre, generate_password_hash(password), rol, activo))
        except Exception as e:
            return jsonify({"error": "El usuario ya existe"}), 400
    db.commit()
    return jsonify({"ok": True})

@app.route("/usuarios/eliminar/<int:uid>", methods=["DELETE"])
@admin_required
def eliminar_usuario(uid):
    if uid == session.get("user_id"):
        return jsonify({"error": "No puedes eliminarte a ti mismo"}), 400
    db = get_db(); db.execute("DELETE FROM usuarios WHERE id=?", (uid,)); db.commit()
    return jsonify({"ok": True})

# ── API helpers ───────────────────────────────────────────────────────────────
@app.route("/api/productos")
@login_required
def api_productos():
    db = get_db()
    return jsonify([dict(r) for r in db.execute("SELECT id, nombre, precio, stock, unidad FROM productos WHERE stock>0 ORDER BY nombre").fetchall()])

@app.route("/api/clientes")
@login_required
def api_clientes():
    db = get_db()
    return jsonify([dict(r) for r in db.execute("SELECT id, nombre FROM clientes ORDER BY nombre").fetchall()])

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
