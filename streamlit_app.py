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
    "GOOH013M",
    "GOOL007M",
    "GOOL021M",
    "GOOL024M",
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


# =============================================================================
# ESTILO / TEMA VISUAL (não altera nenhuma lógica ou matriz de dados abaixo)
# =============================================================================
def injetar_estilo():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        :root {
            --gg-primary: #0f766e;
            --gg-primary-dark: #0a4f4a;
            --gg-accent: #0ea5e9;
            --gg-bg: #f6f8fb;
            --gg-card: #ffffff;
            --gg-border: #e2e8f0;
            --gg-text: #1e293b;
            --gg-muted: #64748b;
        }

        .stApp {
            background: var(--gg-bg);
        }

        /* Cabeçalho principal em faixa gradiente */
        .gg-hero {
            background: linear-gradient(120deg, var(--gg-primary-dark) 0%, var(--gg-primary) 55%, var(--gg-accent) 130%);
            border-radius: 18px;
            padding: 28px 32px;
            margin-bottom: 22px;
            box-shadow: 0 10px 30px -12px rgba(15, 118, 110, 0.45);
        }
        .gg-hero h1 {
            color: #ffffff;
            font-size: 1.9rem;
            font-weight: 800;
            margin: 0 0 4px 0;
            letter-spacing: -0.02em;
        }
        .gg-hero p {
            color: rgba(255,255,255,0.85);
            margin: 0;
            font-size: 0.95rem;
        }
        .gg-hero .gg-badge-update {
            display: inline-block;
            margin-top: 10px;
            background: rgba(255,255,255,0.16);
            color: #ffffff;
            padding: 4px 12px;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
            border: 1px solid rgba(255,255,255,0.25);
        }

        /* Cards de métricas */
        div[data-testid="stMetric"] {
            background: var(--gg-card);
            border: 1px solid var(--gg-border);
            border-radius: 14px;
            padding: 14px 16px 10px 16px;
            box-shadow: 0 2px 8px -4px rgba(15, 23, 42, 0.08);
        }
        div[data-testid="stMetric"] label {
            color: var(--gg-muted) !important;
            font-weight: 600 !important;
            font-size: 0.8rem !important;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }
        div[data-testid="stMetricValue"] {
            color: var(--gg-text) !important;
            font-weight: 800 !important;
        }

        /* Abas */
        .stTabs [data-baseweb="tab-list"] {
            gap: 6px;
            background: var(--gg-card);
            padding: 6px;
            border-radius: 14px;
            border: 1px solid var(--gg-border);
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 10px;
            padding: 8px 16px;
            font-weight: 600;
            color: var(--gg-muted);
        }
        .stTabs [aria-selected="true"] {
            background: var(--gg-primary) !important;
            color: #ffffff !important;
        }

        /* Cabeçalhos de seção */
        .gg-section-title {
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 4px 0 2px 0;
        }
        .gg-section-title h3 {
            margin: 0;
            font-weight: 700;
            color: var(--gg-text);
        }
        .gg-section-sub {
            color: var(--gg-muted);
            font-size: 0.88rem;
            margin: 0 0 14px 0;
        }

        /* Legenda em chips */
        .gg-legend {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 6px 0 16px 0;
        }
        .gg-chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 5px 11px;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
            border: 1px solid rgba(0,0,0,0.06);
        }
        .gg-chip .gg-dot {
            width: 9px;
            height: 9px;
            border-radius: 50%;
            display: inline-block;
            flex-shrink: 0;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid var(--gg-border);
        }
        section[data-testid="stSidebar"] .gg-sidebar-title {
            font-weight: 800;
            font-size: 1.05rem;
            color: var(--gg-text);
            margin-bottom: 2px;
        }
        section[data-testid="stSidebar"] .gg-sidebar-sub {
            color: var(--gg-muted);
            font-size: 0.8rem;
            margin-bottom: 16px;
        }

        /* Botão primário */
        button[kind="primary"] {
            border-radius: 10px !important;
            font-weight: 700 !important;
        }

        /* DataFrames com cantos arredondados */
        div[data-testid="stDataFrame"] {
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid var(--gg-border);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def cabecalho_hero(atualizado_em_texto):
    st.markdown(
        f"""
        <div class="gg-hero">
            <h1>📊 Acompanhamento de Turnos GO</h1>
            <p>Abertura e fechamento reais das equipes de campo • dados atualizados automaticamente pelo bot</p>
            {f'<div class="gg-badge-update">🕒 {atualizado_em_texto}</div>' if atualizado_em_texto else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def titulo_secao(icone, titulo, subtitulo=None):
    st.markdown(
        f"""
        <div class="gg-section-title"><h3>{icone} {titulo}</h3></div>
        {f'<p class="gg-section-sub">{subtitulo}</p>' if subtitulo else ''}
        """,
        unsafe_allow_html=True,
    )


def legenda_chips(itens):
    """itens: lista de tuplas (cor_hex, texto). Mesmo significado da legenda original,
    só muda o formato visual (chips coloridos) — nenhuma cor de matriz é alterada."""
    partes = "".join(
        f'<span class="gg-chip" style="background:{cor}18; color:{cor};">'
        f'<span class="gg-dot" style="background:{cor};"></span>{texto}</span>'
        for cor, texto in itens
    )
    st.markdown(f'<div class="gg-legend">{partes}</div>', unsafe_allow_html=True)


# =============================================================================
# FUNÇÕES DE DADOS — sem nenhuma alteração de lógica ou de matriz
# =============================================================================
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


def primeiro_valor_preenchido(valores, padrao=""):
    for valor in valores:
        if not pd.isna(valor) and str(valor).strip():
            return valor
    return padrao


def juntar_valores_distintos(valores):
    vistos = []
    for valor in valores:
        if pd.isna(valor):
            continue
        texto = str(valor).strip()
        if texto and texto not in vistos:
            vistos.append(texto)
    return " | ".join(vistos)


def consolidar_turnos_por_equipe_dia(dados):
    """Une reaberturas da mesma equipe no dia e soma os intervalos oficiais."""
    dados_validos = dados[dados["INICIO_TURNO"].notna()].copy()
    linhas = []
    for (data_turno, grupo, prefixo), registros in dados_validos.groupby(
        ["DATA", "GRUPO", "PREFIXO"], sort=True
    ):
        registros = registros.sort_values("INICIO_TURNO").reset_index(drop=True)
        inicio = registros.iloc[0]["INICIO_TURNO"]
        ultimo = registros.iloc[-1]
        fim = ultimo["FIM_TURNO"]
        em_andamento = pd.isna(fim)

        if "INTERVALO_OFICIAL_SEGUNDOS" in registros.columns:
            intervalo_segundos = float(
                pd.to_numeric(registros["INTERVALO_OFICIAL_SEGUNDOS"], errors="coerce")
                .fillna(0)
                .sum()
            )
        else:
            intervalo_segundos = 0.0
            fim_cobertura = None
            for _, registro in registros.iterrows():
                inicio_registro = registro["INICIO_TURNO"]
                fim_registro = registro["FIM_TURNO"]
                if fim_cobertura is not None and inicio_registro > fim_cobertura:
                    intervalo_segundos += (inicio_registro - fim_cobertura).total_seconds()
                if not pd.isna(fim_registro):
                    if fim_cobertura is None or fim_registro > fim_cobertura:
                        fim_cobertura = fim_registro

        intervalo_horas = intervalo_segundos / 3600
        permanencia_horas = float("nan")
        trabalho_horas = float("nan")
        if not em_andamento:
            permanencia_horas = max(0.0, (fim - inicio).total_seconds() / 3600)
            # Para o acompanhamento, a jornada vai da primeira abertura ao último
            # fechamento. Os intervalos são exibidos separadamente, sem desconto.
            trabalho_horas = permanencia_horas

        saida_prevista = registros.iloc[0]["SAIDA_PREVISTA"]
        diferenca_fechamento = pd.NA
        if not em_andamento and not pd.isna(saida_prevista):
            diferenca_fechamento = round((fim - saida_prevista).total_seconds() / 60)

        linhas.append({
            "DATA": data_turno,
            "GRUPO": grupo,
            "PREFIXO": prefixo,
            "INICIO_TURNO": inicio,
            "SAIDA_PREVISTA": saida_prevista,
            "FIM_TURNO": pd.NaT if em_andamento else fim,
            "SITUACAO": "EM ANDAMENTO" if em_andamento else "ENCERRADO",
            "ABERTURAS_NO_DIA": registros["HIST_TURMA_PLANTAO_ID"].nunique(),
            "PERMANENCIA_HORAS": round(permanencia_horas, 4),
            "INTERVALO_HORAS": round(intervalo_horas, 4),
            "DURACAO_HORAS": round(trabalho_horas, 4),
            "PERMANENCIA": "EM CURSO" if em_andamento else formatar_duracao(permanencia_horas),
            "INTERVALO": formatar_duracao(intervalo_horas),
            "DURACAO": "EM CURSO" if em_andamento else formatar_duracao(trabalho_horas),
            "DIFERENCA_FECHAMENTO_MIN": diferenca_fechamento,
            "PARTICIPA_ESCALA": primeiro_valor_preenchido(registros["PARTICIPA_ESCALA"]),
            "OBSERVACAO": juntar_valores_distintos(registros["OBSERVACAO"]),
            "MOTIVOS_INTERVALO": juntar_valores_distintos(registros["MOTIVOS_INTERVALO"])
                if "MOTIVOS_INTERVALO" in registros.columns else "",
            "HIST_TURMA_PLANTAO_ID": f"{prefixo}-{data_turno}",
        })
    return pd.DataFrame(linhas)


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

    for coluna in [
        "INICIO_TURNO", "SAIDA_PREVISTA", "FIM_TURNO",
        "INICIO_INTERVALO", "FIM_INTERVALO",
    ]:
        if coluna not in dados.columns:
            dados[coluna] = pd.NaT
        dados[coluna] = converter_data_hora(dados[coluna])

    dados["PREFIXO"] = dados["PREFIXO"].astype(str).str.strip().str.upper()
    dados["GRUPO"] = dados["PREFIXO"].str[:4]
    dados["DATA"] = dados["INICIO_TURNO"].dt.date
    dados = dados[dados["GRUPO"].isin(GRUPOS)].copy()
    for coluna in ["PARTICIPA_ESCALA", "OBSERVACAO"]:
        if coluna not in dados.columns:
            dados[coluna] = ""
    if "INTERVALO_OFICIAL_SEGUNDOS" in dados.columns:
        dados["INTERVALO_OFICIAL_SEGUNDOS"] = pd.to_numeric(
            dados["INTERVALO_OFICIAL_SEGUNDOS"], errors="coerce"
        ).fillna(0)
    if "MOTIVOS_INTERVALO" not in dados.columns:
        if "MOTIVO_INTERVALO" in dados.columns:
            dados["MOTIVOS_INTERVALO"] = dados["MOTIVO_INTERVALO"]
        else:
            dados["MOTIVOS_INTERVALO"] = ""
    if "HIST_TURMA_PLANTAO_ID" not in dados.columns:
        dados["HIST_TURMA_PLANTAO_ID"] = range(1, len(dados) + 1)
    consolidados = consolidar_turnos_por_equipe_dia(dados)
    if consolidados.empty:
        return consolidados
    consolidados["DIFERENCA_FECHAMENTO_MIN"] = pd.array(
        consolidados["DIFERENCA_FECHAMENTO_MIN"], dtype="Int64"
    )
    return consolidados.sort_values(["INICIO_TURNO", "PREFIXO"], na_position="last")


def preparar_intervalos_individuais(brutos):
    """Prepara um registro por intervalo oficial para o ranking."""
    dados = brutos.copy()
    dados.columns = [normalizar_nome(coluna) for coluna in dados.columns]
    necessarias = {
        "INTERVALO_ID", "PREFIXO", "INICIO_INTERVALO", "FIM_INTERVALO",
        "INTERVALO_OFICIAL_SEGUNDOS",
    }
    if not necessarias.issubset(dados.columns):
        return pd.DataFrame()

    dados["INICIO_INTERVALO"] = converter_data_hora(dados["INICIO_INTERVALO"])
    dados["FIM_INTERVALO"] = converter_data_hora(dados["FIM_INTERVALO"])
    dados["INTERVALO_OFICIAL_SEGUNDOS"] = pd.to_numeric(
        dados["INTERVALO_OFICIAL_SEGUNDOS"], errors="coerce"
    )
    dados["PREFIXO"] = dados["PREFIXO"].astype(str).str.strip().str.upper()
    dados["GRUPO"] = dados["PREFIXO"].str[:4]
    if "MOTIVO_INTERVALO" not in dados.columns:
        dados["MOTIVO_INTERVALO"] = ""

    validos = (
        dados["INTERVALO_ID"].notna()
        & dados["INTERVALO_ID"].astype(str).str.strip().ne("")
        & dados["INICIO_INTERVALO"].notna()
        & dados["FIM_INTERVALO"].notna()
        & dados["INTERVALO_OFICIAL_SEGUNDOS"].ge(0)
        & dados["GRUPO"].isin(GRUPOS)
    )
    intervalos = dados.loc[validos].drop_duplicates("INTERVALO_ID").copy()
    intervalos["INTERVALO_HORAS"] = intervalos["INTERVALO_OFICIAL_SEGUNDOS"] / 3600
    intervalos["DURACAO_INTERVALO"] = intervalos["INTERVALO_HORAS"].map(formatar_duracao)
    return intervalos


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
                    valor = "-" if horas == 0 else round(horas, 4)
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
                valor = "-"
            linha[dia] = valor
        linha["TOTAL (h)"] = "-" if total_horas == 0 else round(total_horas, 4)
        linhas.append(linha)
    return pd.DataFrame(linhas).set_index("EQUIPE") if linhas else pd.DataFrame()


def estilo_horas(valor):
    if isinstance(valor, (int, float)) and not pd.isna(valor):
        minutos_totais = round(float(valor) * 60)
        if minutos_totais >= 8 * 60:
            return "background-color: #16a34a; color: white; font-weight: 700;"
        if minutos_totais < 6 * 60:
            return "background-color: #7e22ce; color: white; font-weight: 700;"
        return "background-color: #dc2626; color: white; font-weight: 700;"
    estilos = {
        "EM CURSO": "background-color: #facc15; color: #713f12; font-weight: 700;",
        "-": "background-color: #ffffff; color: #334155; font-weight: 700;",
        "S": "background-color: #dbeafe; color: #1e3a8a; font-weight: 700;",
        "D": "background-color: #e2e8f0; color: #334155; font-weight: 700;",
        "F": "background-color: #fef3c7; color: #92400e; font-weight: 700;",
        "": "background-color: #f8fafc; color: #94a3b8;",
    }
    return estilos.get(str(valor), "")


def estilo_total_horas(valor):
    if str(valor) == "-":
        return "background-color: #ffffff; color: #334155; font-weight: 700;"
    return "background-color: #f1f5f9; font-weight: 700;"


def montar_tabela_intervalos(dados, ano, mes, grupos, equipes_selecionadas):
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
        total_intervalo = 0.0
        turnos_equipe = turnos_mes[turnos_mes["PREFIXO"].eq(equipe)]
        for dia in dias:
            data_celula = date(ano, mes, dia)
            turnos_dia = turnos_equipe[turnos_equipe["DIA"].eq(dia)]
            if not turnos_dia.empty:
                intervalo = float(turnos_dia["INTERVALO_HORAS"].fillna(0).sum())
                valor = round(intervalo, 4)
                total_intervalo += intervalo
            elif data_celula > hoje:
                valor = ""
            elif data_celula in feriados:
                valor = "F"
            elif data_celula.weekday() == 5:
                valor = "S"
            elif data_celula.weekday() == 6:
                valor = "D"
            else:
                valor = "SEM TURNO"
            linha[dia] = valor
        linha["TOTAL"] = round(total_intervalo, 4)
        linhas.append(linha)
    return pd.DataFrame(linhas).set_index("EQUIPE") if linhas else pd.DataFrame()


def estilo_intervalos(valor):
    if isinstance(valor, (int, float)) and not pd.isna(valor):
        minutos_totais = round(float(valor) * 60)
        if minutos_totais > 2 * 60 + 30:
            return "background-color: #7e22ce; color: white; font-weight: 700;"
        if minutos_totais > 1 * 60 + 15:
            return "background-color: #dc2626; color: white; font-weight: 700;"
        if minutos_totais >= 1 * 60:
            return "background-color: #16a34a; color: white; font-weight: 700;"
        return "background-color: #fed7aa; color: #9a3412; font-weight: 700;"
    estilos = {
        "SEM TURNO": "background-color: #ffffff; color: #334155; font-weight: 700;",
        "S": "background-color: #dbeafe; color: #1e3a8a; font-weight: 700;",
        "D": "background-color: #e2e8f0; color: #334155; font-weight: 700;",
        "F": "background-color: #fef3c7; color: #92400e; font-weight: 700;",
        "": "background-color: #f8fafc; color: #94a3b8;",
    }
    return estilos.get(str(valor), "")


def montar_tabela_refeicao(
    dados, intervalos_individuais, ano, mes, grupos, equipes_selecionadas
):
    """Soma somente os intervalos oficiais de refeição por equipe e dia."""
    quantidade_dias = calendar.monthrange(ano, mes)[1]
    dias = list(range(1, quantidade_dias + 1))
    hoje = datetime.now(FUSO_GOIAS).date()
    feriados = feriados_brasil(ano)

    universo = dados[dados["GRUPO"].isin(grupos)].copy()
    if equipes_selecionadas:
        universo = universo[universo["PREFIXO"].isin(equipes_selecionadas)]
    universo = ocultar_desmobilizadas_sem_movimento(universo, ano, mes)
    equipes_tabela = sorted(universo["PREFIXO"].dropna().unique())

    datas_turnos = pd.to_datetime(universo["DATA"], errors="coerce")
    turnos_mes = universo[
        datas_turnos.dt.year.eq(ano) & datas_turnos.dt.month.eq(mes)
    ].copy()
    turnos_mes["DIA"] = pd.to_datetime(turnos_mes["DATA"]).dt.day
    dias_com_turno = set(zip(turnos_mes["PREFIXO"], turnos_mes["DIA"]))

    refeicoes_por_dia = {}
    if not intervalos_individuais.empty:
        refeicoes = intervalos_individuais.copy()
        datas_refeicao = pd.to_datetime(refeicoes["INICIO_INTERVALO"], errors="coerce")
        motivos = refeicoes["MOTIVO_INTERVALO"].fillna("").map(normalizar_nome)
        refeicoes = refeicoes[
            datas_refeicao.dt.year.eq(ano)
            & datas_refeicao.dt.month.eq(mes)
            & refeicoes["GRUPO"].isin(grupos)
            & motivos.eq("REFEICAO")
        ].copy()
        if equipes_selecionadas:
            refeicoes = refeicoes[refeicoes["PREFIXO"].isin(equipes_selecionadas)]
        refeicoes["DIA"] = pd.to_datetime(refeicoes["INICIO_INTERVALO"]).dt.day
        refeicoes_por_dia = (
            refeicoes.groupby(["PREFIXO", "DIA"])["INTERVALO_HORAS"].sum().to_dict()
        )

    linhas = []
    for equipe in equipes_tabela:
        linha = {"EQUIPE": equipe}
        total_refeicao = 0.0
        for dia in dias:
            data_celula = date(ano, mes, dia)
            if (equipe, dia) in dias_com_turno:
                refeicao = float(refeicoes_por_dia.get((equipe, dia), 0.0))
                valor = round(refeicao, 4)
                total_refeicao += refeicao
            elif data_celula > hoje:
                valor = ""
            elif data_celula in feriados:
                valor = "F"
            elif data_celula.weekday() == 5:
                valor = "S"
            elif data_celula.weekday() == 6:
                valor = "D"
            else:
                valor = "SEM TURNO"
            linha[dia] = valor
        linha["TOTAL"] = round(total_refeicao, 4)
        linhas.append(linha)
    return pd.DataFrame(linhas).set_index("EQUIPE") if linhas else pd.DataFrame()


def estilo_refeicao(valor):
    if isinstance(valor, (int, float)) and not pd.isna(valor):
        minutos_totais = round(float(valor) * 60)
        if minutos_totais > 99:
            return "background-color: #7e22ce; color: white; font-weight: 700;"
        if minutos_totais > 75:
            return "background-color: #dc2626; color: white; font-weight: 700;"
        if minutos_totais >= 59:
            return "background-color: #16a34a; color: white; font-weight: 700;"
        return "background-color: #fed7aa; color: #9a3412; font-weight: 700;"
    estilos = {
        "SEM TURNO": "background-color: #ffffff; color: #334155; font-weight: 700;",
        "S": "background-color: #dbeafe; color: #1e3a8a; font-weight: 700;",
        "D": "background-color: #e2e8f0; color: #334155; font-weight: 700;",
        "F": "background-color: #fef3c7; color: #92400e; font-weight: 700;",
        "": "background-color: #f8fafc; color: #94a3b8;",
    }
    return estilos.get(str(valor), "")


# =============================================================================
# INTERFACE
# =============================================================================
injetar_estilo()

with st.sidebar.container():
    st.markdown(
        '<div class="gg-sidebar-title">⚙️ Filtros</div>'
        '<div class="gg-sidebar-sub">Ajuste o período e o recorte de equipes</div>',
        unsafe_allow_html=True,
    )
    if st.button("🔄 Atualizar dados", type="primary", use_container_width=True):
        carregar_turnos.clear()
        st.rerun()

try:
    with st.spinner("Lendo a planilha de turnos..."):
        brutos, atualizado_em = carregar_turnos()
        if brutos.empty:
            st.warning("A planilha ainda está vazia. Execute o teste do bot para enviar os dados.")
            st.stop()
        dados = preparar_dados(brutos)
        intervalos_individuais = preparar_intervalos_individuais(brutos)
except Exception as erro:
    st.error("Não foi possível consultar a planilha de turnos.")
    st.code(str(erro))
    st.stop()

texto_atualizacao = ""
if atualizado_em:
    try:
        atualizado = datetime.fromisoformat(atualizado_em).astimezone(FUSO_GOIAS)
        texto_atualizacao = f"Última carga do bot: {atualizado:%d/%m/%Y %H:%M:%S}"
    except ValueError:
        texto_atualizacao = "Última carga do bot: " + atualizado_em

cabecalho_hero(texto_atualizacao)

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

if intervalos_individuais.empty:
    ranking_intervalos = pd.DataFrame()
else:
    datas_ranking = pd.to_datetime(
        intervalos_individuais["INICIO_INTERVALO"], errors="coerce"
    )
    ranking_intervalos = intervalos_individuais[
        datas_ranking.dt.year.eq(ano)
        & datas_ranking.dt.month.eq(mes)
        & intervalos_individuais["GRUPO"].isin(grupos)
        & intervalos_individuais["INTERVALO_OFICIAL_SEGUNDOS"].gt(0)
    ].copy()
    if equipes:
        ranking_intervalos = ranking_intervalos[
            ranking_intervalos["PREFIXO"].isin(equipes)
        ]
    ranking_intervalos = ranking_intervalos.sort_values(
        ["INTERVALO_OFICIAL_SEGUNDOS", "INICIO_INTERVALO"],
        ascending=[False, True],
    ).reset_index(drop=True)
    ranking_intervalos["MOTIVO_INTERVALO"] = (
        ranking_intervalos["MOTIVO_INTERVALO"].fillna("").astype(str).str.strip()
        .replace("", "Não informado")
    )
    ranking_intervalos["CATEGORIA_MOTIVO"] = ranking_intervalos[
        "MOTIVO_INTERVALO"
    ].map(normalizar_nome)

metricas = st.columns(4)
metricas[0].metric("Turnos consolidados", filtrado["HIST_TURMA_PLANTAO_ID"].nunique())
metricas[1].metric("Equipes", filtrado["PREFIXO"].nunique())
metricas[2].metric("Em andamento", int(filtrado["SITUACAO"].eq("EM ANDAMENTO").sum()))
mediana = filtrado["DURACAO_HORAS"].median()
metricas[3].metric("Duração mediana", "—" if pd.isna(mediana) else formatar_duracao(mediana))

st.write("")

colunas = [
    "DATA", "GRUPO", "PREFIXO", "INICIO_TURNO", "SAIDA_PREVISTA", "FIM_TURNO",
    "SITUACAO", "ABERTURAS_NO_DIA", "PERMANENCIA", "INTERVALO", "DURACAO",
    "DIFERENCA_FECHAMENTO_MIN",
    "MOTIVOS_INTERVALO", "PARTICIPA_ESCALA", "OBSERVACAO",
]
(
    aba_turnos, aba_mapa, aba_horas, aba_intervalos, aba_refeicao,
    aba_ranking, aba_resumo,
) = st.tabs(
    [
        "📋 Turnos", "🗓️ Mapa mensal", "⏱️ Horas trabalhadas", "☕ Intervalos",
        "🍽️ Refeição", "🏆 Ranking", "📈 Resumo diário",
    ]
)
with aba_turnos:
    titulo_secao("📋", f"Turnos de {MESES[mes - 1]} de {ano}")
    st.dataframe(
        filtrado[colunas], hide_index=True, use_container_width=True, height=620,
        column_config={
            "DATA": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "INICIO_TURNO": st.column_config.DatetimeColumn("Abertura", format="DD/MM/YYYY HH:mm"),
            "SAIDA_PREVISTA": st.column_config.DatetimeColumn("Saída prevista", format="DD/MM/YYYY HH:mm"),
            "FIM_TURNO": st.column_config.DatetimeColumn("Fechamento", format="DD/MM/YYYY HH:mm"),
            "ABERTURAS_NO_DIA": st.column_config.NumberColumn("Aberturas no dia", format="%d"),
            "PERMANENCIA": st.column_config.TextColumn("Permanência total"),
            "INTERVALO": st.column_config.TextColumn("Intervalo"),
            "DURACAO": st.column_config.TextColumn("Tempo trabalhado"),
            "MOTIVOS_INTERVALO": st.column_config.TextColumn("Motivo do intervalo"),
            "DIFERENCA_FECHAMENTO_MIN": st.column_config.NumberColumn("Diferença fechamento (min)", format="%d"),
        },
    )
with aba_mapa:
    titulo_secao("🗓️", f"Presença das equipes — {MESES[mes - 1]} de {ano}")
    legenda_chips([
        ("#16a34a", "1 = abriu turno"),
        ("#dc2626", "0 = não abriu em dia útil já transcorrido"),
        ("#1e3a8a", "S = sábado"),
        ("#334155", "D = domingo"),
        ("#92400e", "F = feriado"),
        ("#94a3b8", "vazio = dia futuro"),
    ])
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
    titulo_secao("⏱️", f"Horas trabalhadas — {MESES[mes - 1]} de {ano}")
    legenda_chips([
        ("#7e22ce", "menos de 6 horas"),
        ("#dc2626", "de 6 horas até 07:59"),
        ("#16a34a", "8 horas ou mais"),
        ("#facc15", "turno ainda em curso"),
        ("#334155", "- = nenhuma hora"),
        ("#1e3a8a", "S = sábado"),
        ("#334155", "D = domingo"),
        ("#92400e", "F = feriado"),
        ("#94a3b8", "vazio = dia futuro"),
    ])
    tabela_horas = montar_tabela_horas(dados, ano, mes, grupos, equipes)
    if tabela_horas.empty:
        st.info("Nenhuma equipe disponível para os filtros selecionados.")
    else:
        colunas_dias = [coluna for coluna in tabela_horas.columns if coluna != "TOTAL (h)"]
        horas_estilizadas = (
            tabela_horas.style
            .map(estilo_horas, subset=colunas_dias)
            .format(formatar_duracao, subset=colunas_dias + ["TOTAL (h)"])
            .map(estilo_total_horas, subset=["TOTAL (h)"])
        )
        st.dataframe(
            horas_estilizadas,
            use_container_width=True,
            height=min(800, 70 + len(tabela_horas) * 35),
        )
with aba_intervalos:
    titulo_secao(
        "☕", f"Tempo de intervalo — {MESES[mes - 1]} de {ano}",
        "Soma dos intervalos oficiais registrados para a equipe no dia.",
    )
    legenda_chips([
        ("#fb923c", "menos de 01:00"),
        ("#16a34a", "de 01:00 até 01:15"),
        ("#dc2626", "de 01:16 até 02:30"),
        ("#7e22ce", "acima de 02:30"),
        ("#334155", "branco = sem turno"),
        ("#1e3a8a", "S = sábado"),
        ("#334155", "D = domingo"),
        ("#92400e", "F = feriado"),
        ("#94a3b8", "vazio = dia futuro"),
    ])
    tabela_intervalos = montar_tabela_intervalos(dados, ano, mes, grupos, equipes)
    if tabela_intervalos.empty:
        st.info("Nenhuma equipe disponível para os filtros selecionados.")
    else:
        colunas_dias = [coluna for coluna in tabela_intervalos.columns if coluna != "TOTAL"]
        intervalos_estilizados = (
            tabela_intervalos.style
            .map(estilo_intervalos, subset=colunas_dias)
            .format(formatar_duracao, subset=colunas_dias + ["TOTAL"])
            .set_properties(
                subset=["TOTAL"],
                **{"font-weight": "700", "background-color": "#f1f5f9"},
            )
        )
        st.dataframe(
            intervalos_estilizados,
            use_container_width=True,
            height=min(800, 70 + len(tabela_intervalos) * 35),
        )
with aba_refeicao:
    titulo_secao(
        "🍽️", f"Intervalos de refeição — {MESES[mes - 1]} de {ano}",
        "Soma somente os intervalos oficiais classificados como refeição para a equipe no dia.",
    )
    legenda_chips([
        ("#fb923c", "abaixo de 00:59"),
        ("#16a34a", "de 00:59 até 01:15"),
        ("#dc2626", "acima de 01:15 até 01:39"),
        ("#7e22ce", "acima de 01:39"),
        ("#334155", "branco = sem turno"),
        ("#1e3a8a", "S = sábado"),
        ("#334155", "D = domingo"),
        ("#92400e", "F = feriado"),
        ("#94a3b8", "vazio = dia futuro"),
    ])
    tabela_refeicao = montar_tabela_refeicao(
        dados, intervalos_individuais, ano, mes, grupos, equipes
    )
    if tabela_refeicao.empty:
        st.info("Nenhuma equipe disponível para os filtros selecionados.")
    else:
        colunas_dias = [coluna for coluna in tabela_refeicao.columns if coluna != "TOTAL"]
        refeicao_estilizada = (
            tabela_refeicao.style
            .map(estilo_refeicao, subset=colunas_dias)
            .format(formatar_duracao, subset=colunas_dias + ["TOTAL"])
            .set_properties(
                subset=["TOTAL"],
                **{"font-weight": "700", "background-color": "#f1f5f9"},
            )
        )
        st.dataframe(
            refeicao_estilizada,
            use_container_width=True,
            height=min(800, 70 + len(tabela_refeicao) * 35),
        )
with aba_ranking:
    titulo_secao(
        "🏆", f"Maiores intervalos por motivo — {MESES[mes - 1]} de {ano}",
        "Cada linha representa um intervalo oficial individual. Os valores não são somados por equipe nem por dia.",
    )
    if ranking_intervalos.empty:
        st.info(
            "Nenhum intervalo individual encerrado foi encontrado. Execute novamente "
            "o bot atualizado para enviar os detalhes dos intervalos."
        )
    else:
        categorias_ranking = [
            ("Refeição", "REFEICAO", "refeicao"),
            ("Manutenção no veículo", "MANUTENCAO_NO_VEICULO", "manutencao"),
            ("Retorno para a base", "RETORNO_PARA_BASE", "retorno_base"),
        ]
        for titulo_categoria, codigo_categoria, chave_categoria in categorias_ranking:
            st.markdown(f"#### {titulo_categoria}")
            tabela_categoria = ranking_intervalos[
                ranking_intervalos["CATEGORIA_MOTIVO"].eq(codigo_categoria)
            ].copy().reset_index(drop=True)
            tabela_categoria.insert(
                0, "POSICAO", range(1, len(tabela_categoria) + 1)
            )
            if tabela_categoria.empty:
                st.info(f"Nenhum intervalo de {titulo_categoria.lower()} no período.")
                continue

            colunas_ranking = [
                "POSICAO", "PREFIXO", "INICIO_INTERVALO", "FIM_INTERVALO",
                "DURACAO_INTERVALO", "MOTIVO_INTERVALO",
            ]
            st.dataframe(
                tabela_categoria[colunas_ranking],
                hide_index=True,
                use_container_width=True,
                height=min(600, 70 + len(tabela_categoria) * 35),
                column_config={
                    "POSICAO": st.column_config.NumberColumn("Posição", format="%d"),
                    "PREFIXO": st.column_config.TextColumn("Equipe"),
                    "INICIO_INTERVALO": st.column_config.DatetimeColumn(
                        "Início do intervalo", format="DD/MM/YYYY HH:mm"
                    ),
                    "FIM_INTERVALO": st.column_config.DatetimeColumn(
                        "Fim do intervalo", format="DD/MM/YYYY HH:mm"
                    ),
                    "DURACAO_INTERVALO": st.column_config.TextColumn("Duração"),
                    "MOTIVO_INTERVALO": st.column_config.TextColumn("Motivo"),
                },
            )
            st.download_button(
                f"⬇️ Baixar ranking de {titulo_categoria.lower()} em CSV",
                tabela_categoria[colunas_ranking].to_csv(
                    index=False, sep=";", decimal=","
                ).encode("utf-8-sig"),
                file_name=(
                    f"ranking_{chave_categoria}_{ano}_{mes:02}.csv"
                ),
                mime="text/csv",
                key=f"baixar_ranking_{chave_categoria}",
            )
with aba_resumo:
    titulo_secao("📈", f"Resumo diário — {MESES[mes - 1]} de {ano}")
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

st.write("")
st.download_button(
    "⬇️ Baixar tabela filtrada em CSV",
    filtrado[colunas].to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
    file_name=f"acompanhamento_turnos_{ano}_{mes:02}.csv",
    mime="text/csv",
)
