"""
Camada de banco de dados - WR Exhaust Dashboard
SQLite local (arquivo wr_exhaust.db). Fácil migrar pra Postgres no futuro,
já que as funções aqui isolam todo o SQL do resto do app.
"""

import sqlite3
from datetime import date, datetime
from contextlib import contextmanager

DB_PATH = "wr_exhaust.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        c = conn.cursor()

        c.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            categoria TEXT,
            variacao TEXT,
            preco_venda REAL NOT NULL DEFAULT 0,
            custo REAL NOT NULL DEFAULT 0,
            estoque INTEGER NOT NULL DEFAULT 0,
            estoque_minimo INTEGER NOT NULL DEFAULT 2,
            ativo INTEGER NOT NULL DEFAULT 1
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            contato TEXT,
            plataforma_origem TEXT,
            criado_em TEXT NOT NULL
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_venda TEXT NOT NULL,
            produto_id INTEGER NOT NULL,
            quantidade INTEGER NOT NULL DEFAULT 1,
            preco_unitario REAL NOT NULL,
            plataforma TEXT NOT NULL,          -- Shopee / TikTok Shop / Presencial
            desconto REAL NOT NULL DEFAULT 0,
            cliente_id INTEGER,
            taxa_calculada REAL NOT NULL DEFAULT 0,
            subsidio_pix REAL NOT NULL DEFAULT 0,
            receita_liquida REAL NOT NULL DEFAULT 0,
            observacao TEXT,
            FOREIGN KEY (produto_id) REFERENCES produtos(id),
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
        """)

        # Configuração de taxas por plataforma. Guardamos como linhas simples
        # editáveis pela tela de Configurações, sem precisar mexer no código.
        c.execute("""
        CREATE TABLE IF NOT EXISTS config_taxas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plataforma TEXT NOT NULL,
            comissao_pct REAL NOT NULL DEFAULT 0,      -- % de comissão da plataforma
            imposto_pct REAL NOT NULL DEFAULT 0,       -- % imposto (ex: CPF na Shopee)
            subsidio_pix_pct REAL NOT NULL DEFAULT 0,  -- % de subsídio Pix (Shopee)
            taxa_fixa REAL NOT NULL DEFAULT 0,         -- taxa fixa por venda (maquininha etc)
            vigente_a_partir TEXT NOT NULL DEFAULT '2000-01-01'  -- p/ troca de comissão TikTok
        )
        """)

        conn.commit()

        # Seed inicial de configuração de taxas, se ainda não existir
        c.execute("SELECT COUNT(*) as n FROM config_taxas")
        if c.fetchone()["n"] == 0:
            c.executemany("""
                INSERT INTO config_taxas
                (plataforma, comissao_pct, imposto_pct, subsidio_pix_pct, taxa_fixa, vigente_a_partir)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                ("Shopee", 14.0, 1.0, 0.0, 4.0, "2000-01-01"),
                ("TikTok Shop", 6.0, 0.0, 0.0, 0.0, "2000-01-01"),
                ("TikTok Shop", 8.0, 0.0, 0.0, 0.0, "2026-07-15"),
                ("Presencial", 0.0, 0.0, 0.0, 0.0, "2000-01-01"),
            ])


# ---------- PRODUTOS ----------

def listar_produtos(apenas_ativos=True):
    with get_conn() as conn:
        q = "SELECT * FROM produtos"
        if apenas_ativos:
            q += " WHERE ativo = 1"
        q += " ORDER BY nome"
        return [dict(r) for r in conn.execute(q).fetchall()]


def criar_produto(nome, categoria, variacao, preco_venda, custo, estoque, estoque_minimo):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO produtos (nome, categoria, variacao, preco_venda, custo, estoque, estoque_minimo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (nome, categoria, variacao, preco_venda, custo, estoque, estoque_minimo))


def atualizar_estoque(produto_id, novo_estoque):
    with get_conn() as conn:
        conn.execute("UPDATE produtos SET estoque = ? WHERE id = ?", (novo_estoque, produto_id))


# ---------- CLIENTES ----------

def buscar_ou_criar_cliente(nome, contato, plataforma_origem):
    if not nome:
        return None
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM clientes WHERE nome = ? AND IFNULL(contato,'') = IFNULL(?, '')",
            (nome, contato)
        ).fetchone()
        if row:
            return row["id"]
        cur = conn.execute("""
            INSERT INTO clientes (nome, contato, plataforma_origem, criado_em)
            VALUES (?, ?, ?, ?)
        """, (nome, contato, plataforma_origem, datetime.now().isoformat()))
        return cur.lastrowid


