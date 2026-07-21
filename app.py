import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime, timedelta

import db

st.set_page_config(page_title="WR Exhaust - Painel", page_icon="🏍️", layout="wide")
db.init_db()

PLATAFORMAS = ["Shopee", "TikTok Shop", "Presencial"]

st.sidebar.title("🏍️ WR Exhaust")
pagina = st.sidebar.radio(
    "Navegação",
    ["📊 Painel", "🛒 Nova Venda", "📦 Produtos", "⚙️ Configuração de Taxas"],
)

# ----------------------------------------------------------------------
# PÁGINA: PAINEL
# ----------------------------------------------------------------------
if pagina == "📊 Painel":
    st.title("📊 Painel de Resultados")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        periodo = st.selectbox("Período", ["Hoje", "Últimos 7 dias", "Últimos 30 dias", "Este mês", "Tudo"])
    with col_b:
        plataforma_filtro = st.selectbox("Plataforma", ["Todas"] + PLATAFORMAS)
    with col_c:
        st.write("")

    hoje = date.today()
    if periodo == "Hoje":
        data_inicio = hoje
    elif periodo == "Últimos 7 dias":
        data_inicio = hoje - timedelta(days=7)
    elif periodo == "Últimos 30 dias":
        data_inicio = hoje - timedelta(days=30)
    elif periodo == "Este mês":
        data_inicio = hoje.replace(day=1)
    else:
        data_inicio = None

    vendas = db.listar_vendas(data_inicio=data_inicio, data_fim=hoje, plataforma=plataforma_filtro)
    df = pd.DataFrame(vendas)

    if df.empty:
        st.info("Nenhuma venda registrada nesse período ainda. Cadastre uma venda em **🛒 Nova Venda**.")
    else:
        df["bruto"] = df["preco_unitario"] * df["quantidade"] - df["desconto"]

        # ---- KPIs ----
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Faturamento Bruto", f'R$ {df["bruto"].sum():,.2f}')
        k2.metric("Taxas Pagas", f'R$ {df["taxa_calculada"].sum():,.2f}')
        k3.metric("Receita Líquida", f'R$ {df["receita_liquida"].sum():,.2f}')
        k4.metric("Pedidos", f'{len(df)}')
        clientes_alcancados = df["cliente_id"].nunique() if "cliente_id" in df else 0
        k5.metric("Clientes Alcançados", f'{clientes_alcancados}')

        st.divider()

        c1, c2 = st.columns(2)

        with c1:
            st.subheader("Receita líquida por plataforma")
            por_plat = df.groupby("plataforma")["receita_liquida"].sum().reset_index()
            fig = px.pie(por_plat, names="plataforma", values="receita_liquida", hole=0.45)
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.subheader("Faturamento por dia")
            por_dia = df.groupby("data_venda")["bruto"].sum().reset_index().sort_values("data_venda")
            fig2 = px.bar(por_dia, x="data_venda", y="bruto", labels={"data_venda": "Data", "bruto": "Faturamento (R$)"})
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Produtos mais vendidos")
        top_prod = (
            df.groupby("produto_nome")
            .agg(quantidade=("quantidade", "sum"), receita=("receita_liquida", "sum"))
            .reset_index()
            .sort_values("quantidade", ascending=False)
            .head(10)
        )
        fig3 = px.bar(top_prod, x="produto_nome", y="quantidade", labels={"produto_nome": "Produto", "quantidade": "Unidades vendidas"})
        st.plotly_chart(fig3, use_container_width=True)

        with st.expander("Ver vendas detalhadas"):
            st.dataframe(
                df[["data_venda", "produto_nome", "plataforma", "quantidade", "preco_unitario",
                    "desconto", "taxa_calculada", "receita_liquida"]],
                use_container_width=True,
            )

    st.divider()
    st.subheader("⚠️ Estoque baixo")
    produtos = pd.DataFrame(db.listar_produtos())
    if not produtos.empty:
        baixo = produtos[produtos["estoque"] <= produtos["estoque_minimo"]]
        if baixo.empty:
            st.success("Nenhum produto com estoque baixo. 👍")
        else:
            st.dataframe(baixo[["nome", "variacao", "estoque", "estoque_minimo"]], use_container_width=True)

