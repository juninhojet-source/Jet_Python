/**
 * Conexão com o banco de dados SQLite
 * SIGAZ - PMBC
 *
 * Usa node:sqlite (nativo do Node 22+), sem dependências externas
 * que precisem ser compiladas.
 */
const path = require('path');
const fs = require('fs');
const { DatabaseSync } = require('node:sqlite');
require('dotenv').config();

const DB_PATH = process.env.DB_PATH || path.join(__dirname, 'sigaz.db');

// Garantir que o diretório exista
const dbDir = path.dirname(DB_PATH);
if (!fs.existsSync(dbDir)) {
  fs.mkdirSync(dbDir, { recursive: true });
}

function abrirConexao() {
  const c = new DatabaseSync(DB_PATH);
  c.exec('PRAGMA journal_mode = WAL');
  c.exec('PRAGMA foreign_keys = ON');
  return c;
}

let _db = abrirConexao();

// Adapter compatível com a API do better-sqlite3 + reconexão para restauração
const db = {
  exec: (sql) => _db.exec(sql),
  prepare: (sql) => _db.prepare(sql),
  pragma: (s) => _db.exec('PRAGMA ' + s),
  close: () => _db.close(),
  // Fecha e reabre a conexão — usado depois de restauração
  reconectar: () => {
    try { _db.close(); } catch (e) { /* ignore */ }
    _db = abrirConexao();
  },
  // Caminho do arquivo do banco — útil pra backup/restore
  caminho: DB_PATH
};

module.exports = db;
