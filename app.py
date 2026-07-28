import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from scipy import stats
from statsmodels.formula.api import ols
from statsmodels.stats.anova import anova_lm
from statsmodels.stats.multicomp import pairwise_tukeyhsd
import plotly.express as px
import plotly.graph_objects as go
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
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
                if col3.button("✏️ Editar", key=f"edit_emp_{emp['id']}"):
                    st.session_state.edit_empresa_id = emp['id']
                    st.session_state.edit_empresa_nome = emp['nome']
                    st.session_state.edit_empresa_cnpj = emp.get('cnpj', '')
                    st.session_state.edit_empresa_contato = emp.get('contato', '')
                    st.session_state.edit_empresa_email = emp.get('email', '')
                    st.session_state.edit_empresa_telefone = emp.get('telefone', '')
                    st.rerun()
                if col4.button("🗑️", key=f"del_emp_{emp['id']}"):
                    execute_query("DELETE FROM empresas WHERE id = ?", (emp['id'],))
                    st.rerun()
                st.markdown("---")
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
        st.markdown("**Formato esperado da planilha (CSV ou Excel):**")
        st.code("parcela,variavel_codigo,valor,data,estadio\nB1R1TT1,PMS,227.6,2026-06-28,R8\nB1R1TT1,PMS,228,2026-06-28,R8")
        
        # Mostrar lista de parcelas e variáveis disponíveis para diagnóstico
        with st.expander("🔍 Ver parcelas e variáveis disponíveis no sistema"):
            col_p, col_v = st.columns(2)
            with col_p:
                parcelas_disp = query_to_df("""
                    SELECT identificacao FROM parcelas WHERE projeto_id = ? ORDER BY identificacao
                """, (projeto_id,))
                if len(parcelas_disp) > 0:
                    st.write("**Parcelas cadastradas:**")
                    st.write(", ".join(parcelas_disp["identificacao"].tolist()))
                else:
                    st.warning("Nenhuma parcela cadastrada neste projeto!")
            
            with col_v:
                variaveis_disp = query_to_df("SELECT codigo, nome FROM variaveis ORDER BY codigo")
                if len(variaveis_disp) > 0:
                    st.write("**Variáveis cadastradas:**")
                    for _, v in variaveis_disp.iterrows():
                        st.write(f"• `{v['codigo']}` - {v['nome']}")
                else:
                    st.warning("Nenhuma variável cadastrada no sistema!")
        
        col_modo, _ = st.columns([1, 3])
        with col_modo:
            modo_import = st.radio("Modo de importação", [
                "📥 Adicionar aos existentes",
                "🔄 Substituir tudo (apaga dados atuais e importa)"
            ], key="modo_import_v2")
        
        arquivo = st.file_uploader("Escolha o arquivo", type=["csv", "xlsx"], key="file_uploader_med_v2")
        
        if arquivo is not None:
            try:
                if arquivo.name.endswith(".csv"):
                    df = pd.read_csv(arquivo)
                else:
                    df = pd.read_excel(arquivo)
                
                # Normalizar nomes das colunas
                df.columns = [c.strip().lower() for c in df.columns]
                
                st.write("**Preview dos dados:**")
                st.dataframe(df.head(10))
                st.write(f"**Total de linhas:** {len(df)}")
                
                # Validar colunas necessárias
                colunas_necessarias = ['parcela', 'variavel_codigo', 'valor']
                colunas_presentes = [c for c in colunas_necessarias if c in df.columns]
                colunas_faltando = [c for c in colunas_necessarias if c not in df.columns]
                
                if colunas_faltando:
                    st.error(f"❌ Colunas obrigatórias faltando: {', '.join(colunas_faltando)}")
                    st.write(f"Colunas encontradas no arquivo: {', '.join(df.columns)}")
                else:
                    # Diagnóstico prévio
                    parcelas_csv = df['parcela'].unique()
                    vars_csv = df['variavel_codigo'].unique()
                    
                    parcelas_bd = set(query_to_df("SELECT identificacao FROM parcelas WHERE projeto_id = ?", (projeto_id,))["identificacao"].tolist())
                    vars_bd = set(query_to_df("SELECT codigo FROM variaveis")["codigo"].tolist())
                    
                    parcelas_ok = [p for p in parcelas_csv if p.strip() in parcelas_bd]
                    parcelas_nok = [p for p in parcelas_csv if p.strip() not in parcelas_bd]
                    vars_ok = [v for v in vars_csv if v.strip() in vars_bd]
                    vars_nok = [v for v in vars_csv if v.strip() not in vars_bd]
                    
                    st.markdown("---")
                    st.subheader("🔍 Diagnóstico antes de importar")
                    
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        st.write(f"**Parcelas no arquivo:** {len(parcelas_csv)}")
                        if parcelas_nok:
                            st.error(f"❌ {len(parcelas_nok)} parcelas NÃO encontradas no sistema:")
                            st.code(", ".join(parcelas_nok))
                        else:
                            st.success(f"✅ Todas as {len(parcelas_csv)} parcelas existem no sistema")
                    
                    with col_d2:
                        st.write(f"**Variáveis no arquivo:** {len(vars_csv)}")
                        if vars_nok:
                            st.error(f"❌ {len(vars_nok)} variáveis NÃO encontradas no sistema:")
                            st.code(", ".join(vars_nok))
                            st.info("💡 Cadastre as variáveis faltando em **📏 Variáveis → ➕ Nova Variável**")
                        else:
                            st.success(f"✅ Todas as {len(vars_csv)} variáveis existem no sistema")
                    
                    if parcelas_nok or vars_nok:
                        st.warning("⚠️ Corrija os problemas acima antes de importar.")
                    else:
                        st.success("✅ Diagnóstico OK! Pronto para importar.")
                        
                        if st.button("📥 Importar Dados", type="primary"):
                            substituir = "Substituir" in modo_import
                            
                            if substituir:
                                # Caixa de confirmação com checkbox
                                confirmar = st.checkbox("✅ Sim, quero substituir todos os dados deste projeto", 
                                                       key="confirm_substituir_v2")
                                if not confirmar:
                                    st.info("Marque a caixa de confirmação acima e clique novamente em **Importar Dados**.")
                                    st.stop()
                            
                            count = 0
                            erros = 0
                            erros_detalhes = []
                            
                            # Se for substituir, apaga os dados ANTES de importar
                            if substituir:
                                with st.spinner("Apagando dados antigos..."):
                                    execute_query("""
                                        DELETE FROM medicoes WHERE parcela_id IN 
                                        (SELECT id FROM parcelas WHERE projeto_id = ?)
                                    """, (projeto_id,))
                                st.info("✅ Dados antigos removidos. Importando novos...")
                            
                            # Importar linha por linha
                            with st.spinner(f"Importando {len(df)} registros..."):
                                progresso = st.progress(0)
                                
                                for idx, (_, row) in enumerate(df.iterrows()):
                                    try:
                                        parcela_id = row["parcela"].strip()
                                        var_cod = row["variavel_codigo"].strip()
                                        valor = float(row["valor"])
                                        
                                        # Buscar parcela
                                        parc = query_to_df(
                                            "SELECT id FROM parcelas WHERE projeto_id = ? AND identificacao = ?",
                                            (projeto_id, parcela_id)
                                        )
                                        if len(parc) == 0:
                                            erros += 1
                                            erros_detalhes.append(f"Linha {idx+2}: Parcela '{parcela_id}' não encontrada")
                                            progresso.progress((idx + 1) / len(df))
                                            continue
                                        
                                        # Buscar variável
                                        var = query_to_df(
                                            "SELECT id FROM variaveis WHERE codigo = ?",
                                            (var_cod,)
                                        )
                                        if len(var) == 0:
                                            erros += 1
                                            erros_detalhes.append(f"Linha {idx+2}: Variável '{var_cod}' não encontrada")
                                            progresso.progress((idx + 1) / len(df))
                                            continue
                                        
                                        # Data
                                        data_val = row.get("data", "")
                                        if pd.isna(data_val) or str(data_val).strip() == "":
                                            data_val = datetime.now().strftime("%Y-%m-%d")
                                        else:
                                            data_val = str(data_val).strip()
                                        
                                        # Estádio
                                        estadio_val = row.get("estadio", "")
                                        if pd.isna(estadio_val):
                                            estadio_val = ""
                                        else:
                                            estadio_val = str(estadio_val).strip()
                                        
                                        # Inserir
                                        execute_query(
                                            """INSERT INTO medicoes 
                                               (parcela_id, variavel_id, valor, data_medicao, estadio_fenologico) 
                                               VALUES (?, ?, ?, ?, ?)""",
                                            (parc.iloc[0]["id"], var.iloc[0]["id"], valor, data_val, estadio_val)
                                        )
                                        count += 1
                                        
                                    except Exception as e:
                                        erros += 1
                                        erros_detalhes.append(f"Linha {idx+2}: {str(e)[:100]}")
                                    
                                    progresso.progress((idx + 1) / len(df))
                            
                            # Resultado final
                            st.markdown("---")
                            if substituir:
                                st.success(f"✅ **Dados substituídos com sucesso!**")
                            else:
                                st.success(f"✅ **Importação concluída!**")
                            
                            st.write(f"📥 **{count}** registros importados com sucesso")
                            if erros > 0:
                                st.warning(f"❌ **{erros}** erros")
                                with st.expander("📋 Ver detalhes dos erros"):
                                    for erro in erros_detalhes[:20]:
                                        st.write(f"• {erro}")
                                    if len(erros_detalhes) > 20:
                                        st.write(f"... e mais {len(erros_detalhes) - 20} erros")
                            
                            if count > 0:
                                st.rerun()
            
            except Exception as e:
                st.error(f"❌ Erro ao ler arquivo: {e}")
                import traceback
                st.error(traceback.format_exc())

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
        st.code("parcela,variavel_codigo,valor,data,estadio\nB1R1TT1,PMS,227.6,2026-06-28,R8\nB1R1TT1,PMS,228,2026-06-28,R8")
        
        with st.expander("🔍 Ver parcelas e variáveis disponíveis no sistema"):
            col_p, col_v = st.columns(2)
            with col_p:
                parcelas_disp = query_to_df("""
                    SELECT identificacao FROM parcelas WHERE projeto_id = ? ORDER BY identificacao
                """, (projeto_id,))
                if len(parcelas_disp) > 0:
                    st.write("**Parcelas cadastradas:**")
                    st.write(", ".join(parcelas_disp["identificacao"].tolist()))
                else:
                    st.warning("Nenhuma parcela cadastrada neste projeto!")
            
            with col_v:
                variaveis_disp = query_to_df("SELECT codigo, nome FROM variaveis ORDER BY codigo")
                if len(variaveis_disp) > 0:
                    st.write("**Variáveis cadastradas:**")
                    for _, v in variaveis_disp.iterrows():
                        st.write(f"• `{v['codigo']}` - {v['nome']}")
                else:
                    st.warning("Nenhuma variável cadastrada no sistema!")
        
        col_modo, _ = st.columns([1, 3])
        with col_modo:
            modo_import = st.radio("Modo de importação", [
                "📥 Adicionar aos existentes",
                "🔄 Substituir tudo (apaga dados atuais e importa)"
            ], key="modo_import_v2")
        
        arquivo = st.file_uploader("Escolha o arquivo", type=["csv", "xlsx"], key="file_uploader_med_v2")
        
        if arquivo is not None:
            try:
                if arquivo.name.endswith(".csv"):
                    df = pd.read_csv(arquivo)
                else:
                    df = pd.read_excel(arquivo)
                
                df.columns = [c.strip().lower() for c in df.columns]
                
                st.write("**Preview dos dados:**")
                st.dataframe(df.head(10))
                st.write(f"**Total de linhas:** {len(df)}")
                
                colunas_necessarias = ['parcela', 'variavel_codigo', 'valor']
                colunas_presentes = [c for c in colunas_necessarias if c in df.columns]
                colunas_faltando = [c for c in colunas_necessarias if c not in df.columns]
                
                if colunas_faltando:
                    st.error(f"❌ Colunas obrigatórias faltando: {', '.join(colunas_faltando)}")
                    st.write(f"Colunas encontradas no arquivo: {', '.join(df.columns)}")
                else:
                    parcelas_csv = df['parcela'].unique()
                    vars_csv = df['variavel_codigo'].unique()
                    
                    parcelas_bd = set(query_to_df("SELECT identificacao FROM parcelas WHERE projeto_id = ?", (projeto_id,))["identificacao"].tolist())
                    vars_bd = set(query_to_df("SELECT codigo FROM variaveis")["codigo"].tolist())
                    
                    parcelas_ok = [p for p in parcelas_csv if p.strip() in parcelas_bd]
                    parcelas_nok = [p for p in parcelas_csv if p.strip() not in parcelas_bd]
                    vars_ok = [v for v in vars_csv if v.strip() in vars_bd]
                    vars_nok = [v for v in vars_csv if v.strip() not in vars_bd]
                    
                    st.markdown("---")
                    st.subheader("🔍 Diagnóstico antes de importar")
                    
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        st.write(f"**Parcelas no arquivo:** {len(parcelas_csv)}")
                        if parcelas_nok:
                            st.error(f"❌ {len(parcelas_nok)} parcelas NÃO encontradas no sistema:")
                            st.code(", ".join(parcelas_nok))
                        else:
                            st.success(f"✅ Todas as {len(parcelas_csv)} parcelas existem no sistema")
                    
                    with col_d2:
                        st.write(f"**Variáveis no arquivo:** {len(vars_csv)}")
                        if vars_nok:
                            st.error(f"❌ {len(vars_nok)} variáveis NÃO encontradas no sistema:")
                            st.code(", ".join(vars_nok))
                            st.info("💡 Cadastre as variáveis faltando em **📏 Variáveis → ➕ Nova Variável**")
                        else:
                            st.success(f"✅ Todas as {len(vars_csv)} variáveis existem no sistema")
                    
                    if parcelas_nok or vars_nok:
                        st.warning("⚠️ Corrija os problemas acima antes de importar.")
                    else:
                        st.success("✅ Diagnóstico OK! Pronto para importar.")
                        
                        if st.button("📥 Importar Dados", type="primary"):
                            substituir = "Substituir" in modo_import
                            
                            if substituir:
                                confirmar = st.checkbox("✅ Sim, quero substituir todos os dados deste projeto", key="confirm_substituir_v2")
                                if not confirmar:
                                    st.info("Marque a caixa de confirmação acima e clique novamente em **Importar Dados**.")
                                    st.stop()
                            
                            count = 0
                            erros = 0
                            erros_detalhes = []
                            
                            if substituir:
                                with st.spinner("Apagando dados antigos..."):
                                    execute_query("""
                                        DELETE FROM medicoes WHERE parcela_id IN 
                                        (SELECT id FROM parcelas WHERE projeto_id = ?)
                                    """, (projeto_id,))
                                st.info("✅ Dados antigos removidos. Importando novos...")
                            
                            with st.spinner(f"Importando {len(df)} registros..."):
                                progresso = st.progress(0)
                                
                                for idx, (_, row) in enumerate(df.iterrows()):
                                    try:
                                        parcela_id = str(row["parcela"]).strip()
                                        var_cod = str(row["variavel_codigo"]).strip()
                                        valor = float(row["valor"])
                                        
                                        parc = query_to_df(
                                            "SELECT id FROM parcelas WHERE projeto_id = ? AND identificacao = ?",
                                            (projeto_id, parcela_id)
                                        )
                                        if len(parc) == 0:
                                            erros += 1
                                            erros_detalhes.append(f"Linha {idx+2}: Parcela '{parcela_id}' não encontrada")
                                            progresso.progress((idx + 1) / len(df))
                                            continue
                                        
                                        var = query_to_df(
                                            "SELECT id FROM variaveis WHERE codigo = ?",
                                            (var_cod,)
                                        )
                                        if len(var) == 0:
                                            erros += 1
                                            erros_detalhes.append(f"Linha {idx+2}: Variável '{var_cod}' não encontrada")
                                            progresso.progress((idx + 1) / len(df))
                                            continue
                                        
                                        data_val = row.get("data", "")
                                        if pd.isna(data_val) or str(data_val).strip() == "":
                                            data_val = datetime.now().strftime("%Y-%m-%d")
                                        else:
                                            data_val = str(data_val).strip()
                                        
                                        estadio_val = row.get("estadio", "")
                                        if pd.isna(estadio_val):
                                            estadio_val = ""
                                        else:
                                            estadio_val = str(estadio_val).strip()
                                        
                                        execute_query(
                                            """INSERT INTO medicoes 
                                               (parcela_id, variavel_id, valor, data_medicao, estadio_fenologico) 
                                               VALUES (?, ?, ?, ?, ?)""",
                                            (parc.iloc[0]["id"], var.iloc[0]["id"], valor, data_val, estadio_val)
                                        )
                                        count += 1
                                        
                                    except Exception as e:
                                        erros += 1
                                        erros_detalhes.append(f"Linha {idx+2}: {str(e)[:100]}")
                                    
                                    progresso.progress((idx + 1) / len(df))
                            
                            st.markdown("---")
                            if substituir:
                                st.success(f"✅ **Dados substituídos com sucesso!**")
                            else:
                                st.success(f"✅ **Importação concluída!**")
                            
                            st.write(f"📥 **{count}** registros importados com sucesso")
                            if erros > 0:
                                st.warning(f"❌ **{erros}** erros")
                                with st.expander("📋 Ver detalhes dos erros"):
                                    for erro in erros_detalhes[:20]:
                                        st.write(f"• {erro}")
                                    if len(erros_detalhes) > 20:
                                        st.write(f"... e mais {len(erros_detalhes) - 20} erros")
                            
                            if count > 0:
                                st.rerun()
            
            except Exception as e:
                st.error(f"❌ Erro ao ler arquivo: {e}")
                import traceback
                st.error(traceback.format_exc())
    
    with tab3:
        st.subheader("📋 Dados Coletados")
        
        col_exp1, col_exp2, _ = st.columns([1.5, 1.5, 4])
        with col_exp1:
            if st.button("📥 Baixar CSV (para editar e reimportar)", use_container_width=True):
                dados_export = query_to_df("""
                    SELECT p.identificacao as parcela, v.codigo as variavel_codigo, 
                           m.valor, m.data_medicao as data, m.estadio_fenologico as estadio
                    FROM medicoes m
                    JOIN parcelas p ON m.parcela_id = p.id
                    JOIN variaveis v ON m.variavel_id = v.id
                    WHERE p.projeto_id = ?
                    ORDER BY p.identificacao, v.nome
                """, (projeto_id,))
                
                if len(dados_export) > 0:
                    csv = dados_export.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="📥 Baixar CSV",
                        data=csv,
                        file_name=f"dados_para_editar_projeto_{projeto_id}.csv",
                        mime="text/csv",
                        key="download_csv_editavel"
                    )
                else:
                    st.info("Nenhum dado para exportar.")
        
        with col_exp2:
            if st.button("📥 Baixar XLSX (Excel)", use_container_width=True):
                dados_export = query_to_df("""
                    SELECT p.identificacao as parcela, v.codigo as variavel_codigo, 
                           m.valor, m.data_medicao as data, m.estadio_fenologico as estadio
                    FROM medicoes m
                    JOIN parcelas p ON m.parcela_id = p.id
                    JOIN variaveis v ON m.variavel_id = v.id
                    WHERE p.projeto_id = ?
                    ORDER BY p.identificacao, v.nome
                """, (projeto_id,))
                
                if len(dados_export) > 0:
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        dados_export.to_excel(writer, index=False, sheet_name='Dados')
                    output.seek(0)
                    st.download_button(
                        label="📥 Baixar XLSX",
                        data=output,
                        file_name=f"dados_para_editar_projeto_{projeto_id}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="download_xlsx_editavel"
                    )
                else:
                    st.info("Nenhum dado para exportar.")
        
        st.markdown("---")
        st.markdown("**Instruções:** Baixe o CSV ou XLSX, edite no Excel, e faça upload na aba **Importar Planilha** usando o modo **Substituir tudo**.")
        st.markdown("---")
        
        dados = query_to_df("""
            SELECT m.id, p.identificacao as parcela, t.codigo as tratamento, 
                   v.nome as variavel, v.codigo as var_codigo, v.unidade, 
                   m.valor, m.data_medicao, m.estadio_fenologico,
                   m.parcela_id, m.variavel_id
            FROM medicoes m
            JOIN parcelas p ON m.parcela_id = p.id
            JOIN tratamentos t ON p.tratamento_id = t.id
            JOIN variaveis v ON m.variavel_id = v.id
            WHERE p.projeto_id = ?
            ORDER BY m.data_medicao DESC, p.identificacao
        """, (projeto_id,))
        
        if len(dados) > 0:
            st.write(f"**Total:** {len(dados)} medições")
            
            for _, med in dados.iterrows():
                col1, col2, col3, col4, col5, col6, col7 = st.columns([1.5, 1.5, 1.2, 1, 1, 0.5, 0.5])
                col1.write(f"**{med['parcela']}**")
                col2.write(f"📏 {med['variavel']} ({med['unidade']})")
                col3.write(f"**{med['valor']}**")
                col4.write(f"📅 {med['data_medicao']}")
                col5.write(f"🌿 {med['estadio_fenologico'] or '—'}")
                
                if col6.button("✏️", key=f"edit_med_{med['id']}"):
                    st.session_state.edit_medicao_id = med['id']
                    st.session_state.edit_med_parcela_id = med['parcela_id']
                    st.session_state.edit_med_variavel_id = med['variavel_id']
                    st.session_state.edit_med_valor = float(med['valor'])
                    st.session_state.edit_med_data = med['data_medicao']
                    st.session_state.edit_med_estadio = med['estadio_fenologico'] or ''
                    st.rerun()
                
                if col7.button("🗑️", key=f"del_med_{med['id']}"):
                    execute_query("DELETE FROM medicoes WHERE id = ?", (med['id'],))
                    st.rerun()
                
                st.markdown("---")
            
            if 'edit_medicao_id' in st.session_state:
                with st.expander("✏️ Editando Medição", expanded=True):
                    with st.form("editar_medicao"):
                        parcelas_df = query_to_df("SELECT id, identificacao FROM parcelas WHERE projeto_id = ? ORDER BY identificacao", (projeto_id,))
                        parcela_id = st.selectbox("Parcela", parcelas_df["id"].values, 
                            format_func=lambda x: parcelas_df[parcelas_df["id"]==x]["identificacao"].values[0],
                            index=parcelas_df[parcelas_df["id"]==st.session_state.edit_med_parcela_id].index[0] if st.session_state.edit_med_parcela_id in parcelas_df["id"].values else 0)
                        
                        vars_df = query_to_df("SELECT id, nome, codigo, unidade FROM variaveis ORDER BY nome")
                        var_idx = 0
                        if st.session_state.edit_med_variavel_id in vars_df["id"].values:
                            var_idx = vars_df[vars_df["id"]==st.session_state.edit_med_variavel_id].index[0]
                        variavel_id = st.selectbox("Variável", vars_df["id"].values,
                            format_func=lambda x: f"{vars_df[vars_df['id']==x]['nome'].values[0]} ({vars_df[vars_df['id']==x]['unidade'].values[0]})",
                            index=var_idx)
                        
                        valor = st.number_input("Valor", format="%.4f", value=st.session_state.edit_med_valor)
                        data_med = st.date_input("Data", value=pd.to_datetime(st.session_state.edit_med_data).date())
                        estadio = st.text_input("Estádio", value=st.session_state.edit_med_estadio)
                        
                        col_a, col_b = st.columns(2)
                        if col_a.form_submit_button("💾 Salvar Alterações"):
                            execute_query(
                                "UPDATE medicoes SET parcela_id=?, variavel_id=?, valor=?, data_medicao=?, estadio_fenologico=? WHERE id=?",
                                (parcela_id, variavel_id, valor, data_med, estadio, st.session_state.edit_medicao_id)
                            )
                            del st.session_state.edit_medicao_id
                            st.success("Medição atualizada!")
                            st.rerun()
                        
                        if col_b.form_submit_button("❌ Cancelar"):
                            del st.session_state.edit_medicao_id
                            st.rerun()
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
    df_proj = query_to_df("SELECT * FROM projetos WHERE id = ?", (projeto_id,))
    if len(df_proj) == 0:
        st.error("Projeto não encontrado!")
        return
    projeto = df_proj.iloc[0]
    df_emp = query_to_df("SELECT * FROM empresas WHERE id = ?", (projeto["empresa_id"],))
    empresa_nome = df_emp.iloc[0]["nome"] if len(df_emp) > 0 else "—"
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
    if st.button("📥 Gerar Relatório PDF Completo", use_container_width=True, type="primary"):
        with st.spinner("Gerando relatório completo com gráficos e análises..."):
            try:
                plt.switch_backend('Agg')
                buffer = io.BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=A4,
                                        topMargin=2*28.35, bottomMargin=2*28.35,
                                        leftMargin=2*28.35, rightMargin=2*28.35)
                styles = getSampleStyleSheet()
                c = 28.35
                largura = A4[0] - 4*c
                elementos = []

                # CAPA
                elementos.append(Spacer(1, 80))
                elementos.append(Paragraph("RELATÓRIO TÉCNICO", styles['Title']))
                elementos.append(Spacer(1, 20))
                elementos.append(Paragraph(f"<b>{projeto['titulo']}</b>", styles['Heading1']))
                elementos.append(Spacer(1, 30))
                elementos.append(Paragraph(f"<b>Empresa:</b> {empresa_nome}", styles['Normal']))
                elementos.append(Paragraph(f"<b>Cultura:</b> {projeto.get('cultura', '—')} | <b>Safra:</b> {projeto.get('safra', '—')}", styles['Normal']))
                elementos.append(Paragraph(f"<b>Local:</b> {projeto.get('local', '—')} - {projeto.get('municipio', '—')}/{projeto.get('estado', '—')}", styles['Normal']))
                elementos.append(Paragraph(f"<b>Responsável:</b> {projeto.get('responsavel', '—')}", styles['Normal']))
                elementos.append(Paragraph(f"<b>Data:</b> {datetime.now().strftime('%d/%m/%Y')}", styles['Normal']))
                elementos.append(PageBreak())

                # 1. OBJETIVO
                elementos.append(Paragraph("1. OBJETIVO", styles['Heading1']))
                elementos.append(Spacer(1, 8))
                elementos.append(Paragraph(projeto.get('objetivo', 'Não informado.'), styles['Normal']))
                elementos.append(Spacer(1, 12))

                # 2. MATERIAL E MÉTODOS
                elementos.append(Paragraph("2. MATERIAL E MÉTODOS", styles['Heading1']))
                elementos.append(Spacer(1, 8))
                info_data = [
                    ["Item", "Descrição"],
                    ["Cultura", projeto.get('cultura', '—')],
                    ["Safra", projeto.get('safra', '—')],
                    ["Local", f"{projeto.get('local', '—')} - {projeto.get('municipio', '—')}/{projeto.get('estado', '—')}"],
                    ["Data Plantio", str(projeto.get('data_plantio', '—'))],
                    ["Data Colheita", str(projeto.get('data_colheita', '—'))],
                ]
                info_table = Table(info_data, colWidths=[largura*0.3, largura*0.7])
                info_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2E7D32")),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#E8F5E9")]),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                elementos.append(info_table)
                elementos.append(Spacer(1, 12))

                tratamentos = query_to_df("SELECT * FROM tratamentos WHERE projeto_id = ?", (projeto_id,))
                if len(tratamentos) > 0:
                    elementos.append(Paragraph("<b>Tratamentos Avaliados:</b>", styles['Heading2']))
                    trat_data = [["Código", "Nome", "Descrição"]]
                    for _, t in tratamentos.iterrows():
                        trat_data.append([t['codigo'], t['nome'], t.get('descricao', '—')])
                    trat_table = Table(trat_data, colWidths=[largura*0.12, largura*0.44, largura*0.44])
                    trat_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2E7D32")),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 8),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#E8F5E9")]),
                        ('TOPPADDING', (0, 0), (-1, -1), 3),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ]))
                    elementos.append(trat_table)
                    elementos.append(Spacer(1, 12))

                # 3. RESULTADOS
                elementos.append(Paragraph("3. RESULTADOS", styles['Heading1']))
                elementos.append(Spacer(1, 8))

                variaveis = query_to_df("""
                    SELECT DISTINCT v.id, v.nome, v.codigo, v.unidade
                    FROM medicoes m
                    JOIN variaveis v ON m.variavel_id = v.id
                    JOIN parcelas p ON m.parcela_id = p.id
                    WHERE p.projeto_id = ?
                """, (projeto_id,))

                if len(variaveis) == 0:
                    elementos.append(Paragraph("Nenhum dado coletado.", styles['Normal']))
                else:
                    for idx, (_, var) in enumerate(variaveis.iterrows()):
                        var_nome, var_unid = var['nome'], var['unidade']
                        elementos.append(Paragraph(f"3.{idx+1} {var_nome} ({var_unid})", styles['Heading2']))
                        elementos.append(Spacer(1, 6))

                        df_var = query_to_df("""
                            SELECT m.valor, t.codigo as tratamento, t.nome as trat_nome, p.bloco, p.identificacao
                            FROM medicoes m
                            JOIN parcelas p ON m.parcela_id = p.id
                            JOIN tratamentos t ON p.tratamento_id = t.id
                            WHERE p.projeto_id = ? AND m.variavel_id = ?
                        """, (projeto_id, var['id']))
                        if len(df_var) == 0:
                            continue

                        # Estatística descritiva
                        elementos.append(Paragraph("<b>Estatística Descritiva:</b>", styles['Heading3']))
                        desc = df_var.groupby("tratamento")["valor"].agg(["mean", "std", "min", "max", "count"])
                        desc["cv"] = (desc["std"] / desc["mean"]) * 100
                        desc_data = [["Trat", "Média", "DP", "CV%", "Min", "Max", "N"]]
                        for trat, row in desc.iterrows():
                            desc_data.append([trat, f"{row['mean']:.2f}", f"{row['std']:.2f}", f"{row['cv']:.1f}", f"{row['min']:.2f}", f"{row['max']:.2f}", f"{int(row['count'])}"])
                        desc_table = Table(desc_data, colWidths=[largura*0.1, largura*0.15, largura*0.12, largura*0.1, largura*0.12, largura*0.12, largura*0.08])
                        desc_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1565C0")),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, -1), 7),
                            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#E3F2FD")]),
                            ('TOPPADDING', (0, 0), (-1, -1), 3),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                        ]))
                        elementos.append(desc_table)
                        elementos.append(Spacer(1, 10))

                        cores = ['#2E7D32', '#1565C0', '#E65100', '#6A1B9A', '#C62828', '#00838F', '#F9A825', '#4E342E']

                        # Gráfico de barras
                        if incluir_graficos:
                            plt.close('all')
                            fig, ax = plt.subplots(figsize=(8, 4.5))
                            medias = df_var.groupby("tratamento")["valor"].agg(["mean", "std"]).reset_index()
                            bars = ax.bar(range(len(medias)), medias['mean'], yerr=medias['std'], capsize=5,
                                         color=[cores[i % len(cores)] for i in range(len(medias))],
                                         edgecolor='white', linewidth=1.2)
                            for i, bar in enumerate(bars):
                                h = bar.get_height()
                                ax.text(bar.get_x() + bar.get_width()/2., h + h*0.02,
                                        f'{medias["mean"].iloc[i]:.2f}', ha='center', va='bottom', fontsize=8, fontweight='bold')
                            ax.set_xticks(range(len(medias)))
                            ax.set_xticklabels(medias['tratamento'], fontsize=9)
                            ax.set_ylabel(f'{var_nome} ({var_unid})', fontsize=10)
                            ax.set_title(f'{var_nome} por Tratamento', fontsize=12, fontweight='bold')
                            ax.spines['top'].set_visible(False)
                            ax.spines['right'].set_visible(False)
                            ax.grid(axis='y', alpha=0.3)
                            plt.tight_layout()
                            img_buf = io.BytesIO()
                            fig.savefig(img_buf, format='png', dpi=150, bbox_inches='tight')
                            img_buf.seek(0)
                            plt.close(fig)
                            elementos.append(Image(img_buf, width=largura, height=largura*0.56))
                            elementos.append(Spacer(1, 10))

                        # Boxplot
                        if incluir_graficos:
                            plt.close('all')
                            fig, ax = plt.subplots(figsize=(8, 4))
                            trat_lista = list(df_var['tratamento'].unique())
                            dados_box = [df_var[df_var['tratamento'] == t]['valor'].values for t in trat_lista]
                            bp = ax.boxplot(dados_box, patch_artist=True,
                                           medianprops={'color': 'black', 'linewidth': 2})
                            for patch, color in zip(bp['boxes'], cores[:len(trat_lista)]):
                                patch.set_facecolor(color)
                                patch.set_alpha(0.6)
                            ax.set_xticks(range(1, len(trat_lista) + 1))
                            ax.set_xticklabels(trat_lista, fontsize=9)
                            ax.set_ylabel(f'{var_nome} ({var_unid})', fontsize=10)
                            ax.set_title(f'Boxplot - {var_nome}', fontsize=12, fontweight='bold')
                            ax.spines['top'].set_visible(False)
                            ax.spines['right'].set_visible(False)
                            ax.grid(axis='y', alpha=0.3)
                            plt.tight_layout()
                            img_buf2 = io.BytesIO()
                            fig.savefig(img_buf2, format='png', dpi=150, bbox_inches='tight')
                            img_buf2.seek(0)
                            plt.close(fig)
                            elementos.append(Image(img_buf2, width=largura, height=largura*0.5))
                            elementos.append(Spacer(1, 10))

                        # ANOVA
                        if incluir_anova and len(df_var) >= 6:
                            elementos.append(Paragraph("<b>Análise de Variância (ANOVA):</b>", styles['Heading3']))
                            from scipy.stats import f_oneway, shapiro
                            grupos = [g["valor"].values for _, g in df_var.groupby("tratamento")]
                            residuos = df_var.groupby("tratamento")["valor"].apply(lambda x: x - x.mean())
                            _, shapiro_p = shapiro(residuos)
                            f_stat, f_p = f_oneway(*grupos)
                            media_geral = df_var['valor'].mean()
                            sq_trat = sum(len(g) * (g.mean() - media_geral)**2 for g in grupos)
                            gl_trat = len(grupos) - 1
                            qm_trat = sq_trat / gl_trat if gl_trat > 0 else 0
                            sq_total = sum((v - media_geral)**2 for v in df_var['valor'])
                            gl_total = len(df_var) - 1
                            sq_res = sq_total - sq_trat
                            gl_res = gl_total - gl_trat
                            qm_res = sq_res / gl_res if gl_res > 0 else 0
                            anova_data = [
                                ["Fonte", "SQ", "GL", "QM", "F", "p-valor"],
                                ["Tratamentos", f"{sq_trat:.2f}", f"{gl_trat}", f"{qm_trat:.2f}", f"{f_stat:.4f}", f"{f_p:.6f}"],
                                ["Resíduo", f"{sq_res:.2f}", f"{gl_res}", f"{qm_res:.2f}", "", ""],
                                ["Total", f"{sq_total:.2f}", f"{gl_total}", "", "", ""]
                            ]
                            anova_table = Table(anova_data, colWidths=[largura*0.2, largura*0.16, largura*0.1, largura*0.16, largura*0.16, largura*0.16])
                            anova_table.setStyle(TableStyle([
                                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#E65100")),
                                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                ('FONTSIZE', (0, 0), (-1, -1), 8),
                                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                                ('TOPPADDING', (0, 0), (-1, -1), 3),
                                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                            ]))
                            elementos.append(anova_table)
                            elementos.append(Spacer(1, 6))
                            elementos.append(Paragraph(f"<b>Normalidade (Shapiro-Wilk):</b> p = {shapiro_p:.4f} {'✅ Normal' if shapiro_p > 0.05 else '⚠️ Não normal'}", styles['Normal']))
                            elementos.append(Spacer(1, 4))
                            if f_p < 0.05:
                                elementos.append(Paragraph(f"<b>Resultado ANOVA:</b> F = {f_stat:.4f}, p = {f_p:.6f} — <b>Diferença significativa</b> (p &lt; 0,05) ✅", styles['Normal']))
                                elementos.append(Spacer(1, 6))
                                elementos.append(Paragraph("<b>Teste de Tukey:</b>", styles['Heading3']))
                                tukey = pairwise_tukeyhsd(df_var["valor"], df_var["tratamento"], alpha=0.05)
                                tukey_data = [["Grupo 1", "Grupo 2", "Diferença", "p-valor", "Signif."]]
                                for row in tukey.summary().data[1:]:
                                    sig = "✅" if row[4] < 0.05 else "❌"
                                    tukey_data.append([str(row[0]), str(row[1]), f"{row[2]:.4f}", f"{row[4]:.4f}", sig])
                                tukey_table = Table(tukey_data, colWidths=[largura*0.2, largura*0.2, largura*0.2, largura*0.2, largura*0.1])
                                tukey_table.setStyle(TableStyle([
                                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#6A1B9A")),
                                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                    ('FONTSIZE', (0, 0), (-1, -1), 7),
                                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3E5F5")]),
                                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                                ]))
                                elementos.append(tukey_table)
                                elementos.append(Spacer(1, 6))

                                # Letras
                                medias_sort = df_var.groupby("tratamento")["valor"].mean().sort_values(ascending=False)
                                letras = {}
                                letra_atual = 'a'
                                for i, (trat, _) in enumerate(medias_sort.items()):
                                    letras[trat] = letra_atual
                                    if i < len(medias_sort) - 1:
                                        next_trat = medias_sort.index[i + 1]
                                        for row in tukey.summary().data[1:]:
                                            if (row[0] == trat and row[1] == next_trat) or (row[0] == next_trat and row[1] == trat):
                                                if row[4] < 0.05:
                                                    letra_atual = chr(ord(letra_atual) + 1)
                                                break
                                letras_data = [["Tratamento", "Média", "Letra"]]
                                for trat, media in medias_sort.items():
                                    letras_data.append([trat, f"{media:.2f}", letras[trat]])
                                letras_table = Table(letras_data, colWidths=[largura*0.3, largura*0.3, largura*0.15])
                                letras_table.setStyle(TableStyle([
                                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2E7D32")),
                                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#E8F5E9")]),
                                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                                ]))
                                elementos.append(letras_table)
                                elementos.append(Spacer(1, 4))
                                elementos.append(Paragraph("<i>Médias com mesma letra não diferem (Tukey 5%).</i>", styles['Normal']))

                                # Gráfico com letras
                                if incluir_graficos:
                                    plt.close('all')
                                    fig, ax = plt.subplots(figsize=(8, 4.5))
                                    medias_letras = medias_sort.reset_index()
                                    medias_letras.columns = ['tratamento', 'media']
                                    medias_letras['letra'] = medias_letras['tratamento'].map(letras)
                                    bars = ax.bar(range(len(medias_letras)), medias_letras['media'],
                                                 color=[cores[i % len(cores)] for i in range(len(medias_letras))],
                                                 edgecolor='white', linewidth=1.2)
                                    for i, (_, row) in enumerate(medias_letras.iterrows()):
                                        ax.text(i, row['media'] + row['media']*0.02,
                                                f"{row['media']:.2f}{row['letra']}",
                                                ha='center', va='bottom', fontsize=9, fontweight='bold')
                                    ax.set_xticks(range(len(medias_letras)))
                                    ax.set_xticklabels(medias_letras['tratamento'], fontsize=9)
                                    ax.set_ylabel(f'{var_nome} ({var_unid})', fontsize=10)
                                    ax.set_title(f'{var_nome} - Médias com Letras de Tukey', fontsize=12, fontweight='bold')
                                    ax.spines['top'].set_visible(False)
                                    ax.spines['right'].set_visible(False)
                                    ax.grid(axis='y', alpha=0.3)
                                    plt.tight_layout()
                                    img_buf3 = io.BytesIO()
                                    fig.savefig(img_buf3, format='png', dpi=150, bbox_inches='tight')
                                    img_buf3.seek(0)
                                    plt.close(fig)
                                    elementos.append(Image(img_buf3, width=largura, height=largura*0.56))
                            else:
                                elementos.append(Paragraph(f"<b>Resultado ANOVA:</b> F = {f_stat:.4f}, p = {f_p:.6f} — <b>Sem diferença</b> (p &gt; 0,05)", styles['Normal']))
                        elementos.append(Spacer(1, 16))

                # 4. RECOMENDAÇÕES
                if recomendacoes:
                    elementos.append(Paragraph("4. RECOMENDAÇÕES TÉCNICAS", styles['Heading1']))
                    elementos.append(Spacer(1, 8))
                    elementos.append(Paragraph(recomendacoes, styles['Normal']))
                    elementos.append(Spacer(1, 12))

                # 5. DADOS BRUTOS
                if incluir_dados_brutos:
                    elementos.append(PageBreak())
                    elementos.append(Paragraph("ANEXO - DADOS BRUTOS", styles['Heading1']))
                    elementos.append(Spacer(1, 8))
                    dados_brutos = query_to_df("""
                        SELECT p.identificacao as parcela, t.codigo as tratamento, 
                               v.nome as variavel, v.unidade, m.valor, m.data_medicao
                        FROM medicoes m
                        JOIN parcelas p ON m.parcela_id = p.id
                        JOIN tratamentos t ON p.tratamento_id = t.id
                        JOIN variaveis v ON m.variavel_id = v.id
                        WHERE p.projeto_id = ?
                        ORDER BY p.identificacao, v.nome
                    """, (projeto_id,))
                    if len(dados_brutos) > 0:
                        brutos_data = [list(dados_brutos.columns)]
                        for _, row in dados_brutos.iterrows():
                            brutos_data.append([str(row[c]) for c in dados_brutos.columns])
                        brutos_table = Table(brutos_data, repeatRows=1)
                        brutos_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#37474F")),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, -1), 6),
                            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                            ('TOPPADDING', (0, 0), (-1, -1), 2),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                        ]))
                        elementos.append(brutos_table)

                doc.build(elementos)
                buffer.seek(0)
                st.success("✅ Relatório completo gerado com sucesso!")
                st.download_button(
                    label="📥 Baixar Relatório PDF",
                    data=buffer,
                    file_name=f"relatorio_{projeto['titulo'][:30]}_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Erro ao gerar relatório: {e}")
                import traceback
                st.error(traceback.format_exc())

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
