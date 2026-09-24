from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
import re
import unicodedata
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st


st.set_page_config(page_title="Acompanhamento de Turnos GO", page_icon="📊", layout="wide")
GRUPOS = ["GOOL", "GOOC", "GOOK", "GOOH"]
EQUIPES_DESMOBILIZADAS = {
    "GOOL025M",
    "GOOK013M",
    "GOOK012M",
    "GOOK010M",
}
MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]
FUSO_GOIAS = ZoneInfo("America/Sao_Paulo")


def normalizar_nome(valor):
    texto = unicodedata.normalize("NFKD", str(valor))
    texto = "".join(letra for letra in texto if not unicodedata.combining(letra))
    return re.sub(r"[^A-Z0-9]+", "_", texto.upper()).strip("_")


def converter_data_hora(valores):
    """Aceita o ISO enviado pelo bot e datas brasileiras digitadas na planilha."""
    texto = valores.astype("string").str.strip()
    resultado = pd.Series(pd.NaT, index=valores.index, dtype="datetime64[ns]")
    formato_iso = texto.str.match(r"^\d{4}-\d{2}-\d{2}", na=False)
    resultado.loc[formato_iso] = pd.to_datetime(
        texto.loc[formato_iso], errors="coerce", format="ISO8601"
    )
    resultado.loc[~formato_iso] = pd.to_datetime(
        texto.loc[~formato_iso], errors="coerce", format="mixed", dayfirst=True
    )
    return resultado


def formatar_duracao(valor):
    if pd.isna(valor):
        return ""
    if not isinstance(valor, (int, float)):
        return str(valor)
    minutos_totais = round(abs(float(valor)) * 60)
    horas, minutos = divmod(minutos_totais, 60)
    sinal = "-" if float(valor) < 0 else ""
    return f"{sinal}{horas:02d}:{minutos:02d}"


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
        dados[coluna] = converter_data_hora(dados[coluna])

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
    dados["DURACAO"] = dados["DURACAO_HORAS"].apply(formatar_duracao)
    dados["DIFERENCA_FECHAMENTO_MIN"] = (
        (dados["FIM_TURNO"] - dados["SAIDA_PREVISTA"]).dt.total_seconds() / 60
    ).round().astype("Int64")
    for coluna in ["PARTICIPA_ESCALA", "OBSERVACAO"]:
        if coluna not in dados.columns:
            dados[coluna] = ""
    if "HIST_TURMA_PLANTAO_ID" not in dados.columns:
        dados["HIST_TURMA_PLANTAO_ID"] = range(1, len(dados) + 1)
    return dados.sort_values(["INICIO_TURNO", "PREFIXO"], na_position="last")


def domingo_de_pascoa(ano):
    """Calcula a Páscoa pelo algoritmo gregoriano de Meeus/Jones/Butcher."""
    a = ano % 19
    b = ano // 100
    c = ano % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return date(ano, mes, dia)


def feriados_brasil(ano):
    pascoa = domingo_de_pascoa(ano)
    return {
        date(ano, 1, 1),   # Confraternização Universal
        pascoa - timedelta(days=2),  # Sexta-feira Santa
        date(ano, 4, 21),  # Tiradentes
        date(ano, 5, 1),   # Dia do Trabalho
        pascoa + timedelta(days=60),  # Corpus Christi
        date(ano, 9, 7),   # Independência
        date(ano, 10, 12), # Nossa Senhora Aparecida
        date(ano, 11, 2),  # Finados
        date(ano, 11, 15), # Proclamação da República
        date(ano, 11, 20), # Consciência Negra
        date(ano, 12, 25), # Natal
    }


def ocultar_desmobilizadas_sem_movimento(dados, ano, mes):
    datas = pd.to_datetime(dados["DATA"], errors="coerce")
    equipes_com_movimento = set(
        dados.loc[datas.dt.year.eq(ano) & datas.dt.month.eq(mes), "PREFIXO"]
        .dropna()
        .astype(str)
    )
    manter = (
        ~dados["PREFIXO"].isin(EQUIPES_DESMOBILIZADAS)
        | dados["PREFIXO"].isin(equipes_com_movimento)
    )
    return dados[manter].copy()


