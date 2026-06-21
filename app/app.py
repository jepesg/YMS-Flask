import os
import io
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pandas as pd

# ==========================================
# CONFIGURAÇÕES INICIAIS E DE SEGURANÇA     #
# ==========================================

from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, 
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))

# Configura as chaves puxando dinamicamente do ambiente seguro
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'sua-chave-secreta-padrao-caso-falhe')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configurações de Uploads
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Inicialização do Banco de Dados
db = SQLAlchemy(app)

# Configuração do Gerenciador de Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ==========================================
# MODELOS DO BANCO DE DADOS (MULTI-TENANT) #
# ==========================================

class Empresa(db.Model):
    __tablename__ = 'empresa'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome_fantasia = db.Column(db.String(100), nullable=False)
    cnpj = db.Column(db.String(18), unique=True, nullable=True)
    data_cadastro = db.Column(db.DateTime, default=datetime.now)

class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuario'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    
    # Vinculo Tenant
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresa.id'), nullable=False)
    empresa = db.relationship('Empresa', backref='usuarios')

class Veiculo(db.Model):
    __tablename__ = 'veiculo'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    placa = db.Column(db.String(10), nullable=True)
    modelo = db.Column(db.String(50), nullable=True)
    transportadora = db.Column(db.String(50), nullable=True)
    motorista_nome = db.Column(db.String(100), nullable=False)
    motorista_cpf = db.Column(db.String(14), nullable=False)
    motorista_telefone = db.Column(db.String(20), nullable=True)
    foto_caminho = db.Column(db.String(255), nullable=True)
    
    # Vinculo Tenant
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresa.id'), nullable=False)
    empresa = db.relationship('Empresa', backref='veiculos')

class Doca(db.Model):
    __tablename__ = 'doca'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    numero = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Livre')
    
    # Vinculo Tenant
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresa.id'), nullable=False)
    empresa = db.relationship('Empresa', backref='docas')

class Movimentacao(db.Model):
    __tablename__ = 'movimentacao'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    veiculo_id = db.Column(db.Integer, db.ForeignKey('veiculo.id'), nullable=False)
    doca_id = db.Column(db.Integer, db.ForeignKey('doca.id'), nullable=True)
    tipo_operacao = db.Column(db.String(20), default='Carga')
    
    veiculo = db.relationship('Veiculo', backref='movimentacoes')
    doca = db.relationship('Doca', backref='movimentacoes')
    
    status_atual = db.Column(db.String(20), nullable=False, default='No Pátio')
    operacao = db.Column(db.String(20), nullable=True)
    
    data_hora_entrada = db.Column(db.DateTime, nullable=False, default=datetime.now)
    data_hora_doca = db.Column(db.DateTime, nullable=True)
    data_hora_saida = db.Column(db.DateTime, nullable=True)
    
    # Vinculo Tenant
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresa.id'), nullable=False)
    empresa = db.relationship('Empresa', backref='movimentacoes')

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# ==================
# ROTAS DO SISTEMA #
# ==================

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        usuario = Usuario.query.filter_by(username=username).first()
        
        if usuario and check_password_hash(usuario.senha_hash, password):
            login_user(usuario)
            return redirect(url_for('dashboard'))
        
        flash('Usuário ou senha incorretos!', 'danger')
        
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    termo_busca = request.args.get('busca', '').strip()
    filtro_status = request.args.get('status_filtro', '').strip()

    if filtro_status == 'Concluído' or filtro_status == 'Concluido':
        query = Movimentacao.query.filter(Movimentacao.empresa_id == current_user.empresa_id, Movimentacao.status_atual == 'Concluído')
    elif filtro_status:
        query = Movimentacao.query.filter(Movimentacao.empresa_id == current_user.empresa_id, Movimentacao.status_atual == filtro_status)
    else:
        query = Movimentacao.query.filter(Movimentacao.empresa_id == current_user.empresa_id, Movimentacao.status_atual != 'Concluído')

    if termo_busca:
        query = query.join(Veiculo).filter(
            (Veiculo.motorista_nome.like(f"%{termo_busca}%")) |
            (Veiculo.motorista_cpf.like(f"%{termo_busca}%")) |
            (Veiculo.placa.like(f"%{termo_busca}%")) |
            (Veiculo.modelo.like(f"%{termo_busca}%")) |
            (Veiculo.transportadora.like(f"%{termo_busca}%"))
        )

    movimentacoes_filtradas = query.order_by(Movimentacao.data_hora_entrada.desc()).all()
    docas_totais = Doca.query.filter_by(empresa_id=current_user.empresa_id).all()

    return render_template(
        'dashboard.html', 
        movimentacoes=movimentacoes_filtradas, 
        docas=docas_totais,
        busca_atual=termo_busca,
        status_atual=filtro_status
    )

