import sqlite3
import re # Import para expressões regulares
from flask import Flask, render_template, request, redirect, url_for, session, g, abort, flash
from datetime import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'uma-chave-secreta-muito-segura'
DATABASE = 'database.db'

# --- Funções de Banco de Dados e outras ---
# ... (sem alterações)
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='rb') as f:
            db.cursor().executescript(f.read().decode('utf-8'))
        admin_user = db.execute('SELECT id FROM usuarios WHERE nome = ?', ('admin',)).fetchone()
        if not admin_user:
            db.execute('INSERT INTO usuarios (nome, senha, is_admin) VALUES (?, ?, ?)',
                       ('admin', generate_password_hash('admin123'), 1)
            )
            print("Usuário 'admin' criado com sucesso.")
        db.commit()
    print("Banco de dados inicializado.")

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# --- Rotas Principais ---
# ... (sem alterações)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nome = request.form['nome']
        senha = request.form['senha']
        db = get_db()
        usuario = db.execute('SELECT * FROM usuarios WHERE nome = ?', (nome,)).fetchone()
        if usuario and check_password_hash(usuario['senha'], senha):
            session.clear()
            session['user_id'] = usuario['id']
            session['is_admin'] = (usuario['is_admin'] == 1)
            if session['is_admin']:
                return redirect(url_for('admin_panel'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Usuário ou senha inválidos', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/')
def index():
    if session.get('is_admin'):
        return redirect(url_for('admin_panel'))
    user_id = session.get('user_id')
    if not user_id: return redirect(url_for('login'))
    db = get_db()
    usuario = db.execute('SELECT * FROM usuarios WHERE id = ?', (user_id,)).fetchone()
    transacoes = db.execute('SELECT * FROM transacoes WHERE id_usuario = ? ORDER BY data DESC', (user_id,)).fetchall()
    return render_template('index.html', usuario=usuario, transacoes=transacoes)

@app.route('/logout')
def logout():
    session.clear()
    flash('Você foi desconectado com sucesso.', 'success')
    return redirect(url_for('login'))

@app.route('/solicitar_folga', methods=['POST'])
def solicitar_folga():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    tipo = request.form['tipo']
    dias = int(request.form['dias'])
    motivo = request.form['motivo']
    data = datetime.now().strftime("%Y-%m-%d")
    db = get_db()
    db.execute(
        'INSERT INTO transacoes (id_usuario, tipo, dias, data, motivo) VALUES (?, ?, ?, ?, ?)',
        (user_id, tipo, dias, data, motivo)
    )
    db.commit()
    flash('Sua solicitação foi enviada para aprovação.', 'success')
    return redirect(url_for('index'))

# --- ROTAS DE ADMIN ---
@app.route('/admin')
@admin_required
def admin_panel():
    db = get_db()
    todos_usuarios = db.execute('SELECT id, nome, saldo_atual FROM usuarios ORDER BY nome').fetchall()
    solicitacoes_pendentes = db.execute(
        """
        SELECT t.id, t.tipo, t.dias, t.motivo, u.nome as nome_funcionario
        FROM transacoes t JOIN usuarios u ON t.id_usuario = u.id
        WHERE t.status = 'pendente'
        ORDER BY t.data
        """
    ).fetchall()
    return render_template('admin.html', todos_usuarios=todos_usuarios, solicitacoes_pendentes=solicitacoes_pendentes)

@app.route('/add_usuario', methods=['POST'])
@admin_required
def add_usuario():
    # ... (sem alterações)
    nome = request.form['nome']
    senha = request.form['senha']
    hash_senha = generate_password_hash(senha)
    db = get_db()
    db.execute('INSERT INTO usuarios (nome, senha) VALUES (?, ?)', (nome, hash_senha))
    db.commit()
    flash(f'Funcionário "{nome}" cadastrado com sucesso!', 'success')
    return redirect(url_for('admin_panel'))

# FUNÇÃO ALTERADA
@app.route('/add_transacao', methods=['POST'])
@admin_required
def add_transacao():
    funcionario_selecionado = request.form['funcionario_selecionado']
    # Extrai o ID do formato "Nome (ID: 123)"
    match = re.search(r'\(ID: (\d+)\)', funcionario_selecionado)
    
    if not match:
        flash('Funcionário inválido. Por favor, selecione um da lista.', 'danger')
        return redirect(url_for('admin_panel'))
        
    id_usuario = int(match.group(1))
    
    # O resto da função continua
    tipo = request.form['tipo']
    dias = int(request.form['dias'])
    motivo = request.form['motivo']
    data = datetime.now().strftime("%Y-%m-%d")
    db = get_db()
    
    db.execute(
        'INSERT INTO transacoes (id_usuario, tipo, dias, data, motivo, status) VALUES (?, ?, ?, ?, ?, ?)',
        (id_usuario, tipo, dias, data, motivo, 'aprovado')
    )
    if tipo == 'ganho':
        db.execute('UPDATE usuarios SET saldo_atual = saldo_atual + ? WHERE id = ?', (dias, id_usuario))
    elif tipo == 'gasto':
        db.execute('UPDATE usuarios SET saldo_atual = saldo_atual - ? WHERE id = ?', (dias, id_usuario))
    db.commit()
    
    flash('Transação direta adicionada e aprovada com sucesso!', 'success')
    return redirect(url_for('admin_panel'))

# ... (Restante das rotas de admin sem alterações)
@app.route('/editar_usuario/<int:id_usuario>', methods=['GET', 'POST'])
@admin_required
def editar_usuario(id_usuario):
    db = get_db()
    usuario = db.execute('SELECT * FROM usuarios WHERE id = ?', (id_usuario,)).fetchone()
    if not usuario: abort(404)
    if request.method == 'POST':
        novo_nome = request.form['nome']
        nova_senha = request.form['nova_senha']
        if nova_senha:
            hash_senha = generate_password_hash(nova_senha)
            db.execute('UPDATE usuarios SET nome = ?, senha = ? WHERE id = ?', (novo_nome, hash_senha, id_usuario))
        else:
            db.execute('UPDATE usuarios SET nome = ? WHERE id = ?', (novo_nome, id_usuario))
        db.commit()
        flash(f'Dados do funcionário "{novo_nome}" atualizados com sucesso!', 'success')
        return redirect(url_for('admin_panel'))
    return render_template('edit_usuario.html', usuario=usuario)

@app.route('/excluir_usuario/<int:id_usuario>')
@admin_required
def excluir_usuario(id_usuario):
    db = get_db()
    usuario = db.execute('SELECT nome FROM usuarios WHERE id = ?', (id_usuario,)).fetchone()
    if usuario and usuario['nome'] == 'admin':
        flash('O usuário admin não pode ser excluído.', 'danger')
        return redirect(url_for('admin_panel'))
    nome_excluido = usuario['nome']
    db.execute('DELETE FROM usuarios WHERE id = ?', (id_usuario,))
    db.commit()
    flash(f'Funcionário "{nome_excluido}" excluído com sucesso!', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/historico_usuario/<int:id_usuario>')
@admin_required
def historico_usuario(id_usuario):
    db = get_db()
    usuario = db.execute('SELECT * FROM usuarios WHERE id = ?', (id_usuario,)).fetchone()
    if not usuario: abort(404)
    transacoes = db.execute('SELECT * FROM transacoes WHERE id_usuario = ? ORDER BY data DESC', (id_usuario,)).fetchall()
    return render_template('historico_usuario.html', usuario=usuario, transacoes=transacoes)

@app.route('/responder_solicitacao/<int:id_transacao>/<string:acao>')
@admin_required
def responder_solicitacao(id_transacao, acao):
    if acao not in ['aprovado', 'recusado']:
        abort(400)
    db = get_db()
    transacao = db.execute('SELECT * FROM transacoes WHERE id = ? AND status = "pendente"', (id_transacao,)).fetchone()
    if not transacao:
        flash('Solicitação não encontrada ou já respondida.', 'danger')
        return redirect(url_for('admin_panel'))
    if acao == 'aprovado':
        db.execute("UPDATE transacoes SET status = 'aprovado' WHERE id = ?", (id_transacao,))
        dias = transacao['dias']
        id_usuario = transacao['id_usuario']
        if transacao['tipo'] == 'ganho':
            db.execute('UPDATE usuarios SET saldo_atual = saldo_atual + ? WHERE id = ?', (dias, id_usuario))
        else:
            db.execute('UPDATE usuarios SET saldo_atual = saldo_atual - ? WHERE id = ?', (dias, id_usuario))
        flash('Solicitação aprovada com sucesso!', 'success')
    else:
        db.execute("UPDATE transacoes SET status = 'recusado' WHERE id = ?", (id_transacao,))
        flash('Solicitação recusada.', 'success')
    db.commit()
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    app.run(debug=True)