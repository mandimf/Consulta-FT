import streamlit as st
import pandas as pd
import re

st.set_page_config(
    page_title="Catálogo Técnico FT | CFS",
    page_icon="📄",
    layout="centered"
)

# ---------------------------------------------------------
# 1. AUTENTICAÇÃO BLINDADA
# ---------------------------------------------------------
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

# ---------------------------------------------------------
# 2. LEITURA E NORMALIZAÇÃO AUTOMÁTICA
# ---------------------------------------------------------
URL_PARTE_1 = "https://docs.google.com/spreadsheets/d/"
URL_PARTE_2 = "1B-qyvNzkGi3FQJr92zVH_eaulh8YXZain7KoeTUecP4"
URL_PARTE_3 = "/export?format=csv"
DEFAULT_CSV_URL = URL_PARTE_1 + URL_PARTE_2 + URL_PARTE_3

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
        filtro_validos = ~df["Produto"].str.strip().isin(["", "-", "nan"])
        df = df[filtro_validos]

    return df

def extrair_dicionario_ativos(row, df_cols):
    ativos_dict = {}
    invalidos = {"-", "--", "---", "", "nan", "none", "ausente", "e"}
    col_garantias = "Principios_Ativos_Garantias"

    if col_garantias in df_cols:
        bruto = str(row.get(col_garantias, "-")).strip()
        if bruto.lower() not in invalidos:
            partes = [p.strip() for p in bruto.split("|") if p.strip()]
            for parte in partes:
                if ":" in parte:
                    k, v = parte.split(":", 1)
                    k_limpo, v_limpo = k.strip(), v.strip()
                    if v_limpo.lower() not in invalidos:
                        ativos_dict[k_limpo] = v_limpo
                else:
                    if parte.lower() not in invalidos:
                        ativos_dict["Garantia / Ativo"] = parte
    else:
        colunas_meta = {
            "ID_Produto", "Categoria", "Marca_Linha", "Produto",
            "Estado_Fisico", "Estado", "Composicao", "Composição",
            "Observacoes"
        }
        for col in df_cols:
            if col not in colunas_meta:
                val = str(row.get(col, "-")).strip()
                if val.lower() not in invalidos:
                    ativos_dict[col.replace("_", " ")] = val

    return ativos_dict

# ---------------------------------------------------------
# 3. CARREGAMENTO EM MEMÓRIA
# ---------------------------------------------------------
try:
    df_base = carregar_base()
except Exception:
    st.error("⚠️ Erro ao ler planilha. Verifique se o link é público.")
    st.stop()

if df_base.empty:
    st.warning("⚠️ A base de dados está vazia ou inacessível.")
    st.stop()

col_est = "Estado_Fisico" if "Estado_Fisico" in df_base.columns else "Estado"
if col_est not in df_base.columns:
    col_est = None

col_comp = "Composicao" if "Composicao" in df_base.columns else "Composição"
if col_comp not in df_base.columns:
    col_comp = None

mapa_ativos = []
ativos_unicos = set()

for _, row in df_base.iterrows():
    d_ativos = extrair_dicionario_ativos(row, df_base.columns)
    mapa_ativos.append(d_ativos)
    for k in d_ativos.keys():
        nome_limpo = re.sub(r"\s*%\s
