# WR Exhaust — Painel de Resultados

Sistema simples em **Python + SQLite + Streamlit** pra acompanhar vendas, taxas por
plataforma (Shopee, TikTok Shop, Presencial), estoque e clientes alcançados.

## Como rodar

1. Instale o Python 3.10+ (se ainda não tiver).
2. Abra um terminal na pasta do projeto e instale as dependências:

   ```
   pip install -r requirements.txt
   ```

3. Rode o app:

   ```
   streamlit run app.py
   ```

4. Vai abrir automaticamente no navegador (algo como `http://localhost:8501`).
   É a "telinha" do dashboard — pode deixar aberta numa aba, num tablet na loja,
   ou acessar de qualquer computador na mesma rede.

O banco de dados fica salvo no arquivo `wr_exhaust.db`, criado automaticamente
na primeira vez que você roda o app. Ele guarda tudo: produtos, vendas, clientes
e configuração de taxas. Faça backup desse arquivo de vez em quando (é só copiar).

## Estrutura

- `db.py` — todo o banco de dados e as regras de cálculo de taxa (SQLite)
- `app.py` — o dashboard visual (Streamlit)
- `wr_exhaust.db` — o banco de dados (criado automaticamente)

## Passo a passo de uso

1. **📦 Produtos** — cadastre seus produtos primeiro (nome, variação, preço, estoque).
2. **⚙️ Configuração de Taxas** — confira/ajuste as taxas de cada plataforma.
   Comissão, imposto (CPF), subsídio Pix e taxa fixa, tudo editável ali.
   Pra trocas de comissão por data (como a do TikTok Shop em 15/07/2026),
   crie uma nova regra com a data de vigência — o sistema escolhe sozinho
   a regra certa conforme a data da venda.
3. **🛒 Nova Venda** — registre cada venda manualmente (por enquanto). O sistema
   já mostra a taxa e a receita líquida estimada antes de confirmar, e dá
   baixa automática no estoque.
4. **📊 Painel** — acompanhe faturamento, taxas, receita líquida, clientes
   alcançados, produtos mais vendidos e alertas de estoque baixo, com filtro
   por período e por plataforma.

## Próximos passos (quando quiser evoluir)

- **Importação automática**: dá pra criar uma função em `db.py` que lê um CSV
  exportado do Shopee/TikTok Shop e chama `registrar_venda()` pra cada linha,
  eliminando a digitação manual.
- **API**: quando o Shopee/TikTok Shop liberarem acesso via API pra você, dá
  pra trocar a tela de "Nova Venda" manual por um script que puxa os pedidos
  automaticamente todo dia.
- **Nuvem**: hoje o app roda local. Se quiser acessar de qualquer lugar sem
  precisar ligar seu computador, dá pra publicar de graça no Streamlit
  Community Cloud, ou usar um serviço pago tipo Railway/Render.
