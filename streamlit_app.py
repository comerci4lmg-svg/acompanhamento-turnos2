from __future__ import annotations

from datetime import date, datetime
import re
import unicodedata

import pandas as pd
import requests
import streamlit as st


st.set_page_config(page_title="Acompanhamento de Turnos GO", page_icon="📊", layout="wide")
GRUPOS = ["GOOL", "GOOC", "GOOK", "GOOH"]
MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def normalizar_nome(valor):
    texto = unicodedata.normalize("NFKD", str(valor))
    texto = "".join(letra for letra in texto if not unicodedata.combining(letra))
    return re.sub(r"[^A-Z0-9]+", "_", texto.upper()).strip("_")


@st.cache_data(ttl=60, show_spinner=False)
def carregar_turnos():
    configuracao = st.secrets["apps_script"]
    resposta = requests.post(
        configuracao["url"],
        json={"action": "read_turnos", "token": configuracao["read_token"]},
        timeout=60,
    )
    resposta.raise_for_status()
    payload = resposta.json()
    if not payload.get("ok"):
        raise RuntimeError(payload.get("error", "Apps Script recusou a leitura."))
    dados = pd.DataFrame(payload.get("registros", []), columns=payload.get("colunas", []))
    return dados, payload.get("atualizadoEm", "")


def preparar_dados(brutos):
    dados = brutos.copy()
    dados.columns = [normalizar_nome(coluna) for coluna in dados.columns]
    obrigatorias = {"PREFIXO", "INICIO_TURNO"}
    ausentes = sorted(obrigatorias - set(dados.columns))
    if ausentes:
        raise ValueError("Colunas ausentes na planilha: " + ", ".join(ausentes))

    for coluna in ["INICIO_TURNO", "SAIDA_PREVISTA", "FIM_TURNO"]:
        if coluna not in dados.columns:
            dados[coluna] = pd.NaT
        dados[coluna] = pd.to_datetime(dados[coluna], errors="coerce", dayfirst=True)

    dados["PREFIXO"] = dados["PREFIXO"].astype(str).str.strip().str.upper()
    dados["GRUPO"] = dados["PREFIXO"].str[:4]
    dados["DATA"] = dados["INICIO_TURNO"].dt.date
    dados = dados[dados["GRUPO"].isin(GRUPOS)].copy()
    dados["SITUACAO"] = dados["FIM_TURNO"].apply(
        lambda valor: "EM ANDAMENTO" if pd.isna(valor) else "ENCERRADO"
    )
    dados["DURACAO_HORAS"] = (
        (dados["FIM_TURNO"] - dados["INICIO_TURNO"]).dt.total_seconds() / 3600
    ).round(2)
    dados["DIFERENCA_FECHAMENTO_MIN"] = (
        (dados["FIM_TURNO"] - dados["SAIDA_PREVISTA"]).dt.total_seconds() / 60
    ).round().astype("Int64")
    for coluna in ["PARTICIPA_ESCALA", "OBSERVACAO"]:
        if coluna not in dados.columns:
            dados[coluna] = ""
    if "HIST_TURMA_PLANTAO_ID" not in dados.columns:
        dados["HIST_TURMA_PLANTAO_ID"] = range(1, len(dados) + 1)
    return dados.sort_values(["INICIO_TURNO", "PREFIXO"], na_position="last")


st.title("Acompanhamento de Turnos GO")
st.caption("Abertura e fechamento reais • dados atualizados pelo bot")
if st.sidebar.button("Atualizar dados", type="primary", use_container_width=True):
    carregar_turnos.clear()
    st.rerun()

try:
    with st.spinner("Lendo a planilha de turnos..."):
        brutos, atualizado_em = carregar_turnos()
        if brutos.empty:
            st.warning("A planilha ainda está vazia. Execute o teste do bot para enviar os dados.")
            st.stop()
        dados = preparar_dados(brutos)
except Exception as erro:
    st.error("Não foi possível consultar a planilha de turnos.")
    st.code(str(erro))
    st.stop()

if atualizado_em:
    try:
        atualizado = datetime.fromisoformat(atualizado_em).astimezone()
        st.caption(f"Última carga do bot: {atualizado:%d/%m/%Y %H:%M:%S}")
    except ValueError:
        st.caption("Última carga do bot: " + atualizado_em)

