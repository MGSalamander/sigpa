import sqlite3
import os

DB_NAME = "sigpa.db"

def criar_banco():
    """Cria todas as tabelas do banco de dados"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # ===== TABELA: EMPRESAS =====
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS empresas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cnpj TEXT,
            contato TEXT,
            email TEXT,
            telefone TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ativo INTEGER DEFAULT 1
        )
    """)
    
    # ===== TABELA: PROJETOS =====
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projetos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            objetivo TEXT,
            tipo_pesquisa TEXT,
            local TEXT,
            municipio TEXT,
            estado TEXT,
            safra TEXT,
            cultura TEXT,
            data_plantio DATE,
            data_colheita DATE,
            responsavel TEXT,
            status TEXT DEFAULT 'planejamento',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        )
    """)
    
    # ===== TABELA: DELINEAMENTOS =====
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS delineamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            projeto_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            num_tratamentos INTEGER,
            num_blocos INTEGER,
            num_repeticoes INTEGER,
            area_parcela REAL,
            detalhes TEXT,
            FOREIGN KEY (projeto_id) REFERENCES projetos(id)
        )
    """)
    
    # ===== TABELA: TRATAMENTOS =====
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tratamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            projeto_id INTEGER NOT NULL,
            codigo TEXT NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT,
            FOREIGN KEY (projeto_id) REFERENCES projetos(id)
        )
    """)
    
    # ===== TABELA: VARIAVEIS =====
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS variaveis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            codigo TEXT NOT NULL,
            categoria TEXT,
            unidade TEXT,
            metodo TEXT
        )
    """)
    
    # ===== TABELA: PARCELAS =====
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS parcelas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            projeto_id INTEGER NOT NULL,
            tratamento_id INTEGER NOT NULL,
            bloco INTEGER,
            repeticao INTEGER,
            identificacao TEXT,
            FOREIGN KEY (projeto_id) REFERENCES projetos(id),
            FOREIGN KEY (tratamento_id) REFERENCES tratamentos(id)
        )
    """)
    
    # ===== TABELA: MEDICOES =====
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parcela_id INTEGER NOT NULL,
            variavel_id INTEGER NOT NULL,
            valor REAL,
            data_medicao DATE,
            estadio_fenologico TEXT,
            observador TEXT,
            validado INTEGER DEFAULT 0,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parcela_id) REFERENCES parcelas(id),
            FOREIGN KEY (variavel_id) REFERENCES variaveis(id)
        )
    """)
    
    # ===== TABELA: USUARIOS =====
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            tipo TEXT DEFAULT 'pesquisador',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # ===== TABELA: PERMISSOES =====
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS permissoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            projeto_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            nivel TEXT NOT NULL DEFAULT 'visualizador',
            FOREIGN KEY (projeto_id) REFERENCES projetos(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Banco de dados criado com sucesso!")

if __name__ == "__main__":
    criar_banco()