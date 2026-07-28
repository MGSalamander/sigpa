import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from statsmodels.formula.api import ols
from statsmodels.stats.anova import anova_lm
from statsmodels.stats.multicomp import pairwise_tukeyhsd
import plotly.express as px
import plotly.graph_objects as go
import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

DB_NAME = "sigpa.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def query_to_df(query, params=()):
    conn = get_connection()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def execute_query(query, params=()):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()

st.set_page_config(
    page_title="SIGPA - Sistema de Pesquisas Agrícolas",
    page_icon="🌱",
    layout="wide"
)

if "usuario_id" not in st.session_state:
    st.session_state.usuario_id = None
    st.session_state.usuario_nome = ""
    st.session_state.usuario_tipo = ""

def fazer_login(email, senha):
    df = query_to_df("SELECT * FROM usuarios WHERE email = ? AND senha = ?", (email, senha))
    if len(df) > 0:
        st.session_state.usuario_id = df.iloc[0]["id"]
        st.session_state.usuario_nome = df.iloc[0]["nome"]
        st.session_state.usuario_tipo = df.iloc[0]["tipo"]
        return True
    return False

def fazer_logout():
    st.session_state.usuario_id = None
    st.session_state.usuario_nome = ""
    st.session_state.usuario_tipo = ""

def tela_login():
    st.title("🌱 SIGPA - Sistema Integrado de Gestão de Pesquisas Agrícolas")
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("🔐 Acesse o Sistema")
        email = st.text_input("E-mail", key="login_email")
        senha = st.text_input("Senha", type="password", key="login_senha")
        if st.button("Entrar", use_container_width=True):
            if fazer_login(email, senha):
                st.rerun()
            else:
                st.error("E-mail ou senha incorretos!")
        st.markdown("---")
        st.markdown("**Primeiro acesso?**")
        with st.expander("Criar conta"):
            nome = st.text_input("Nome completo", key="cad_nome")
            email_cad = st.text_input("E-mail", key="cad_email")
            senha_cad = st.text_input("Senha", type="password", key="cad_senha")
            tipo = st.selectbox("Tipo", ["pesquisador", "admin"], key="cad_tipo")
            if st.button("Criar Conta", key="btn_criar_conta"):
                try:
                    execute_query(
                        "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                        (nome, email_cad, senha_cad, tipo)
                    )
                    st.success("Conta criada! Faça login.")
                except:
                    st.error("E-mail já cadastrado!")

def tela_dashboard():
    st.title(f"📊 Dashboard - Bem-vindo, {st.session_state.usuario_nome}!")
    col1, col2, col3, col4 = st.columns(4)
    total_projetos = query_to_df("SELECT COUNT(*) as total FROM projetos").iloc[0]["total"]
    ativos = query_to_df("SELECT COUNT(*) as total FROM projetos WHERE status = 'conducao'").iloc[0]["total"]
    concluidos = query_to_df("SELECT COUNT(*) as total FROM projetos WHERE status = 'concluido'").iloc[0]["total"]
    total_empresas = query_to_df("SELECT COUNT(*) as total FROM empresas").iloc[0]["total"]
    with col1:
        st.metric("📋 Total Projetos", total_projetos)
    with col2:
        st.metric("🌱 Em Condução", ativos)
    with col3:
        st.metric("✅ Concluídos", concluidos)
    with col4:
        st.metric("🏢 Empresas", total_empresas)
    st.markdown("---")
    st.subheader("📋 Projetos Recentes")
    projetos = query_to_df("""
        SELECT p.id, p.titulo, e.nome as empresa, p.cultura, p.safra, p.status, p.criado_em
        FROM projetos p
        JOIN empresas e ON p.empresa_id = e.id
        ORDER BY p.criado_em DESC
        LIMIT 10
    """)
    if len(projetos) > 0:
        for _, proj in projetos.iterrows():
            with st.container():
                cols = st.columns([3, 2, 1, 1, 1])
                cols[0].write(f"**{proj['titulo']}**")
                cols[1].write(f"🏢 {proj['empresa']}")
                cols[2].write(f"🌾 {proj['cultura']}")
                cols[3].write(f"📅 {proj['safra']}")
                status_emoji = {"planejamento": "📝", "conducao": "🌱", "analise": "📊", "concluido": "✅"}
                cols[4].write(f"{status_emoji.get(proj['status'], '📋')} {proj['status']}")
                st.markdown("---")
    else:
        st.info("Nenhum projeto cadastrado ainda. Crie o primeiro!")

def tela_empresas():
    st.title("🏢 Gerenciar Empresas")
    tab1, tab2 = st.tabs(["📋 Empresas Cadastradas", "➕ Nova Empresa"])
    
    with tab1:
        empresas = query_to_df("SELECT * FROM empresas ORDER BY nome")
        if len(empresas) > 0:
            for _, emp in empresas.iterrows():
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                col1.write(f"**{emp['nome']}**")
                col2.write(f"📧 {emp.get('email', '—')}")
                
                # Botão Editar
                if col3.button("✏️ Editar", key=f"edit_emp_{emp['id']}"):
                    st.session_state.edit_empresa_id = emp['id']
                    st.session_state.edit_empresa_nome = emp['nome']
                    st.session_state.edit_empresa_cnpj = emp.get('cnpj', '')
                    st.session_state.edit_empresa_contato = emp.get('contato', '')
                    st.session_state.edit_empresa_email = emp.get('email', '')
                    st.session_state.edit_empresa_telefone = emp.get('telefone', '')
                    st.rerun()
                
                # Botão Excluir
                if col4.button("🗑️", key=f"del_emp_{emp['id']}"):
                    execute_query("DELETE FROM empresas WHERE id = ?", (emp['id'],))
                    st.rerun()
                
                st.markdown("---")
            
            # Modal de edição
            if 'edit_empresa_id' in st.session_state:
                with st.expander("✏️ Editando Empresa", expanded=True):
                    with st.form("editar_empresa"):
                        nome = st.text_input("Nome", value=st.session_state.edit_empresa_nome)
                        cnpj = st.text_input("CNPJ", value=st.session_state.edit_empresa_cnpj)
                        contato = st.text_input("Contato", value=st.session_state.edit_empresa_contato)
                        email = st.text_input("E-mail", value=st.session_state.edit_empresa_email)
                        telefone = st.text_input("Telefone", value=st.session_state.edit_empresa_telefone)
                        
                        col_a, col_b = st.columns(2)
                        if col_a.form_submit_button("💾 Salvar"):
                            execute_query(
                                "UPDATE empresas SET nome=?, cnpj=?, contato=?, email=?, telefone=? WHERE id=?",
                                (nome, cnpj, contato, email, telefone, st.session_state.edit_empresa_id)
                            )
                            del st.session_state.edit_empresa_id
                            st.rerun()
                        if col_b.form_submit_button("❌ Cancelar"):
                            del st.session_state.edit_empresa_id
                            st.rerun()
        else:
            st.info("Nenhuma empresa cadastrada.")
    
    with tab2:
        with st.form("nova_empresa"):
            nome = st.text_input("Nome da Empresa*")
            cnpj = st.text_input("CNPJ")
            contato = st.text_input("Nome do Contato")
            email = st.text_input("E-mail")
            telefone = st.text_input("Telefone")
            if st.form_submit_button("💾 Salvar Empresa"):
                if nome:
                    execute_query(
                        "INSERT INTO empresas (nome, cnpj, contato, email, telefone) VALUES (?, ?, ?, ?, ?)",
                        (nome, cnpj, contato, email, telefone)
                    )
                    st.success(f"Empresa '{nome}' cadastrada!")
                    st.rerun()
                else:
                    st.error("Nome é obrigatório!")

