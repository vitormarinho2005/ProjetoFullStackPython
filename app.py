from flask import Flask, render_template, request, send_file, jsonify
import os, uuid, sqlite3, shutil
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
import matplotlib.pyplot as plt
from datetime import datetime

app = Flask(__name__)

# ----------------------------
# Pastas para PDFs e backup
# ----------------------------
DATA_DIR = os.environ.get('DATA_DIR', '/opt/render/project/data')
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "database.db")
BACKUP_DIR = os.path.join(DATA_DIR, "backup_db")
PDF_DIR = os.path.join(DATA_DIR, "temp_pdfs")
os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)
# ----------------------------
# Inicialização segura do banco
# ----------------------------
def init_db():
    db_to_use = DB_PATH
    criar = False

    if not os.path.exists(DB_PATH):
        criar = True
    else:
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("SELECT name FROM sqlite_master LIMIT 1;")
            conn.close()
        except sqlite3.DatabaseError:
            # Backup do banco corrompido
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(BACKUP_DIR, f"database_corrompido_{timestamp}.db")
            try:
                shutil.copy2(DB_PATH, backup_file)
                print(f"⚠️ Banco corrompido! Backup criado: {backup_file}")
            except Exception as e:
                print(f"⚠️ Erro ao criar backup do banco corrompido: {e}")

            # Novo banco alternativo
            db_to_use = os.path.join(os.getcwd(), f"database_novo_{timestamp}.db")
            print(f"ℹ️ Novo banco será criado: {db_to_use}")
            criar = True

    if criar:
        conn = sqlite3.connect(db_to_use)
        conn.execute('''
            CREATE TABLE respostas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                papel TEXT NOT NULL,
                motivacao TEXT,
                desempenho TEXT,
                objetivos TEXT,
                pdf_name TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        print(f"✅ Banco {os.path.basename(db_to_use)} criado com sucesso!")

    return db_to_use

# ----------------------------
# Conexão com o banco
# ----------------------------
DB_PATH = init_db()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ----------------------------
# Rotas Flask
# ----------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/processar', methods=['POST'])
def processar():
    nome = request.form['nome']
    papel = request.form['papel']
    motivacao = request.form['motivacao']
    desempenho = request.form['desempenho']
    objetivos = request.form['objetivos']

    # Gráfico
    labels = ['Motivação','Desempenho','Objetivos']
    values = [min(10,len(motivacao)//10), min(10,len(desempenho)//10), min(10,len(objetivos)//10)]
    plt.figure(figsize=(4,2))
    plt.bar(labels, values, color=['#0d6efd','#6c757d','#198754'])
    img_path = os.path.join(PDF_DIR, f"{uuid.uuid4()}.png")
    plt.savefig(img_path, bbox_inches='tight'); plt.close()

    # PDF
    pdf_filename = f"Relatorio_{nome}_{uuid.uuid4().hex}.pdf"
    pdf_path = os.path.join(PDF_DIR, pdf_filename)
    pdf = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4

    pdf.setFillColor(colors.HexColor('#0d6efd'))
    pdf.rect(0, height-80, width, 80, fill=True, stroke=False)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawString(2*cm, height-50, f"Relatório Educacional - {nome}")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 12)
    pdf.drawString(2*cm, height-100, f"Nome: {nome}")
    pdf.drawString(2*cm, height-115, f"Papel: {papel}")
    pdf.drawString(2*cm, height-130, "----------------------------------------")

    y = height-150
    for label, valor in zip(labels, [motivacao, desempenho, objetivos]):
        pdf.setFont("Helvetica-Bold", 12); pdf.drawString(2*cm, y, f"{label}:")
        pdf.setFont("Helvetica", 11)
        y -= 15
        for linha in valor.split("\n"): pdf.drawString(3*cm, y, linha); y -= 15
        y -= 10

    pdf.drawImage(img_path, 2*cm, y-150, width=16*cm, height=150)
    pdf.save()
    os.remove(img_path)

    # Salvar no banco
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO respostas (nome, papel, motivacao, desempenho, objetivos, pdf_name)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (nome, papel, motivacao, desempenho, objetivos, pdf_filename))
    conn.commit()
    conn.close()

    return jsonify({"pdf_name": pdf_filename})

@app.route('/download/<filename>')
def download(filename):
    pdf_path = os.path.join(PDF_DIR, filename)
    if not os.path.exists(pdf_path):
        return jsonify({"error": "Arquivo não encontrado"}), 404

    def remover():
        try:
            os.remove(pdf_path)
            print(f"🗑️ PDF removido: {filename}")
            conn = get_db_connection()
            conn.execute('DELETE FROM respostas WHERE pdf_name = ?', (filename,))
            conn.commit()
            conn.close()
        except:
            pass

    response = send_file(pdf_path, as_attachment=True, download_name=filename)
    response.call_on_close(remover)
    return response

@app.route('/remover_pdf/<filename>', methods=['DELETE'])
def remover_pdf(filename):
    pdf_path = os.path.join(PDF_DIR, filename)
    try: os.remove(pdf_path)
    except FileNotFoundError: pass

    conn = get_db_connection()
    conn.execute('DELETE FROM respostas WHERE pdf_name = ?', (filename,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/historico')
def historico():
    conn = get_db_connection()
    rows = conn.execute('SELECT nome, papel, pdf_name FROM respostas ORDER BY id DESC').fetchall()
    conn.close()
    return jsonify([{"nome": r["nome"], "papel": r["papel"], "pdf_name": r["pdf_name"]} for r in rows])

# ----------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