@app.route('/entrada', methods=['GET', 'POST'])
@login_required
def entrada():
    if request.method == 'POST':
        tipo_entrada = request.form.get('tipo_entrada')
        name = request.form.get('motorista')
        cpf = request.form.get('motorista_cpf')
        telefone = request.form.get('motorista_telefone')
        
        foto_salva_como = None
        if 'foto' in request.files:
            arquivo_foto = request.files['foto']
            if arquivo_foto and arquivo_foto.filename != '':
                nome_seguro = secure_filename(arquivo_foto.filename)
                extensao = os.path.splitext(nome_seguro)[1]
                nome_final_foto = f"acesso_{cpf}_{int(datetime.now().timestamp())}{extensao}"
                caminho_fisico = os.path.join(app.config['UPLOAD_FOLDER'], nome_final_foto)
                arquivo_foto.save(caminho_fisico)
                foto_salva_como = f"uploads/{nome_final_foto}"

        if tipo_entrada == 'visitante':
            novo_veiculo = Veiculo(
                motorista_nome=name, motorista_cpf=cpf, motorista_telefone=telefone,
                placa=None, modelo=None, transportadora=None, foto_caminho=foto_salva_como,
                empresa_id=current_user.empresa_id
            )
        else:
            novo_veiculo = Veiculo(
                motorista_nome=name, motorista_cpf=cpf, motorista_telefone=telefone,
                placa=request.form.get('placa'), modelo=request.form.get('modelo'),
                transportadora=request.form.get('transportadora'), foto_caminho=foto_salva_como,
                empresa_id=current_user.empresa_id
            )
            
        db.session.add(novo_veiculo)
        db.session.flush()

        nova_movimentacao = Movimentacao(
            veiculo_id=novo_veiculo.id, 
            status_atual='No Pátio',
            empresa_id=current_user.empresa_id
        )
        db.session.add(nova_movimentacao)
        db.session.commit()
        
        return redirect(url_for('dashboard'))
        
    return render_template('entrada.html')

@app.route('/atualizar_status/<int:id>', methods=['POST'])
@login_required
def atualizar_status(id):
    mov = Movimentacao.query.filter_by(id=id, empresa_id=current_user.empresa_id).first_or_404()
    
    doca_id_raw = request.form.get('doca_id')
    doca_id = int(doca_id_raw) if doca_id_raw else None
    
    tipo_op = request.form.get('tipo_operacao', 'Carga')
    
    if not doca_id:
        flash('Nenhuma doca foi selecionada.', 'erro')
        return redirect(url_for('dashboard'))

    doca = Doca.query.filter_by(id=doca_id, empresa_id=current_user.empresa_id).first()
    if doca:
        doca.status = 'Ocupada'
        mov.doca_id = doca.id
        mov.status_atual = 'Em Doca'
        mov.tipo_operacao = tipo_op
        mov.data_hora_doca = datetime.now()
        db.session.commit()
        flash('Veículo direcionado para a doca com sucesso!', 'sucesso')
    else:
        flash('Doca não encontrada ou inválida.', 'erro')
    
    return redirect(url_for('dashboard'))

