import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

st.set_page_config(page_title="Mini-ERP Demo con SQLite", layout="wide")

# ==========================================
# 1. CONFIGURACIÓN DE LA BASE DE DATOS SQLITE
# ==========================================
def init_db():
    conn = sqlite3.connect('erp_database.db')
    cursor = conn.cursor()
    
    # Tabla de Usuarios y Roles
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    ''')
    
    # Tabla de Afiliados
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS afiliados (
            id TEXT PRIMARY KEY,
            nombre TEXT,
            tipo TEXT,
            fecha TEXT
        )
    ''')
    
    # Tabla de Gastos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gastos (
            id TEXT PRIMARY KEY,
            concepto TEXT,
            categoria TEXT,
            monto REAL,
            fecha TEXT
        )
    ''')
    
    # Insertar usuarios por defecto si no existen
    cursor.execute('SELECT COUNT(*) FROM usuarios')
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO usuarios (username, password, role) VALUES ('admin', '1234', 'admin')")
        cursor.execute("INSERT INTO usuarios (username, password, role) VALUES ('captura', '1234', 'capturista')")
        conn.commit()
        
    conn.close()

# Inicializar base de datos al arrancar
init_db()

# ==========================================
# 2. GESTIÓN DE SESIÓN Y LOGIN
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""

if not st.session_state.logged_in:
    st.title("🔐 Iniciar Sesión - Mini-ERP (Base de Datos SQLite)")
    with st.form("login_form"):
        user_input = st.text_input("Usuario (admin / captura)")
        pass_input = st.text_input("Contraseña", type="password")
        submit_login = st.form_submit_button("Entrar")
        
        if submit_login:
            conn = sqlite3.connect('erp_database.db')
            cursor = conn.cursor()
            cursor.execute("SELECT role FROM usuarios WHERE username = ? AND password = ?", (user_input, pass_input))
            user_record = cursor.fetchone()
            conn.close()
            
            if user_record:
                st.session_state.logged_in = True
                st.session_state.username = user_input
                st.session_state.role = user_record[0] # 'admin' o 'capturista'
                st.rerun()
            else:
                st.error("Credenciales incorrectas. (Prueba admin/1234 o captura/1234)")
    st.stop()

# ==========================================
# 3. INTERFAZ PRINCIPAL Y NAVEGACIÓN POR ROL
# ==========================================
st.sidebar.write(f"👤 Conectado como: **{st.session_state.username}** ({st.session_state.role})")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.logged_in = False
    st.rerun()

st.sidebar.markdown("---")

# Definir menú según rol
if st.session_state.role == "admin":
    menu_opciones = ["Dashboard", "Registro de Afiliaciones", "Registro de Gastos"]
else:
    menu_opciones = ["Registro de Afiliaciones", "Registro de Gastos"]

menu = st.sidebar.selectbox("Navegación", menu_opciones)

# Conexión genérica para consultas
def query_db(query, params=(), fetch=True):
    conn = sqlite3.connect('erp_database.db')
    cursor = conn.cursor()
    cursor.execute(query, params)
    if fetch:
        data = cursor.fetchall()
        conn.close()
        return data
    conn.commit()
    conn.close()

# 1. DASHBOARD (Solo Admin)
if menu == "Dashboard":
    st.header("📊 Panel de Control General (Base de Datos Persistente)")
    
    # Cargar datos desde SQLite
    afiliados_data = query_db("SELECT * FROM afiliados")
    gastos_data = query_db("SELECT * FROM gastos")
    
    total_afiliados = len(afiliados_data)
    total_gastos = sum([g[3] for g in gastos_data]) if gastos_data else 0.0
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Total Afiliados")
        st.metric(label="Activos", value=total_afiliados)
        
    with col2:
        st.subheader("Gasto Total")
        st.metric(label="USD", value=f"${total_gastos:,.2f}")
        
    st.markdown("---")
    st.subheader("Historial de Gastos Registrados")
    if gastos_data:
        df_gastos = pd.DataFrame(gastos_data, columns=["ID", "Concepto", "Categoría", "Monto", "Fecha"])
        st.dataframe(df_gastos, use_container_width=True)
    else:
        st.info("No hay gastos registrados en la base de datos.")

# 2. MÓDULO DE AFILIACIONES
elif menu == "Registro de Afiliaciones":
    st.header("👥 Gestión de Afiliaciones")
    
    with st.form("form_afiliado"):
        nombre = st.text_input("Nombre del Afiliado o Empresa")
        tipo = st.selectbox("Tipo de Afiliación", ["Regular", "Corporativo", "VIP"])
        fecha = st.date_input("Fecha de Ingreso", datetime.now())
        
        submitted = st.form_submit_button("Guardar Afiliado")
        if submitted and nombre:
            # Generar ID único basado en conteo
            conteo = len(query_db("SELECT * FROM afiliados"))
            nuevo_id = f"AF-{conteo + 1:03d}"
            
            query_db("INSERT INTO afiliados (id, nombre, tipo, fecha) VALUES (?, ?, ?, ?)", 
                     (nuevo_id, nombre, tipo, str(fecha)), fetch=False)
            st.success(f"¡Afiliado {nombre} guardado en la base de datos con éxito!")

    st.subheader("Listado de Afiliados en la Base de Datos")
    afiliados_data = query_db("SELECT * FROM afiliados")
    if afiliados_data:
        df_afiliados = pd.DataFrame(afiliados_data, columns=["ID", "Nombre", "Tipo", "Fecha"])
        st.dataframe(df_afiliados, use_container_width=True)
    else:
        st.info("Aún no hay afiliados registrados.")

# 3. MÓDULO DE GASTOS
elif menu == "Registro de Gastos":
    st.header("💰 Control de Gastos")
    
    with st.form("form_gasto"):
        concepto = st.text_input("Concepto del Gasto")
        categoria = st.selectbox("Categoría", ["Operativo", "Viáticos", "Infraestructura", "Suministros"])
        monto = st.number_input("Monto ($)", min_value=0.0, format="%.2f")
        fecha_gasto = st.date_input("Fecha de Gasto", datetime.now())
        
        submitted_gasto = st.form_submit_button("Registrar Gasto")
        if submitted_gasto and concepto:
            conteo = len(query_db("SELECT * FROM gastos"))
            gasto_id = f"GT-{conteo + 1:03d}"
            
            query_db("INSERT INTO gastos (id, concepto, categoria, monto, fecha) VALUES (?, ?, ?, ?, ?)",
                     (gasto_id, concepto, categoria, monto, str(fecha_gasto)), fetch=False)
            st.success("¡Gasto registrado y guardado permanentemente!")

    st.subheader("Historial de Gastos en la Base de Datos")
    gastos_data = query_db("SELECT * FROM gastos")
    if gastos_data:
        df_gastos = pd.DataFrame(gastos_data, columns=["ID", "Concepto", "Categoría", "Monto", "Fecha"])
        st.dataframe(df_gastos, use_container_width=True)
    else:
        st.info("Aún no hay gastos registrados.")
