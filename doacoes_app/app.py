from flask import Flask, render_template, request, redirect, url_for, flash, g, session
import sqlite3
import os
from datetime import datetime

# ==========================================
# CONFIGURAÇÃO DA APLICAÇÃO
# ==========================================
app = Flask(__name__)
app.config["SECRET_KEY"] = "sua_chave_super_segura_aqui"
app.config["DATABASE"] = os.path.join(app.root_path, "doacoes.db")

# ==========================================
# BANCO DE DADOS
# ==========================================

def get_db():
    """Retorna conexão com banco usando contexto da aplicação"""
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    """Fecha conexão automaticamente ao finalizar requisição"""
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    """Cria estrutura do banco e usuário admin padrão"""
    db = get_db()
    # Tabela de doações
    db.execute("""
        CREATE TABLE IF NOT EXISTS doacoes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            item TEXT NOT NULL,
            quantidade INTEGER NOT NULL,
            localizacao TEXT NOT NULL,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Tabela de usuários
    db.execute("""
        CREATE TABLE IF NOT EXISTS usuarios(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            usuario TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            tipo TEXT DEFAULT 'operador'
        )
    """)
    # Usuário admin padrão
    db.execute("""
        INSERT OR IGNORE INTO usuarios (nome, usuario, senha, tipo)
        VALUES ('Administrador','admin','123','admin')
    """)
    db.commit()

with app.app_context():
    init_db()

# ==========================================
# FUNÇÃO AUXILIAR PARA PROTEÇÃO DE ROTAS
# ==========================================
def login_required(f):
    """Decorator para rotas que precisam de login"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario" not in session:
            flash("Você precisa estar logado para acessar essa página.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# ROTAS DE AUTENTICAÇÃO
# ==========================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        senha = request.form["senha"]

        db = get_db()
        user = db.execute(
            "SELECT * FROM usuarios WHERE usuario=? AND senha=?",
            (usuario, senha)
        ).fetchone()

        if user:
            session["usuario"] = user["usuario"]
            session["tipo"] = user["tipo"]
            flash(f"Bem-vindo(a), {user['nome']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Login inválido.", "danger")

    return render_template("login.html")

@app.route("/register", methods=["POST"])
def register():
    nome = request.form.get("nome_completo")
    usuario = request.form.get("usuario")
    email = request.form.get("email")
    cpf = request.form.get("cpf")
    senha = request.form.get("senha")
    confirm_senha = request.form.get("confirm_senha")

    if not all([nome, usuario, email, cpf, senha, confirm_senha]):
        flash("Preencha todos os campos", "danger")
        return redirect(url_for("login"))

    if senha != confirm_senha:
        flash("As senhas não coincidem", "danger")
        return redirect(url_for("login"))

    try:
        db = get_db()
        db.execute("""
            INSERT INTO usuarios (nome, usuario, senha, tipo)
            VALUES (?, ?, ?, 'operador')
        """, (nome, usuario, senha))
        db.commit()
        flash("Cadastro realizado com sucesso! Faça login.", "success")
    except sqlite3.IntegrityError:
        flash("Nome de usuário já existe.", "danger")
    except Exception as e:
        flash("Erro ao cadastrar usuário.", "danger")
        print("Erro:", e)

    return redirect(url_for("login"))

@app.route("/logout")
def logout():
    session.clear()
    flash("Você saiu do sistema.", "info")
    return redirect(url_for("login"))

# ==========================================
# ROTAS PRINCIPAIS
# ==========================================
@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/cadastrar", methods=["GET", "POST"])
@login_required
def cadastrar():
    if request.method == "POST":
        nome = request.form.get("nome")
        item = request.form.get("item")
        quantidade = request.form.get("quantidade")
        localizacao = request.form.get("localizacao")

        if not nome or not item or not quantidade or not localizacao:
            flash("Preencha todos os campos.", "danger")
            return redirect(url_for("cadastrar"))

        try:
            db = get_db()
            db.execute(
                "INSERT INTO doacoes (nome, item, quantidade, localizacao) VALUES (?, ?, ?, ?)",
                (nome, item, int(quantidade), localizacao)
            )
            db.commit()
            flash("Doação cadastrada com sucesso!", "success")
            return redirect(url_for("lista"))
        except Exception as e:
            flash("Erro ao cadastrar doação.", "danger")
            print("Erro:", e)

    return render_template("cadastrar.html")

@app.route("/lista")
@login_required
def lista():
    db = get_db()
    dados = db.execute("SELECT * FROM doacoes ORDER BY data_criacao DESC").fetchall()
    return render_template("lista.html", dados=dados)

@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    total_doacoes = db.execute("SELECT COUNT(*) FROM doacoes").fetchone()[0]
    total_itens = db.execute("SELECT SUM(quantidade) FROM doacoes").fetchone()[0] or 0
    ultimas = db.execute("SELECT * FROM doacoes ORDER BY data_criacao DESC LIMIT 5").fetchall()

    return render_template(
        "dashboard.html",
        total_doacoes=total_doacoes,
        total_itens=total_itens,
        ultimas=ultimas
    )

# ==========================================
# TRATAMENTO DE ERROS
# ==========================================
@app.errorhandler(404)
def pagina_nao_encontrada(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def erro_servidor(e):
    return render_template("500.html"), 500

# ==========================================
# INICIALIZAÇÃO
# ==========================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
