"""Analytical layer for Power BI: star schema exported as CSV (UTF-8) and optionally Parquet.

A single schema (``TABLES``) drives everything: the export, the field dictionary, the Power
Query (M) import script and the tests. Grain of the fact table: one row per AIH *record*.
A record is not a patient and not necessarily a distinct admission (see docs/powerbi/modelo.md).

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
from hospital_analytics.integrity import sha256_file
from hospital_analytics.sql import read_sql

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


@dataclass(frozen=True)
class Table:
    name: str
    key: tuple[str, ...]
    grain: str
    columns: tuple[Column, ...]
    sql: str  # sql/powerbi/<sql>.sql, or "report:<name>" for auxiliary tables built from reports
    code_dimension: tuple[str, str] | None = None  # (source column, codebook field)

    @property
    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]


TXT, INT, DATE, NUM, CUR = "type text", "Int64.Type", "type date", "type number", "Currency.Type"


def _code_dim(name: str, code_col: str, source: str, field: str, what: str) -> Table:
    return Table(
        name,
        (code_col,),
        f"1 linha por código de {source} presente no fato",
        (
            Column(code_col, TXT, f"Código de {what} ({source})", source),
            Column("descricao", TXT, f"Descrição do código ({what})", "dicionário", nullable=True),
            Column("fonte", TXT, "Fonte/status da interpretação do código", "dicionário"),
        ),
        "dim_code",
        (source, field),
    )


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
                "Diagnóstico principal, código CID-10 (sem dimensão: descrições pendentes)",
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
            Column(
                "natureza_juridica_cod",
                TXT,
                "Natureza jurídica (código; descrição pendente)",
                "NAT_JUR",
            ),
            Column("gestao_cod", TXT, "Tipo de gestão (código; descrição pendente)", "GESTAO"),
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
        ),
        "dim_procedimento",
    ),
    _code_dim("dim_especialidade", "especialidade_cod", "ESPEC", "ESPEC", "especialidade do leito"),
    _code_dim("dim_carater", "carater_cod", "CAR_INT", "CAR_INT", "caráter da internação"),
    _code_dim("dim_complexidade", "complexidade_cod", "COMPLEX", "COMPLEX", "complexidade"),
    _code_dim("dim_tipo_aih", "tipo_aih_cod", "IDENT", "IDENT", "tipo de AIH"),
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
        ),
        "dim_perfil_demografico",
    ),
)

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
def _literal(path: Path) -> str:
    return "'" + str(Path(path).resolve()).replace("'", "''") + "'"


def connect_model(processed: Path) -> duckdb.DuckDBPyConnection:
    """Connection with the processed layer, the codebook and the ``base`` table."""
    con = duckdb.connect()
    con.execute(
        "create view rd_file as select * from "
        f"read_parquet({_literal(processed)}, file_row_number = true)"
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
    return con


def table_query(table: Table) -> tuple[str, dict[str, Any]]:
    if table.sql.startswith("report:"):
        return _aux_query(table), {}
    sql = read_sql(f"powerbi/{table.sql}")
    if table.code_dimension is None:
        return sql, {}
    source, field = table.code_dimension
    allowed = {t.code_dimension[0] for t in TABLES if t.code_dimension}
    if source not in allowed or not source.isidentifier():
        raise ValueError(f"column {source!r} is not an allowed code-dimension source")
    if field not in CODEBOOK:
        raise ValueError(f"field {field!r} is not in the codebook")
    # Identifiers cannot be bound as parameters: both names come from the closed lists above.
    sql = sql.replace('"$source_column"', f'"{source}"').replace("$field", f"'{field}'")
    sql = f"select code as {table.key[0]}, descricao, fonte from ({sql}) order by 1"
    return sql, {}


def _copy(con, sql: str, params: dict, destination: Path, fmt: str) -> None:
    options = (
        "format csv, header true, delimiter ','"
        if fmt == "csv"
        else "format parquet, compression zstd"
    )
    partial = destination.with_name(destination.name + ".partial")
    con.execute(f"copy ({sql}) to {_literal(partial)} ({options})", params or None)
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
    processed: Path, directory: Path, *, parquet: bool = False, reports: Path | None = None
) -> dict[str, Any]:
    """Export every table. Returns a deterministic summary (row counts, SHA-256, totals)."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    con = connect_model(processed)
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
    log.info("exported %d tables to %s", len(TABLES), directory)
    return summary


def write_summary(summary: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", "utf-8")


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
    return f"read_csv({_literal(path)}, header = true, all_varchar = true)"


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
    return {
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
