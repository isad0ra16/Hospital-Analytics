"""Analytical layer for Power BI: star schema exported as CSV (UTF-8) and optionally Parquet.

A single schema (``TABLES``) drives everything: the export, the field dictionary, the Power
Query (M) import script and the tests. Grain of the fact table: one row per AIH *record*.
A record is not a patient and not necessarily a distinct admission (see docs/04_modelagem.md).

Privacy: identifying fields (N_AIH, NASC, CEP, CPF_AUT, GESTOR_CPF, INSC_PN) and free text
(AUD_JUST, SIS_JUST) are never exported. N_AIH is replaced by ``aih_id``, a deterministic
dense rank used only for distinct counts.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb

from hospital_analytics.dictionary import CODEBOOK
from hospital_analytics.enrichment import References, official_code_rows
from hospital_analytics.integrity import sha256_file
from hospital_analytics.sql import path_literal, read_sql

log = logging.getLogger(__name__)

SOURCE_STATUS_LABEL = {
    "secondary": "fonte secundária (microdatasus)",
    "prior_knowledge": "conhecimento prévio (não verificado)",
}
EXCLUDED_FIELDS = {
    "N_AIH": "identificador da AIH — substituído por aih_id (pseudônimo determinístico)",
    "NASC": "data de nascimento — substituída por idade_anos e faixa etária",
    "DT_INTER (dia)": "exportada só como mês (mes_internacao) — minimização;"
    " a permanência em dias é preservada",
    "DT_SAIDA (dia)": "exportada só como mês (mes_saida) — minimização;"
    " a permanência em dias é preservada",
    "CEP": "CEP de residência — granularidade desnecessária para o dashboard",
    "CPF_AUT": "CPF — identificador pessoal (100% vazio nesta base)",
    "GESTOR_CPF": "CPF do gestor — identificador pessoal",
    "INSC_PN": "inscrição no pré-natal — identificador",
    "AUD_JUST": "texto livre de auditoria",
    "SIS_JUST": "texto livre do sistema",
}


@dataclass(frozen=True)
class Column:
    name: str
    m_type: str  # Power Query type
    description: str
    origin: str
    nullable: bool = False
    enriched: bool = False  # filled from an official reference table (added, never replacing)


@dataclass(frozen=True)
class Table:
    name: str
    key: tuple[str, ...]
    grain: str
    columns: tuple[Column, ...]
    sql: str  # sql/powerbi/<sql>.sql, or "report:<name>" for auxiliary tables built from reports
    # (source column, codebook field, official TabWin source in params reference_sources)
    code_dimension: tuple[str, str, str] | None = None

    @property
    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]


TXT, INT, DATE, NUM, CUR = "type text", "Int64.Type", "type date", "type number", "Currency.Type"


def _code_dim(name: str, code_col: str, source: str, field: str, what: str, official: str) -> Table:
    return Table(
        name,
        (code_col,),
        f"1 linha por código de {source} presente no fato",
        (
            Column(code_col, TXT, f"Código de {what} ({source})", source),
            Column(
                "descricao",
                TXT,
                f"Descrição do código ({what}) — fonte secundária",
                "dicionário",
                nullable=True,
            ),
            Column("fonte", TXT, "Fonte/status da interpretação do código", "dicionário"),
            Column(
                "descricao_oficial",
                TXT,
                f"Descrição oficial ({what}) — usar nos visuais",
                "TabWin SIH/SUS",
                nullable=True,
                enriched=True,
            ),
            Column(
                "fonte_oficial",
                TXT,
                "Pacote e tabela de conversão oficiais",
                "TabWin SIH/SUS",
                nullable=True,
                enriched=True,
            ),
        ),
        "dim_code",
        (source, field, official),
    )


def _named(name: str, description: str, origin: str) -> Column:
    """Column filled by an official reference: null only when the code is not found."""
    return Column(name, TXT, description, origin, nullable=True, enriched=True)


TABLES: tuple[Table, ...] = (
    Table(
        "fato_registro_aih",
        ("registro_id",),
        "1 linha por registro de AIH do arquivo RD "
        "(não é paciente nem, necessariamente, internação)",
        (
            Column(
                "registro_id",
                INT,
                "Chave técnica: posição do registro no arquivo (1..n)",
                "ordem física",
            ),
            Column(
                "aih_id",
                INT,
                "Pseudônimo determinístico do N_AIH (posto denso); só para contagem distinta",
                "N_AIH",
            ),
            Column(
                "competencia",
                TXT,
                "Competência de processamento (AAAA-MM) — não é data de ocorrência",
                "ANO_CMPT, MES_CMPT",
            ),
            Column(
                "mes_saida",
                DATE,
                "Mês da saída, 1º dia do mês (relação ATIVA com dim_mes)",
                "DT_SAIDA",
            ),
            Column(
                "mes_internacao",
                DATE,
                "Mês da internação, 1º dia do mês (relação INATIVA com dim_mes)",
                "DT_INTER",
            ),
            Column("cnes", TXT, "Estabelecimento (chave de dim_estabelecimento)", "CNES"),
            Column(
                "municipio_residencia_cod",
                TXT,
                "Município de residência (chave de dim_municipio_residencia)",
                "MUNIC_RES",
            ),
            Column(
                "procedimento_cod",
                TXT,
                "Procedimento realizado, código SIGTAP (chave de dim_procedimento)",
                "PROC_REA",
            ),
            Column(
                "diagnostico_principal_cod",
                TXT,
                "Diagnóstico principal, código CID-10 (chave de dim_diagnostico)",
                "DIAG_PRINC",
            ),
            Column(
                "especialidade_cod",
                TXT,
                "Especialidade do leito (chave de dim_especialidade)",
                "ESPEC",
            ),
            Column("carater_cod", TXT, "Caráter da internação (chave de dim_carater)", "CAR_INT"),
            Column("complexidade_cod", TXT, "Complexidade (chave de dim_complexidade)", "COMPLEX"),
            Column(
                "tipo_aih_cod",
                TXT,
                "Tipo de AIH: 1 principal, 5 longa permanência (chave de dim_tipo_aih)",
                "IDENT",
            ),
            Column(
                "perfil_id",
                INT,
                "Perfil demográfico do registro (chave de dim_perfil_demografico)",
                "COD_IDADE, IDADE, SEXO, RACA_COR",
            ),
            Column("valor_total", CUR, "Valor total do registro (R$, 2 casas, exato)", "VAL_TOT"),
            Column(
                "valor_total_centavos",
                INT,
                "Valor total em centavos (inteiro, para conferência exata)",
                "VAL_TOT",
            ),
            Column(
                "dias_permanencia",
                INT,
                "Dias de permanência do registro (na AIH tipo 5: dias do período coberto)",
                "DIAS_PERM",
            ),
            Column(
                "dias_entre_datas",
                INT,
                "DT_SAIDA − DT_INTER em dias (difere de DIAS_PERM na longa permanência)",
                "DT_INTER, DT_SAIDA",
            ),
            Column(
                "idade_anos",
                NUM,
                "Idade em anos convertida pela unidade COD_IDADE (6 casas)",
                "COD_IDADE, IDADE",
                nullable=True,
            ),
            Column("obito", INT, "1 = óbito (MORTE = 1); 0 = não", "MORTE"),
            Column("aih_ocorrencias", INT, "Nº de registros com o mesmo N_AIH", "N_AIH"),
            Column(
                "aih_repetida",
                INT,
                "1 = o N_AIH aparece em mais de um registro (apenas sinalização)",
                "N_AIH",
            ),
        ),
        "fato_registro_aih",
    ),
    Table(
        "dim_mes",
        ("mes",),
        "1 linha por mês, anos completos cobrindo todos os meses de internação e saída",
        (
            Column("mes", DATE, "Mês (1º dia do mês)", "calendário"),
            Column("ano", INT, "Ano", "calendário"),
            Column("trimestre", INT, "Trimestre (1–4)", "calendário"),
            Column("mes_num", INT, "Mês (1–12)", "calendário"),
            Column("ano_mes", TXT, "Ano-mês (AAAA-MM)", "calendário"),
            Column("ano_mes_ordem", INT, "Ordenação de ano_mes (AAAAMM)", "calendário"),
            Column("mes_abrev", TXT, "Mês abreviado (pt-BR)", "calendário"),
        ),
        "dim_mes",
    ),
    Table(
        "dim_estabelecimento",
        ("cnes",),
        "1 linha por CNES presente no fato",
        (
            Column("cnes", TXT, "Código CNES do estabelecimento", "CNES"),
            Column(
                "municipio_estabelecimento_cod",
                TXT,
                "Município do ESTABELECIMENTO (≠ residência)",
                "MUNIC_MOV",
            ),
            Column(
                "uf_estabelecimento_cod",
                TXT,
                "2 primeiros dígitos do código do município",
                "MUNIC_MOV",
            ),
            Column("natureza_juridica_cod", TXT, "Natureza jurídica (código)", "NAT_JUR"),
            Column("gestao_cod", TXT, "Tipo de gestão (código)", "GESTAO"),
            _named(
                "estabelecimento_nome",
                "Nome fantasia no cadastro CNES (cadastro vigente no download, não 2024-01)",
                "CNES CADGERRJ.FANTASIA",
            ),
            _named(
                "estabelecimento_rotulo",
                "Nome fantasia (CNES) — único; usar nos visuais (há nomes repetidos)",
                "CNES CADGERRJ.FANTASIA",
            ),
            _named("municipio_estabelecimento_nome", "Município do estabelecimento", "IBGE"),
            _named("uf_estabelecimento_sigla", "UF do estabelecimento", "IBGE"),
            _named(
                "natureza_juridica_descricao",
                "Natureza jurídica (texto oficial)",
                "TabWin SIH/SUS natjur.cnv",
            ),
            _named(
                "esfera_juridica",
                "Esfera: administração pública (federal, estadual, municipal), empresarial,"
                " sem fins lucrativos",
                "TabWin SIH/SUS esferajur.cnv",
            ),
            _named(
                "gestao_descricao", "Tipo de gestão (texto oficial)", "TabWin SIH/SUS GESTAO.CNV"
            ),
            _named("estabelecimento_nome_fonte", "Fonte e data do cadastro do nome", "CNES"),
        ),
        "dim_estabelecimento",
    ),
    Table(
        "dim_municipio_residencia",
        ("municipio_residencia_cod",),
        "1 linha por município de residência presente no fato",
        (
            Column(
                "municipio_residencia_cod",
                TXT,
                "Código do município de RESIDÊNCIA (6 dígitos)",
                "MUNIC_RES",
            ),
            Column(
                "uf_residencia_cod", TXT, "2 primeiros dígitos do código do município", "MUNIC_RES"
            ),
            _named("municipio_residencia_ibge", "Código IBGE de 7 dígitos", "IBGE"),
            _named("municipio_residencia_nome", "Nome do município de residência", "IBGE"),
            _named("uf_residencia_sigla", "UF de residência (sigla)", "IBGE"),
            _named(
                "municipio_residencia_rotulo",
                "Município (UF) — único; usar nos visuais",
                "IBGE",
            ),
            _named("municipio_residencia_fonte", "Fonte do nome", "IBGE"),
        ),
        "dim_municipio_residencia",
    ),
    Table(
        "dim_procedimento",
        ("procedimento_cod",),
        "1 linha por procedimento realizado presente no fato",
        (
            Column("procedimento_cod", TXT, "Código SIGTAP do procedimento realizado", "PROC_REA"),
            Column("grupo_cod", TXT, "Grupo SIGTAP (2 primeiros dígitos)", "PROC_REA"),
            Column(
                "grupo_descricao", TXT, "Descrição do grupo SIGTAP", "dicionário", nullable=True
            ),
            Column(
                "grupo_fonte",
                TXT,
                "Fonte/status da descrição do grupo",
                "dicionário",
                nullable=True,
            ),
            _named("procedimento_nome", "Nome oficial do procedimento", "SIGTAP tb_procedimento"),
            _named("grupo_nome_sigtap", "Nome oficial do grupo (texto literal)", "SIGTAP tb_grupo"),
            Column("subgrupo_cod", TXT, "Subgrupo SIGTAP (4 primeiros dígitos)", "PROC_REA"),
            _named("subgrupo_nome", "Nome oficial do subgrupo", "SIGTAP tb_sub_grupo"),
            Column(
                "forma_organizacao_cod",
                TXT,
                "Forma de organização SIGTAP (6 primeiros dígitos)",
                "PROC_REA",
            ),
            _named(
                "forma_organizacao_nome",
                "Nome oficial da forma de organização",
                "SIGTAP tb_forma_organizacao",
            ),
            _named("procedimento_fonte", "Fonte e competência dos nomes", "SIGTAP"),
        ),
        "dim_procedimento",
    ),
    Table(
        "dim_diagnostico",
        ("diagnostico_cod",),
        "1 linha por código CID-10 de diagnóstico principal presente no fato",
        (
            Column(
                "diagnostico_cod", TXT, "Código CID-10 (3 ou 4 caracteres, sem ponto)", "DIAG_PRINC"
            ),
            _named("diagnostico_nome", "Descrição oficial do código", "SIGTAP tb_cid"),
            _named("diagnostico_rotulo", "Código · descrição — usar nos visuais", "SIGTAP tb_cid"),
            Column("categoria_cod", TXT, "Categoria CID-10 (3 primeiros caracteres)", "DIAG_PRINC"),
            _named("categoria_nome", "Descrição oficial da categoria", "SIGTAP tb_cid"),
            Column(
                "capitulo_ordem",
                INT,
                "Ordenação do capítulo CID-10 (1–22)",
                "TabWin SIH/SUS CID10CAP.CNV",
                nullable=True,
                enriched=True,
            ),
            _named("capitulo", "Capítulo CID-10 (texto oficial)", "TabWin SIH/SUS CID10CAP.CNV"),
            _named("diagnostico_fonte", "Fonte e competência das descrições", "SIGTAP"),
        ),
        "dim_diagnostico",
    ),
    _code_dim(
        "dim_especialidade",
        "especialidade_cod",
        "ESPEC",
        "ESPEC",
        "especialidade do leito",
        "sih_leitos",
    ),
    _code_dim(
        "dim_carater", "carater_cod", "CAR_INT", "CAR_INT", "caráter da internação", "sih_carater"
    ),
    _code_dim(
        "dim_complexidade",
        "complexidade_cod",
        "COMPLEX",
        "COMPLEX",
        "complexidade",
        "sih_complexidade",
    ),
    _code_dim("dim_tipo_aih", "tipo_aih_cod", "IDENT", "IDENT", "tipo de AIH", "sih_ident"),
    Table(
        "dim_perfil_demografico",
        ("perfil_id",),
        "1 linha por combinação faixa etária × sexo × raça/cor presente no fato "
        "(perfil, não paciente)",
        (
            Column("perfil_id", INT, "Chave do perfil", "derivado"),
            Column(
                "faixa_etaria_ordem",
                INT,
                "Ordenação da faixa etária (99 = sem informação)",
                "COD_IDADE, IDADE",
            ),
            Column(
                "faixa_etaria", TXT, "Faixa etária (idade em anos corrigida)", "COD_IDADE, IDADE"
            ),
            Column("sexo_cod", TXT, "Código de sexo", "SEXO"),
            Column("sexo_descricao", TXT, "Sexo (fonte secundária)", "dicionário", nullable=True),
            Column("raca_cor_cod", TXT, "Código de raça/cor", "RACA_COR"),
            Column(
                "raca_cor_descricao",
                TXT,
                "Raça/cor (fonte secundária)",
                "dicionário",
                nullable=True,
            ),
            _named("sexo_descricao_oficial", "Sexo (texto oficial)", "TabWin SIH/SUS SEXO.CNV"),
            _named(
                "raca_cor_descricao_oficial",
                "Raça/cor (texto oficial)",
                "TabWin SIH/SUS RACACOR.CNV",
            ),
        ),
        "dim_perfil_demografico",
    ),
    Table(
        "aux_curva_lorenz",
        ("percentil",),
        "1 linha por percentil de registros (0–100), base completa; sem relacionamento",
        (
            Column("percentil", INT, "Percentil de registros (0–100)", "derivado"),
            Column(
                "pct_registros",
                NUM,
                "Fração acumulada de registros, do menor para o maior valor",
                "VAL_TOT",
            ),
            Column("pct_valor", NUM, "Fração acumulada do valor total (VAL_TOT)", "VAL_TOT"),
            Column("igualdade", NUM, "Linha de igualdade (= pct_registros)", "derivado"),
        ),
        "aux_curva_lorenz",
    ),
)

# Columns that an official reference must fill for every row (coverage is checked, never forced).
ENRICHED_COLUMNS: dict[str, tuple[str, ...]] = {
    "dim_estabelecimento": (
        "estabelecimento_nome", "municipio_estabelecimento_nome", "natureza_juridica_descricao",
        "esfera_juridica", "gestao_descricao",
    ),
    "dim_municipio_residencia": ("municipio_residencia_nome", "uf_residencia_sigla"),
    "dim_procedimento": (
        "procedimento_nome", "grupo_nome_sigtap", "subgrupo_nome", "forma_organizacao_nome",
    ),
    "dim_diagnostico": ("diagnostico_nome", "capitulo"),
    "dim_especialidade": ("descricao_oficial",),
    "dim_carater": ("descricao_oficial",),
    "dim_complexidade": ("descricao_oficial",),
    "dim_tipo_aih": ("descricao_oficial",),
    "dim_perfil_demografico": ("sexo_descricao_oficial", "raca_cor_descricao_oficial"),
}  # fmt: skip

AUXILIARY_TABLES: tuple[Table, ...] = (
    Table(
        "ref_indicadores_validados",
        ("indicador_id",),
        "1 linha por indicador reconciliado (reports/indicators/reconciliation.json);"
        " sem relacionamento",
        (
            Column("indicador_id", TXT, "Identificador do indicador", "reconciliação"),
            Column("indicador", TXT, "Nome do indicador", "reconciliação"),
            Column("base", TXT, "Base/escopo (filtro aplicado)", "reconciliação"),
            Column("unidade", TXT, "count, money, days, years ou pct", "reconciliação"),
            Column("historico", TXT, "Valor histórico recuperado", "reconciliação", nullable=True),
            Column(
                "reproduzido",
                TXT,
                "Reproduzido na precisão do histórico",
                "reconciliação",
                nullable=True,
            ),
            Column("valor_exato", NUM, "Valor reproduzido exato (6 casas)", "reconciliação"),
            Column("status", TXT, "Status de validação", "reconciliação"),
        ),
        "report:reconciliation",
    ),
    Table(
        "qualidade_campos",
        ("campo",),
        "1 linha por campo original do RD (reports/audit/audit_rdrj2401.json); sem relacionamento",
        (
            Column("campo", TXT, "Campo original do arquivo RD", "auditoria"),
            Column("tipo_dbf", TXT, "Tipo e tamanho no DBF", "auditoria"),
            Column("vazios", INT, "Registros com o campo vazio", "auditoria"),
            Column("pct_vazios", NUM, "% de registros com o campo vazio", "auditoria"),
            Column("distintos", INT, "Valores distintos", "auditoria"),
            Column("exportado_powerbi", TXT, "sim / não (motivo)", "modelo"),
        ),
        "report:audit",
    ),
)

RELATIONSHIPS: tuple[tuple[str, str, str, str, bool], ...] = (
    # (fact column, dimension table, dimension column, cardinality, active)
    ("mes_saida", "dim_mes", "mes", "N:1", True),
    ("mes_internacao", "dim_mes", "mes", "N:1", False),
    ("cnes", "dim_estabelecimento", "cnes", "N:1", True),
    (
        "municipio_residencia_cod",
        "dim_municipio_residencia",
        "municipio_residencia_cod",
        "N:1",
        True,
    ),
    ("procedimento_cod", "dim_procedimento", "procedimento_cod", "N:1", True),
    ("diagnostico_principal_cod", "dim_diagnostico", "diagnostico_cod", "N:1", True),
    ("especialidade_cod", "dim_especialidade", "especialidade_cod", "N:1", True),
    ("carater_cod", "dim_carater", "carater_cod", "N:1", True),
    ("complexidade_cod", "dim_complexidade", "complexidade_cod", "N:1", True),
    ("tipo_aih_cod", "dim_tipo_aih", "tipo_aih_cod", "N:1", True),
    ("perfil_id", "dim_perfil_demografico", "perfil_id", "N:1", True),
)
ALL_TABLES: tuple[Table, ...] = TABLES + AUXILIARY_TABLES
TABLE_BY_NAME = {t.name: t for t in ALL_TABLES}
FACT_SOURCE_FIELDS = {
    "ANO_CMPT", "MES_CMPT", "DT_SAIDA", "DT_INTER", "CNES", "MUNIC_RES", "PROC_REA", "DIAG_PRINC",
    "ESPEC", "CAR_INT", "COMPLEX", "IDENT", "COD_IDADE", "IDADE", "SEXO", "RACA_COR", "VAL_TOT",
    "DIAS_PERM", "MORTE", "MUNIC_MOV", "NAT_JUR", "GESTAO",
}  # fmt: skip


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def load_reference_tables(con: duckdb.DuckDBPyConnection, refs: References) -> None:
    """Official lookups as DuckDB tables. TabWin codes are resolved in Python for every code
    present in ``base`` (range and precedence semantics cannot be expressed as an equi-join)."""
    simple = {
        "ref_procedimento": refs.procedimento,
        "ref_grupo": refs.grupo,
        "ref_subgrupo": refs.subgrupo,
        "ref_forma": refs.forma,
        "ref_cid": refs.cid,
        "ref_estabelecimento": refs.estabelecimento,
    }
    for name, mapping in simple.items():
        con.execute(f"create table {name} (code varchar primary key, nome varchar)")
        con.executemany(f"insert into {name} values (?, ?)", sorted(mapping.items()))
    con.execute(
        "create table ref_municipio (code varchar primary key, ibge_id varchar, nome varchar,"
        " uf_sigla varchar)"
    )
    con.executemany(
        "insert into ref_municipio values (?, ?, ?, ?)",
        [(k, v["id"], v["nome"], v["uf_sigla"]) for k, v in sorted(refs.municipio.items())],
    )
    con.execute("create table ref_source (name varchar primary key, label varchar)")
    con.executemany("insert into ref_source values (?, ?)", sorted(refs.sources.items()))
    fields = {
        source: [
            r[0]
            for r in con.execute(f'select distinct "{RD_FIELD_OF[source]}" from base').fetchall()
        ]
        for source in refs.cnv
    }
    con.execute(
        "create table official_code (source varchar, code varchar, label varchar,"
        " sequence varchar, file varchar, primary key (source, code))"
    )
    con.executemany(
        "insert into official_code values (?, ?, ?, ?, ?)",
        [(*row, refs.cnv[row[0]].name) for row in official_code_rows(refs, fields)],
    )


# RD field described by each official TabWin source (as in RD2008.DEF).
RD_FIELD_OF = {
    "sih_leitos": "ESPEC",
    "sih_ident": "IDENT",
    "sih_carater": "CAR_INT",
    "sih_complexidade": "COMPLEX",
    "sih_sexo": "SEXO",
    "sih_raca_cor": "RACA_COR",
    "sih_natureza_juridica": "NAT_JUR",
    "sih_esfera_juridica": "NAT_JUR",
    "sih_gestao": "GESTAO",
    "sih_cid10_capitulo": "DIAG_PRINC",
}


def connect_model(processed: Path, refs: References) -> duckdb.DuckDBPyConnection:
    """Connection with the processed layer, the codebook, the ``base`` table and the official
    reference tables."""
    con = duckdb.connect()
    con.execute(
        "create view rd_file as select * from "
        f"read_parquet({path_literal(processed)}, file_row_number = true)"
    )
    con.execute(
        "create table codebook (field varchar, code varchar, label varchar, source_status varchar)"
    )
    rows = [
        (fc.field, code, label, SOURCE_STATUS_LABEL[fc.status])
        for fc in CODEBOOK.values()
        for code, label in fc.codes.items()
    ]
    con.executemany("insert into codebook values (?, ?, ?, ?)", rows)
    con.execute(read_sql("powerbi/base"))
    load_reference_tables(con, refs)
    return con


def table_query(table: Table) -> tuple[str, dict[str, Any]]:
    if table.sql.startswith("report:"):
        return _aux_query(table), {}
    sql = read_sql(f"powerbi/{table.sql}")
    if table.code_dimension is None:
        return sql, {}
    source, field, official = table.code_dimension
    allowed = {t.code_dimension[0] for t in TABLES if t.code_dimension}
    if source not in allowed or not source.isidentifier():
        raise ValueError(f"column {source!r} is not an allowed code-dimension source")
    if field not in CODEBOOK:
        raise ValueError(f"field {field!r} is not in the codebook")
    if RD_FIELD_OF.get(official) != source:
        raise ValueError(f"official source {official!r} does not describe {source}")
    # Identifiers cannot be bound as parameters: all names come from the closed lists above.
    sql = (
        sql.replace('"$source_column"', f'"{source}"')
        .replace("$field", f"'{field}'")
        .replace("$official_source", f"'{official}'")
    )
    columns = ", ".join(table.column_names[1:])
    sql = f"select code as {table.key[0]}, {columns} from ({sql}) order by 1"
    return sql, {}


def _copy(con, sql: str, params: dict, destination: Path, fmt: str) -> None:
    options = (
        "format csv, header true, delimiter ','"
        if fmt == "csv"
        else "format parquet, compression zstd"
    )
    partial = destination.with_name(destination.name + ".partial")
    con.execute(f"copy ({sql}) to {path_literal(partial)} ({options})", params or None)
    os.replace(partial, destination)


def load_auxiliary(con, reports: Path | None) -> list[Table]:
    """Create the auxiliary tables from the versioned reports (skipped when absent)."""
    if reports is None:
        return []
    reconciliation = Path(reports) / "indicators" / "reconciliation.json"
    audit = Path(reports) / "audit" / "audit_rdrj2401.json"
    if not (reconciliation.is_file() and audit.is_file()):
        return []
    con.execute(
        "create table rep_reconciliation (indicador_id varchar, indicador varchar, base varchar,"
        " unidade varchar, historico varchar, reproduzido varchar, valor_exato decimal(24, 6),"
        " status varchar)"
    )
    rows = [
        (r["id"], r["name"], r["filters"], r["unit"], r["historical"], r["rounded"],
         r["reproduced"], r["status"])
        for r in json.loads(reconciliation.read_text(encoding="utf-8"))["indicators"]
    ]  # fmt: skip
    con.executemany("insert into rep_reconciliation values (?, ?, ?, ?, ?, ?, ?, ?)", rows)
    con.execute(
        "create table rep_audit (campo varchar, tipo_dbf varchar, vazios bigint,"
        " pct_vazios decimal(9, 4), distintos bigint, exportado_powerbi varchar)"
    )
    excluded = {k: v for k, v in EXCLUDED_FIELDS.items() if " " not in k}
    rows = []
    for p in json.loads(audit.read_text(encoding="utf-8"))["profiles"]:
        dbf = f"{p['dbf_type']}{p['dbf_length']}" + (
            f".{p['dbf_decimals']}" if p["dbf_decimals"] else ""
        )
        if p["name"] in excluded:
            exported = f"não ({excluded[p['name']].split(' — ')[0]})"
        elif p["name"] in {"DT_INTER", "DT_SAIDA"}:
            exported = "sim (apenas o mês)"
        elif p["name"] in FACT_SOURCE_FIELDS:
            exported = "sim"
        else:
            exported = "não (não usado no dashboard)"
        rows.append((p["name"], dbf, p["blank"], p["blank_pct"], p["distinct"], exported))
    con.executemany("insert into rep_audit values (?, ?, ?, ?, ?, ?)", rows)
    return list(AUXILIARY_TABLES)


def _aux_query(table: Table) -> str:
    source = {"report:reconciliation": "rep_reconciliation", "report:audit": "rep_audit"}[table.sql]
    return f"select {', '.join(table.column_names)} from {source} order by 1"


def export_model(
    processed: Path,
    directory: Path,
    *,
    references: References,
    parquet: bool = False,
    reports: Path | None = None,
) -> dict[str, Any]:
    """Export every table. Returns a deterministic summary (row counts, SHA-256, totals)."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    con = connect_model(processed, references)
    summary: dict[str, Any] = {"source": Path(processed).name, "tables": {}}
    for table in [*TABLES, *load_auxiliary(con, reports)]:
        sql, params = table_query(table)
        header = [
            d[0] for d in con.execute(f"select * from ({sql}) limit 0", params or None).description
        ]
        if header != table.column_names:
            raise ValueError(f"{table.name}: columns {header} != schema {table.column_names}")
        formats = ["csv"] + (["parquet"] if parquet else [])
        entry: dict[str, Any] = {}
        for fmt in formats:
            path = directory / f"{table.name}.{fmt}"
            _copy(con, sql, params, path, fmt)
            entry[fmt] = (
                {"file": path.name, "sha256": sha256_file(path)}
                if fmt == "csv"
                else {"file": path.name}
            )
        (rows,) = con.execute(f"select count(*) from ({sql})", params or None).fetchone()
        entry["rows"] = int(rows)
        summary["tables"][table.name] = entry
    (cents,) = con.execute("select sum(val_tot_cents) from base").fetchone()
    summary["fact_valor_total_centavos"] = int(cents)
    summary["references"] = {
        name: {"file": p["file"], "sha256": p["sha256"]}
        for name, p in sorted(references.provenance.items())
    }
    log.info("exported %d tables to %s", len(TABLES), directory)
    return summary


