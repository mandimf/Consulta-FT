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
# Aponta prioritariamente para a base completa de 91 produtos (7 colunas)
# Para trocar de planilha no futuro, basta alterar a URL abaixo nas Secrets ou aqui
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

    # Garante que linhas vazias sejam descartadas
    if "Produto" in df.columns:
        df = df[df["Produto"].str.strip().isin(["", "-", "nan"]) == False]

    return df

def extrair_dicionario_ativos(row, df_cols):
    """
    Suporta tanto o modelo de 7 colunas (Principios_Ativos_Garantias separados por '|')
    quanto o modelo Wide Flat Table (várias colunas de ativos).
    """
    ativos_dict = {}
    valores_invalidos = {"-", "--", "---", "", "nan", "none", "ausente", "e"}

    if "Principios_Ativos_Garantias" in df_cols:
        texto_bruto = str(row.get("Principios_Ativos_Garantias", "-")).strip()
        if texto_bruto.lower() not in valores_invalidos:
            partes = [p.strip() for p in texto_bruto.split("|") if p.strip()]
            for parte in partes:
                if ":" in parte:
                    k, v = parte.split(":", 1)
                    k_clean, v_clean = k.strip(), v.strip()
                    if v_clean.lower() not in valores_invalidos:
                        ativos_dict[k_clean] = v_clean
                else:
                    if parte.lower() not in valores_invalidos:
                        ativos_dict["Garantia / Ativo"] = parte
    else:
        colunas_meta = {
            "ID_Produto", "Categoria", "Marca_Linha", "Produto",
            "Estado_Fisico", "Estado", "Composicao", "Composição", "Observacoes"
        }
        for col in df_cols:
            if col not in colunas_meta:
                val = str(row.get(col, "-")).strip()
                if val.lower() not in valores_invalidos:
                    ativos_dict[col.replace("_", " ")] = val

    return ativos_dict

# -------------------------------------------------------------------------
# 3. CARREGAMENTO E PREPARAÇÃO EM MEMÓRIA
# -------------------------------------------------------------------------
try:
    df_base = carregar_base()
except Exception as e:
    st.error("⚠️ Erro ao conectar à planilha. Verifique se o compartilhamento está como 'Qualquer pessoa com o link pode ver'.")
    st.stop()

if df_base.empty:
    st.warning("⚠️ A base de dados está vazia ou inacessível.")
    st.stop()

col_estado = "Estado_Fisico" if "Estado_Fisico" in df_base.columns else ("Estado" if "Estado" in df_base.columns else None)
col_comp = "Composicao" if "Composicao" in df_base.columns else ("Composição" if "Composição" in df_base.columns else None)

# Pré-processa os ativos de cada linha para permitir filtro rápido por princípio ativo
mapa_ativos_por_linha = []
todos_ativos_unicos = set()

for _, row in df_base.iterrows():
    d_ativos = extrair_dicionario_ativos(row, df_base.columns)
    mapa_ativos_por_linha.append(d_ativos)
    for k in d_ativos.keys():
        # Normaliza o nome do ativo para o filtro (remove '%' extra)
        nome_ativo_limpo = re.sub(r"\s*%\s*$", "", k).strip()
        todos_ativos_unicos.add(nome_ativo_limpo)

df_base["_Ativos_Dict"] = mapa_ativos_por_linha

# -------------------------------------------------------------------------
# 4. INTERFACE DE CONSULTA E FILTROS INTELIGENTES
# -------------------------------------------------------------------------
st.title("📄 Consulta Rápida de FT")

busca_rapida = st.text_input(
    "🔍 Busca Rápida (Nome do produto, código ou ingrediente):",
    placeholder="Ex: 591, P98, Salplus, BHA, Tocoferol..."
)

col_f1, col_f2, col_f3 = st.columns(3)

with col_f1:
    lista_categorias = ["Todas"] + sorted(df_base["Categoria"].unique().tolist())
    filtro_cat = st.selectbox("1️⃣ Categoria:", lista_categorias)

df_filtrado = df_base.copy()
if filtro_cat != "Todas":
    df_filtrado = df_filtrado[df_filtrado["Categoria"] == filtro_cat]

