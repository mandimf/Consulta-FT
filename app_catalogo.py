import streamlit as st
import pandas as pd

st.set_page_config(page_title="Resumo de FT | CFS", page_icon="📄", layout="centered")

NEW_SHEET_ID = "1cFPQ1MFNQ-PHhR24u-mrwjP5G8bDPV6q1gAK4fuKMfU"
URL_FLAT_TABLE = f"https://docs.google.com/spreadsheets/d/{NEW_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Base_Dados_Geral"

def verificar_autenticacao():
    if st.session_state.get("autenticado", False):
        return True
    try:
        senha_correta = st.secrets["SENHA_ACESSO"]
    except Exception:
        senha_correta = "cfs2026"

    st.subheader("🔒 Acesso Restrito")
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

@st.cache_data(ttl=300)
def carregar_dados():
    try:
        df = pd.read_csv(URL_FLAT_TABLE).dropna(how="all")
        df.columns = df.columns.str.strip()
        df = df[df["Produto"].notna() & (df["Produto"].astype(str).str.strip() != "-")]
        return df.fillna("-")
    except Exception:
        return pd.DataFrame()

df_base = carregar_dados()

st.title("📄 Resumo de Ficha Técnica")

if df_base.empty:
    st.warning("⚠️ Não foi possível carregar a base de dados.")
    st.stop()

col1, col2 = st.columns(2)
with col1:
    categorias = ["Todas"] + sorted(list(df_base["Categoria"].unique()))
    cat_escolhida = st.selectbox("1️⃣ Categoria:", categorias)

df_filtrado = df_base if cat_escolhida == "Todas" else df_base[df_base["Categoria"] == cat_escolhida]

with col2:
    estados = ["Todos"] + sorted(list(df_filtrado["Estado_Fisico"].unique()))
    est_escolhido = st.selectbox("2️⃣ Estado Físico:", estados)

if est_escolhido != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Estado_Fisico"] == est_escolhido]

if df_filtrado.empty:
    st.info("Nenhum produto encontrado.")
    st.stop()

prod_escolhido = st.selectbox("3️⃣ Selecione o Produto:", df_filtrado["Produto"].tolist())
linha = df_filtrado[df_filtrado["Produto"] == prod_escolhido].iloc[0]

st.divider()

st.subheader(f"📌 {linha['Produto']}")
st.caption(f"Categoria: {linha['Categoria']} | Linha: {linha['Marca_Linha']}")
st.markdown(f"**Estado Físico:** `{linha['Estado_Fisico']}`")

st.markdown("#### 🧪 Garantias / Princípios Ativos")

colunas_excluidas = ['ID_Produto', 'Categoria', 'Marca_Linha', 'Produto', 'Estado_Fisico', 'Composicao', 'Observacoes']
colunas_ativos = [c for c in df_base.columns if c not in colunas_excluidas]

ativos_presentes = []
for ativo in colunas_ativos:
    valor = str(linha[ativo]).strip()
    if valor not in ["-", "", "nan", "Ausente", "NaN"]:
        nome_limpo = ativo.replace("_", " ")
        st.markdown(f"- **{nome_limpo}:** {valor}")
        ativos_presentes.append(f"• {nome_limpo}: {valor}")

if not ativos_presentes:
    st.write("*Nenhum nível de garantia destacado.*")

st.markdown("#### 📋 Composição Básica")
st.info(linha["Composicao"])

with st.expander("📲 Copiar Resumo", expanded=True):
    texto_zap = f"*{linha['Produto']}* ({linha['Marca_Linha']})\n▪ *Estado:* {linha['Estado_Fisico']}\n"
    if ativos_presentes:
        texto_zap += "▪ *Garantias:*\n" + "\n".join(ativos_presentes) + "\n"
    texto_zap += f"▪ *Composição:* {linha['Composicao']}"
    st.code(texto_zap, language="markdown")

st.divider()
col_b1, col_b2 = st.columns(2)
with col_b1:
    if st.button("🔄 Atualizar Base", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with col_b2:
    if st.button("🚪 Sair", use_container_width=True):
        st.session_state["autenticado"] = False
        st.rerun()