LABEL_COMPARISONS = (
    # (table, code column, secondary label, official label)
    ("dim_especialidade", "especialidade_cod", "descricao", "descricao_oficial"),
    ("dim_carater", "carater_cod", "descricao", "descricao_oficial"),
    ("dim_complexidade", "complexidade_cod", "descricao", "descricao_oficial"),
    ("dim_tipo_aih", "tipo_aih_cod", "descricao", "descricao_oficial"),
    ("dim_perfil_demografico", "sexo_cod", "sexo_descricao", "sexo_descricao_oficial"),
    ("dim_perfil_demografico", "raca_cor_cod", "raca_cor_descricao", "raca_cor_descricao_oficial"),
    ("dim_procedimento", "grupo_cod", "grupo_descricao", "grupo_nome_sigtap"),
)


def _fold(text: str) -> str:
    import unicodedata

    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return " ".join("".join(c for c in decomposed if not unicodedata.combining(c)).split())


def enrichment_report(directory: Path) -> dict[str, Any]:
    """Coverage of every enriched column and secondary × official label comparison (aggregates
    and code labels only; read from the exported CSV files)."""
    con = duckdb.connect()
    directory = Path(directory)
    coverage = []
    for table, columns in ENRICHED_COLUMNS.items():
        source = _csv(con, directory, table)
        for column in columns:
            rows, filled, distinct = con.execute(
                f"select count(*), count(nullif({column}, '')), count(distinct {column})"
                f" from {source}"
            ).fetchone()
            coverage.append(
                {"table": table, "column": column, "rows": rows, "filled": filled,
                 "distinct": distinct, "pct": round(100 * filled / rows, 2) if rows else 0.0}
            )  # fmt: skip
    comparisons = []
    for table, code, secondary, official in LABEL_COMPARISONS:
        for c, s, o in con.execute(
            f"select distinct {code}, {secondary}, {official} from {_csv(con, directory, table)}"
            " order by 1"
        ).fetchall():
            if not s:
                status = "novo (sem rótulo secundário)"
            elif not o:
                status = "sem rótulo oficial"
            elif s == o:
                status = "igual"
            elif _fold(s) == _fold(o):
                status = "igual (grafia)"
            else:
                status = "diferente — adotado o oficial"
            comparisons.append(
                {"table": table, "code_column": code, "code": c, "secondary": s or None,
                 "official": o or None, "status": status}
            )  # fmt: skip
    est = _csv(con, directory, "dim_estabelecimento")
    (repeated_groups, repeated_establishments) = con.execute(
        "select count(*), coalesce(sum(n), 0) from (select estabelecimento_nome, count(*) n"
        f" from {est} group by 1 having count(*) > 1)"
    ).fetchone()
    return {
        "coverage": coverage,
        "label_comparison": comparisons,
        "establishment_names": {
            "repeated_name_groups": int(repeated_groups),
            "establishments_with_repeated_name": int(repeated_establishments),
            "note": "estabelecimento_rotulo = nome (CNES) is unique and should be used in visuals",
        },
    }