def montar_mapa_mensal(dados, ano, mes, grupos, equipes_selecionadas):
    quantidade_dias = calendar.monthrange(ano, mes)[1]
    dias = list(range(1, quantidade_dias + 1))
    hoje = datetime.now(FUSO_GOIAS).date()
    feriados = feriados_brasil(ano)

    universo = dados[dados["GRUPO"].isin(grupos)].copy()
    if equipes_selecionadas:
        universo = universo[universo["PREFIXO"].isin(equipes_selecionadas)]
    universo = ocultar_desmobilizadas_sem_movimento(universo, ano, mes)
    equipes_mapa = sorted(universo["PREFIXO"].dropna().unique())

    datas = pd.to_datetime(universo["DATA"], errors="coerce")
    aberturas_mes = universo[datas.dt.year.eq(ano) & datas.dt.month.eq(mes)].copy()
    aberturas_mes["DIA"] = pd.to_datetime(aberturas_mes["DATA"]).dt.day
    presencas = set(zip(aberturas_mes["PREFIXO"], aberturas_mes["DIA"]))

    linhas = []
    for equipe in equipes_mapa:
        linha = {"EQUIPE": equipe}
        total = 0
        for dia in dias:
            data_celula = date(ano, mes, dia)
            if (equipe, dia) in presencas:
                valor = "1"
                total += 1
            elif data_celula > hoje:
                valor = ""
            elif data_celula in feriados:
                valor = "F"
            elif data_celula.weekday() == 5:
                valor = "S"
            elif data_celula.weekday() == 6:
                valor = "D"
            else:
                valor = "0"
            linha[dia] = valor
        linha["TOTAL"] = total
        linhas.append(linha)
    return pd.DataFrame(linhas).set_index("EQUIPE") if linhas else pd.DataFrame()


def estilo_mapa(valor):
    estilos = {
        "1": "background-color: #16a34a; color: white; font-weight: 700;",
        "0": "background-color: #dc2626; color: white; font-weight: 700;",
        "S": "background-color: #dbeafe; color: #1e3a8a; font-weight: 700;",
        "D": "background-color: #e2e8f0; color: #334155; font-weight: 700;",
        "F": "background-color: #fef3c7; color: #92400e; font-weight: 700;",
        "": "background-color: #f8fafc; color: #94a3b8;",
    }
    return estilos.get(str(valor), "font-weight: 700;")


def montar_tabela_horas(dados, ano, mes, grupos, equipes_selecionadas):
    quantidade_dias = calendar.monthrange(ano, mes)[1]
    dias = list(range(1, quantidade_dias + 1))
    hoje = datetime.now(FUSO_GOIAS).date()
    feriados = feriados_brasil(ano)

    universo = dados[dados["GRUPO"].isin(grupos)].copy()
    if equipes_selecionadas:
        universo = universo[universo["PREFIXO"].isin(equipes_selecionadas)]
    universo = ocultar_desmobilizadas_sem_movimento(universo, ano, mes)
    equipes_tabela = sorted(universo["PREFIXO"].dropna().unique())

    datas = pd.to_datetime(universo["DATA"], errors="coerce")
    turnos_mes = universo[datas.dt.year.eq(ano) & datas.dt.month.eq(mes)].copy()
    turnos_mes["DIA"] = pd.to_datetime(turnos_mes["DATA"]).dt.day

    linhas = []
    for equipe in equipes_tabela:
        linha = {"EQUIPE": equipe}
        total_horas = 0.0
        turnos_equipe = turnos_mes[turnos_mes["PREFIXO"].eq(equipe)]
        for dia in dias:
            data_celula = date(ano, mes, dia)
            turnos_dia = turnos_equipe[turnos_equipe["DIA"].eq(dia)]
            if not turnos_dia.empty:
                if turnos_dia["FIM_TURNO"].isna().any():
                    valor = "EM CURSO"
                else:
                    horas = float(turnos_dia["DURACAO_HORAS"].fillna(0).sum())
                    valor = round(horas, 1)
                    total_horas += horas
            elif data_celula > hoje:
                valor = ""
            elif data_celula in feriados:
                valor = "F"
            elif data_celula.weekday() == 5:
                valor = "S"
            elif data_celula.weekday() == 6:
                valor = "D"
            else:
                valor = 0.0
            linha[dia] = valor
        linha["TOTAL (h)"] = round(total_horas, 1)
        linhas.append(linha)
    return pd.DataFrame(linhas).set_index("EQUIPE") if linhas else pd.DataFrame()


