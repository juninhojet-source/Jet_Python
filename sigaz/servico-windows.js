/**
 * Instalador do SIGAZ como Serviço do Windows
 *
 * Uso (Windows, como Administrador):
 *   1. npm install node-windows --no-save
 *   2. node servico-windows.js instalar
 *
 * Outros comandos:
 *   node servico-windows.js desinstalar
 *   node servico-windows.js iniciar
 *   node servico-windows.js parar
 *   node servico-windows.js status
 *
 * Importante: precisa estar rodando o terminal como Administrador.
 */

const path = require('path');
const acao = (process.argv[2] || 'ajuda').toLowerCase();

if (process.platform !== 'win32') {
  console.error('Este script funciona apenas no Windows.');
  process.exit(1);
}

let Service;
try {
  Service = require('node-windows').Service;
} catch (err) {
  console.error('\n⚠️  Módulo node-windows não está instalado.');
  console.error('Execute primeiro:\n  npm install node-windows --no-save\n');
  process.exit(1);
}

const svc = new Service({
  name: 'SIGAZ',
  description: 'Sistema Integrado de Gestão Animal e Zoonoses - PMBC',
  script: path.join(__dirname, 'backend', 'server.js'),
  nodeOptions: ['--max-old-space-size=4096'],
  workingDirectory: __dirname,
  // Reinicia em caso de crash
  wait: 2,
  grow: 0.25,
  maxRestarts: 10
});

svc.on('install', () => {
  console.log('\n✓ Serviço SIGAZ instalado com sucesso!');
  console.log('  Iniciando o serviço...');
  svc.start();
});

svc.on('start', () => {
  console.log('✓ Serviço SIGAZ está rodando.');
  console.log('  Acesse: http://localhost:3000');
  console.log('\n  O serviço subirá automaticamente sempre que o Windows ligar.');
  console.log('  Você pode gerenciá-lo em: Serviços do Windows (services.msc)');
});

svc.on('uninstall', () => {
  console.log('✓ Serviço SIGAZ desinstalado.');
});

svc.on('alreadyinstalled', () => {
  console.log('⚠️  O serviço SIGAZ já está instalado.');
  console.log('   Para reinstalar: node servico-windows.js desinstalar && node servico-windows.js instalar');
});

svc.on('error', (err) => {
  console.error('Erro no serviço:', err);
});

svc.on('invalidinstallation', () => {
  console.error('⚠️  Instalação inválida do serviço. Tente desinstalar e instalar de novo.');
});

switch (acao) {
  case 'instalar':
  case 'install':
    console.log('Instalando o SIGAZ como serviço do Windows...');
    console.log('Isso requer privilégios de Administrador.\n');
    svc.install();
    break;

  case 'desinstalar':
  case 'uninstall':
    console.log('Desinstalando o serviço SIGAZ...');
    svc.uninstall();
    break;

  case 'iniciar':
  case 'start':
    console.log('Iniciando o serviço SIGAZ...');
    svc.start();
    break;

  case 'parar':
  case 'stop':
    console.log('Parando o serviço SIGAZ...');
    svc.stop();
    break;

  case 'status':
    console.log('Para ver o status, abra:');
    console.log('  Painel de Controle → Ferramentas Administrativas → Serviços');
    console.log('  ou execute: services.msc');
    console.log('  e procure por "SIGAZ"');
    break;

  default:
    console.log(`
==========================================
  SIGAZ — Instalador de Serviço Windows
==========================================

USO:
  node servico-windows.js <comando>

COMANDOS:
  instalar     Instala e inicia o SIGAZ como serviço (executar como Admin)
  desinstalar  Remove o serviço
  iniciar      Inicia o serviço
  parar        Para o serviço
  status       Mostra como visualizar o status

PRÉ-REQUISITOS:
  • PowerShell ou CMD aberto como Administrador
  • Módulo node-windows instalado:
      npm install node-windows --no-save
  • npm install já executado uma vez para baixar as dependências

DEPOIS DE INSTALADO:
  • O SIGAZ sobe sozinho ao ligar a máquina
  • Acesse http://localhost:3000
  • Gerencie em services.msc (procure "SIGAZ")
`);
}
