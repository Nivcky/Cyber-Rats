from flask import Flask, render_template, redirect, url_for, request, session
import sqlite3
import numpy as np
from datetime import datetime
import random
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cyber-rats-chave-secreta")


# ================= CONFIGURAÇÃO DO BANCO SQLITE LOCAL =================
def get_db():
    conn = sqlite3.connect("seguranca.db")
    conn.row_factory = sqlite3.Row
    return conn


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

    cursor.execute(
        "SELECT * FROM usuarios WHERE email = %s",
        ("teste@cyber.com",)
    )

    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO usuarios (email, senha) VALUES (%s, %s)",
            ("teste@cyber.com", "123456")
        )

    conn.commit()
    cursor.close()
    conn.close()


try:
    init_db()
except Exception as e:
    print("Erro ao inicializar banco:", e)


# ================= INSERÇÃO =================
def inserir_log(usuario, data, localizacao, status, horario, local_flag, tentativas):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO logs (usuario, data, localizacao, status, horario, local_flag, tentativas)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (usuario, data, localizacao, status, horario, local_flag, tentativas))

    conn.commit()
    cursor.close()
    conn.close()


# ================= IA / ANÁLISE DE RISCO =================
def calcular_perfil_normal():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT horario, local_flag, tentativas 
        FROM logs 
        WHERE status = 'OK'
    """)

    dados_dict = cursor.fetchall()

    cursor.close()
    conn.close()

    if len(dados_dict) == 0:
        return np.array([0, 0, 1])

    dados = [
        [d["horario"], d["local_flag"], d["tentativas"]]
        for d in dados_dict
    ]

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

    inserir_log(
        usuario,
        data,
        local,
        status,
        horario,
        local_flag,
        tentativas
    )


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

    cursor.execute("""
        SELECT usuario, data, localizacao, status 
        FROM logs 
        ORDER BY id DESC
    """)

    logs_dict = cursor.fetchall()

    cursor.close()
    conn.close()

    logs = [
        (l["usuario"], l["data"], l["localizacao"], l["status"])
        for l in logs_dict
    ]

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
            return redirect(url_for("dashboard"))

    return render_template("login.html")


# ================= REGISTER =================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        senha = request.form.get("senha")

        if not email or not senha:
            return "E-mail e senha são obrigatórios."

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
            print("Erro no cadastro:", e)
            return "Usuário já existe ou erro no banco."

    return render_template("register.html")


# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ================= VULNERABILIDADES =================
@app.route("/vulnerabilidades")
def vulnerabilidades():
    return render_template("vulnerabilidades.html")


# ================= PHISHING =================
@app.route("/phishing")
def phishing():
    return render_template("phishing.html")


# ================= ERP E CRM =================
@app.route("/erp-crm")
def erp_crm():
    return render_template("erp_crm.html")


# ================= CONSULTORIA EM SEGURANÇA =================
@app.route("/consultoria")
def consultoria():
    return render_template("consultoria.html")


# ================= CONTATO =================
@app.route("/contato", methods=["GET", "POST"])
def contato():
    if request.method == "POST":
        nome = request.form.get("nome")
        email = request.form.get("email")
        empresa = request.form.get("empresa")
        mensagem = request.form.get("mensagem")

        print("Mensagem recebida:")
        print("Nome:", nome)
        print("Email:", email)
        print("Empresa:", empresa)
        print("Mensagem:", mensagem)

        return render_template("contact.html", enviado=True)

    return render_template("contact.html")


# ================= RUN LOCAL =================
if __name__ == "__main__":
    app.run(debug=True, port=5001)