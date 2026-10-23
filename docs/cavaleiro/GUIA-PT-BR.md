# Guia do Cavaleiro Learning Agent

Guia completo em português: o que é o agente, como ele é organizado por dentro, como instalar no Windows, no macOS e no Linux, como usar no dia a dia, como configurar, como resolver problemas e como contribuir.

> O Cavaleiro Learning Agent é mantido pela Cavaleiro AI. Os comandos, os arquivos e as pastas são os mesmos do projeto original: o comando continua sendo `hermes`. Sem afiliação com o projeto original.

**Neste guia:** [O que é e para quem](#o-que-é-e-para-quem) · [Arquitetura](#arquitetura) · [Instalação](#instalação-passo-a-passo) · [Primeiros passos](#primeiros-passos) · [Exemplos práticos](#exemplos-práticos) · [Configuração](#configuração) · [Solução de problemas](#solução-de-problemas) · [Como contribuir](#como-contribuir)

---

## O que é e para quem

O Cavaleiro Learning Agent é um **agente pessoal de IA** que roda na sua máquina ou no seu servidor. Ele conversa com um modelo de linguagem (o que você escolher: OpenRouter, OpenAI, Anthropic, Nous Portal, um servidor local llama.cpp ou outro endpoint compatível com a API da OpenAI) e usa **ferramentas** para agir: terminal, arquivos, navegador, busca na web, visão, agendamento de tarefas, subagentes e servidores MCP.

O que o diferencia de um chat comum é o **ciclo de aprendizado**:

- **Memória curada.** O agente guarda fatos importantes em `MEMORY.md` e um perfil seu em `USER.md`, e recebe lembretes periódicos para manter essa memória útil.
- **Habilidades (skills).** Depois de uma tarefa complexa, ele pode registrar o procedimento como uma habilidade reutilizável, e melhorá-la nas próximas vezes.
- **Busca nas conversas anteriores.** Todas as sessões ficam num banco SQLite com busca de texto completo, para que o agente recupere o que já foi feito.

**Para quem é:**

- Desenvolvedores que querem um agente de terminal que lembra do projeto entre sessões.
- Quem quer um assistente acessível pelo Telegram, Discord, Slack, WhatsApp ou Signal, rodando em um servidor próprio.
- Quem precisa de automações agendadas em linguagem natural (relatórios, backups, auditorias).
- Pesquisadores que geram trajetórias de uso de ferramentas para treinar modelos.

**O que este derivado acrescenta:** correções de segurança e de confiabilidade com testes de regressão (veja o [CHANGELOG](../../CHANGELOG.md) e o [relatório de engenharia](ENGINEERING.md)), além deste guia e de um repositório que não publica nada em nome do projeto original.

---

## Arquitetura

O mesmo núcleo do agente atende a todas as entradas: a CLI, o gateway de mensagens, a interface de terminal (TUI), o aplicativo desktop e a integração com editores (ACP).

```text
            Entradas
  ┌──────────┬──────────────┬──────────────┬─────────────┬──────────┐
  │ CLI      │ Gateway      │ TUI / Desktop │ ACP (IDEs) │ Cron     │
  │ hermes   │ hermes       │ ui-tui/ +     │ acp_adapter│ cron/    │
  │ cli.py   │ gateway/     │ tui_gateway/  │            │          │
  └────┬─────┴──────┬───────┴──────┬───────┴─────┬──────┴────┬─────┘
       └────────────┴──────────────┼─────────────┴───────────┘
                                   ▼
                  ┌─────────────────────────────────┐
                  │ AIAgent (run_agent.py)           │
                  │ ciclo de turnos: agent/turn_*.py │
                  │ prompt: agent/prompt_builder.py  │
                  │ provedores: hermes_cli/runtime_  │
                  │   provider.py, providers/        │
                  │ compressão de contexto           │
                  └───────┬─────────────────┬────────┘
                          ▼                 ▼
          ┌───────────────────────┐  ┌───────────────────────────────┐
          │ Ferramentas           │  │ Estado e aprendizado           │
          │ tools/registry.py     │  │ hermes_state*.py (SQLite+FTS5) │
          │ model_tools.py        │  │ tools/memory_tool*.py          │
          │ toolsets.py           │  │ skills/, agent/curator*.py     │
          │ aprovação: tools/     │  │ plugins/memory/                │
          │   approval*.py        │  └───────────────────────────────┘
          │ backends: tools/      │
          │   environments/       │
          └───────────────────────┘
```

### Componentes e responsabilidades

| Componente | Onde fica | Responsabilidade |
|---|---|---|
| Ponto de entrada | `hermes_cli/main.py` (comando `hermes`) | Subcomandos (`setup`, `model`, `gateway`, `doctor`…) e a CLI interativa |
| CLI interativa | `cli.py` + `hermes_cli/cli_*_mixin.py` | REPL, comandos de barra, exibição |
| Núcleo do agente | `run_agent.py`, `agent/` | Ciclo de turnos, montagem do prompt, chamadas ao modelo, novas tentativas, compressão |
| Ferramentas | `tools/`, `model_tools.py`, `toolsets.py` | Cada ferramenta se registra em `tools/registry.py`; toolsets agrupam ferramentas por plataforma |
| Segurança de execução | `tools/approval*.py`, `tools/shell_heredoc.py`, `tools/terminal_tool_guards.py` | Detecção de comandos perigosos, lista hardline, `approvals.deny`, aprovação manual/inteligente |
| Backends de terminal | `tools/environments/` | Local, Docker, SSH, Singularity, Modal, Daytona, Vercel Sandbox |
| Gateway de mensagens | `gateway/`, `plugins/platforms/` | Adaptadores de Telegram, Discord, Slack, WhatsApp e outros; autorização e sessões |
| Estado | `hermes_state.py` + `hermes_state_*.py` | Banco SQLite das sessões, busca FTS5, títulos, linhagem |
| Memória | `tools/memory_tool.py`, `tools/memory_tool_store.py`, `plugins/memory/` | Memória em arquivo com trava, provedores de memória plugáveis |
| Habilidades | `skills/`, `optional-skills/`, `tools/skills_*.py` | Habilidades embutidas, Skills Hub, curadoria |
| Agendador | `cron/` | Tarefas agendadas com entrega em qualquer plataforma |
| Ambiente de desenvolvimento | `pm/`, `setup-hermes.*`, `activate*` | Gerenciador de dependências próprio (PM) sobre o `uv` |
| Documentação completa | `website/` | Fontes do site Docusaurus (em inglês) |

### Fluxo de uma mensagem

1. Você escreve na CLI ou manda uma mensagem pelo aplicativo.
2. O gateway (no caso de mensagens) autoriza o remetente pela lista de permissão ou pelo pareamento, e encontra a sessão.
3. O `AIAgent` monta o prompt de sistema (identidade, habilidades, arquivos de contexto, memória) e chama o modelo.
4. Se o modelo pede uma ferramenta, ela é executada pelo registro. Comandos de terminal passam antes pelas travas de aprovação: lista hardline, suas regras `approvals.deny` e o detector de comandos perigosos.
5. O resultado volta para o modelo, e o ciclo continua até a resposta final, que é salva no banco de sessões.

### Pontos de extensão

- **Habilidades:** pastas com `SKILL.md` em `~/.hermes/skills/`.
- **Plugins:** `~/.hermes/plugins/` ou pacotes Python (provedores de memória, de modelo, de geração de imagem, plataformas de mensagem).
- **Servidores MCP:** configurados em `mcp_servers` no `config.yaml`.
- **Arquivos de contexto:** `AGENTS.md` e similares no diretório do projeto moldam cada conversa.

---

## Instalação passo a passo

A instalação é feita a partir do código-fonte deste repositório. O script de setup baixa e verifica um `uv` fixado, instala o Python 3.14 e as dependências travadas em `uv.lock`, sem mexer no Python do sistema.

> Os instaladores de uma linha do projeto original instalam o projeto original, não este repositório.

### Antes de começar (todos os sistemas)

- **Git** com a extensão **git-lfs**.
- Cerca de 3 GB livres para o ambiente e as dependências.
- Uma chave de API de algum provedor de modelo (por exemplo OpenRouter, OpenAI ou Anthropic), ou um servidor de modelo local.

### Windows (nativo)

1. Instale o Git for Windows (inclui o Git Bash, que o agente usa para rodar comandos) e o git-lfs:
   ```powershell
   winget install --id Git.Git
   git lfs install
   ```
2. Abra o **PowerShell** e clone o repositório:
   ```powershell
   git clone https://github.com/cavaleiro-ai/cavaleiro-learning-agent.git
   cd cavaleiro-learning-agent
   ```
3. Rode o setup e ative o ambiente (o ponto e o espaço antes de `.\activate.ps1` são obrigatórios):
   ```powershell
   .\setup-hermes.ps1
   . .\activate.ps1
   hermes --version
   ```
4. Configure o provedor e o modelo, depois comece:
   ```powershell
   hermes setup
   hermes
   ```

A pasta de dados no Windows nativo é `%LOCALAPPDATA%\hermes`. Se o PowerShell bloquear scripts, rode `Set-ExecutionPolicy -Scope Process RemoteSigned` na mesma janela antes do passo 3. Se preferir, o WSL2 funciona como o Linux.

### macOS

1. Instale as ferramentas de linha de comando da Apple e o git-lfs (com Homebrew):
   ```bash
   xcode-select --install
   brew install git git-lfs
   git lfs install
   ```
2. Clone, rode o setup e ative:
   ```bash
   git clone https://github.com/cavaleiro-ai/cavaleiro-learning-agent.git
   cd cavaleiro-learning-agent
   ./setup-hermes.sh
   source ./activate
   hermes --version
   ```
3. Configure e comece: `hermes setup` e depois `hermes`.

### Linux (Ubuntu/Debian; outras distribuições são parecidas)

1. Instale o Git e o git-lfs:
   ```bash
   sudo apt update
   sudo apt install -y git git-lfs curl
   git lfs install
   ```
2. Clone, rode o setup e ative:
   ```bash
   git clone https://github.com/cavaleiro-ai/cavaleiro-learning-agent.git
   cd cavaleiro-learning-agent
   ./setup-hermes.sh
   source ./activate
   hermes --version
   ```
3. Configure e comece: `hermes setup` e depois `hermes`.

### Em todo sistema

- `deactivate` sai do ambiente. Em cada novo terminal, entre na pasta e ative de novo (`source ./activate` ou `. .\activate.ps1`).
- Para testar sem tocar nos seus dados, defina antes uma pasta separada: `export HERMES_HOME="$HOME/hermes-teste"` (bash) ou `$env:HERMES_HOME = "$HOME\hermes-teste"` (PowerShell).
- Para atualizar: `git pull` na pasta do repositório e ative de novo; a ativação sincroniza as dependências.

---

## Primeiros passos

1. **Escolha o modelo.** `hermes model` lista os provedores; cole a chave quando pedir. As chaves ficam em `~/.hermes/.env`, que serve só para segredos.
2. **Converse.** `hermes` abre a CLI. Escreva a tarefa em linguagem natural.
3. **Veja o que ele pode usar.** `hermes tools` ativa ou desativa ferramentas por plataforma.
4. **Confira a saúde da instalação.** `hermes doctor` aponta dependências faltando, chaves ausentes e problemas de configuração.
5. **Comandos úteis dentro da conversa:**

| Comando | O que faz |
|---|---|
| `/new` | Começa uma conversa nova |
| `/model provedor:modelo` | Troca o modelo |
| `/retry`, `/undo` | Repete ou desfaz a última rodada |
| `/compress` | Comprime o contexto da conversa |
| `/usage`, `/insights` | Mostra uso de tokens e estatísticas |
| `/skills` | Lista as habilidades |
| `Ctrl+C` | Interrompe o trabalho atual |

---

## Exemplos práticos

**Entender um projeto.** Dentro da pasta do projeto:

```text
hermes
> Leia este repositório e me explique a arquitetura em 10 tópicos. Guarde na memória os comandos de teste.
```

Na próxima sessão, o agente já sabe como rodar os testes desse projeto.

**Automatizar uma tarefa recorrente.**

```text
> Todo dia útil às 8h, verifique os pull requests abertos do repositório X e me mande um resumo no Telegram.
```

O agente cria um job no agendador (`~/.hermes/cron/`). Para gerenciar: `/cron` na conversa ou `hermes cron` no terminal.

**Conversar pelo Telegram.**

```bash
hermes gateway setup     # escolha Telegram e cole o token do BotFather
hermes gateway start
```

Depois, mande mensagem para o bot. Só usuários da lista de permissão ou pareados recebem resposta.

**Rodar comandos isolados em Docker.** Em `~/.hermes/config.yaml`:

```yaml
terminal:
  backend: docker
```

Os comandos do agente passam a rodar em um contêiner, não na sua máquina.

**Bloquear um comando para sempre.** Mesmo com `--yolo`:

```yaml
approvals:
  deny:
    - "git push --force*"
    - "rm -rf *"
```

**Usar um modelo local.** `hermes model` oferece o runtime llama.cpp gerenciado: ele baixa um modelo GGUF, sobe o `llama-server` em `127.0.0.1` e protege o endpoint com uma chave que, nesta versão, não aparece mais na lista de processos nem nos logs.

---

## Configuração

| Arquivo | Conteúdo |
|---|---|
| `~/.hermes/config.yaml` | Comportamento: modelo, terminal, toolsets, aprovações, compressão, memória, gateway |
| `~/.hermes/.env` | Somente segredos (chaves de API, tokens de bots) |
| `~/.hermes/memories/` | `MEMORY.md` e `USER.md` |
| `~/.hermes/skills/` | Habilidades |
| `~/.hermes/state.db` | Sessões |
| `~/.hermes/logs/` | Logs (`hermes logs`) |

Use `hermes config get <chave>` e `hermes config set <chave> <valor>` em vez de editar à mão, quando possível. O arquivo [`cli-config.yaml.example`](../../cli-config.yaml.example) traz todas as opções comentadas, e o [`.env.example`](../../.env.example) lista as variáveis de segredo.

Opções mais usadas:

| Chave | Valores | Efeito |
|---|---|---|
| `model.default` | nome do modelo | Modelo padrão |
| `model.provider` | `auto`, `openrouter`, `anthropic`… | Provedor |
| `terminal.backend` | `local`, `docker`, `ssh`, `modal`, `daytona`, `singularity`, `vercel` | Onde os comandos rodam |
| `approvals.mode` | `manual`, `smart` (padrão), `off` | Quando pedir aprovação para comandos arriscados |
| `approvals.deny` | lista de padrões | Comandos sempre bloqueados, mesmo com `--yolo` |
| `memory.memory_enabled` | `true`/`false` | Liga a memória persistente |
| `memory.nudge_interval` | número | A cada quantas mensagens o agente é lembrado de cuidar da memória |
| `compression.enabled` | `true`/`false` | Compressão automática do contexto |
| `telemetry.shared_metrics.enabled` / `.send` | `false` (padrão) | Métricas agregadas; coleta e envio são consentimentos separados |

**Perfis.** `hermes profile` cria perfis com pastas de dados separadas (por exemplo, um para trabalho e outro pessoal).

**Segurança.** Mantenha `approvals.mode` em `smart` ou `manual` no backend `local`; use `off` só com um backend isolado. A lista hardline e `approvals.deny` continuam valendo em qualquer modo.

---

## Solução de problemas

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| `hermes: command not found` | O ambiente não está ativo neste terminal | Entre na pasta do repositório e rode `source ./activate` (ou `. .\activate.ps1`) |
| O PowerShell recusa `setup-hermes.ps1` | Política de execução de scripts | `Set-ExecutionPolicy -Scope Process RemoteSigned` e rode de novo |
| O antivírus remove o `uv.exe` | Falso positivo em binário Rust sem assinatura | Verifique com `gh attestation verify` (veja o README) e crie exceção para a pasta |
| Erro de autenticação do provedor | Chave ausente ou errada | `hermes model` de novo, ou confira a chave em `~/.hermes/.env`; `hermes doctor` mostra o que falta |
| O bot do Telegram não responde | Remetente fora da lista de permissão, ou gateway parado | `hermes gateway status`, depois confira a lista de permissão ou faça o pareamento |
| Comando bloqueado como "hardline" | O comando está na lista incondicional | Rode-o você mesmo, fora do agente, se for realmente necessário |
| Comando bloqueado por "approvals.deny" | Uma regra sua casou com o comando | Ajuste a lista `approvals.deny` no `config.yaml` |
| O contexto estoura | Conversa longa demais | `/compress`, ou `/new` para começar outra |
| Dados de teste misturados com os reais | Mesma pasta de dados | Defina `HERMES_HOME` para outra pasta antes de testar |
| Algo estranho e sem pista | — | `hermes doctor`, depois `hermes logs`; para pedir ajuda, use `hermes debug share --local` e revise a saída antes de colar |

Ao abrir uma issue, nunca cole chaves de API, tokens ou o conteúdo do `.env`. `hermes debug share` sem `--local` envia o relatório para um serviço público de paste.

---

## Como contribuir

1. Leia o [CONTRIBUTING.md](../../CONTRIBUTING.md) (em inglês) e o [código de conduta](../../CODE_OF_CONDUCT.md).
2. Prepare o ambiente de testes (separado do ambiente de uso):
   ```bash
   python -m pm.build_env --source . --out .venv --group dev --group test
   ```
   Com `uv`, uma alternativa local é `uv sync --frozen --python 3.14 --group dev --group test`.
3. Rode os testes **sempre** pelo executor do projeto, nunca com `pytest` direto (ele isola variáveis de ambiente, `HERMES_HOME` e cada arquivo em um processo próprio):
   ```bash
   scripts/run_tests.sh tests/tools/test_heredoc_floors.py
   scripts/run_tests.sh tests/gateway/ -j 4
   ```
   No Windows, rode pelo Git Bash; se o executor não achar o ambiente, defina `HERMES_PYTHON` para o `python.exe` do `.venv`.
4. Rode as verificações de estilo: `python scripts/check` (ou, só para os arquivos alterados, `ruff check <arquivos>`).
5. Para correções de bug, escreva primeiro um teste que falha no código atual, depois a correção que o faz passar, e mostre as duas execuções no pull request.
6. Acrescente uma linha em **Unreleased** no [CHANGELOG.md](../../CHANGELOG.md). Se mudar o `README.md`, atualize o `README.pt-BR.md` junto.
7. Vulnerabilidades: siga a [política de segurança](../../SECURITY.md) e relate de forma privada.

Para entender as decisões técnicas desta versão, leia o [relatório de engenharia](ENGINEERING.md).