@app.route('/registrar_saida/<int:id>', methods=['POST'])
@login_required
def registrar_saida(id):
    mov = Movimentacao.query.filter_by(id=id, empresa_id=current_user.empresa_id).first_or_404()
    
    if mov.doca:
        mov.doca.status = 'Livre'
        
    mov.status_atual = 'Concluído'
    mov.data_hora_saida = datetime.now()
    db.session.commit()
    
    flash('Saída registrada e doca liberada com sucesso!', 'sucesso')
    return redirect(url_for('dashboard'))

@app.route('/config_docas', methods=['GET', 'POST'])
@login_required
def config_docas():
    if request.method == 'POST':
        numero_doca = request.form.get('numero')
        if numero_doca:
            doca_existe = Doca.query.filter_by(numero=numero_doca, empresa_id=current_user.empresa_id).first()
            if not doca_existe:
                db.session.add(Doca(numero=numero_doca, status='Livre', empresa_id=current_user.empresa_id))
                db.session.commit()
        return redirect(url_for('config_docas'))
    return render_template('config_docas.html', docas=Doca.query.filter_by(empresa_id=current_user.empresa_id).all())

@app.route('/deletar_doca/<int:doca_id>', methods=['POST'])
@login_required
def deletar_doca(doca_id):
    doca = Doca.query.filter_by(id=doca_id, empresa_id=current_user.empresa_id).first()
    if doca:
        db.session.delete(doca)
        db.session.commit()
    return redirect(url_for('config_docas'))

@app.route('/exportar')
@login_required
def exportar():
    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')
    
    if not data_inicio_str or not data_fim_str:
        flash('Por favor, informe o período completo para exportar.', 'danger')
        return redirect(url_for('dashboard'))

    inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d')
    fim = datetime.strptime(data_fim_str + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    
    dados = Movimentacao.query.filter(
        Movimentacao.empresa_id == current_user.empresa_id,
        Movimentacao.data_hora_entrada.between(inicio, fim)
    ).all()
    
    dados_planilha = []
    for mov in dados:
        dados_planilha.append({
            "ID Registro": mov.id, 
            "Nome/Motorista": mov.veiculo.motorista_nome, 
            "CPF": mov.veiculo.motorista_cpf,
            "Tipo": "Logística" if mov.veiculo.placa else "Pedestre", 
            "Placa": mov.veiculo.placa if mov.veiculo.placa else "-",
            "Modelo": mov.veiculo.modelo if mov.veiculo.modelo else "-", 
            "Doca Alocada": mov.doca.numero if mov.doca else "-",
            "Status Atual": mov.status_atual,
            "Operação Realizada": mov.tipo_operacao if mov.tipo_operacao else "Nenhuma",
            "Horário Entrada": mov.data_hora_entrada.strftime('%d/%m/%Y %H:%M:%S') if mov.data_hora_entrada else "-",
            "Horário Saída": mov.data_hora_saida.strftime('%d/%m/%Y %H:%M:%S') if mov.data_hora_saida else "-"
        })
        
    if not dados_planilha:
        flash('Nenhum registro encontrado para o intervalo de datas selecionado.', 'warning')
        return redirect(url_for('dashboard'))

    df = pd.DataFrame(dados_planilha)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Movimentacoes')
    output.seek(0)
    
    return send_file(
        output, 
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        as_attachment=True, 
        download_name=f"relatorio_yms_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    )

# =======================================
# INICIALIZAÇÃO SEGURA DO BANCO DE DADOS #
# =======================================
with app.app_context():
    db.create_all()
    
    if Empresa.query.count() == 0:
        empresa_demo = Empresa(nome_fantasia="Logística Demo S/A", cnpj="00.000.000/0001-00")
        db.session.add(empresa_demo)
        db.session.flush() 
        
        senha_criptografada = generate_password_hash('admin')
        usuario_admin = Usuario(username='admin', senha_hash=senha_criptografada, empresa_id=empresa_demo.id)
        db.session.add(usuario_admin)
        
        db.session.add(Doca(numero="Doca 01", status='Livre', empresa_id=empresa_demo.id))
        db.session.add(Doca(numero="Doca 02", status='Livre', empresa_id=empresa_demo.id))
        
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)