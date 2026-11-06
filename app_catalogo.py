import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Resumo de FT | CFS",
    page_icon="📄",
    layout="centered"
)

# -------------------------------------------------------------------------
# LOGIN SIMPLIFICADO E À PROVA DE ERROS (Não trava se Secrets estiver vazio)
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
# CARREGAMENTO DAS ABAS DA PLANILHA
# -------------------------------------------------------------------------
SHEET_URL_BASE = "https://docs.google.com/spreadsheets/d/102Q3VkPmHuErDCeb73Jfe3NA6xxjyyEleO7ALzbnREQ/gviz/tq?tqx=out:csv&sheet="

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
    url = f"{SHEET_URL_BASE}{nome_aba.replace(' ', '%20')}"
    try:
        df = pd.read_csv(url).dropna(how="all")
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        return df.fillna("-")
    except Exception:
        return pd.DataFrame()

# -------------------------------------------------------------------------
# INTERFACE DE CONSULTA DIRETA (RESUMO DA FT)
# -------------------------------------------------------------------------
st.title("📄 Resumo de Ficha Técnica")

col_linha, col_busca = st.columns([1, 1])

with col_linha:
    aba_selecionada = st.selectbox("1️⃣ Escolha a Linha:", CATEGORIAS_ABAS)

df = carregar_aba(aba_selecionada)

if df.empty:
    st.warning("⚠️ Não foi possível carregar os dados desta aba. Verifique o compartilhamento da planilha.")
    st.stop()

col_produto = df.columns[0]
col_estado = "Estado" if "Estado" in df.columns else None
col_comp = "Composição" if "Composição" in df.columns else None
colunas_ativos = [c for c in df.columns if c not in [col_produto, col_estado, col_comp]]

with col_busca:
    filtro_nome = st.text_input("🔍 Filtrar nome ou ativo (opcional):", placeholder="Ex: 578, BHA, Líquido...")

df_filtrado = df.copy()
if filtro_nome:
    mascara = df_filtrado.astype(str).apply(
        lambda x: x.str.lower().str.contains(filtro_nome.lower(), na=False)
    ).any(axis=1)
    df_filtrado = df_filtrado[mascara]

if df_filtrado.empty:
    st.info("Nenhum produto encontrado com esse termo.")
    st.stop()

produto_escolhido = st.selectbox(
    "2️⃣ Selecione o Produto:",
    df_filtrado[col_produto].tolist()
)

linha = df_filtrado[df_filtrado[col_produto] == produto_escolhido].iloc[0]

st.divider()

# -------------------------------------------------------------------------
# EXIBIÇÃO DO RESUMO DA FT
# -------------------------------------------------------------------------
st.subheader(f"📌 {linha[col_produto]}")
st.caption(f"Categoria: {aba_selecionada}")

if col_estado:
    st.markdown(f"**Estado Físico:** `{linha[col_estado]}`")

st.markdown("#### 🧪 Garantias / Princípios Ativos")
ativos_presentes = []
for ativo in colunas_ativos:
    valor = str(linha[ativo]).strip()
    if valor not in ["-", "", "nan", "Ausente"]:
        st.markdown(f"- **{ativo}:** {valor}")
        ativos_presentes.append(f"• {ativo}: {valor}")

if not ativos_presentes:
    st.write("*Sem níveis de garantia destacados em colunas específicas.*")

if col_comp:
    st.markdown("#### 📋 Composição Básica")
    st.info(linha[col_comp])

# Bloco pronto para copiar
with st.expander("📲 Copiar Resumo (WhatsApp / E-mail)", expanded=True):
    texto_resumo = f"*{linha[col_produto]}* ({aba_selecionada})\n"
    if col_estado:
        texto_resumo += f"▪ *Estado Físico:* {linha[col_estado]}\n"
    if ativos_presentes:
        texto_resumo += "▪ *Garantias / Ativos:*\n" + "\n".join(ativos_presentes) + "\n"
    if col_comp:
        texto_resumo += f"▪ *Composição:* {linha[col_comp]}"
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