with col_f2:
    if col_estado:
        estados_unicos = sorted([e for e in df_filtrado[col_estado].unique() if str(e).strip() not in ["-", ""]])
        filtro_est = st.selectbox("2️⃣ Estado Físico:", ["Todos"] + estados_unicos)
        if filtro_est != "Todos":
            df_filtrado = df_filtrado[df_filtrado[col_estado] == filtro_est]

with col_f3:
    lista_ativos = ["Todos"] + sorted(list(todos_ativos_unicos))
    filtro_ativo = st.selectbox("3️⃣ Princípio Ativo:", lista_ativos)
    if filtro_ativo != "Todos":
        df_filtrado = df_filtrado[
            df_filtrado["_Ativos_Dict"].apply(
                lambda d: any(filtro_ativo.lower() in k.lower() for k in d.keys())
            )
        ]

if busca_rapida.strip():
    termo = busca_rapida.strip().lower()
    mascara_busca = (
        df_filtrado["Produto"].str.lower().str.contains(termo, na=False) |
        df_filtrado[col_comp].str.lower().str.contains(termo, na=False) |
        df_filtrado["_Ativos_Dict"].apply(lambda d: termo in str(d).lower())
    )
    df_filtrado = df_filtrado[mascara_busca]

if df_filtrado.empty:
    st.info("Nenhum produto encontrado com os filtros selecionados.")
    st.stop()

st.caption(f"✅ **{len(df_filtrado)}** produto(s) encontrado(s)")

produto_selecionado = st.selectbox(
    "4️⃣ Selecione o Produto:",
    df_filtrado["Produto"].tolist()
)

linha = df_filtrado[df_filtrado["Produto"] == produto_selecionado].iloc[0]
ativos_produto = linha["_Ativos_Dict"]

st.divider()

# -------------------------------------------------------------------------
# 5. CARTÃO DE EXIBIÇÃO DA FICHA TÉCNICA
# -------------------------------------------------------------------------
st.subheader(f"📌 {linha['Produto']}")
marca_str = f" | Linha: **{linha['Marca_Linha']}**" if "Marca_Linha" in linha and linha["Marca_Linha"] != "-" else ""
id_str = f"`{linha['ID_Produto']}` | " if "ID_Produto" in linha and linha["ID_Produto"] != "-" else ""
st.markdown(f"{id_str}Categoria: **{linha['Categoria']}**{marca_str}")

if col_estado:
    st.markdown(f"**Estado Físico:** `{linha[col_estado]}`")

st.markdown("#### 🧪 Garantias / Princípios Ativos")
linhas_zap_ativos = []
if ativos_produto:
    for nome_at, val_at in ativos_produto.items():
        st.markdown(f"- **{nome_at}:** {val_at}")
        linhas_zap_ativos.append(f"  • {nome_at}: {val_at}")
else:
    st.write("*Sem níveis de garantia específicos destacados.*")

composicao_texto = str(linha[col_comp]).strip() if col_comp else "-"
if composicao_texto in ["-", "", "nan"] and "Outros_Ativos" in linha:
    # Fallback automático caso use a planilha Wide que tinha deslocamento de coluna
    composicao_texto = str(linha["Outros_Ativos"]).strip()

st.markdown("#### 📋 Composição Básica")
st.info(composicao_texto)

if "Observacoes" in linha and str(linha["Observacoes"]).strip() not in ["-", "", "nan"]:
    st.markdown(f"**💡 Aplicação / Observações:** {linha['Observacoes']}")

# -------------------------------------------------------------------------
# 6. BLOCO PRONTO PARA WHATSAPP / E-MAIL
# -------------------------------------------------------------------------
with st.expander("📲 Copiar Resumo (WhatsApp / E-mail)", expanded=True):
    resumo = f"*{linha['Produto']}* ({linha['Categoria']})\n"
    if col_estado:
        resumo += f"▪ *Estado Físico:* {linha[col_estado]}\n"
    if linhas_zap_ativos:
        resumo += "▪ *Garantias / Ativos:*\n" + "\n".join(linhas_zap_ativos) + "\n"
    resumo += f"▪ *Composição:* {composicao_texto}"
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
