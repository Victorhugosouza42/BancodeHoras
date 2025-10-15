-- schema.sql (versão com status)

DROP TABLE IF EXISTS usuarios;
DROP TABLE IF EXISTS transacoes;

CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT UNIQUE NOT NULL,
    senha TEXT NOT NULL,
    saldo_atual INTEGER NOT NULL DEFAULT 0,
    is_admin INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE transacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario INTEGER NOT NULL,
    tipo TEXT NOT NULL,
    dias INTEGER NOT NULL,
    data TEXT NOT NULL,
    motivo TEXT NOT NULL,
    -- NOVA COLUNA PARA O STATUS DA SOLICITAÇÃO
    status TEXT NOT NULL DEFAULT 'pendente' CHECK(status IN ('pendente', 'aprovado', 'recusado')),
    FOREIGN KEY (id_usuario) REFERENCES usuarios (id) ON DELETE CASCADE
);