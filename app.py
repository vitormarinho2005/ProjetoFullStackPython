from flask import Flask, render_template, request, send_file, jsonify
import os, uuid
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
import matplotlib.pyplot as plt

app = Flask(__name__)

PDF_DIR = os.path.join(os.getcwd(), "temp_pdfs")
os.makedirs(PDF_DIR, exist_ok=True)

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

    # Gráfico simples
    labels = ['Motivação','Desempenho','Objetivos']
    values = [min(10,len(motivacao)//10), min(10,len(desempenho)//10), min(10,len(objetivos)//10)]
    plt.figure(figsize=(4,2))
    plt.bar(labels, values, color=['#0d6efd','#6c757d','#198754'])
    img_path=os.path.join(PDF_DIR,f"{uuid.uuid4()}.png")
    plt.savefig(img_path,bbox_inches='tight'); plt.close()

    # PDF
    pdf_filename=f"Relatorio_{nome}_{uuid.uuid4().hex}.pdf"
    pdf_path=os.path.join(PDF_DIR,pdf_filename)
    pdf=canvas.Canvas(pdf_path,pagesize=A4)
    width,height=A4

    pdf.setFillColor(colors.HexColor('#0d6efd'))
    pdf.rect(0,height-80,width,80,fill=True,stroke=False)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold",24)
    pdf.drawString(2*cm,height-50,f"Relatório Educacional - {nome}")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica",12)
    pdf.drawString(2*cm,height-100,f"Nome: {nome}")
    pdf.drawString(2*cm,height-115,f"Papel: {papel}")
    pdf.drawString(2*cm,height-130,"----------------------------------------")

    y=height-150
    for label, valor in zip(labels,[motivacao,desempenho,objetivos]):
        pdf.setFont("Helvetica-Bold",12); pdf.drawString(2*cm,y,f"{label}:")
        pdf.setFont("Helvetica",11)
        y-=15
        for linha in valor.split("\n"): pdf.drawString(3*cm,y,linha); y-=15
        y-=10

    pdf.drawImage(img_path, 2*cm, y-150, width=16*cm, height=150)
    pdf.save()
    os.remove(img_path)

    return jsonify({"pdf_name": pdf_filename})

@app.route('/download/<filename>')
def download(filename):
    pdf_path=os.path.join(PDF_DIR,filename)
    if not os.path.exists(pdf_path): return jsonify({"error":"Arquivo não encontrado"}),404
    def remover(): 
        try: os.remove(pdf_path); print(f"🗑️ PDF removido: {filename}")
        except: pass
    response=send_file(pdf_path,as_attachment=True,download_name=filename)
    response.call_on_close(remover)
    return response

@app.route('/remover_pdf/<filename>', methods=['DELETE'])
def remover_pdf(filename):
    pdf_path=os.path.join(PDF_DIR,filename)
    try: os.remove(pdf_path); print(f"🗑️ PDF removido via DELETE: {filename}")
        # Remover do servidor
    except FileNotFoundError: pass
    return jsonify({"status":"ok"})

if __name__=='__main__':
    app.run(debug=True)
