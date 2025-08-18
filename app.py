from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime
import hashlib
import os
from pathlib import Path

# Configuração inicial
app = Flask(__name__, template_folder='templates')
app.secret_key = 'sua_chave_secreta_aqui'  # Troque por uma chave segura em produção

# Verificação da estrutura de diretórios
print(f"Diretório atual: {os.getcwd()}")
print(f"Caminho templates: {Path('templates').absolute()}")
print(f"Arquivos em templates: {os.listdir('templates') if os.path.exists('templates') else 'Pasta não existe'}")

# Configuração do banco de dados
def get_db_connection():
    conn = sqlite3.connect('obreiros.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabela de obreiros
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS obreiros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        telefone TEXT,
        grupo TEXT NOT NULL,
        data_cadastro TEXT NOT NULL
    )
    ''')
    
    # Tabela de check-ins
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS checkins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        obreiro_id INTEGER NOT NULL,
        data_checkin TEXT NOT NULL,
        FOREIGN KEY (obreiro_id) REFERENCES obreiros (id)
    )
    ''')
    
    # Tabela de líderes
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS lideres (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE NOT NULL,
        senha_hash TEXT NOT NULL,
        grupo TEXT NOT NULL
    )
    ''')
    
    # Inserir líder padrão se não existir
    cursor.execute("SELECT COUNT(*) FROM lideres")
    if cursor.fetchone()[0] == 0:
        senha_hash = hashlib.sha256('admin123'.encode()).hexdigest()
        cursor.execute(
            "INSERT INTO lideres (usuario, senha_hash, grupo) VALUES (?, ?, ?)",
            ('admin', senha_hash, 'todos')
        )
    
    conn.commit()
    conn.close()

init_db()

# Rotas públicas
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip()
        telefone = request.form.get('telefone', '').strip()
        grupo = request.form.get('grupo', '').strip()
        
        if not all([nome, email, grupo]):
            flash('Preencha todos os campos obrigatórios!', 'danger')
            return redirect(url_for('cadastrar'))
        
        data_cadastro = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO obreiros (nome, email, telefone, grupo, data_cadastro) VALUES (?, ?, ?, ?, ?)",
                (nome, email, telefone, grupo, data_cadastro)
            )
            conn.commit()
            obreiro_id = cursor.lastrowid
            conn.close()
            
            flash(f'Cadastro realizado com sucesso! Seu ID para check-in é: {obreiro_id}', 'success')
            return redirect(url_for('checkin', obreiro_id=obreiro_id))
        except sqlite3.IntegrityError:
            flash('E-mail já cadastrado!', 'danger')
            return redirect(url_for('cadastrar'))
        except Exception as e:
            flash(f'Erro no cadastro: {str(e)}', 'danger')
            return redirect(url_for('cadastrar'))
    
    return render_template('cadastro.html')

@app.route('/checkin/<int:obreiro_id>')
def checkin(obreiro_id):
    conn = get_db_connection()
    obreiro = conn.execute('SELECT * FROM obreiros WHERE id = ?', (obreiro_id,)).fetchone()
    conn.close()
    
    if obreiro is None:
        flash('ID de obreiro não encontrado!', 'danger')
        return redirect(url_for('index'))
    
    return render_template('checkin.html', obreiro=obreiro)

@app.route('/registrar_checkin', methods=['POST'])
def registrar_checkin():
    obreiro_id = request.form.get('obreiro_id', '').strip()
    
    if not obreiro_id:
        flash('ID de obreiro inválido!', 'danger')
        return redirect(url_for('index'))
    
    try:
        obreiro_id = int(obreiro_id)
    except ValueError:
        flash('ID de obreiro inválido!', 'danger')
        return redirect(url_for('index'))
    
    data_checkin = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db_connection()
    
    obreiro = conn.execute('SELECT * FROM obreiros WHERE id = ?', (obreiro_id,)).fetchone()
    if obreiro is None:
        conn.close()
        flash('ID de obreiro inválido!', 'danger')
        return redirect(url_for('index'))
    
    try:
        conn.execute(
            "INSERT INTO checkins (obreiro_id, data_checkin) VALUES (?, ?)",
            (obreiro_id, data_checkin)
        )
        conn.commit()
        flash(f'Check-in registrado com sucesso para {obreiro["nome"]}!', 'success')
    except Exception as e:
        flash(f'Erro ao registrar check-in: {str(e)}', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('checkin', obreiro_id=obreiro_id))

@app.route('/checkin_rapido', methods=['GET', 'POST'])
def checkin_rapido():
    if request.method == 'POST':
        identificador = request.form.get('identificador', '').strip()
        
        if not identificador:
            flash('Por favor, informe um ID ou e-mail', 'danger')
            return redirect(url_for('checkin_rapido'))
        
        data_checkin = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = get_db_connection()
        
        try:
            # Tenta como ID numérico
            obreiro_id = int(identificador)
            obreiro = conn.execute('SELECT * FROM obreiros WHERE id = ?', (obreiro_id,)).fetchone()
        except ValueError:
            # Se não for número, trata como email
            obreiro = conn.execute('SELECT * FROM obreiros WHERE email = ?', (identificador,)).fetchone()
        
        if obreiro is None:
            conn.close()
            flash('Obreiro não encontrado! Verifique o ID ou e-mail.', 'danger')
            return redirect(url_for('checkin_rapido'))
        
        try:
            conn.execute(
                "INSERT INTO checkins (obreiro_id, data_checkin) VALUES (?, ?)",
                (obreiro['id'], data_checkin)
            )
            conn.commit()
            flash(f'Check-in registrado com sucesso para {obreiro["nome"]}!', 'success')
        except Exception as e:
            flash(f'Erro ao registrar check-in: {str(e)}', 'danger')
        finally:
            conn.close()
        
        return redirect(url_for('checkin_rapido'))
    
    return render_template('checkin_rapido.html')

# Rotas para líderes
@app.route('/login_lider', methods=['GET', 'POST'])
def login_lider():
    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        senha = request.form.get('senha', '').strip()
        
        if not usuario or not senha:
            flash('Preencha todos os campos!', 'danger')
            return redirect(url_for('login_lider'))
        
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        conn = get_db_connection()
        
        lider = conn.execute(
            'SELECT * FROM lideres WHERE usuario = ? AND senha_hash = ?',
            (usuario, senha_hash)
        ).fetchone()
        conn.close()
        
        if lider:
            session['lider_id'] = lider['id']
            session['grupo_lider'] = lider['grupo']
            return redirect(url_for('painel_lider'))
        else:
            flash('Usuário ou senha incorretos!', 'danger')
    
    return render_template('login_lider.html')

@app.route('/painel_lider')
def painel_lider():
    if 'lider_id' not in session:
        return redirect(url_for('login_lider'))
    
    grupo_lider = session.get('grupo_lider', 'todos')
    conn = get_db_connection()
    
    # Obter obreiros conforme o grupo do líder
    if grupo_lider == 'todos':
        obreiros = conn.execute('''
            SELECT o.*, COUNT(c.id) as total_presencas 
            FROM obreiros o 
            LEFT JOIN checkins c ON o.id = c.obreiro_id 
            GROUP BY o.id
        ''').fetchall()
    else:
        obreiros = conn.execute('''
            SELECT o.*, COUNT(c.id) as total_presencas 
            FROM obreiros o 
            LEFT JOIN checkins c ON o.id = c.obreiro_id 
            WHERE o.grupo = ?
            GROUP BY o.id
        ''', (grupo_lider,)).fetchall()
    
    # Obter check-ins recentes
    checkins_recentes = conn.execute('''
        SELECT c.*, o.nome 
        FROM checkins c 
        JOIN obreiros o ON c.obreiro_id = o.id 
        ORDER BY c.data_checkin DESC 
        LIMIT 10
    ''').fetchall()
    
    conn.close()
    
    return render_template(
        'painel_lider.html',
        obreiros=obreiros,
        checkins_recentes=checkins_recentes,
        grupo_lider=grupo_lider
    )

@app.route('/logout_lider')
def logout_lider():
    session.pop('lider_id', None)
    session.pop('grupo_lider', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)