# ----------------------------------------------------------------------
# PÁGINA: NOVA VENDA
# ----------------------------------------------------------------------
elif pagina == "🛒 Nova Venda":
    st.title("🛒 Registrar Nova Venda")

    produtos = db.listar_produtos()
    if not produtos:
        st.warning("Cadastre pelo menos um produto antes de lançar uma venda. Vá em **📦 Produtos**.")
    else:
        mapa_produtos = {f'{p["nome"]} {("- " + p["variacao"]) if p["variacao"] else ""} (estoque: {p["estoque"]})': p for p in produtos}

        with st.form("form_venda", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                data_venda = st.date_input("Data da venda", value=date.today())
                produto_label = st.selectbox("Produto", list(mapa_produtos.keys()))
                quantidade = st.number_input("Quantidade", min_value=1, value=1, step=1)
                plataforma = st.selectbox("Plataforma", PLATAFORMAS)
            with col2:
                produto_sel = mapa_produtos[produto_label]
                preco_unitario = st.number_input("Preço unitário (R$)", min_value=0.0, value=float(produto_sel["preco_venda"]), step=1.0)
                desconto = st.number_input("Desconto total (R$)", min_value=0.0, value=0.0, step=1.0)
                cliente_nome = st.text_input("Nome do cliente (opcional)")
                cliente_contato = st.text_input("Contato do cliente (opcional)")

            observacao = st.text_area("Observação (opcional)")

            # prévia do cálculo
            calc_preview = db.calcular_venda(preco_unitario, quantidade, desconto, plataforma, data_venda)
            st.info(
                f'Taxa estimada: R$ {calc_preview["taxa_calculada"]:.2f}  |  '
                f'Subsídio Pix: R$ {calc_preview["subsidio_pix"]:.2f}  |  '
                f'**Receita líquida estimada: R$ {calc_preview["receita_liquida"]:.2f}**'
            )

            submitted = st.form_submit_button("Registrar Venda", type="primary")
            if submitted:
                db.registrar_venda(
                    data_venda=data_venda,
                    produto_id=produto_sel["id"],
                    quantidade=quantidade,
                    preco_unitario=preco_unitario,
                    plataforma=plataforma,
                    desconto=desconto,
                    cliente_nome=cliente_nome or None,
                    cliente_contato=cliente_contato or None,
                    observacao=observacao or None,
                )
                st.success("Venda registrada com sucesso! ✅")
                st.rerun()

# ----------------------------------------------------------------------
# PÁGINA: PRODUTOS
# ----------------------------------------------------------------------
elif pagina == "📦 Produtos":
    st.title("📦 Catálogo de Produtos")

    with st.expander("➕ Cadastrar novo produto"):
        with st.form("form_produto", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                nome = st.text_input("Nome do produto")
                categoria = st.text_input("Categoria (ex: Suporte, Protetor de Carenagem)")
            with col2:
                variacao = st.text_input("Variação (cor, modelo, etc)")
                preco_venda = st.number_input("Preço de venda (R$)", min_value=0.0, step=1.0)
            with col3:
                custo = st.number_input("Custo (R$)", min_value=0.0, step=1.0)
                estoque = st.number_input("Estoque inicial", min_value=0, step=1)
                estoque_minimo = st.number_input("Estoque mínimo (alerta)", min_value=0, value=2, step=1)

            if st.form_submit_button("Cadastrar produto", type="primary"):
                if nome:
                    db.criar_produto(nome, categoria, variacao, preco_venda, custo, estoque, estoque_minimo)
                    st.success(f"Produto '{nome}' cadastrado!")
                    st.rerun()
                else:
                    st.error("Informe o nome do produto.")

    produtos = pd.DataFrame(db.listar_produtos())
    if produtos.empty:
        st.info("Nenhum produto cadastrado ainda.")
    else:
        st.dataframe(produtos, use_container_width=True)

# ----------------------------------------------------------------------
# PÁGINA: CONFIGURAÇÃO DE TAXAS
# ----------------------------------------------------------------------
elif pagina == "⚙️ Configuração de Taxas":
    st.title("⚙️ Configuração de Taxas por Plataforma")
    st.caption(
        "Aqui você ajusta comissão, imposto, subsídio Pix e taxa fixa de cada plataforma. "
        "Você pode criar mais de uma linha pra mesma plataforma com datas de vigência diferentes "
        "(é assim que resolvemos a troca de comissão do TikTok Shop em julho/2026, por exemplo)."
    )

    configs = db.listar_config_taxas()
    for cfg in configs:
        with st.expander(f'{cfg["plataforma"]} — vigente a partir de {cfg["vigente_a_partir"]}'):
            with st.form(f"form_cfg_{cfg['id']}"):
                c1, c2, c3, c4, c5 = st.columns(5)
                comissao = c1.number_input("Comissão (%)", value=float(cfg["comissao_pct"]), key=f"com_{cfg['id']}")
                imposto = c2.number_input("Imposto (%)", value=float(cfg["imposto_pct"]), key=f"imp_{cfg['id']}")
                subsidio = c3.number_input("Subsídio Pix (%)", value=float(cfg["subsidio_pix_pct"]), key=f"sub_{cfg['id']}")
                fixa = c4.number_input("Taxa fixa (R$)", value=float(cfg["taxa_fixa"]), key=f"fix_{cfg['id']}")
                vigencia = c5.date_input(
                    "Vigente a partir de",
                    value=datetime.strptime(cfg["vigente_a_partir"], "%Y-%m-%d").date(),
                    key=f"vig_{cfg['id']}",
                )
                if st.form_submit_button("Salvar"):
                    db.atualizar_config_taxa(cfg["id"], comissao, imposto, subsidio, fixa, str(vigencia))
                    st.success("Configuração atualizada!")
                    st.rerun()

    st.divider()
    st.subheader("➕ Nova regra de taxa")
    with st.form("form_nova_taxa", clear_on_submit=True):
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        plataforma_nova = c1.selectbox("Plataforma", PLATAFORMAS)
        comissao_n = c2.number_input("Comissão (%)", value=0.0, key="novo_com")
        imposto_n = c3.number_input("Imposto (%)", value=0.0, key="novo_imp")
        subsidio_n = c4.number_input("Subsídio Pix (%)", value=0.0, key="novo_sub")
        fixa_n = c5.number_input("Taxa fixa (R$)", value=0.0, key="novo_fix")
        vigencia_n = c6.date_input("Vigente a partir de", value=date.today(), key="novo_vig")

        if st.form_submit_button("Adicionar regra", type="primary"):
            db.criar_config_taxa(plataforma_nova, comissao_n, imposto_n, subsidio_n, fixa_n, str(vigencia_n))
            st.success("Nova regra criada!")
            st.rerun()
