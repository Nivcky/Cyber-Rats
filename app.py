from flask import Flask, render_template, redirect, url_for, request, session
import sqlite3
import numpy as np
from datetime import datetime
import random

app = Flask(__name__)
app.secret_key = "cyber-rats-chave-secreta"

# ================= BANCO =================
def get_db():
    return sqlite3.connect("seguranca.db")

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # TABELA LOGS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        data TEXT,
        localizacao TEXT,
        status TEXT,
        horario INTEGER,
        local_flag INTEGER,
        tentativas INTEGER
    )
    """)

    # TABELA USUÁRIOS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        senha TEXT
    )
    """)

    # USUÁRIO TESTE (se não existir)
    cursor.execute("SELECT * FROM usuarios WHERE email = ?", ("teste@cyber.com",))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO usuarios (email, senha) VALUES (?, ?)",
            ("teste@cyber.com", "123456")
        )

    conn.commit()
    conn.close()

init_db()

# ================= INSERÇÃO =================
def inserir_log(usuario, data, localizacao, status, horario, local_flag, tentativas):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO logs (usuario, data, localizacao, status, horario, local_flag, tentativas)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (usuario, data, localizacao, status, horario, local_flag, tentativas))

    conn.commit()
    conn.close()

# ================= IA =================
def calcular_perfil_normal():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT horario, local_flag, tentativas FROM logs WHERE status = 'OK'")
    dados = cursor.fetchall()
    conn.close()

    if len(dados) == 0:
        return np.array([0, 0, 1])

    return np.mean(np.array(dados), axis=0)

pesos = np.array([0.4, 0.4, 0.2])

def classificar(entrada):
    perfil = calcular_perfil_normal()
    entrada = np.array(entrada)

    risco = np.dot(entrada, pesos)
    anomalia = np.linalg.norm(entrada - perfil)

    score = (risco + anomalia) / 2

    if score < 0.7:
        return "OK"
    elif score < 1.4:
        return "Suspeito"
    else:
        return "Crítico"

# ================= SIMULAÇÃO =================
def gerar_simulacao():
    usuario = random.choice(["Ana", "Carlos", "Maria", "João"])
    local = random.choice(["SP", "RJ", "MG"])
    horario = random.choice([0, 1])
    local_flag = 0 if local == "SP" else 1
    tentativas = random.randint(1, 3)

    entrada = [horario, local_flag, tentativas]
    status = classificar(entrada)

    data = datetime.now().strftime("%d/%m %H:%M")
    inserir_log(usuario, data, local, status, horario, local_flag, tentativas)

# ================= ROTAS =================

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    if not session.get("logado"):
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT usuario, data, localizacao, status FROM logs ORDER BY id DESC")
    logs = cursor.fetchall()
    conn.close()

    total = len(logs)
    suspeitos = sum(1 for l in logs if l[3] == "Suspeito")
    criticos = sum(1 for l in logs if l[3] == "Crítico")

    return render_template(
        "dashboard.html",
        logs=logs,
        total=total,
        suspeitos=suspeitos,
        criticos=criticos
    )

@app.route("/simular")
def simular():
    if not session.get("logado"):
        return redirect(url_for("login"))

    gerar_simulacao()
    return redirect(url_for("dashboard"))

# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        senha = request.form.get("senha")

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM usuarios WHERE email = ? AND senha = ?",
            (email, senha)
        )
        user = cursor.fetchone()
        conn.close()

        if user:
            session["logado"] = True
            session["usuario"] = email
            return redirect(url_for("home"))

    return render_template("login.html")

# ================= REGISTER =================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        senha = request.form.get("senha")

        try:
            conn = get_db()
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO usuarios (email, senha) VALUES (?, ?)",
                (email, senha)
            )

            conn.commit()
            conn.close()

            return redirect(url_for("login"))

        except:
            return "Usuário já existe 👀"

    return render_template("register.html")

# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# ================= CONTATO =================
@app.route("/contato")
def contato():
    return render_template("contact.html")

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True, port=5001)