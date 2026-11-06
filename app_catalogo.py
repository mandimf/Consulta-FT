import streamlit as st
import pandas as pd
import requests
import json

st.set_page_config(
    page_title="Resumo de FT | CFS",
    page_icon="📄",
    layout="centered"
)

# -------------------------------------------------------------------------
# CAMADA DE SEGURANÇA (LOGIN)
# -------------------------------------------------------------------------
def verificar_autenticacao():
    if st.session_state.get("autenticado", False):
        return True

    try:
        senha_correta = st.secrets["SENHA_ACESSO"]
    except Exception:
        senha_correta = "cfs2026"

    st.subheader("🔒 Acesso Restrito | Resumo de FT")
    with st.form("form_login"):
        senha_digitada = st.text_input("Senha de Acesso:", type="password")
        if st.form_submit_button("Entrar", use_container_width=True):
            if senha_digitada == senha_correta:
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("❌ Senha incorreta.")
    return False

if not verificar_autenticacao():
    st.stop()

# -------------------------------------------------------------------------
# LEITURA E LIMPEZA ROBUSTA DOS DADOS (JSON GVIZ)
# -------------------------------------------------------------------------
SHEET_ID = "102Q3VkPmHuErDCeb73Jfe3NA6xxjyyEleO7ALzbnREQ"

CATEGORIAS_ABAS = [
    "AnOx Tradicionais",
    "AnOx Naturais",
    "Novamold",
    "Salplus",
    "Dresbond",
    "Outros"
]

@st.cache_data(ttl=300)
def carregar_aba(nome_aba):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:json&sheet={nome_aba.replace(' ', '%20')}"
    try:
        response = requests.get(url)
        text = response.text
        if "setResponse(" in text:
            json_str = text.split("setResponse(")[1].rsplit(");", 1)[0]
            data = json.loads(json_str)
            
            cols = [col.get('label', f'Col{i}').strip() for i, col in enumerate(data['table']['cols'])]
            rows_data = []
            for r in data['table']['rows']:
                row_vals = [cell.get('v', '') if cell else '' for cell in r.get('c', [])]
                rows_data.append(row_vals)
                
            df = pd.DataFrame(rows_data, columns=cols)
            df = df.loc[:, df.columns != '']
            df = df.dropna(how="all")
            
            if not df.empty:
                col_prod = df.columns[0]
                # Remove linhas vazias ou traços
                df = df[df[col_prod].notna() & (df[col_prod].astype(str).str.strip() != "") & (df[col_prod].astype(str).str.strip() != "-")]
                
            return df.fillna("-")
    except Exception:
        pass
    return pd.DataFrame()

# -------------------------------------------------------------------------
# INTERFACE DO APLICATIVO
# -------------------------------------------------------------------------
st.title("📄 Resumo de Ficha Técnica")

aba_selecionada = st.selectbox("1️⃣ Escolha a Linha (Categoria):", CATEGORIAS_ABAS)

df = carregar_aba(aba_selecionada)

if df.empty:
    st.warning("⚠️ Não foi possível carregar os dados desta aba. Verifique o compartilhamento da planilha.")
    st.stop()

# Identificação inteligente das colunas
col_produto = df.columns[0]
col_estado = None
for col in df.columns:
    if col.lower() in ["estado", "estado físico", "forma"]:
        col_estado = col
        break

col_comp = None
for col in df.columns:
    if "composição" in col.lower() or "composicao" in col.lower():
        col_comp = col
        break

colunas_ativos = [c for c in df.columns if c not in [col_produto, col_estado, col_comp] and c is not None]

# -------------------------------------------------------------------------
# FILTRO POR ESTADO FÍSICO
# -------------------------------------------------------------------------
df_filtrado = df.copy()

if col_estado:
    # Extrai valores únicos reais para montar o filtro do selectbox
    estados_unicos = sorted(list(set([str(x).strip() for x in df[col_estado].unique() if str(x).strip() not in ["-", "", "nan"] and not pd.isna(x)])))
    estados_disponiveis = ["Todos"] + estados_unicos
    
    filtro_estado_escolhido = st.selectbox("2️⃣ Filtrar por Estado Físico:", estados_disponiveis)
    
    if filtro_estado_escolhido != "Todos":
        df_filtrado = df_filtrado[df_filtrado[col_estado].astype(str).str.strip() == filtro_estado_escolhido]
else:
    st.info("ℹ️ Coluna de Estado Físico não identificada nesta aba.")

if df_filtrado.empty:
    st.warning("⚠️ Nenhum produto encontrado para o filtro selecionado.")
    st.stop()

# Seleção de Produto
produto_escolhido = st.selectbox(
    "3️⃣ Selecione o Produto:",
    df_filtrado[col_produto].tolist()
)

# Extração da linha exata correspondente ao produto selecionado
linha = df_filtrado[df_filtrado[col_produto] == produto_escolhido].iloc[0]

st.divider()

# -------------------------------------------------------------------------
# EXIBIÇÃO DO RESUMO DA FT (Limpo, sem duplicações de texto)
# -------------------------------------------------------------------------
st.subheader(f"📌 {linha[col_produto]}")
st.caption(f"Categoria: {aba_selecionada}")

if col_estado:
    st.markdown(f"**Estado Físico:** `{str(linha[col_estado]).strip()}`")

st.markdown("#### 🧪 Garantias / Princípios Ativos")
ativos_presentes = []
for ativo in colunas_ativos:
    valor = str(linha[ativo]).strip()
    # Filtra valores válidos e evita lixo/traços
    if valor and valor not in ["-", "", "nan", "Ausente", "NaN"]:
        st.markdown(f"- **{ativo}:** {valor}")
        ativos_presentes.append(f"• {ativo}: {valor}")

if not ativos_presentes:
    st.write("*Sem níveis de garantia destacados em colunas específicas.*")

if col_comp:
    st.markdown("#### 📋 Composição Básica")
    st.info(str(linha[col_comp]).strip())

# Bloco pronto para copiar
with st.expander("📲 Copiar Resumo (WhatsApp / E-mail)", expanded=True):
    texto_resumo = f"*{linha[col_produto]}* ({aba_selecionada})\n"
    if col_estado:
        texto_resumo += f"▪ *Estado Físico:* {str(linha[col_estado]).strip()}\n"
    if ativos_presentes:
        texto_resumo += "▪ *Garantias / Ativos:*\n" + "\n".join(ativos_presentes) + "\n"
    if col_comp:
        texto_resumo += f"▪ *Composição:* {str(linha[col_comp]).strip()}"
    st.code(texto_resumo, language="markdown")

st.divider()
col_b1, col_b2 = st.columns(2)
with col_b1:
    if st.button("🔄 Atualizar Planilha", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with col_b2:
    if st.button("🚪 Sair", use_container_width=True):
        st.session_state["autenticado"] = False
        st.rerun()
