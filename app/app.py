import os
import io
import hmac
import secrets
import base64
import binascii
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pandas as pd


# CONFIGURAÇÕES INICIAIS E DE SEGURANÇA

from dotenv import load_dotenv
load_dotenv()

# variável BASE_DIR
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Configuração do Flask
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)

# Configuração da pasta de upload
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configura as chaves puxando dinamicamente do ambiente seguro
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') or secrets.token_hex(32)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL') or (
    'sqlite:///' + os.path.abspath(os.path.join(BASE_DIR, '..', 'DB', 'portyard.db')).replace(os.sep, '/')
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
                  SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE', 'false').lower() == 'true',
                  PERMANENT_SESSION_LIFETIME=__import__('datetime').timedelta(hours=8),
                  MAX_CONTENT_LENGTH=5 * 1024 * 1024)
ALLOWED_IMAGE_TYPES = {'image/jpeg': '.jpg', 'image/png': '.png', 'image/webp': '.webp'}

def is_valid_image(image_bytes, mime):
    if mime == 'image/jpeg':
        return image_bytes.startswith(bytes.fromhex('ffd8ff'))
    if mime == 'image/png':
        return image_bytes.startswith(bytes.fromhex('89504e470d0a1a0a'))
    if mime == 'image/webp':
        return len(image_bytes) >= 12 and image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP'
    return False

@app.context_processor
def inject_csrf_token():
    return {'csrf_token': csrf_token}

@app.template_global('company_logo_url')
def company_logo_url(path):
    if not path:
        return None
    if path.startswith('https://'):
        return path
    return url_for('static', filename=path.lstrip('/'))

def csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_urlsafe(32)
    return session['_csrf_token']

@app.before_request
def protect_state_changes():
    if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
        expected = session.get('_csrf_token', '')
        supplied = request.form.get('_csrf_token', '') or request.headers.get('X-CSRF-Token', '')
        if not expected or not supplied or not hmac.compare_digest(expected, supplied):
            abort(400, description='Token de segurança inválido. Atualize a página e tente novamente.')

@app.after_request
def set_security_headers(response):
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'DENY')
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    response.headers.setdefault('Permissions-Policy', 'camera=(self), microphone=(), geolocation=()')
    return response

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

# MODELOS DO BANCO DE DADOS (MULTI-TENANT)


class Empresa(db.Model):
    __tablename__ = 'empresa'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome_fantasia = db.Column(db.String(100), nullable=False)
    cnpj = db.Column(db.String(18), unique=True, nullable=True)
    nome_empresa_seguranca = db.Column(db.String(100), nullable=True)
    logo_empresa_seguranca = db.Column(db.String(500), nullable=True)
    logo_empresa_portaria = db.Column(db.String(500), nullable=True)
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
    try:
        return db.session.get(Usuario, int(user_id))
    except (TypeError, ValueError):
        return None


# ROTAS DO SISTEMA 

# Rota de Login e Logout
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip().lower()
        password = request.form.get('password') or ''
        
        usuario = Usuario.query.filter(func.lower(Usuario.username) == username).first()
        
        try:
            if usuario and usuario.senha_hash.startswith('$2a$'):
                # O trigger do Supabase gera bcrypt via pgcrypto; compare no PostgreSQL.
                senha_valida = bool(
                    db.engine.dialect.name == 'postgresql'
                    and db.session.query(Usuario.id).filter(
                        Usuario.id == usuario.id,
                        func.extensions.crypt(password, Usuario.senha_hash) == Usuario.senha_hash
                    ).first()
                )
            else:
                # Mantem os hashes Werkzeug antigos e o SQLite local funcionando.
                senha_valida = bool(usuario and check_password_hash(usuario.senha_hash, password))
        except (AttributeError, TypeError, ValueError, SQLAlchemyError):
            # Hash antigo, truncado ou incompatível deve falhar como credencial inválida,
            # sem derrubar a tela de login.
            db.session.rollback()
            app.logger.warning('Hash de senha inválido ou incompatível para um usuário.')
            senha_valida = False

        if senha_valida:
            session.clear()
            login_user(usuario, remember=False, fresh=True)
            session.permanent = True
            return redirect(url_for('dashboard'))
        
        flash('Usuário ou senha incorretos!', 'danger')
        
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# Rotas do Dashboard e Funcionalidades
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

