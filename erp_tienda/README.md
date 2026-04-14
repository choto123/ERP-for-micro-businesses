# ERP Tienda Familiar

Sistema ERP completo para tiendas pequeñas. Construido con Flask + SQLite.

## Módulos incluidos
- Dashboard con métricas en tiempo real
- Ventas y facturación
- Inventario con alertas de stock bajo
- Clientes (CRM básico)
- Proveedores
- Gastos y caja
- Reportes mensuales

---

## 1. Correr en localhost (desarrollo)

### Requisitos
- Python 3.9 o superior
- pip

### Pasos

```bash
# 1. Entra a la carpeta
cd erp_tienda

# 2. Crea un entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate        # Linux / Mac
venv\Scripts\activate           # Windows

# 3. Instala dependencias
pip install -r requirements.txt

# 4. Corre la app
python app.py
```

Abre tu navegador en: **http://localhost:5000**

La base de datos `erp.db` se crea automáticamente en la misma carpeta.

---

## 2. Despliegue en servidor propio (producción)

### Opción A — VPS con Ubuntu (recomendado)

**Requisitos en el servidor:**
- Ubuntu 20.04 / 22.04
- Python 3.9+
- Nginx
- Gunicorn (servidor WSGI de producción)

```bash
# --- En el servidor ---

# 1. Actualizar e instalar dependencias del sistema
sudo apt update && sudo apt install -y python3-pip python3-venv nginx

# 2. Subir el proyecto (desde tu PC)
scp -r erp_tienda/ usuario@IP_DEL_SERVIDOR:/home/usuario/

# 3. En el servidor: entrar a la carpeta y crear entorno virtual
cd /home/usuario/erp_tienda
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn

# 4. Probar que funciona
gunicorn --bind 0.0.0.0:5000 app:app
# (Ctrl+C para detener)
```

### Configurar Gunicorn como servicio (systemd)

Crea el archivo `/etc/systemd/system/erp.service`:

```ini
[Unit]
Description=ERP Tienda Familiar
After=network.target

[Service]
User=usuario
WorkingDirectory=/home/usuario/erp_tienda
Environment="PATH=/home/usuario/erp_tienda/venv/bin"
ExecStart=/home/usuario/erp_tienda/venv/bin/gunicorn --workers 2 --bind 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable erp
sudo systemctl start erp
sudo systemctl status erp    # debe decir "active (running)"
```

### Configurar Nginx como proxy reverso

Crea `/etc/nginx/sites-available/erp`:

```nginx
server {
    listen 80;
    server_name TU_DOMINIO_O_IP;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static {
        alias /home/usuario/erp_tienda/static;
        expires 7d;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/erp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

Ahora accedes en: **http://TU_DOMINIO_O_IP**

### Agregar HTTPS con Let's Encrypt (gratis)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d tu-dominio.com
```

---

### Opción B — Render.com (gratis, sin servidor propio)

1. Sube el proyecto a GitHub
2. En [render.com](https://render.com) → New Web Service → conecta tu repo
3. Configuración:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app`
4. ¡Listo! Render te da una URL pública automáticamente.

> Nota: En Render el disco es efímero. Para producción real considera usar PostgreSQL en lugar de SQLite.

---

## Estructura del proyecto

```
erp_tienda/
├── app.py              ← Rutas y lógica principal
├── database.py         ← Configuración SQLite y esquema
├── requirements.txt
├── erp.db              ← Base de datos (se crea automáticamente)
├── static/
│   ├── css/style.css
│   └── js/main.js
└── templates/
    ├── base.html
    ├── dashboard.html
    ├── ventas.html
    ├── inventario.html
    ├── clientes.html
    ├── proveedores.html
    ├── gastos.html
    └── reportes.html
```

## Personalización rápida

| Qué cambiar | Dónde |
|---|---|
| Nombre del negocio | `templates/base.html` → `.sidebar-brand` |
| Moneda ($ → COP, €, etc.) | `templates/*.html` → formato de precio |
| Categorías de gastos | `templates/gastos.html` → `<select id="g-cat">` |
| Colores | `static/css/style.css` → variables `:root` |
| Puerto | `app.py` → última línea `port=5000` |
