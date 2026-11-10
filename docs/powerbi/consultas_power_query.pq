// Gerado a partir de src/hospital_analytics/powerbi.py — não editar manualmente.
// 1) Crie o parâmetro PastaDados (Texto) com o caminho da pasta data/powerbi (terminado em \).
// 2) Crie uma consulta em branco por tabela e cole o bloco correspondente.

// ---- fato_registro_aih ----
let
    Fonte = Csv.Document(File.Contents(PastaDados & "fato_registro_aih.csv"), [Delimiter = ",", Columns = 22, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Cabecalho = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Cabecalho, {
        {"registro_id", Int64.Type},
        {"aih_id", Int64.Type},
        {"competencia", type text},
        {"mes_saida", type date},
        {"mes_internacao", type date},
        {"cnes", type text},
        {"municipio_residencia_cod", type text},
        {"procedimento_cod", type text},
        {"diagnostico_principal_cod", type text},
        {"especialidade_cod", type text},
        {"carater_cod", type text},
        {"complexidade_cod", type text},
        {"tipo_aih_cod", type text},
        {"perfil_id", Int64.Type},
        {"valor_total", Currency.Type},
        {"valor_total_centavos", Int64.Type},
        {"dias_permanencia", Int64.Type},
        {"dias_entre_datas", Int64.Type},
        {"idade_anos", type number},
        {"obito", Int64.Type},
        {"aih_ocorrencias", Int64.Type},
        {"aih_repetida", Int64.Type}
    }, "en-US")
in
    Tipos

// ---- dim_mes ----
let
    Fonte = Csv.Document(File.Contents(PastaDados & "dim_mes.csv"), [Delimiter = ",", Columns = 7, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Cabecalho = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Cabecalho, {
        {"mes", type date},
        {"ano", Int64.Type},
        {"trimestre", Int64.Type},
        {"mes_num", Int64.Type},
        {"ano_mes", type text},
        {"ano_mes_ordem", Int64.Type},
        {"mes_abrev", type text}
    }, "en-US")
in
    Tipos

// ---- dim_estabelecimento ----
let
    Fonte = Csv.Document(File.Contents(PastaDados & "dim_estabelecimento.csv"), [Delimiter = ",", Columns = 5, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Cabecalho = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Cabecalho, {
        {"cnes", type text},
        {"municipio_estabelecimento_cod", type text},
        {"uf_estabelecimento_cod", type text},
        {"natureza_juridica_cod", type text},
        {"gestao_cod", type text}
    }, "en-US")
in
    Tipos

// ---- dim_municipio_residencia ----
let
    Fonte = Csv.Document(File.Contents(PastaDados & "dim_municipio_residencia.csv"), [Delimiter = ",", Columns = 2, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Cabecalho = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Cabecalho, {
        {"municipio_residencia_cod", type text},
        {"uf_residencia_cod", type text}
    }, "en-US")
in
    Tipos

// ---- dim_procedimento ----
let
    Fonte = Csv.Document(File.Contents(PastaDados & "dim_procedimento.csv"), [Delimiter = ",", Columns = 4, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Cabecalho = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Cabecalho, {
        {"procedimento_cod", type text},
        {"grupo_cod", type text},
        {"grupo_descricao", type text},
        {"grupo_fonte", type text}
    }, "en-US")
in
    Tipos

// ---- dim_especialidade ----
let
    Fonte = Csv.Document(File.Contents(PastaDados & "dim_especialidade.csv"), [Delimiter = ",", Columns = 3, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Cabecalho = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Cabecalho, {
        {"especialidade_cod", type text},
        {"descricao", type text},
        {"fonte", type text}
    }, "en-US")
in
    Tipos

// ---- dim_carater ----
let
    Fonte = Csv.Document(File.Contents(PastaDados & "dim_carater.csv"), [Delimiter = ",", Columns = 3, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Cabecalho = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Cabecalho, {
        {"carater_cod", type text},
        {"descricao", type text},
        {"fonte", type text}
    }, "en-US")
in
    Tipos

// ---- dim_complexidade ----
let
    Fonte = Csv.Document(File.Contents(PastaDados & "dim_complexidade.csv"), [Delimiter = ",", Columns = 3, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Cabecalho = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Cabecalho, {
        {"complexidade_cod", type text},
        {"descricao", type text},
        {"fonte", type text}
    }, "en-US")
in
    Tipos

// ---- dim_tipo_aih ----
let
    Fonte = Csv.Document(File.Contents(PastaDados & "dim_tipo_aih.csv"), [Delimiter = ",", Columns = 3, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Cabecalho = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Cabecalho, {
        {"tipo_aih_cod", type text},
        {"descricao", type text},
        {"fonte", type text}
    }, "en-US")
in
    Tipos

// ---- dim_perfil_demografico ----
let
    Fonte = Csv.Document(File.Contents(PastaDados & "dim_perfil_demografico.csv"), [Delimiter = ",", Columns = 7, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Cabecalho = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Cabecalho, {
        {"perfil_id", Int64.Type},
        {"faixa_etaria_ordem", Int64.Type},
        {"faixa_etaria", type text},
        {"sexo_cod", type text},
        {"sexo_descricao", type text},
        {"raca_cor_cod", type text},
        {"raca_cor_descricao", type text}
    }, "en-US")
in
    Tipos

// ---- ref_indicadores_validados ----
let
    Fonte = Csv.Document(File.Contents(PastaDados & "ref_indicadores_validados.csv"), [Delimiter = ",", Columns = 8, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Cabecalho = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Cabecalho, {
        {"indicador_id", type text},
        {"indicador", type text},
        {"base", type text},
        {"unidade", type text},
        {"historico", type text},
        {"reproduzido", type text},
        {"valor_exato", type number},
        {"status", type text}
    }, "en-US")
in
    Tipos

// ---- qualidade_campos ----
let
    Fonte = Csv.Document(File.Contents(PastaDados & "qualidade_campos.csv"), [Delimiter = ",", Columns = 6, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Cabecalho = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Cabecalho, {
        {"campo", type text},
        {"tipo_dbf", type text},
        {"vazios", Int64.Type},
        {"pct_vazios", type number},
        {"distintos", Int64.Type},
        {"exportado_powerbi", type text}
    }, "en-US")
in
    Tipos