def estilo_horas(valor):
    if isinstance(valor, (int, float)) and not pd.isna(valor):
        if float(valor) >= 8:
            return "background-color: #16a34a; color: white; font-weight: 700;"
        return "background-color: #dc2626; color: white; font-weight: 700;"
    estilos = {
        "EM CURSO": "background-color: #facc15; color: #713f12; font-weight: 700;",
        "S": "background-color: #dbeafe; color: #1e3a8a; font-weight: 700;",
        "D": "background-color: #e2e8f0; color: #334155; font-weight: 700;",
        "F": "background-color: #fef3c7; color: #92400e; font-weight: 700;",
        "": "background-color: #f8fafc; color: #94a3b8;",
    }
    return estilos.get(str(valor), "")


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
        atualizado = datetime.fromisoformat(atualizado_em).astimezone(FUSO_GOIAS)
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
metricas[3].metric("Duração mediana", "—" if pd.isna(mediana) else formatar_duracao(mediana))

colunas = [
    "DATA", "GRUPO", "PREFIXO", "INICIO_TURNO", "SAIDA_PREVISTA", "FIM_TURNO",
    "SITUACAO", "DURACAO", "DIFERENCA_FECHAMENTO_MIN",
    "PARTICIPA_ESCALA", "OBSERVACAO",
]
aba_turnos, aba_mapa, aba_horas, aba_resumo = st.tabs(
    ["Turnos", "Mapa mensal", "Horas trabalhadas", "Resumo diário"]
)
with aba_turnos:
    st.subheader(f"Turnos de {MESES[mes - 1]} de {ano}")
    st.dataframe(
        filtrado[colunas], hide_index=True, use_container_width=True, height=620,
        column_config={
            "DATA": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "INICIO_TURNO": st.column_config.DatetimeColumn("Abertura", format="DD/MM/YYYY HH:mm"),
            "SAIDA_PREVISTA": st.column_config.DatetimeColumn("Saída prevista", format="DD/MM/YYYY HH:mm"),
            "FIM_TURNO": st.column_config.DatetimeColumn("Fechamento", format="DD/MM/YYYY HH:mm"),
            "DURACAO": st.column_config.TextColumn("Duração"),
            "DIFERENCA_FECHAMENTO_MIN": st.column_config.NumberColumn("Diferença fechamento (min)", format="%d"),
        },
    )
with aba_mapa:
    st.subheader(f"Presença das equipes — {MESES[mes - 1]} de {ano}")
    st.caption(
        "🟩 1 = abriu turno  •  🟥 0 = não abriu em dia útil já transcorrido  •  "
        "S = sábado  •  D = domingo  •  F = feriado  •  vazio = dia futuro"
    )
    mapa = montar_mapa_mensal(dados, ano, mes, grupos, equipes)
    if mapa.empty:
        st.info("Nenhuma equipe disponível para os filtros selecionados.")
    else:
        colunas_dias = [coluna for coluna in mapa.columns if coluna != "TOTAL"]
        tabela_estilizada = (
            mapa.style
            .map(estilo_mapa, subset=colunas_dias)
            .set_properties(
                subset=["TOTAL"],
                **{"font-weight": "700", "background-color": "#f1f5f9"},
            )
        )
        st.dataframe(
            tabela_estilizada,
            use_container_width=True,
            height=min(800, 70 + len(mapa) * 35),
        )
with aba_horas:
    st.subheader(f"Horas trabalhadas — {MESES[mes - 1]} de {ano}")
    st.caption(
        "🟩 8 horas ou mais  •  🟥 menos de 8 horas  •  🟨 turno ainda em curso  •  "
        "S = sábado  •  D = domingo  •  F = feriado  •  vazio = dia futuro"
    )
    tabela_horas = montar_tabela_horas(dados, ano, mes, grupos, equipes)
    if tabela_horas.empty:
        st.info("Nenhuma equipe disponível para os filtros selecionados.")
    else:
        colunas_dias = [coluna for coluna in tabela_horas.columns if coluna != "TOTAL (h)"]
        horas_estilizadas = (
            tabela_horas.style
            .map(estilo_horas, subset=colunas_dias)
            .format(formatar_duracao, subset=colunas_dias + ["TOTAL (h)"])
            .set_properties(
                subset=["TOTAL (h)"],
                **{"font-weight": "700", "background-color": "#f1f5f9"},
            )
        )
        st.dataframe(
            horas_estilizadas,
            use_container_width=True,
            height=min(800, 70 + len(tabela_horas) * 35),
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
