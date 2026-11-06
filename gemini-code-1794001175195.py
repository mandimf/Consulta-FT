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
        nome_limpo = re.sub(r"\s*%\s*$", "", k).strip()
        ativos_unicos.add(nome_limpo)

df_base["_Ativos_Dict"] = mapa_ativos

# ---------------------------------------------------------
# 4. INTERFACE E FILTROS INTELIGENTES
# ---------------------------------------------------------
st.title("📄 Consulta Rápida de FT")

busca_rapida = st.text_input(
    "🔍 Busca Rápida (Produto, código ou ingrediente):",
    placeholder="Ex: 591, P98, Salplus, BHA, Tocoferol..."
)

col_f1, col_f2 = st.columns(2)

with col_f1:
    cats = ["Todas"] + sorted(df_base["Categoria"].unique().tolist())
    filtro_cat = st.selectbox("1️⃣ Categoria:", cats)

df_filtrado = df_base.copy()
if filtro_cat != "Todas":
    df_filtrado = df_filtrado[df_filtrado["Categoria"] == filtro_cat]

with col_f2:
    if col_est:
        est_lista = [
            e for e in df_filtrado[col_est].unique()
            if str(e).strip() not in ["-", ""]
        ]
        opcoes_est = ["Todos"] + sorted(est_lista)
        filtro_est = st.selectbox("2️⃣ Estado Físico:", opcoes_est)
        if filtro_est != "Todos":
            df_filtrado = df_filtrado[df_filtrado[col_est] == filtro_est]

ativos_selecionados = st.multiselect(
    "3️⃣ Princípios Ativos (exibe produtos que contêm TODOS):",
    options=sorted(list(ativos_unicos)),
    placeholder="Selecione um ou mais ativos (Ex: BHT, BHA)..."
)

if ativos_selecionados:
    def contem_todos_ativos(d_prod):
        chaves = [k.lower() for k in d_prod.keys()]
        return all(
            any(sel.lower() in ch for ch in chaves)
            for sel in ativos_selecionados
        )

    mascara_ativos = df_filtrado["_Ativos_Dict"].apply(contem_todos_ativos)
    df_filtrado = df_filtrado[mascara_ativos]

if busca_rapida.strip():
    termo = busca_rapida.strip().lower()
    m_prod = df_filtrado["Produto"].str.lower().str.contains(termo, na=False)
    m_comp = (
        df_filtrado[col_comp].str.lower().str.contains(termo, na=False)
        if col_comp else False
    )
    m_ativ = df_filtrado["_Ativos_Dict"].apply(
        lambda d: termo in str(d).lower()
    )
    df_filtrado = df_filtrado[m_prod | m_comp | m_ativ]

if df_filtrado.empty:
    st.info("Nenhum produto encontrado para estes filtros.")
    st.stop()

st.caption(f"✅ **{len(df_filtrado)}** produto(s) encontrado(s)")

produto_selecionado = st.selectbox(
    "4️⃣ Selecione o Produto:",
    df_filtrado["Produto"].tolist()
)

linha = df_filtrado[df_filtrado["Produto"] == produto_selecionado].iloc[0]
ativos_produto = linha["_Ativos_Dict"]

st.divider()

# ---------------------------------------------------------
# 5. CARTÃO DE EXIBIÇÃO DA FICHA TÉCNICA
# ---------------------------------------------------------
st.subheader(f"📌 {linha['Produto']}")

marca_val = linha.get("Marca_Linha", "-")
marca_str = f" | Linha: **{marca_val}**" if marca_val != "-" else ""

id_val = linha.get("ID_Produto", "-")
id_str = f"`{id_val}` | " if id_val != "-" else ""

st.markdown(f"{id_str}Categoria: **{linha['Categoria']}**{marca_str}")

if col_est:
    st.markdown(f"**Estado Físico:** `{linha[col_est]}`")

st.markdown("#### 🧪 Garantias / Princípios Ativos")
linhas_zap = []
if ativos_produto:
    for nome_at, val_at in ativos_produto.items():
        st.markdown(f"- **{nome_at}:** {val_at}")
        linhas_zap.append(f"  • {nome_at}: {val_at}")
else:
    st.write("*Sem níveis de garantia específicos destacados.*")

comp_txt = str(linha[col_comp]).strip() if col_comp else "-"
if comp_txt in ["-", "", "nan"] and "Outros_Ativos" in linha:
    comp_txt = str(linha["Outros_Ativos"]).strip()

st.markdown("#### 📋 Composição Básica")
st.info(comp_txt)

obs_val = str(linha.get("Observacoes", "-")).strip()
if obs_val not in ["-", "", "nan"]:
    st.markdown(f"**💡 Aplicação / Observações:** {obs_val}")

# ---------------------------------------------------------
# 6. BLOCO PRONTO PARA COPIAR (WHATSAPP / E-MAIL)
# ---------------------------------------------------------
with st.expander("📲 Copiar Resumo (WhatsApp / E-mail)", expanded=True):
    resumo = f"*{linha['Produto']}* ({linha['Categoria']})\n"
    if col_est:
        resumo += f"▪ *Estado Físico:* {linha[col_est]}\n"
    if linhas_zap:
        resumo += "▪ *Garantias / Ativos:*\n" + "\n".join(linhas_zap) + "\n"
    resumo += f"▪ *Composição:* {comp_txt}"
    st.code(resumo, language="markdown")

st.divider()
c1, c2 = st.columns(2)
with c1:
    if st.button("🔄 Atualizar Dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with c2:
    if st.button("🚪 Sair", use_container_width=True):
        st.session_state["autenticado"] = False
        st.rerun()