# Rota de Registro de Entrada (Incluindo processamento de Foto via Webcam Base64)
@app.route('/entrada', methods=['GET', 'POST'])
@login_required
def entrada():
    if request.method == 'POST':
        tipo_entrada = request.form.get('tipo_entrada')
        name = request.form.get('motorista')
        cpf = request.form.get('motorista_cpf')
        telefone = request.form.get('motorista_telefone')
        placa = (request.form.get('placa') or '').strip() or None
        modelo = (request.form.get('modelo') or '').strip() or None
        transportadora = (request.form.get('transportadora') or '').strip() or None
        
        foto_salva_como = None
        
        # Primeiro, verifica se veio a foto tirada em tempo real via Webcam (String Base64)
        foto_base64 = request.form.get('foto_base64', '')
        if foto_base64:
            try:
                header, encoded = foto_base64.split(',', 1)
                mime = header.split(';', 1)[0].replace('data:', '')
                extension = ALLOWED_IMAGE_TYPES.get(mime)
                if not extension or len(encoded) > 4_500_000:
                    raise ValueError('Imagem inválida ou muito grande.')
                image_bytes = base64.b64decode(encoded, validate=True)
                if not is_valid_image(image_bytes, mime):
                    raise ValueError('Conteúdo de imagem inválido.')
                filename = f"webcam_{uuid.uuid4().hex}{extension}"
                with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'wb') as image_file:
                    image_file.write(image_bytes)
                foto_salva_como = f"uploads/{filename}"
            except (ValueError, binascii.Error):
                flash('A foto enviada é inválida. Use JPG, PNG ou WEBP de até 5 MB.', 'danger')
                return render_template('entrada.html'), 400
        elif 'foto' in request.files:
            arquivo_foto = request.files['foto']
            if arquivo_foto and arquivo_foto.filename:
                extension = ALLOWED_IMAGE_TYPES.get(arquivo_foto.mimetype)
                signature = arquivo_foto.stream.read(12)
                arquivo_foto.stream.seek(0)
                if not extension or not is_valid_image(signature, arquivo_foto.mimetype):
                    flash('Envie uma foto JPG, PNG ou WEBP válida.', 'danger')
                    return render_template('entrada.html'), 400
                filename = f"acesso_{uuid.uuid4().hex}{extension}"
                arquivo_foto.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                foto_salva_como = f"uploads/{filename}"

        if tipo_entrada == 'visitante':
            novo_veiculo = Veiculo(
                motorista_nome=name, motorista_cpf=cpf, motorista_telefone=telefone,
                placa=placa, modelo=modelo, transportadora=transportadora,
                foto_caminho=foto_salva_como,
                empresa_id=current_user.empresa_id
            )
        else:
            novo_veiculo = Veiculo(
                motorista_nome=name, motorista_cpf=cpf, motorista_telefone=telefone,
                placa=placa, modelo=modelo, transportadora=transportadora,
                foto_caminho=foto_salva_como,
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
    try:
        doca_id = int(doca_id_raw) if doca_id_raw else None
    except (TypeError, ValueError):
        doca_id = None
    
    tipo_op = request.form.get('tipo_operacao', 'Carga')
    
    if not doca_id:
        flash('Nenhuma doca foi selecionada.', 'erro')
        return redirect(url_for('dashboard'))

    doca = Doca.query.filter_by(id=doca_id, empresa_id=current_user.empresa_id).first()
    if doca and doca.status == 'Livre' and mov.status_atual != 'Concluído':
        doca.status = 'Ocupada'
        mov.doca_id = doca.id
        mov.status_atual = 'Em Doca'
        mov.tipo_operacao = tipo_op
        mov.data_hora_doca = datetime.now()
        db.session.commit()
        flash('Veículo direcionado para a doca com sucesso!', 'sucesso')
    else:
        flash('Doca indisponível, não encontrada ou inválida.', 'erro')
    
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
        possui_historico = Movimentacao.query.filter_by(doca_id=doca.id).first() is not None
        if doca.status != 'Livre' or possui_historico:
            flash('Esta doca está ocupada ou possui histórico e não pode ser removida.', 'warning')
        else:
            db.session.delete(doca)
            db.session.commit()
            flash('Doca removida com sucesso.', 'sucesso')
    return redirect(url_for('config_docas'))

@app.route('/exportar')
@login_required
def exportar():
    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')
    
    if not data_inicio_str or not data_fim_str:
        flash('Por favor, informe o período completo para exportar.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d')
        fim = datetime.strptime(data_fim_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        if fim < inicio or (fim.date() - inicio.date()).days >= 365:
            raise ValueError('Período inválido')
    except ValueError:
        flash('O período informado é inválido. Use um intervalo de até 365 dias.', 'danger')
        return redirect(url_for('dashboard'))
    
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


@app.route('/gerenciamento')
@login_required
def gerenciamento():
    hoje = datetime.now().date()
    
    # Totalizadores filtrando por empresa
    movimentacoes_hoje = Movimentacao.query.filter(
        Movimentacao.empresa_id == current_user.empresa_id,
        func.date(Movimentacao.data_hora_entrada) == hoje
    ).all()
    ativos_no_momento = Movimentacao.query.filter(
        Movimentacao.empresa_id == current_user.empresa_id,
        Movimentacao.status_atual != 'Concluído'
    ).count()
    
    # Dados para o gráfico de pizza por status
    status_dados = db.session.query(
        Movimentacao.status_atual, func.count(Movimentacao.id)
    ).filter(
        Movimentacao.empresa_id == current_user.empresa_id
    ).group_by(Movimentacao.status_atual).all()
    
    label_status = [d[0] for d in status_dados]
    valores_status = [d[1] for d in status_dados]

    # Calcula em Python para manter compatibilidade entre PostgreSQL e SQLite.
    registros_com_doca = db.session.query(
        Doca.numero, Movimentacao.data_hora_entrada, Movimentacao.data_hora_saida
    ).join(Doca, Movimentacao.doca_id == Doca.id).filter(
        Movimentacao.empresa_id == current_user.empresa_id,
        Movimentacao.data_hora_entrada.isnot(None),
        Movimentacao.data_hora_saida.isnot(None)
    ).all()

    tempos_por_doca = {}
    for numero, entrada, saida in registros_com_doca:
        minutos = (saida - entrada).total_seconds() / 60
        if minutos >= 0:
            total, quantidade = tempos_por_doca.get(numero, (0.0, 0))
            tempos_por_doca[numero] = (total + minutos, quantidade + 1)

    # Mapeamento e formatação das legendas textuais
    if tempos_por_doca:
        labels_docas = sorted(str(numero) for numero in tempos_por_doca)
        media_tempo_doca = [
            round(tempos_por_doca[numero][0] / tempos_por_doca[numero][1], 1)
            for numero in sorted(tempos_por_doca)
        ]
    else:
        labels_docas = ["Sem movimentações"]
        media_tempo_doca = [0]

    return render_template('gerenciamento.html',
                            movimentacoes=movimentacoes_hoje, 
                            ativos_no_momento=ativos_no_momento,
                            label_status=label_status, 
                            valores_status=valores_status, 
                            labels_docas=labels_docas, 
                            media_tempo_doca=media_tempo_doca)
 
# A criação automática é opcional e limitada ao SQLite local. O schema Supabase
# deve ser provisionado separadamente, sem alterações durante a inicialização.
if (app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite:///')
        and os.getenv('AUTO_CREATE_DB', 'false').lower() == 'true'):
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true')
