import streamlit as st
import pandas as pd
import re

st.set_page_config(
    page_title="Catálogo Técnico FT | CFS",
    page_icon="📄",
    layout="centered"
)

# -------------------------------------------------------------------------
# 1. AUTENTICAÇÃO BLINDADA (À prova de TOMLDecodeError)
# -------------------------------------------------------------------------
def verificar_autenticacao():
    if st.session_state.get("autenticado", False):
        return True

    senha_correta = "cfs2026"
    try:
        if "SENHA_ACESSO" in st.secrets:
            senha_correta = str(st.secrets["SENHA_ACESSO"]).strip()
    except Exception:
        pass

    st.subheader("🔒 Acesso Restrito | Consulta de FT")
    with st.form("form_login"):
        senha_digitada = st.text_input("Senha de Acesso:", type="password")
        if st.form_submit_button("Entrar", use_container_width=True):
            if senha_digitada.strip() == senha_correta:
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("❌ Senha incorreta.")
    return False

if not verificar_autenticacao():
    st.stop()

# -------------------------------------------------------------------------
# 2. ENGENHARIA DE DADOS: LEITURA E NORMALIZAÇÃO AUTOMÁTICA
# -------------------------------------------------------------------------
# Configurado para ler a base consolidada de 91 produtos via link público CSV
# Também pode ser sobrescrito via Secrets (SHEET_CSV_URL) se desejar
DEFAULT_CSV_URL = "https://docs.google.com/spreadsheets/d/1B-qyvNzkGi3FQJr92zVH_eaulh8YXZain7KoeTUecP4/export?format=csv"

@st.cache_data(ttl=300)
def carregar_base():
    url = DEFAULT_CSV_URL
    try:
        if "SHEET_CSV_URL" in st.secrets:
            url = st.secrets["SHEET_CSV_URL"]
    except Exception:
        pass

    df = pd.read_csv(url, dtype=str).dropna(how="all")
    df.columns = [str(c).strip() for c in df.columns]
    df = df.fillna("-")

    if "Produto" in df.columns:
        df = df[~df["Produto"].str.strip().isin(["", "-", "nan"])]

    return df

def extrair_dicionario_ativos(row, df_cols):
    """
    Suporta tanto o modelo de 7 colunas (Principios_Ativos_Garantias separados por '|')
    quanto o modelo Wide Flat Table (várias colunas de ativos).
    """
    ativos_dict = {}
    valores_invalidos = {"-", "--", "---", "", "nan", "none", "ausente", "e"}

    if "Principios_Ativos_Garantias" in df_cols:
        texto_bruto = str(row.get("Principios_Ativos_Garant
