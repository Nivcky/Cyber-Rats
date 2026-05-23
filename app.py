from flask import Flask, render_template, redirect, url_for, request, session
import pymysql  # Certifique-se de que 'pymysql' está no seu requirements.txt
import numpy as np
from datetime import datetime
import random
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cyber-rats-chave-secreta")

# ================= CONFIGURAÇÃO DO BANCO (MYSQL DO AIVEN) =================
def get_db():
    return pymysql.connect(
        host=os.environ.get("DB_HOST"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        database=os.environ.get("DB_NAME"),
        port=int(os.environ.get("DB_PORT", 3306)),
        ssl={'ssl': {}}, # EXIGIDO PELO AIVEN: Força a conexão segura SSL
        cursorclass=pymysql.cursors.DictCursor
    )

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        usuario VARCHAR(100),
        data VARCHAR(50),
        localizacao VARCHAR(50),
        status VARCHAR(20),
        horario INT,
        local_flag INT,
        tentativas INT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INT AUTO_INCREMENT PRIMARY KEY,
        email VARCHAR(255) UNIQUE,
        senha VARCHAR(255)
    )
    """)

    cursor.execute("SELECT * FROM usuarios WHERE email = %s", ("teste@cyber.com",))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO usuarios (email, senha) VALUES (%s, %s)",
            ("teste@cyber.com", "123456")
        )

    conn.commit()
    cursor.close()
    conn.close()

# Inicializa o banco ao rodar o app
init_db()

# ================= INSERÇÃO =================
def inserir_log(usuario, data, localizacao, status, horario, local_flag, tentativas):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO logs (usuario, data, localizacao, status, horario, local_flag, tentativas)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (usuario, data, localizacao, status, horario, local_flag, tentativas))

    conn.commit()
    cursor.close()
    conn.close()

# ================= IA =================
def calcular_perfil_normal():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT horario, local_flag, tentativas FROM logs WHERE status = 'OK'")
    dados_dict = cursor.fetchall()
    cursor.close()
    conn.close()

    if len(dados_dict) == 0:
        return np.array([0, 0, 1])

    dados = [[d['horario'], d['local_flag'], d['tentativas']] for d in dados_dict]
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
    logs_dict = cursor.fetchall()
    cursor.close()
    conn.close()

    logs = [(l['usuario'], l['data'], l['localizacao'], l['status']) for l in logs_dict]

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
            "SELECT * FROM usuarios WHERE email = %s AND senha = %s",
            (email, senha)
        )
        user = cursor.fetchone()
        cursor.close()
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
                "INSERT INTO usuarios (email, senha) VALUES (%s, %s)",
                (email, senha)
            )

            conn.commit()
            cursor.close()
            conn.close()

            return redirect(url_for("login"))

        except Exception as e:
            return "Usuário já existe ou erro no banco 👀"

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
