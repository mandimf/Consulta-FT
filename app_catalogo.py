import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Resumo de FT | CFS",
    page_icon="📄",
    layout="centered"
)

# -------------------------------------------------------------------------
# LOGIN SIMPLIFICADO E À PROVA DE ERROS
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
# CARREGAMENTO E NORMALIZAÇÃO DOS DADOS DA PLANILHA
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
        df = pd.read_csv(url)
        # Remove linhas totalmente vazias
        df = df.dropna(how="all")
        # Remove colunas vazias ou Unnamed
        df = df.loc[:, ~df.columns.str.contains('^Unnamed', case=False)]
        
        # Limpar os nomes das colunas (remover espaços extras)
        df.columns = df.columns.str.strip()
        
        if not df.empty:
            col_prod = df.columns[0]
            # Remove linhas inválidas ou traços no nome do produto
            df = df[df[col_prod].notna() & (df[col_prod].astype(str).str.strip() != "-")]
            
        return df.fillna("-")
    except Exception:
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

# Identificar dinamicamente as colunas importantes ignorando maiúsculas/minúsculas
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
# FILTRO POR ESTADO FÍSICO (Pó, Líquido, etc.)
# -------------------------------------------------------------------------
df_filtrado = df.copy()

if col_estado:
    # Extrair lista única de estados limpos
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

# Obter linha exata do produto escolhido
linha = df_filtrado[df_filtrado[col_produto] == produto_escolhido].iloc[0]

st.divider()

# -------------------------------------------------------------------------
# EXIBIÇÃO DO RESUMO DA FT (Limpo e sem duplicações)
# -------------------------------------------------------------------------
st.subheader(f"📌 {linha[col_produto]}")
st.caption(f"Categoria: {aba_selecionada}")

if col_estado:
    st.markdown(f"**Estado Físico:** `{linha[col_estado]}`")

st.markdown("#### 🧪 Garantias / Princípios Ativos")
ativos_presentes = []
for ativo in colunas_ativos:
    valor = str(linha[ativo]).strip()
    if valor and valor not in ["-", "", "nan", "Ausente", "nan"]:
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
        texto_resuumo_val = str(linha[col_comp])
        texto_resumo += f"▪ *Composição:* {texto_resuumo_val}"
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