def tela_projetos():
    st.title("📋 Gerenciar Projetos")
    tab1, tab2 = st.tabs(["📋 Projetos", "➕ Novo Projeto"])
    
    with tab1:
        projetos = query_to_df("""
            SELECT p.*, e.nome as empresa_nome
            FROM projetos p
            JOIN empresas e ON p.empresa_id = e.id
            ORDER BY p.criado_em DESC
        """)
        
        if len(projetos) > 0:
            for _, proj in projetos.iterrows():
                col1, col2, col3, col4, col5 = st.columns([3, 2, 1, 1, 1])
                col1.write(f"**{proj['titulo']}**")
                col2.write(f"🏢 {proj['empresa_nome']}")
                status_emoji = {"planejamento": "📝", "conducao": "🌱", "analise": "📊", "concluido": "✅"}
                col3.write(f"{status_emoji.get(proj['status'], '📋')} {proj['status']}")
                
                if col4.button("✏️ Editar", key=f"edit_proj_{proj['id']}"):
                    st.session_state.edit_projeto_id = proj['id']
                    for campo in ['titulo', 'objetivo', 'tipo_pesquisa', 'cultura', 'local', 'municipio', 'estado', 'safra', 'responsavel', 'empresa_id']:
                        st.session_state[f'edit_proj_{campo}'] = proj.get(campo, '') if campo != 'empresa_id' else proj[campo]
                    st.session_state.edit_proj_data_plantio = proj.get('data_plantio', datetime.now())
                    st.session_state.edit_proj_data_colheita = proj.get('data_colheita', datetime.now())
                    st.rerun()
                
                if col5.button("🗑️", key=f"del_proj_{proj['id']}"):
                    execute_query("DELETE FROM medicoes WHERE parcela_id IN (SELECT id FROM parcelas WHERE projeto_id = ?)", (proj['id'],))
                    execute_query("DELETE FROM parcelas WHERE projeto_id = ?", (proj['id'],))
                    execute_query("DELETE FROM tratamentos WHERE projeto_id = ?", (proj['id'],))
                    execute_query("DELETE FROM delineamentos WHERE projeto_id = ?", (proj['id'],))
                    execute_query("DELETE FROM permissoes WHERE projeto_id = ?", (proj['id'],))
                    execute_query("DELETE FROM projetos WHERE id = ?", (proj['id'],))
                    st.rerun()
                
                st.markdown("---")
            
            # Modal de edição
            if 'edit_projeto_id' in st.session_state:
                with st.expander("✏️ Editando Projeto", expanded=True):
                    with st.form("editar_projeto"):
                        empresas = query_to_df("SELECT id, nome FROM empresas ORDER BY nome")
                        empresa_id = st.selectbox("Empresa", empresas["id"].values, 
                            format_func=lambda x: empresas[empresas["id"]==x]["nome"].values[0],
                            index=0 if len(empresas)==0 else empresas[empresas["id"]==st.session_state.edit_proj_empresa_id].index[0] if st.session_state.edit_proj_empresa_id in empresas["id"].values else 0)
                        titulo = st.text_input("Título", value=st.session_state.edit_proj_titulo)
                        objetivo = st.text_area("Objetivo", value=st.session_state.edit_proj_objetivo)
                        tipo_pesquisa = st.selectbox("Tipo", ["cultivar", "nutricao", "defensivo", "irrigacao", "densidade", "epoca", "sistema_cultivo", "outros"],
                            index=["cultivar", "nutricao", "defensivo", "irrigacao", "densidade", "epoca", "sistema_cultivo", "outros"].index(st.session_state.edit_proj_tipo_pesquisa) if st.session_state.edit_proj_tipo_pesquisa in ["cultivar", "nutricao", "defensivo", "irrigacao", "densidade", "epoca", "sistema_cultivo", "outros"] else 0)
                        cultura = st.text_input("Cultura", value=st.session_state.edit_proj_cultura)
                        local = st.text_input("Local", value=st.session_state.edit_proj_local)
                        municipio = st.text_input("Município", value=st.session_state.edit_proj_municipio)
                        estado = st.text_input("Estado", value=st.session_state.edit_proj_estado)
                        safra = st.text_input("Safra", value=st.session_state.edit_proj_safra)
                        responsavel = st.text_input("Responsável", value=st.session_state.edit_proj_responsavel)
                        
                        col_a, col_b = st.columns(2)
                        if col_a.form_submit_button("💾 Salvar"):
                            execute_query("""
                                UPDATE projetos SET empresa_id=?, titulo=?, objetivo=?, tipo_pesquisa=?, cultura=?, local=?, municipio=?, estado=?, safra=?, responsavel=?, atualizado_em=CURRENT_TIMESTAMP WHERE id=?
                            """, (empresa_id, titulo, objetivo, tipo_pesquisa, cultura, local, municipio, estado, safra, responsavel, st.session_state.edit_projeto_id))
                            del st.session_state.edit_projeto_id
                            st.rerun()
                        if col_b.form_submit_button("❌ Cancelar"):
                            del st.session_state.edit_projeto_id
                            st.rerun()
        else:
            st.info("Nenhum projeto cadastrado.")
    
    with tab2:
        with st.form("novo_projeto"):
            empresas = query_to_df("SELECT id, nome FROM empresas ORDER BY nome")
            if len(empresas) == 0:
                st.warning("Cadastre uma empresa primeiro!")
                return
            empresa_id = st.selectbox("Empresa*", empresas["id"].values, format_func=lambda x: empresas[empresas["id"]==x]["nome"].values[0])
            titulo = st.text_input("Título do Projeto*")
            objetivo = st.text_area("Objetivo")
            tipo_pesquisa = st.selectbox("Tipo de Pesquisa", ["cultivar", "nutricao", "defensivo", "irrigacao", "densidade", "epoca", "sistema_cultivo", "outros"])
            cultura = st.text_input("Cultura (ex: Soja, Milho)")
            local = st.text_input("Local/Fazenda")
            municipio = st.text_input("Município")
            estado = st.text_input("Estado (UF)")
            safra = st.text_input("Safra (ex: 2025/2026)")
            responsavel = st.text_input("Responsável")
            data_plantio = st.date_input("Data de Plantio")
            data_colheita = st.date_input("Data de Colheita")
            if st.form_submit_button("💾 Salvar Projeto"):
                if titulo and empresa_id:
                    execute_query("""
                        INSERT INTO projetos (empresa_id, titulo, objetivo, tipo_pesquisa, cultura, local, municipio, estado, safra, responsavel, data_plantio, data_colheita)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (empresa_id, titulo, objetivo, tipo_pesquisa, cultura, local, municipio, estado, safra, responsavel, data_plantio, data_colheita))
                    st.success("Projeto criado!")
                    st.rerun()

def tela_tratamentos():
    st.title("🧪 Gerenciar Tratamentos")
    projetos = query_to_df("SELECT id, titulo FROM projetos ORDER BY titulo")
    if len(projetos) == 0:
        st.warning("Crie um projeto primeiro!")
        return
    projeto_id = st.selectbox("Selecione o Projeto", projetos["id"].values, format_func=lambda x: projetos[projetos["id"]==x]["titulo"].values[0], key="sel_trat_proj")
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["📋 Tratamentos", "➕ Novo Tratamento"])
    
    with tab1:
        tratamentos = query_to_df("SELECT * FROM tratamentos WHERE projeto_id = ? ORDER BY codigo", (projeto_id,))
        if len(tratamentos) > 0:
            for _, trat in tratamentos.iterrows():
                col1, col2, col3, col4 = st.columns([1, 3, 1, 1])
                col1.write(f"**{trat['codigo']}**")
                col2.write(trat['nome'])
                
                if col3.button("✏️", key=f"edit_trat_{trat['id']}"):
                    st.session_state.edit_tratamento_id = trat['id']
                    st.session_state.edit_trat_codigo = trat['codigo']
                    st.session_state.edit_trat_nome = trat['nome']
                    st.session_state.edit_trat_descricao = trat.get('descricao', '')
                    st.rerun()
                
                if col4.button("🗑️", key=f"del_trat_{trat['id']}"):
                    execute_query("DELETE FROM tratamentos WHERE id = ?", (trat['id'],))
                    st.rerun()
                
                st.markdown("---")
            
            # Modal de edição
            if 'edit_tratamento_id' in st.session_state:
                with st.expander("✏️ Editando Tratamento", expanded=True):
                    with st.form("editar_tratamento"):
                        codigo = st.text_input("Código", value=st.session_state.edit_trat_codigo)
                        nome = st.text_input("Nome", value=st.session_state.edit_trat_nome)
                        descricao = st.text_area("Descrição", value=st.session_state.edit_trat_descricao)
                        col_a, col_b = st.columns(2)
                        if col_a.form_submit_button("💾 Salvar"):
                            execute_query(
                                "UPDATE tratamentos SET codigo=?, nome=?, descricao=? WHERE id=?",
                                (codigo, nome, descricao, st.session_state.edit_tratamento_id)
                            )
                            del st.session_state.edit_tratamento_id
                            st.rerun()
                        if col_b.form_submit_button("❌ Cancelar"):
                            del st.session_state.edit_tratamento_id
                            st.rerun()
        else:
            st.info("Nenhum tratamento cadastrado.")
    
    with tab2:
        with st.form("novo_tratamento"):
            codigo = st.text_input("Código (ex: T1, T2, C1)")
            nome = st.text_input("Nome do Tratamento*")
            descricao = st.text_area("Descrição")
            if st.form_submit_button("💾 Salvar"):
                if codigo and nome:
                    execute_query(
                        "INSERT INTO tratamentos (projeto_id, codigo, nome, descricao) VALUES (?, ?, ?, ?)",
                        (projeto_id, codigo, nome, descricao)
                    )
                    st.success(f"Tratamento {codigo} cadastrado!")
                    st.rerun()

def tela_parcelas():
    st.title("🧩 Gerenciar Parcelas")
    projetos = query_to_df("SELECT id, titulo FROM projetos ORDER BY titulo")
    if len(projetos) == 0:
        st.warning("Crie um projeto e tratamentos primeiro!")
        return
    projeto_id = st.selectbox("Selecione o Projeto", projetos["id"].values, format_func=lambda x: projetos[projetos["id"]==x]["titulo"].values[0], key="sel_parc_proj")
    st.markdown("---")
    
    st.subheader("⚙️ Gerar Parcelas Automaticamente")
    tratamentos = query_to_df("SELECT * FROM tratamentos WHERE projeto_id = ?", (projeto_id,))
    if len(tratamentos) == 0:
        st.warning("Cadastre os tratamentos primeiro!")
        return
    col1, col2 = st.columns(2)
    with col1:
        num_blocos = st.number_input("Número de Blocos", min_value=1, max_value=20, value=3, key="num_blocos")
    with col2:
        num_repeticoes = st.number_input("Repetições por Bloco", min_value=1, max_value=10, value=1, key="num_rep")
    if st.button("🔨 Gerar Parcelas"):
        execute_query("DELETE FROM parcelas WHERE projeto_id = ?", (projeto_id,))
        count = 0
        for bloco in range(1, num_blocos + 1):
            for rep in range(1, num_repeticoes + 1):
                for _, trat in tratamentos.iterrows():
                    ident = f"B{bloco}R{rep}T{trat['codigo']}"
                    execute_query(
                        "INSERT INTO parcelas (projeto_id, tratamento_id, bloco, repeticao, identificacao) VALUES (?, ?, ?, ?, ?)",
                        (projeto_id, trat["id"], bloco, rep, ident)
                    )
                    count += 1
        st.success(f"{count} parcelas geradas!")
        st.rerun()
    
    st.markdown("---")
    parcelas = query_to_df("""
        SELECT p.id, p.identificacao, t.codigo as tratamento, t.nome as trat_nome, p.bloco, p.repeticao
        FROM parcelas p
        JOIN tratamentos t ON p.tratamento_id = t.id
        WHERE p.projeto_id = ?
        ORDER BY p.bloco, p.repeticao, t.codigo
    """, (projeto_id,))
    
    if len(parcelas) > 0:
        st.subheader(f"📋 Parcelas ({len(parcelas)} total)")
        for _, parc in parcelas.iterrows():
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            col1.write(f"**{parc['identificacao']}**")
            col2.write(f"🧪 {parc['tratamento']} - {parc['trat_nome']}")
            col3.write(f"Bloco {parc['bloco']}")
            if col4.button("🗑️", key=f"del_parc_{parc['id']}"):
                execute_query("DELETE FROM medicoes WHERE parcela_id = ?", (parc['id'],))
                execute_query("DELETE FROM parcelas WHERE id = ?", (parc['id'],))
                st.rerun()
            st.markdown("---")

def tela_variaveis():
    st.title("📏 Gerenciar Variáveis de Resposta")
    tab1, tab2 = st.tabs(["📋 Variáveis", "➕ Nova Variável"])
    
    with tab1:
        variaveis = query_to_df("SELECT * FROM variaveis ORDER BY categoria, nome")
        if len(variaveis) > 0:
            for _, var in variaveis.iterrows():
                col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                col1.write(f"**{var['nome']}** ({var['codigo']})")
                col2.write(f"📏 {var.get('unidade', '—')} | 🏷️ {var.get('categoria', '—')}")
                
                if col3.button("✏️", key=f"edit_var_{var['id']}"):
                    st.session_state.edit_variavel_id = var['id']
                    st.session_state.edit_var_nome = var['nome']
                    st.session_state.edit_var_codigo = var['codigo']
                    st.session_state.edit_var_categoria = var.get('categoria', 'outros')
                    st.session_state.edit_var_unidade = var.get('unidade', '')
                    st.session_state.edit_var_metodo = var.get('metodo', '')
                    st.rerun()
                
                if col4.button("🗑️", key=f"del_var_{var['id']}"):
                    execute_query("DELETE FROM variaveis WHERE id = ?", (var['id'],))
                    st.rerun()
                
                st.markdown("---")
            
            # Modal de edição
            if 'edit_variavel_id' in st.session_state:
                with st.expander("✏️ Editando Variável", expanded=True):
                    with st.form("editar_variavel"):
                        nome = st.text_input("Nome", value=st.session_state.edit_var_nome)
                        codigo = st.text_input("Código", value=st.session_state.edit_var_codigo)
                        categoria = st.selectbox("Categoria", ["fenologia", "produtividade", "qualidade", "sanidade", "nutricao", "solo", "outros"],
                            index=["fenologia", "produtividade", "qualidade", "sanidade", "nutricao", "solo", "outros"].index(st.session_state.edit_var_categoria) if st.session_state.edit_var_categoria in ["fenologia", "produtividade", "qualidade", "sanidade", "nutricao", "solo", "outros"] else 6)
                        unidade = st.text_input("Unidade", value=st.session_state.edit_var_unidade)
                        metodo = st.text_area("Método", value=st.session_state.edit_var_metodo)
                        col_a, col_b = st.columns(2)
                        if col_a.form_submit_button("💾 Salvar"):
                            execute_query(
                                "UPDATE variaveis SET nome=?, codigo=?, categoria=?, unidade=?, metodo=? WHERE id=?",
                                (nome, codigo, categoria, unidade, metodo, st.session_state.edit_variavel_id)
                            )
                            del st.session_state.edit_variavel_id
                            st.rerun()
                        if col_b.form_submit_button("❌ Cancelar"):
                            del st.session_state.edit_variavel_id
                            st.rerun()
        else:
            st.info("Nenhuma variável cadastrada.")
    
    with tab2:
        with st.form("nova_variavel"):
            nome = st.text_input("Nome da Variável* (ex: Altura de Plantas)")
            codigo = st.text_input("Código* (ex: ALT_PLANT)")
            categoria = st.selectbox("Categoria", ["fenologia", "produtividade", "qualidade", "sanidade", "nutricao", "solo", "outros"])
            unidade = st.text_input("Unidade (ex: cm, kg/ha, g, %)")
            metodo = st.text_area("Método de medição")
            if st.form_submit_button("💾 Salvar"):
                if nome and codigo:
                    execute_query(
                        "INSERT INTO variaveis (nome, codigo, categoria, unidade, metodo) VALUES (?, ?, ?, ?, ?)",
                        (nome, codigo, categoria, unidade, metodo)
                    )
                    st.success(f"Variável '{nome}' cadastrada!")
                    st.rerun()

def tela_medicoes():
    st.title("📝 Coleta de Dados")
    projetos = query_to_df("SELECT id, titulo FROM projetos ORDER BY titulo")
    if len(projetos) == 0:
        st.warning("Crie um projeto primeiro!")
        return
    projeto_id = st.selectbox("Selecione o Projeto", projetos["id"].values, format_func=lambda x: projetos[projetos["id"]==x]["titulo"].values[0], key="sel_med_proj")
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["📝 Inserir Dados", "📤 Importar Planilha", "📋 Dados Coletados"])
    
    with tab1:
        parcelas = query_to_df("""
            SELECT p.id, p.identificacao, t.codigo as tratamento
            FROM parcelas p
            JOIN tratamentos t ON p.tratamento_id = t.id
            WHERE p.projeto_id = ?
            ORDER BY p.identificacao
        """, (projeto_id,))
        variaveis = query_to_df("SELECT * FROM variaveis ORDER BY nome")
        if len(parcelas) == 0:
            st.warning("Gere as parcelas primeiro!")
            return
        if len(variaveis) == 0:
            st.warning("Cadastre variáveis primeiro!")
            return
        with st.form("inserir_medicao"):
            parcela = st.selectbox("Parcela", parcelas["id"].values, format_func=lambda x: parcelas[parcelas["id"]==x]["identificacao"].values[0])
            variavel = st.selectbox("Variável", variaveis["id"].values, format_func=lambda x: f"{variaveis[variaveis['id']==x]['nome'].values[0]} ({variaveis[variaveis['id']==x]['unidade'].values[0]})")
            valor = st.number_input("Valor medido", format="%.4f")
            data_med = st.date_input("Data da medição", datetime.now())
            estadio = st.text_input("Estádio fenológico (ex: R2, V8)")
            if st.form_submit_button("💾 Salvar Medição"):
                execute_query(
                    "INSERT INTO medicoes (parcela_id, variavel_id, valor, data_medicao, estadio_fenologico) VALUES (?, ?, ?, ?, ?)",
                    (parcela, variavel, valor, data_med, estadio)
                )
                st.success("Medição salva!")
                st.rerun()
    
    with tab2:
        st.markdown("**Formato esperado da planilha (CSV ou Excel):**")
        st.code("parcela,variavel_codigo,valor,data,estadio\nB1R1T1,ALT_PLANT,85.2,2025-12-01,R2\nB1R1T1,PROD,4520,2025-12-01,R2")
        arquivo = st.file_uploader("Escolha o arquivo", type=["csv", "xlsx"])
        if arquivo is not None:
            try:
                if arquivo.name.endswith(".csv"):
                    df = pd.read_csv(arquivo)
                else:
                    df = pd.read_excel(arquivo)
                st.write("**Preview dos dados:**")
                st.dataframe(df.head())
                if st.button("📥 Importar Dados"):
                    count = 0
                    erros = 0
                    for _, row in df.iterrows():
                        try:
                            parc = query_to_df("SELECT id FROM parcelas WHERE projeto_id = ? AND identificacao = ?", (projeto_id, row["parcela"]))
                            if len(parc) == 0:
                                erros += 1
                                continue
                            var = query_to_df("SELECT id FROM variaveis WHERE codigo = ?", (row["variavel_codigo"],))
                            if len(var) == 0:
                                erros += 1
                                continue
                            execute_query(
                                "INSERT INTO medicoes (parcela_id, variavel_id, valor, data_medicao, estadio_fenologico) VALUES (?, ?, ?, ?, ?)",
                                (parc.iloc[0]["id"], var.iloc[0]["id"], row["valor"], row.get("data", datetime.now()), row.get("estadio", ""))
                            )
                            count += 1
                        except:
                            erros += 1
                    st.success(f"✅ {count} medições importadas! ❌ {erros} erros.")
                    st.rerun()
            except Exception as e:
                st.error(f"Erro ao ler arquivo: {e}")
    
    with tab3:
        st.subheader("📋 Dados Coletados")
        dados = query_to_df("""
            SELECT m.id, p.identificacao as parcela, t.codigo as tratamento, v.nome as variavel, v.unidade, m.valor, m.data_medicao, m.estadio_fenologico
            FROM medicoes m
            JOIN parcelas p ON m.parcela_id = p.id
            JOIN tratamentos t ON p.tratamento_id = t.id
            JOIN variaveis v ON m.variavel_id = v.id
            WHERE p.projeto_id = ?
            ORDER BY m.data_medicao DESC, p.identificacao
        """, (projeto_id,))
        
        if len(dados) > 0:
            for _, med in dados.iterrows():
                col1, col2, col3, col4, col5 = st.columns([2, 2, 1.5, 1, 1])
                col1.write(f"**{med['parcela']}**")
                col2.write(f"📏 {med['variavel']} ({med['unidade']})")
                col3.write(f"**{med['valor']}**")
                col4.write(f"📅 {med['data_medicao']}")
                if col5.button("🗑️", key=f"del_med_{med['id']}"):
                    execute_query("DELETE FROM medicoes WHERE id = ?", (med['id'],))
                    st.rerun()
                st.markdown("---")
        else:
            st.info("Nenhum dado coletado ainda.")

def tela_analises():
    st.title("📊 Análises Estatísticas")
    projetos = query_to_df("SELECT id, titulo FROM projetos ORDER BY titulo")
    if len(projetos) == 0:
        st.warning("Crie um projeto primeiro!")
        return
    projeto_id = st.selectbox("Selecione o Projeto", projetos["id"].values, format_func=lambda x: projetos[projetos["id"]==x]["titulo"].values[0], key="sel_analise_proj")
    st.markdown("---")
    variaveis = query_to_df("""
        SELECT DISTINCT v.id, v.nome, v.codigo, v.unidade
        FROM medicoes m
        JOIN variaveis v ON m.variavel_id = v.id
        JOIN parcelas p ON m.parcela_id = p.id
        WHERE p.projeto_id = ?
    """, (projeto_id,))
    if len(variaveis) == 0:
        st.warning("Nenhum dado coletado neste projeto ainda.")
        return
    variavel_id = st.selectbox("Selecione a variável para análise", variaveis["id"].values, format_func=lambda x: f"{variaveis[variaveis['id']==x]['nome'].values[0]} ({variaveis[variaveis['id']==x]['unidade'].values[0]})", key="sel_var_analise")
    df_dados = query_to_df("""
        SELECT m.valor, m.data_medicao, m.estadio_fenologico, t.codigo as tratamento, t.nome as trat_nome, p.bloco, p.identificacao
        FROM medicoes m
        JOIN parcelas p ON m.parcela_id = p.id
        JOIN tratamentos t ON p.tratamento_id = t.id
        WHERE p.projeto_id = ? AND m.variavel_id = ?
    """, (projeto_id, variavel_id))
    if len(df_dados) == 0:
        st.warning("Nenhum dado para esta variável.")
        return
    var_nome = variaveis[variaveis["id"]==variavel_id]["nome"].values[0]
    var_unidade = variaveis[variaveis["id"]==variavel_id]["unidade"].values[0]
    st.subheader(f"📊 Estatística Descritiva - {var_nome} ({var_unidade})")
    descritiva = df_dados.groupby("tratamento")["valor"].agg(["mean", "std", "min", "max", "count"])
    descritiva["cv"] = (descritiva["std"] / descritiva["mean"]) * 100
    descritiva.columns = ["Média", "Desvio Padrão", "Mínimo", "Máximo", "N", "CV%"]
    descritiva = descritiva.round(2)
    st.dataframe(descritiva, use_container_width=True)
    st.markdown("---")
    st.subheader("📈 Gráfico de Barras")
    col1, col2 = st.columns([3, 1])
    with col2:
        mostrar_erro = st.checkbox("Mostrar barra de erro", value=True, key="mostrar_erro")
        tipo_erro = st.radio("Tipo de erro", ["dp", "ep", "ic95"], format_func=lambda x: {"dp": "Desvio Padrão", "ep": "Erro Padrão", "ic95": "IC 95%"}[x], key="tipo_erro")
    with col1:
        medias = df_dados.groupby("tratamento")["valor"].agg(["mean", "std", "count"])
        medias["se"] = medias["std"] / np.sqrt(medias["count"])
        medias["ci"] = medias["se"] * 1.96
        medias = medias.reset_index()
        erro_col = {"dp": "std", "ep": "se", "ic95": "ci"}[tipo_erro]
        fig = px.bar(medias, x="tratamento", y="mean", error_y=medias[erro_col] if mostrar_erro else None,
                     title=f"{var_nome} por Tratamento",
                     labels={"tratamento": "Tratamento", "mean": f"{var_nome} ({var_unidade})"},
                     color="tratamento", color_discrete_sequence=px.colors.qualitative.Set2)
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("---")
    st.subheader("📦 Boxplot")
    fig_box = px.box(df_dados, x="tratamento", y="valor", title=f"Distribuição - {var_nome}",
                     labels={"tratamento": "Tratamento", "valor": f"{var_nome} ({var_unidade})"}, color="tratamento")
    st.plotly_chart(fig_box, use_container_width=True)
    st.markdown("---")
    st.subheader("🔬 Análise de Variância (ANOVA)")
    if st.button("▶ Executar ANOVA"):
        with st.spinner("Executando análise..."):
            try:
                residuos = df_dados.groupby("tratamento")["valor"].apply(lambda x: x - x.mean())
                shapiro_stat, shapiro_p = stats.shapiro(residuos)
                st.write("**1. Teste de Normalidade (Shapiro-Wilk)**")
                st.write(f"Estatística W: {shapiro_stat:.4f}")
                st.write(f"p-valor: {shapiro_p:.4f}")
                if shapiro_p > 0.05:
                    st.success("✅ Dados seguem distribuição normal (p > 0.05)")
                else:
                    st.warning("⚠️ Dados NÃO seguem distribuição normal (p < 0.05)")
                from scipy.stats import f_oneway
                grupos = [group["valor"].values for name, group in df_dados.groupby("tratamento")]
                f_stat, f_p = f_oneway(*grupos)
                st.write("**2. ANOVA**")
                st.write(f"Estatística F: {f_stat:.4f}")
                st.write(f"p-valor: {f_p:.6f}")
                if f_p < 0.05:
                    st.success("✅ Diferença significativa entre tratamentos (p < 0.05)")
                    st.write("**3. Teste de Tukey (Comparação Múltipla)**")
                    tukey = pairwise_tukeyhsd(df_dados["valor"], df_dados["tratamento"], alpha=0.05)
                    tukey_df = pd.DataFrame(data=tukey.summary().data[1:], columns=tukey.summary().data[0])
                    st.dataframe(tukey_df, use_container_width=True)
                    st.write("**4. Letras de Significância**")
                    medias = df_dados.groupby("tratamento")["valor"].mean().sort_values(ascending=False)
                    letras = {}
                    letra_atual = 'a'
                    for i, (trat, media) in enumerate(medias.items()):
                        letras[trat] = letra_atual
                        if i < len(medias) - 1:
                            next_trat = medias.index[i + 1]
                            for row in tukey.summary().data[1:]:
                                if (row[0] == trat and row[1] == next_trat) or (row[0] == next_trat and row[1] == trat):
                                    if row[4] < 0.05:
                                        letra_atual = chr(ord(letra_atual) + 1)
                                    break
                    letras_df = pd.DataFrame(list(letras.items()), columns=["Tratamento", "Letra"])
                    letras_df["Média"] = medias.values
                    st.dataframe(letras_df, use_container_width=True)
                    fig_tukey = px.bar(letras_df, x="Tratamento", y="Média", text="Letra",
                                       title=f"{var_nome} - Médias com Letras de Tukey", color="Tratamento")
                    fig_tukey.update_traces(textposition="outside")
                    st.plotly_chart(fig_tukey, use_container_width=True)
                else:
                    st.info("ℹ️ Nenhuma diferença significativa entre tratamentos (p > 0.05)")
            except Exception as e:
                st.error(f"Erro na análise: {e}")
    st.markdown("---")
    st.subheader("🔗 Matriz de Correlação")
    if st.button("▶ Gerar Matriz de Correlação"):
        vars_corr = query_to_df("""
            SELECT DISTINCT v.id, v.nome, v.codigo
            FROM medicoes m
            JOIN variaveis v ON m.variavel_id = v.id
            JOIN parcelas p ON m.parcela_id = p.id
            WHERE p.projeto_id = ?
        """, (projeto_id,))
        if len(vars_corr) >= 2:
            dados_corr = None
            for _, var in vars_corr.iterrows():
                var_data = query_to_df("""
                    SELECT p.identificacao, m.valor
                    FROM medicoes m
                    JOIN parcelas p ON m.parcela_id = p.id
                    WHERE p.projeto_id = ? AND m.variavel_id = ?
                """, (projeto_id, var["id"]))
                if len(var_data) > 0:
                    var_data = var_data.rename(columns={"valor": var["codigo"]})
                    if dados_corr is None:
                        dados_corr = var_data[["identificacao", var["codigo"]]]
                    else:
                        dados_corr = dados_corr.merge(var_data[["identificacao", var["codigo"]]], on="identificacao", how="outer")
            if dados_corr is not None:
                corr_matrix = dados_corr.select_dtypes(include=[np.number]).corr()
                fig_corr = px.imshow(corr_matrix, text_auto=True, color_continuous_scale="RdBu_r",
                                     title="Matriz de Correlação entre Variáveis")
                st.plotly_chart(fig_corr, use_container_width=True)
        else:
            st.info("Precisa de pelo menos 2 variáveis com dados para correlação.")

def tela_relatorios():
    st.title("📋 Gerar Relatórios")
    projetos = query_to_df("SELECT id, titulo FROM projetos ORDER BY titulo")
    if len(projetos) == 0:
        st.warning("Crie um projeto primeiro!")
        return
    projeto_id = st.selectbox("Selecione o Projeto", projetos["id"].values, format_func=lambda x: projetos[projetos["id"]==x]["titulo"].values[0], key="sel_rel_proj")
    
    # Buscar projeto e verificar se existe
    df_proj = query_to_df("SELECT * FROM projetos WHERE id = ?", (projeto_id,))
    if len(df_proj) == 0:
        st.error("Projeto não encontrado!")
        return
    projeto = df_proj.iloc[0]
    
    # Buscar empresa - tratar caso não exista
    df_emp = query_to_df("SELECT * FROM empresas WHERE id = ?", (projeto["empresa_id"],))
    if len(df_emp) > 0:
        empresa = df_emp.iloc[0]
        empresa_nome = empresa["nome"]
    else:
        empresa_nome = "** Empresa não encontrada **"
    
    st.markdown("---")
    st.subheader("📄 Relatório do Projeto")
    col1, col2 = st.columns(2)
    with col1:
        incluir_graficos = st.checkbox("Incluir gráficos", value=True, key="incluir_graficos")
        incluir_anova = st.checkbox("Incluir ANOVA", value=True, key="incluir_anova")
    with col2:
        incluir_dados_brutos = st.checkbox("Incluir dados brutos", value=False, key="incluir_dados")
        incluir_recomendacoes = st.checkbox("Incluir campo de recomendações", value=True, key="incluir_recomendacoes")
    recomendacoes = ""
    if incluir_recomendacoes:
        recomendacoes = st.text_area("Recomendações técnicas para o relatório", key="recomendacoes")
    if st.button("📥 Gerar Relatório PDF", use_container_width=True):
        with st.spinner("Gerando relatório..."):
            try:
                buffer = io.BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=A4)
                styles = getSampleStyleSheet()
                elementos = []
                elementos.append(Paragraph(f"Relatório Técnico: {projeto['titulo']}", styles['Title']))
                elementos.append(Spacer(1, 12))
                elementos.append(Paragraph(f"<b>Empresa:</b> {empresa_nome}", styles['Normal']))
                elementos.append(Paragraph(f"<b>Cultura:</b> {projeto.get('cultura', '—')} | <b>Safra:</b> {projeto.get('safra', '—')}", styles['Normal']))
                elementos.append(Paragraph(f"<b>Local:</b> {projeto.get('local', '—')} - {projeto.get('municipio', '—')}/{projeto.get('estado', '—')}", styles['Normal']))
                elementos.append(Paragraph(f"<b>Responsável:</b> {projeto.get('responsavel', '—')}", styles['Normal']))
                elementos.append(Spacer(1, 20))
                if projeto.get('objetivo'):
                    elementos.append(Paragraph("<b>Objetivo:</b>", styles['Heading2']))
                    elementos.append(Paragraph(projeto['objetivo'], styles['Normal']))
                    elementos.append(Spacer(1, 12))
                tratamentos = query_to_df("SELECT * FROM tratamentos WHERE projeto_id = ?", (projeto_id,))
                if len(tratamentos) > 0:
                    elementos.append(Paragraph("<b>Tratamentos Avaliados:</b>", styles['Heading2']))
                    for _, t in tratamentos.iterrows():
                        elementos.append(Paragraph(f"• <b>{t['codigo']}:</b> {t['nome']}", styles['Normal']))
                    elementos.append(Spacer(1, 12))
                variaveis = query_to_df("""
                    SELECT DISTINCT v.nome, v.codigo, v.unidade
                    FROM medicoes m
                    JOIN variaveis v ON m.variavel_id = v.id
                    JOIN parcelas p ON m.parcela_id = p.id
                    WHERE p.projeto_id = ?
                """, (projeto_id,))
                if len(variaveis) > 0:
                    elementos.append(Paragraph("<b>Resultados:</b>", styles['Heading2']))
                    for _, var in variaveis.iterrows():
                        elementos.append(Paragraph(f"<b>{var['nome']} ({var['unidade']}):</b>", styles['Heading3']))
                        df_var = query_to_df("""
                            SELECT t.codigo, m.valor
                            FROM medicoes m
                            JOIN parcelas p ON m.parcela_id = p.id
                            JOIN tratamentos t ON p.tratamento_id = t.id
                            WHERE p.projeto_id = ? AND m.variavel_id = (SELECT id FROM variaveis WHERE codigo = ?)
                        """, (projeto_id, var['codigo']))
                        if len(df_var) > 0:
                            medias = df_var.groupby("codigo")["valor"].agg(["mean", "std"]).round(2)
                            medias.columns = ["Média", "DP"]
                            dados_tabela = [["Tratamento", "Média", "DP"]]
                            for trat, row in medias.iterrows():
                                dados_tabela.append([trat, str(row["Média"]), str(row["DP"])])
                            tabela = Table(dados_tabela)
                            tabela.setStyle(TableStyle([
                                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4CAF50")),
                                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                ('FONTSIZE', (0, 0), (-1, -1), 10),
                                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                                ('GRID', (0, 0), (-1, -1), 1, colors.black)
                            ]))
                            elementos.append(tabela)
                            elementos.append(Spacer(1, 12))
                if recomendacoes:
                    elementos.append(Paragraph("<b>Recomendações Técnicas:</b>", styles['Heading2']))
                    elementos.append(Paragraph(recomendacoes, styles['Normal']))
                doc.build(elementos)
                buffer.seek(0)
                st.download_button(
                    label="📥 Baixar PDF",
                    data=buffer,
                    file_name=f"relatorio_{projeto['titulo'][:30]}.pdf",
                    mime="application/pdf"
                )
                st.success("✅ Relatório gerado com sucesso!")
            except Exception as e:
                st.error(f"Erro ao gerar relatório: {e}")
    st.markdown("---")
    st.subheader("📤 Exportar Dados Brutos")
    if st.button("📥 Exportar CSV"):
        dados = query_to_df("""
            SELECT p.identificacao as parcela, t.codigo as tratamento, t.nome as trat_nome,
                   p.bloco, v.nome as variavel, v.unidade, m.valor, m.data_medicao, m.estadio_fenologico
            FROM medicoes m
            JOIN parcelas p ON m.parcela_id = p.id
            JOIN tratamentos t ON p.tratamento_id = t.id
            JOIN variaveis v ON m.variavel_id = v.id
            WHERE p.projeto_id = ?
            ORDER BY p.identificacao, v.nome
        """, (projeto_id,))
        csv = dados.to_csv(index=False).encode("utf-8")
        st.download_button(label="📥 Baixar CSV", data=csv, file_name=f"dados_{projeto['titulo'][:30]}.csv", mime="text/csv")

def tela_compartilhar():
    st.title("👥 Compartilhar Projetos")
    projetos = query_to_df("SELECT id, titulo FROM projetos ORDER BY titulo")
    if len(projetos) == 0:
        st.warning("Crie um projeto primeiro!")
        return
    projeto_id = st.selectbox("Selecione o Projeto", projetos["id"].values, format_func=lambda x: projetos[projetos["id"]==x]["titulo"].values[0], key="sel_comp_proj")
    st.markdown("---")
    st.subheader("👥 Usuários com Acesso")
    permissoes = query_to_df("""
        SELECT u.nome, u.email, p.nivel, p.id as permissao_id
        FROM permissoes p
        JOIN usuarios u ON p.usuario_id = u.id
        WHERE p.projeto_id = ?
    """, (projeto_id,))
    if len(permissoes) > 0:
        for _, perm in permissoes.iterrows():
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            col1.write(perm["nome"])
            col2.write(perm["email"])
            col3.write(f"🔑 {perm['nivel']}")
            if col4.button("🗑️", key=f"rem_perm_{perm['permissao_id']}"):
                execute_query("DELETE FROM permissoes WHERE id = ?", (perm["permissao_id"],))
                st.rerun()
            st.markdown("---")
    else:
        st.info("Nenhum compartilhamento ainda.")
    st.markdown("---")
    st.subheader("➕ Convidar Usuário")
    usuarios = query_to_df("SELECT id, nome, email FROM usuarios WHERE id != ?", (st.session_state.usuario_id,))
    if len(usuarios) > 0:
        usuario_id = st.selectbox("Selecione o usuário", usuarios["id"].values, format_func=lambda x: f"{usuarios[usuarios['id']==x]['nome'].values[0]} ({usuarios[usuarios['id']==x]['email'].values[0]})")
        nivel = st.selectbox("Nível de permissão", ["visualizador", "editor", "visualizador_restrito"])
        if st.button("🔗 Compartilhar"):
            existente = query_to_df("SELECT id FROM permissoes WHERE projeto_id = ? AND usuario_id = ?", (projeto_id, usuario_id))
            if len(existente) == 0:
                execute_query("INSERT INTO permissoes (projeto_id, usuario_id, nivel) VALUES (?, ?, ?)", (projeto_id, usuario_id, nivel))
                st.success("Acesso compartilhado!")
                st.rerun()
            else:
                st.warning("Usuário já tem acesso a este projeto.")
    else:
        st.info("Nenhum outro usuário cadastrado para compartilhar.")

def main():
    if st.session_state.usuario_id is None:
        tela_login()
        return
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/000000/agriculture.png", width=80)
        st.title("🌱 SIGPA")
        st.markdown(f"**👤 {st.session_state.usuario_nome}**")
        st.markdown(f"*{st.session_state.usuario_tipo}*")
        st.markdown("---")
        menu = st.radio("Navegação", [
            "📊 Dashboard", "🏢 Empresas", "📋 Projetos", "🧪 Tratamentos",
            "🧩 Parcelas", "📏 Variáveis", "📝 Coleta de Dados",
            "📊 Análises", "📋 Relatórios", "👥 Compartilhar"
        ])
        st.markdown("---")
        if st.button("🚪 Sair", use_container_width=True):
            fazer_logout()
            st.rerun()
    paginas = {
        "📊 Dashboard": tela_dashboard, "🏢 Empresas": tela_empresas,
        "📋 Projetos": tela_projetos, "🧪 Tratamentos": tela_tratamentos,
        "🧩 Parcelas": tela_parcelas, "📏 Variáveis": tela_variaveis,
        "📝 Coleta de Dados": tela_medicoes, "📊 Análises": tela_analises,
        "📋 Relatórios": tela_relatorios, "👥 Compartilhar": tela_compartilhar
    }
    if menu in paginas:
        paginas[menu]()

if __name__ == "__main__":
    main()