def enrichment_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Enriquecimento das dimensões — cobertura e rótulos oficiais",
        "",
        "> Gerado por `hospital-analytics powerbi` a partir dos CSV exportados. Não editar"
        " manualmente. Apenas agregados e rótulos de códigos (nenhum dado de pessoa).",
        "",
        "## Cobertura por coluna",
        "",
        "| Tabela | Coluna | Linhas | Preenchidas | % | Valores distintos |",
        "|---|---|---:|---:|---:|---:|",
    ]
    lines += [
        f"| `{c['table']}` | `{c['column']}` | {c['rows']} | {c['filled']} | {c['pct']:.2f} "
        f"| {c['distinct']} |"
        for c in report["coverage"]
    ]
    lines += [
        "",
        "## Rótulos: fonte secundária × fonte oficial",
        "",
        "Os visuais usam a coluna oficial. A coluna secundária é mantida (nada é sobrescrito).",
        "",
        "| Tabela | Código | Secundária | Oficial | Situação |",
        "|---|---|---|---|---|",
    ]
    lines += [
        f"| `{c['table']}` ({c['code_column']}) | `{c['code']}` | {c['secondary'] or '—'} "
        f"| {c['official'] or '—'} | {c['status']} |"
        for c in report["label_comparison"]
    ]
    names = report["establishment_names"]
    lines += [
        "",
        "## Nomes de estabelecimentos",
        "",
        f"- Grupos de nome fantasia repetido: {names['repeated_name_groups']} "
        f"({names['establishments_with_repeated_name']} estabelecimentos) — usar "
        "`estabelecimento_rotulo` (nome + CNES), que é único.",
        "",
    ]
    return "\n".join(lines)