# ---------- CONFIG DE TAXAS ----------

def get_config_vigente(plataforma, data_venda):
    """Pega a config de taxa vigente na data da venda (suporta troca de comissão por data)."""
    with get_conn() as conn:
        row = conn.execute("""
            SELECT * FROM config_taxas
            WHERE plataforma = ? AND vigente_a_partir <= ?
            ORDER BY vigente_a_partir DESC
            LIMIT 1
        """, (plataforma, str(data_venda))).fetchone()
        return dict(row) if row else None


def listar_config_taxas():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM config_taxas ORDER BY plataforma, vigente_a_partir"
        ).fetchall()]


def atualizar_config_taxa(config_id, comissao_pct, imposto_pct, subsidio_pix_pct, taxa_fixa, vigente_a_partir):
    with get_conn() as conn:
        conn.execute("""
            UPDATE config_taxas
            SET comissao_pct=?, imposto_pct=?, subsidio_pix_pct=?, taxa_fixa=?, vigente_a_partir=?
            WHERE id=?
        """, (comissao_pct, imposto_pct, subsidio_pix_pct, taxa_fixa, vigente_a_partir, config_id))


def criar_config_taxa(plataforma, comissao_pct, imposto_pct, subsidio_pix_pct, taxa_fixa, vigente_a_partir):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO config_taxas
            (plataforma, comissao_pct, imposto_pct, subsidio_pix_pct, taxa_fixa, vigente_a_partir)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (plataforma, comissao_pct, imposto_pct, subsidio_pix_pct, taxa_fixa, vigente_a_partir))


# ---------- VENDAS ----------

def calcular_venda(preco_unitario, quantidade, desconto, plataforma, data_venda):
    """Aplica a lógica de taxas de cada plataforma e devolve os valores calculados."""
    bruto = preco_unitario * quantidade - desconto
    cfg = get_config_vigente(plataforma, data_venda)

    if not cfg:
        return {"taxa_calculada": 0, "subsidio_pix": 0, "receita_liquida": bruto}

    comissao = bruto * (cfg["comissao_pct"] / 100)
    imposto = bruto * (cfg["imposto_pct"] / 100)
    subsidio = bruto * (cfg["subsidio_pix_pct"] / 100)
    taxa_fixa = cfg["taxa_fixa"]

    taxa_total = comissao + imposto + taxa_fixa
    liquido = bruto - taxa_total + subsidio

    return {
        "taxa_calculada": round(taxa_total, 2),
        "subsidio_pix": round(subsidio, 2),
        "receita_liquida": round(liquido, 2),
    }


def registrar_venda(data_venda, produto_id, quantidade, preco_unitario, plataforma,
                     desconto=0, cliente_nome=None, cliente_contato=None, observacao=None):
    calc = calcular_venda(preco_unitario, quantidade, desconto, plataforma, data_venda)
    cliente_id = buscar_ou_criar_cliente(cliente_nome, cliente_contato, plataforma)

    with get_conn() as conn:
        conn.execute("""
            INSERT INTO vendas
            (data_venda, produto_id, quantidade, preco_unitario, plataforma, desconto,
             cliente_id, taxa_calculada, subsidio_pix, receita_liquida, observacao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (str(data_venda), produto_id, quantidade, preco_unitario, plataforma, desconto,
              cliente_id, calc["taxa_calculada"], calc["subsidio_pix"], calc["receita_liquida"], observacao))

        # baixa de estoque
        prod = conn.execute("SELECT estoque FROM produtos WHERE id = ?", (produto_id,)).fetchone()
        if prod:
            novo_estoque = max(0, prod["estoque"] - quantidade)
            conn.execute("UPDATE produtos SET estoque = ? WHERE id = ?", (novo_estoque, produto_id))

    return calc


def listar_vendas(data_inicio=None, data_fim=None, plataforma=None):
    with get_conn() as conn:
        q = """
            SELECT v.*, p.nome as produto_nome, p.categoria
            FROM vendas v
            JOIN produtos p ON p.id = v.produto_id
            WHERE 1=1
        """
        params = []
        if data_inicio:
            q += " AND v.data_venda >= ?"
            params.append(str(data_inicio))
        if data_fim:
            q += " AND v.data_venda <= ?"
            params.append(str(data_fim))
        if plataforma and plataforma != "Todas":
            q += " AND v.plataforma = ?"
            params.append(plataforma)
        q += " ORDER BY v.data_venda DESC, v.id DESC"
        return [dict(r) for r in conn.execute(q, params).fetchall()]