datas_validas = pd.to_datetime(dados["DATA"], errors="coerce").dropna()
ano_padrao = int(datas_validas.dt.year.max()) if not datas_validas.empty else date.today().year
meses = datas_validas[datas_validas.dt.year.eq(ano_padrao)].dt.month
mes_padrao = int(meses.max()) if not meses.empty else date.today().month
ano = st.sidebar.number_input("Ano", min_value=2020, max_value=2100, value=ano_padrao)
mes = st.sidebar.selectbox(
    "Mês", range(1, 13), index=mes_padrao - 1,
    format_func=lambda valor: MESES[valor - 1],
)

datas = pd.to_datetime(dados["DATA"], errors="coerce")
filtrado = dados[datas.dt.year.eq(ano) & datas.dt.month.eq(mes)].copy()
grupos = st.sidebar.multiselect("Grupos", GRUPOS, default=GRUPOS)
filtrado = filtrado[filtrado["GRUPO"].isin(grupos)]
equipes = st.sidebar.multiselect("Equipes", sorted(filtrado["PREFIXO"].dropna().unique()))
if equipes:
    filtrado = filtrado[filtrado["PREFIXO"].isin(equipes)]
situacoes = st.sidebar.multiselect(
    "Situação", ["EM ANDAMENTO", "ENCERRADO"], default=["EM ANDAMENTO", "ENCERRADO"]
)
filtrado = filtrado[filtrado["SITUACAO"].isin(situacoes)]

metricas = st.columns(4)
metricas[0].metric("Turnos", filtrado["HIST_TURMA_PLANTAO_ID"].nunique())
metricas[1].metric("Equipes", filtrado["PREFIXO"].nunique())
metricas[2].metric("Em andamento", int(filtrado["SITUACAO"].eq("EM ANDAMENTO").sum()))
mediana = filtrado["DURACAO_HORAS"].median()
metricas[3].metric("Duração mediana", "—" if pd.isna(mediana) else f"{mediana:.1f} h")

colunas = [
    "DATA", "GRUPO", "PREFIXO", "INICIO_TURNO", "SAIDA_PREVISTA", "FIM_TURNO",
    "SITUACAO", "DURACAO_HORAS", "DIFERENCA_FECHAMENTO_MIN",
    "PARTICIPA_ESCALA", "OBSERVACAO",
]
aba_turnos, aba_resumo = st.tabs(["Turnos", "Resumo diário"])
with aba_turnos:
    st.subheader(f"Turnos de {MESES[mes - 1]} de {ano}")
    st.dataframe(
        filtrado[colunas], hide_index=True, use_container_width=True, height=620,
        column_config={
            "DATA": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "INICIO_TURNO": st.column_config.DatetimeColumn("Abertura", format="DD/MM/YYYY HH:mm"),
            "SAIDA_PREVISTA": st.column_config.DatetimeColumn("Saída prevista", format="DD/MM/YYYY HH:mm"),
            "FIM_TURNO": st.column_config.DatetimeColumn("Fechamento", format="DD/MM/YYYY HH:mm"),
            "DURACAO_HORAS": st.column_config.NumberColumn("Duração (h)", format="%.2f"),
            "DIFERENCA_FECHAMENTO_MIN": st.column_config.NumberColumn("Diferença fechamento (min)", format="%d"),
        },
    )
with aba_resumo:
    if filtrado.empty:
        st.info("Nenhum turno encontrado para os filtros selecionados.")
    else:
        resumo = filtrado.pivot_table(
            index="DATA", columns="GRUPO", values="HIST_TURMA_PLANTAO_ID",
            aggfunc="nunique", fill_value=0,
        ).reindex(columns=GRUPOS, fill_value=0)
        resumo["TOTAL"] = resumo.sum(axis=1)
        st.dataframe(resumo, use_container_width=True)
        if grupos:
            st.line_chart(resumo[grupos])

st.download_button(
    "Baixar tabela filtrada em CSV",
    filtrado[colunas].to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
    file_name=f"acompanhamento_turnos_{ano}_{mes:02}.csv",
    mime="text/csv",
)
