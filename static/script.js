document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("formAvaliacao");
    const statusMsg = document.getElementById("statusMsg");
    const historico = document.getElementById("listaHistorico");
    const toastContainer = document.getElementById("toastContainer");
    const toggleBtn = document.getElementById("toggleTheme");

    let tema = localStorage.getItem("tema") || "auto";
    let relatorios = []; // agora vamos buscar do servidor

    // --- Função Toast ---
    const mostrarToast = (msg, tipo="info", duracao=4000) => {
        const cores = { 
            success:"bg-success text-white", 
            info:"bg-info text-white", 
            danger:"bg-danger text-white", 
            secondary:"bg-secondary text-white" 
        };
        const toast = document.createElement("div");
        toast.className = `toast align-items-center ${cores[tipo]||"bg-light text-dark"} border-0 shadow`;
        toast.setAttribute("role","alert");
        toast.setAttribute("aria-live","assertive");
        toast.setAttribute("aria-atomic","true");
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${msg}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        toastContainer.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast,{delay:duracao});
        bsToast.show();
        toast.addEventListener("hidden.bs.toast",()=>toast.remove());
    };

    // --- Atualizar histórico ---
    const atualizarHistorico = () => {
        historico.innerHTML = "";
        if(!relatorios.length){
            const vazio = document.createElement("li");
            vazio.className="list-group-item text-muted text-center";
            vazio.textContent="Nenhum relatório gerado ainda.";
            historico.appendChild(vazio);
            return;
        }
        relatorios.forEach((r,i)=>{
            const li=document.createElement("li");
            li.className="list-group-item d-flex justify-content-between align-items-center";
            li.innerHTML=`
                <span>${r.nome} - ${r.papel}</span>
                <div>
                    <button class="btn btn-sm btn-primary me-2" data-action="baixar" data-index="${i}">📥 Baixar</button>
                    <button class="btn btn-sm btn-danger" data-action="remover" data-index="${i}">🗑️ Remover</button>
                </div>
            `;
            historico.appendChild(li);
        });
    };

    // --- Buscar histórico do servidor ---
    const carregarHistorico = async () => {
        try {
            const resp = await fetch("/historico");
            relatorios = await resp.json();
            relatorios = relatorios.map(r=>({
                nome: r.nome,
                papel: r.papel,
                url: `/download/${r.pdf_name}`,
                pdf_name: r.pdf_name
            }));
            atualizarHistorico();
        } catch(err){
            mostrarToast("🚫 Falha ao carregar histórico do servidor","danger");
        }
    };
    carregarHistorico();

    // --- Enviar formulário ---
    form.addEventListener("submit", async e=>{
        e.preventDefault();
        statusMsg.innerHTML="⚙️ Gerando relatório via IA...";
        statusMsg.className="alert alert-info mt-3";
        const dados=new FormData(form);
        try {
            const resp=await fetch("/processar",{method:"POST",body:dados});
            const data=await resp.json();
            if(data.pdf_name){
                const nome=dados.get("nome"), papel=dados.get("papel"), url=`/download/${data.pdf_name}`;
                relatorios.unshift({nome,papel,url,pdf_name:data.pdf_name});
                atualizarHistorico();
                mostrarToast("✅ Relatório gerado! Download iniciado","success");
                statusMsg.innerHTML="✅ Relatório gerado com sucesso!";

                // Download automático
                const a=document.createElement("a"); a.href=url; a.download=data.pdf_name; document.body.appendChild(a); a.click(); document.body.removeChild(a);

                // Remover PDF do servidor após 3s
                setTimeout(async ()=>{
                    await fetch(`/remover_pdf/${data.pdf_name}`,{method:"DELETE"});
                    relatorios = relatorios.filter(r=>r.pdf_name !== data.pdf_name);
                    atualizarHistorico();
                    mostrarToast("🗑️ Relatório removido automaticamente do servidor!","secondary");
                    statusMsg.innerHTML="🗑️ Relatório removido automaticamente do servidor!";
                    statusMsg.className="alert alert-secondary mt-3";
                },3000);
            } else {
                mostrarToast("❌ Erro ao gerar relatório","danger");
                statusMsg.innerHTML="❌ Erro ao gerar relatório";
                statusMsg.className="alert alert-danger mt-3";
            }
        } catch(err){
            mostrarToast("🚫 Falha na comunicação com o servidor","danger");
            statusMsg.innerHTML="❌ Falha na comunicação com o servidor";
            statusMsg.className="alert alert-danger mt-3";
        }
    });

    // --- Histórico: baixar/remover ---
    historico.addEventListener("click", async e=>{
        if(e.target.tagName!=="BUTTON") return;
        const i=e.target.getAttribute("data-index"), acao=e.target.getAttribute("data-action"), r=relatorios[i];

        if(acao==="baixar"){
            mostrarToast("📦 Iniciando download...","info");
            statusMsg.innerHTML="📦 Iniciando download..."; statusMsg.className="alert alert-info mt-3";
            const a=document.createElement("a"); a.href=r.url; a.download=r.nome+".pdf"; document.body.appendChild(a); a.click(); document.body.removeChild(a);
            setTimeout(async ()=>{
                await fetch(`/remover_pdf/${r.pdf_name}`,{method:"DELETE"});
                relatorios.splice(i,1);
                atualizarHistorico();
                mostrarToast("🗑️ Relatório removido automaticamente!","secondary");
            },3000);
        }

        if(acao==="remover"){
            if(!confirm("Deseja realmente remover este relatório?")) return;
            await fetch(`/remover_pdf/${r.pdf_name}`,{method:"DELETE"});
            relatorios.splice(i,1);
            atualizarHistorico();
            mostrarToast("🗑️ Relatório excluído com sucesso!","secondary");
        }
    });

    // --- Tema ---
    const aplicarTema=modo=>{
        if(modo==="dark"){ document.body.classList.add("dark-mode"); toggleBtn.textContent="☀️"; }
        else if(modo==="light"){ document.body.classList.remove("dark-mode"); toggleBtn.textContent="🌙"; }
        else{ document.body.classList.remove("dark-mode"); toggleBtn.textContent=window.matchMedia("(prefers-color-scheme: dark)").matches?"☀️":"🌙"; }
    };
    aplicarTema(tema);

    toggleBtn.addEventListener("click",()=>{
        tema=(tema==="auto"||tema==="light")?"dark":"light"; localStorage.setItem("tema",tema); aplicarTema(tema);
    });

    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", e=>{ if(tema==="auto") aplicarTema("auto"); });
});