def write_enrichment_report(report: dict[str, Any], directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "enriquecimento.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", "utf-8", newline="\n"
    )
    (directory / "enriquecimento.md").write_text(enrichment_markdown(report), "utf-8", newline="\n")


def write_summary(summary: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", "utf-8", newline="\n")


# ---------------------------------------------------------------------------
# Validation of the exported files (independent of the pipeline code paths)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ModelCheck:
    name: str
    expected: Any
    observed: Any

    @property
    def passed(self) -> bool:
        return self.expected == self.observed


def _csv(con, directory: Path, name: str) -> str:
    path = directory / f"{name}.csv"
    return f"read_csv({path_literal(path)}, header = true, all_varchar = true)"


def validate_model(directory: Path, expected: dict[str, Any]) -> list[ModelCheck]:
    """Check keys, referential integrity, join fan-out and indicator values on the CSV files.

    ``expected`` holds reference values: records, val_tot_cents, deaths, dias_perm_sum,
    age_years_count (and, optionally, any indicator from the reconciliation report).
    """
    con = duckdb.connect()
    present = [t for t in ALL_TABLES if (Path(directory) / f"{t.name}.csv").is_file()]
    for t in present:
        con.execute(f"create view {t.name} as select * from {_csv(con, directory, t.name)}")
    checks: list[ModelCheck] = []
    for t in present:
        cols = ", ".join(t.key)
        (dup, nulls) = con.execute(
            f"select count(*) - count(distinct ({cols})), "
            f"count(*) filter (where {t.key[0]} is null) from {t.name}"
        ).fetchone()
        checks.append(ModelCheck(f"{t.name}: key {cols} unique", 0, int(dup)))
        checks.append(ModelCheck(f"{t.name}: key {cols} not null", 0, int(nulls)))
        header = [d[0] for d in con.execute(f"select * from {t.name} limit 0").description]
        checks.append(ModelCheck(f"{t.name}: columns match schema", t.column_names, header))
    for fact_col, dim, dim_col, _, _ in RELATIONSHIPS:
        (orphans,) = con.execute(
            f"select count(*) from fato_registro_aih f "
            f"left join {dim} d on f.{fact_col} = d.{dim_col} "
            f"where d.{dim_col} is null"
        ).fetchone()
        checks.append(
            ModelCheck(f"RI fato.{fact_col} -> {dim}.{dim_col}: orphans", 0, int(orphans))
        )
        if dim != "dim_mes":  # dim_mes holds complete years on purpose
            (dim_rows, fact_keys) = con.execute(
                f"select (select count(*) from {dim}),"
                f" (select count(distinct {fact_col}) from fato_registro_aih)"
            ).fetchone()
            checks.append(
                ModelCheck(
                    f"{dim}: rows == distinct fato.{fact_col} (no fan-out, no extra rows)",
                    int(fact_keys),
                    int(dim_rows),
                )
            )
    for table, columns in ENRICHED_COLUMNS.items():
        if table not in {t.name for t in present}:
            continue
        for column in columns:
            (rows, filled) = con.execute(
                f"select count(*), count(nullif({column}, '')) from {table}"
            ).fetchone()
            checks.append(
                ModelCheck(f"coverage {table}.{column}: rows with official value", rows, filled)
            )
    joins = " ".join(
        f"join {dim} on f.{fc} = {dim}.{dc}" for fc, dim, dc, _, active in RELATIONSHIPS if active
    )
    (rows, rows_joined, cents_joined) = con.execute(
        "select (select count(*) from fato_registro_aih), count(*), "
        "sum(cast(f.valor_total_centavos as bigint)) "
        f"from fato_registro_aih f {joins}"
    ).fetchone()
    checks.append(
        ModelCheck("join with all active dimensions keeps row count", int(rows), int(rows_joined))
    )
    fact = con.execute(
        """select count(*), sum(cast(valor_total_centavos as bigint)),
                  sum(cast(valor_total as decimal(18,2))),
                  sum(cast(obito as int)), sum(cast(dias_permanencia as bigint)), count(idade_anos),
                  count(distinct aih_id),
                  count(*) filter (
                      where cast(valor_total as decimal(18,2)) * 100
                          <> cast(valor_total_centavos as bigint))
           from fato_registro_aih"""
    ).fetchone()
    records, cents, money, deaths, los_sum, ages, aihs, money_mismatch = fact
    checks += [
        ModelCheck("fact records == pipeline", expected["records"], int(records)),
        ModelCheck("fact valor_total_centavos == pipeline", expected["val_tot_cents"], int(cents)),
        ModelCheck(
            "fact valor_total (decimal) == centavos / 100",
            Decimal(expected["val_tot_cents"]) / 100,
            money,
        ),
        ModelCheck("join preserves financial total", expected["val_tot_cents"], int(cents_joined)),
        ModelCheck("valor_total and centavos agree row by row", 0, int(money_mismatch)),
        ModelCheck("deaths == pipeline", expected["deaths"], int(deaths)),
        ModelCheck("sum of dias_permanencia == pipeline", expected["dias_perm_sum"], int(los_sum)),
        ModelCheck("non-null idade_anos == pipeline", expected["age_years_count"], int(ages)),
    ]
    if "distinct_aih" in expected:
        checks.append(
            ModelCheck("distinct aih_id == distinct N_AIH", expected["distinct_aih"], int(aihs))
        )
    return checks


def _dashboard_measures(con, directory: Path) -> dict[str, Decimal]:
    """Equivalents of the dashboard measures that are not historical indicators (base completa).
    Written to reports/powerbi/medidas_referencia.json to check the cards in Power BI."""
    for name in ("dim_estabelecimento", "dim_municipio_residencia", "dim_tipo_aih"):
        con.execute(f"create or replace view {name} as select * from {_csv(con, directory, name)}")
    row = con.execute(
        """select count(*),
                  count(distinct f.cnes),
                  count(distinct f.municipio_residencia_cod),
                  count(*) filter (where f.carater_cod = '02'),
                  count(*) filter (where f.municipio_residencia_cod
                                   <> e.municipio_estabelecimento_cod),
                  count(*) filter (where m.uf_residencia_cod <> '33'),
                  count(*) filter (where f.tipo_aih_cod = '1'),
                  sum(cast(f.obito as int)) filter (where f.tipo_aih_cod = '1'),
                  count(*) filter (where cast(f.valor_total_centavos as bigint) = 0),
                  count(*) filter (where f.aih_repetida = '1'),
                  count(distinct f.aih_id),
                  count(*) filter (where f.tipo_aih_cod = '5')
           from f
           join dim_estabelecimento e on e.cnes = f.cnes
           join dim_municipio_residencia m
             on m.municipio_residencia_cod = f.municipio_residencia_cod"""
    ).fetchone()
    (n, estab, munic, urg, other_munic, other_uf, n1, deaths1, zero, rep, aihs, n5) = row
    return {
        "aihs_distintas": Decimal(aihs),
        "registros_excedentes_aih": Decimal(n - aihs),
        "registros_aih_repetida": Decimal(rep),
        "registros_longa_permanencia": Decimal(n5),
        "registros_valor_zero": Decimal(zero),
        "estabelecimentos": Decimal(estab),
        "municipios_residencia": Decimal(munic),
        "pct_urgencia_razao": Decimal(urg) / n,
        "pct_residentes_outro_municipio_razao": Decimal(other_munic) / n,
        "pct_residentes_fora_rj_razao": Decimal(other_uf) / n,
        "mortalidade_aih_principal_razao": Decimal(deaths1) / n1,
    }


# Measure equivalents checked against the reconciled indicators: (indicator id, scale).
MEASURE_INDICATORS = {
    "registros_aih": ("records_full", 1),
    "valor_total": ("val_tot_full", 1),
    "valor_medio": ("val_mean_full", 1),
    "permanencia_media": ("los_mean_full", 1),
    "obitos": ("deaths_full", 1),
    "mortalidade_razao": ("mortality_full", 100),
    "idade_media_anos": ("age_mean_years_full", 1),
    "concentracao_top10_razao": ("top10_share_full", 100),
}


def pipeline_checks(directory: Path, reports: Path) -> tuple[list[ModelCheck], dict[str, Decimal]]:
    """Model checks with expected values taken from the versioned pipeline reports.

    The reconciliation report gives the exact aggregates and indicators; the analysis report,
    the Lorenz points. Returns the checks and the measure equivalents (for the reference file).
    """
    reconciliation = json.loads(
        (reports / "indicators" / "reconciliation.json").read_text(encoding="utf-8")
    )
    full = reconciliation["aggregates"]["base"]["full"]
    expected = {
        "records": full["records"],
        "val_tot_cents": full["val_tot_cents"],
        "deaths": full["deaths"],
        "dias_perm_sum": full["dias_perm_sum"],
        "age_years_count": full["age_years_count"],
        "distinct_aih": full["records"]
        - reconciliation["aggregates"]["repeated_aih"]["excess_records"],
    }
    checks = validate_model(directory, expected)
    indicator = {r["id"]: r for r in reconciliation["indicators"]}
    measures = measure_values(directory)
    q = Decimal("0.0001")
    for measure, (indicator_id, scale) in MEASURE_INDICATORS.items():
        reference = (Decimal(indicator[indicator_id]["reproduced"]) / scale).quantize(q)
        checks.append(
            ModelCheck(
                f"measure {measure} == indicator {indicator_id}",
                reference,
                measures[measure].quantize(q),
            )
        )
    checks.append(
        ModelCheck(
            "dashboard: distinct AIH == records - repeated-AIH excess",
            Decimal(expected["distinct_aih"]),
            measures["aihs_distintas"],
        )
    )
    analysis_path = reports / "analysis" / "analysis.json"
    if analysis_path.is_file():
        lorenz = lorenz_points(directory)
        for point in json.loads(analysis_path.read_text(encoding="utf-8"))["lorenz"]:
            p = point["records_pct"]
            checks.append(
                ModelCheck(
                    f"aux_curva_lorenz p={p} == analysis report (%, 2 decimals)",
                    Decimal(point["value_pct"]),
                    (lorenz[p] * 100).quantize(Decimal("0.01")),
                )
            )
    return checks, measures


def write_measure_reference(measures: dict[str, Decimal], path: Path) -> None:
    """Exact values of the DAX-equivalent measures, used to check the cards in Power BI."""
    base = "completa (73.046 registros, competência 2024-01)"
    document = {
        "base": base if measures["registros_aih"] == 73046 else "completa",
        "nota": "Valores exatos das medidas DAX equivalentes (razões não multiplicadas"
        " por 100). Use-os para conferir os cartões no Power BI.",
        "medidas": {k: str(v.quantize(Decimal("0.000001"))) for k, v in sorted(measures.items())},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n", "utf-8", newline="\n"
    )


def lorenz_points(directory: Path) -> dict[int, Decimal]:
    con = duckdb.connect()
    rows = con.execute(
        f"select percentil, pct_valor from {_csv(con, directory, 'aux_curva_lorenz')}"
    ).fetchall()
    return {int(p): Decimal(v) for p, v in rows}


def measure_values(directory: Path) -> dict[str, Decimal]:
    """Python/SQL equivalents of the DAX measures, computed on the exported CSV files."""
    con = duckdb.connect()
    con.execute(f"create view f as select * from {_csv(con, directory, 'fato_registro_aih')}")
    (n, cents, deaths, los, age_sum, age_n) = con.execute(
        """select count(*), sum(cast(valor_total_centavos as bigint)), sum(cast(obito as int)),
                  sum(cast(dias_permanencia as bigint)), sum(cast(idade_anos as decimal(18,6))),
                  count(idade_anos) from f"""
    ).fetchone()
    k = int(Decimal(n) * Decimal("0.1"))
    (top,) = con.execute(
        f"""select sum(c) from (select cast(valor_total_centavos as bigint) c from f
            order by c desc, cast(registro_id as bigint) asc limit {k})"""
    ).fetchone()
    extra = _dashboard_measures(con, directory)
    return extra | {
        "registros_aih": Decimal(n),
        "valor_total": Decimal(cents) / 100,
        "valor_medio": Decimal(cents) / n / 100,
        "permanencia_media": Decimal(los) / n,
        "obitos": Decimal(deaths),
        "mortalidade_razao": Decimal(deaths) / n,
        "idade_media_anos": Decimal(age_sum) / age_n,
        "concentracao_top10_razao": Decimal(top) / cents,
    }


# ---------------------------------------------------------------------------
# Generated documentation and Power Query
# ---------------------------------------------------------------------------
def field_dictionary_markdown() -> str:
    lines = [
        "# Dicionário de campos — modelo Power BI",
        "",
        "> Gerado a partir de `src/hospital_analytics/powerbi.py` (`TABLES`)."
        " Não editar manualmente.",
        "",
    ]
    for t in ALL_TABLES:
        lines += [
            f"## `{t.name}`",
            "",
            f"- **Granularidade:** {t.grain}",
            f"- **Chave:** `{', '.join(t.key)}`",
            "",
        ]
        lines += [
            "| Campo | Tipo (Power Query) | Pode ser nulo | Origem | Descrição |",
            "|---|---|---|---|---|",
        ]
        lines += [
            f"| `{c.name}` | `{c.m_type}` | {'sim' if c.nullable else 'não'} "
            f"| {c.origin} | {c.description} |"
            for c in t.columns
        ]
        lines.append("")
    lines += [
        "## Relacionamentos",
        "",
        "| Fato | Dimensão | Cardinalidade | Ativo | Direção do filtro |",
        "|---|---|---|---|---|",
    ]
    lines += [
        f"| `fato_registro_aih[{fc}]` | `{dim}[{dc}]` | {card} "
        f"| {'sim' if active else 'não (USERELATIONSHIP)'} | única (dimensão → fato) |"
        for fc, dim, dc, card, active in RELATIONSHIPS
    ]
    lines += [
        "",
        "## Campos de origem não exportados (privacidade / minimização)",
        "",
        "| Campo | Motivo |",
        "|---|---|",
    ]
    lines += [f"| `{k}` | {v} |" for k, v in EXCLUDED_FIELDS.items()]
    return "\n".join(lines) + "\n"


def power_query_m() -> str:
    """One Power Query (M) query per table: CSV read with explicit types and en-US culture."""
    out = [
        "// Gerado a partir de src/hospital_analytics/powerbi.py — não editar manualmente.",
        "// 1) Crie o parâmetro PastaDados (Texto) com o caminho da pasta data/powerbi"
        " (terminado em \\).",
        "// 2) Crie uma consulta em branco por tabela e cole o bloco correspondente.",
        "",
    ]
    for t in ALL_TABLES:
        types = ",\n        ".join(f'{{"{c.name}", {c.m_type}}}' for c in t.columns)
        out += [
            f"// ---- {t.name} ----",
            "let",
            f'    Fonte = Csv.Document(File.Contents(PastaDados & "{t.name}.csv"),'
            f' [Delimiter = ",", Columns = {len(t.columns)}, Encoding = 65001,'
            " QuoteStyle = QuoteStyle.Csv]),",
            "    Cabecalho = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true]),",
            "    Tipos = Table.TransformColumnTypes(Cabecalho, {",
            f"        {types}",
            '    }, "en-US")',
            "in",
            "    Tipos",
            "",
        ]
    return "\n".join(out)
