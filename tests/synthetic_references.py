"""SYNTHETIC official reference files (SIGTAP, IBGE, CNES CADGER, TabWin .cnv) for the records of
``synthetic_data.SIH_RECORDS``. Same formats as the official files; every value is fictitious.

``build_references(directory)`` writes the files and returns the ``reference_sources`` mapping
(sizes and SHA-256 computed on the written files), ready for ``load_references``.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from synthetic_data import FieldSpec, build_dbf, write

from hospital_analytics.integrity import sha256_file


def layout(*fields: tuple[str, int]) -> str:
    lines, start = ["Coluna,Tamanho,Inicio,Fim,Tipo"], 1
    for name, size in fields:
        lines.append(f"{name},{size},{start},{start + size - 1},VARCHAR2")
        start += size
    return "\r\n".join(lines) + "\r\n"


def fixed_rows(widths: tuple[int, ...], rows: list[tuple[str, ...]]) -> bytes:
    return b"".join(
        b"".join(v.encode("cp1252").ljust(w) for v, w in zip(r, widths, strict=True)) + b"\r\n"
        for r in rows
    )


PROCEDURES = {
    "0201010010": "BIOPSIA SINTETICA",
    "0303010010": "TRATAMENTO SINTETICO A",
    "0303060010": "TRATAMENTO SINTETICO B",
    "0303150010": "TRATAMENTO SINTETICO C",
    "0303170010": "TRATAMENTO SINTETICO D",
    "0411010010": "PARTO SINTETICO",
    "0415010010": "CIRURGIA SINTETICA A",
    "0415020010": "CIRURGIA SINTETICA B",
}
CID = {"J18": "Pneumonia sintética", "J189": "Pneumonia sintética não especificada"}
SIGTAP_TABLES = {
    "tb_procedimento": (
        (("CO_PROCEDIMENTO", 10), ("NO_PROCEDIMENTO", 30), ("DT_COMPETENCIA", 6)),
        [(c, n, "202401") for c, n in PROCEDURES.items()],
    ),
    "tb_grupo": (
        (("CO_GRUPO", 2), ("NO_GRUPO", 30), ("DT_COMPETENCIA", 6)),
        [("02", "Diagnóstico sintético", "202401"), ("03", "Clínico sintético", "202401"),
         ("04", "Cirúrgico sintético", "202401")],
    ),
    "tb_sub_grupo": (
        (("CO_GRUPO", 2), ("CO_SUB_GRUPO", 2), ("NO_SUB_GRUPO", 30), ("DT_COMPETENCIA", 6)),
        [("02", "01", "Coleta", "202401"), ("03", "03", "Tratamentos", "202401"),
         ("04", "11", "Obstetrícia", "202401"), ("04", "15", "Múltiplas", "202401")],
    ),
    "tb_forma_organizacao": (
        (("CO_GRUPO", 2), ("CO_SUB_GRUPO", 2), ("CO_FORMA_ORGANIZACAO", 2),
         ("NO_FORMA_ORGANIZACAO", 30), ("DT_COMPETENCIA", 6)),
        [(c[:2], c[2:4], c[4:6], f"Forma {c[:6]}", "202401")
         for c in sorted({p[:6] + "0000" for p in PROCEDURES})],
    ),
    "tb_cid": (
        (("CO_CID", 4), ("NO_CID", 40), ("TP_AGRAVO", 1)),
        [(c, n, "0") for c, n in CID.items()],
    ),
}  # fmt: skip

# TabWin conversion tables, in the variants found in the official package: optional flags,
# catch-all ranges listed first, hierarchical lines, continuation lines and trailing commas.
CNV_FILES = {
    "LEITOS.CNV": "N 3 2 L\n  1  01-Cirúrgico         01\n  2  03-Clínico           03\n"
    "  3  87-Saúde Mental (Clínico) 87\n",
    "IDENT.CNV": "3 1\n  3  Outras/ignorado     0-9\n  1  Normal              1\n"
    "  2  Longa permanência   5\n",
    "CARATEND.CNV": "2 2\n  1  01 Eletivo          01\n  2  02 Urgência         02\n",
    "COMPLEX2.CNV": "03 2\n 03  Não se aplica       00-99\n 01  Média complexidade  02\n"
    " 02  Alta complexidade   03\n",
    "SEXO.CNV": "3 1\n  3  Ignorado            0-9\n  1  Masculino           1\n"
    "  2  Feminino            2,3\n",
    "RACACOR.CNV": "3 2 L\n  3  Sem informação      00-99\n  1  Branca              01\n"
    "  2  Parda               03\n",
    "natjur.cnv": "N 3 4\n  3  --- Não especificado   -zzzz,\n"
    " 01  1. Administracao Publica  1000-1999,\n  01  02  102-3 Orgao Publico Estadual 1023\n",
    "esferajur.cnv": "3 4\n 01  Administração Pública  1000-1999,\n 01  02  .. Estadual  1023,\n"
    " 01  02  .. Estadual  1058\n 03  Não especificado  0000\n",
    "GESTAO.CNV": "2 1 L\n  1  Estadual plena      2,E\n  2  Municipal plena assist  1,M\n",
    "CID10CAP.CNV": "2 3 L\n  1  X.   Doenças do aparelho respiratório   J00-J99,\n"
    "  2  Não preenchido      ,\n",
}  # fmt: skip
CNV_SOURCES = {
    "sih_leitos": "LEITOS.CNV",
    "sih_ident": "IDENT.CNV",
    "sih_carater": "CARATEND.CNV",
    "sih_complexidade": "COMPLEX2.CNV",
    "sih_sexo": "SEXO.CNV",
    "sih_raca_cor": "RACACOR.CNV",
    "sih_natureza_juridica": "natjur.cnv",
    "sih_esfera_juridica": "esferajur.cnv",
    "sih_gestao": "GESTAO.CNV",
    "sih_cid10_capitulo": "CID10CAP.CNV",
}
CADGER_FIELDS = (
    FieldSpec("CNES", "C", 7),
    FieldSpec("RAZ_SOCI", "C", 30),
    FieldSpec("FANTASIA", "C", 30),
    FieldSpec("CPF_CNPJ", "C", 14),
)
CADGER_ROWS = [
    ["0000001", "RAZAO SOCIAL SECRETA UM", "HOSPITAL SINTETICO UM", "11111111000191"],
    ["0000002", "RAZAO SOCIAL SECRETA DOIS", "HOSPITAL SINTETICO DOIS", "22222222000191"],
    ["0000003", "RAZAO SOCIAL SECRETA TRES", "CLINICA FORA DO MODELO", "33333333000191"],
]


def ibge(code: int, name: str, uf_id: int, sigla: str) -> dict:
    uf = {"id": uf_id, "sigla": sigla, "nome": "x"}
    return {"id": code, "nome": name, "microrregiao": {"mesorregiao": {"UF": uf}}}


def build_references(directory: Path, *, sigtap_tables: dict | None = None) -> dict:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    sigtap = directory / "TabelaUnificada_SYNTH.zip"
    with zipfile.ZipFile(sigtap, "w") as zf:
        for table, (fields, rows) in (sigtap_tables or SIGTAP_TABLES).items():
            zf.writestr(f"{table}_layout.txt", layout(*fields))
            zf.writestr(f"{table}.txt", fixed_rows(tuple(w for _, w in fields), rows))
    municipios = [ibge(3304557, "Rio de Janeiro", 33, "RJ"), ibge(3500001, "Sintética", 35, "SP")]
    (directory / "municipios.json").write_text(json.dumps(municipios), encoding="utf-8")
    write(
        directory / "CADGER.dbf",
        build_dbf(CADGER_FIELDS, CADGER_ROWS, encoding="cp1252", language_driver=0x58),
    )
    for name, text in CNV_FILES.items():
        (directory / name).write_bytes(text.encode("cp1252"))

    def spec(filename: str, **extra) -> dict:
        path = directory / filename
        return {
            "filename": filename,
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            **extra,
        }

    sources = {
        "sigtap": spec(sigtap.name, competence="2024-01"),
        "ibge_municipios": spec("municipios.json", file_timestamp="2026-11-10T19:19:32-03:00"),
        "cnes_cadger": spec(
            "CADGER.dbf", encoding="cp1252", key_column="CNES", name_column="FANTASIA"
        ),
    }
    for source, filename in CNV_SOURCES.items():
        sources[source] = spec(
            filename, kind="cnv", start=1, official_package=f"TAB_SYNTH.zip (CNV/{filename})"
        )
    return sources
