# 🎬 Subtitle Engine — Plano de Desenvolvimento e Refatoração

Este documento estabelece as fases de estabilização, unificação do Guardian, agendamento automático e refatoração do microserviço `subtitle-engine`, alinhado com o padrão de excelência e qualidade do repositório `transcoder`.

---

## 📌 Objetivos Principais

1. **Unificação do Subtitle Guardian**: Incorporar toda a lógica de auditoria de sintonia e purga de legendas órfãs diretamente no `subtitle-engine`, descontinuando a necessidade de scripts/repositórios externos.
2. **Agendamento Autônomo (Background Scheduler)**: Implementar background tasks configuráveis via `.env` para execução periódica independente da varredura de legendas ausentes e da auditoria/limpeza.
3. **Contratos Estritos & DTOs Pydantic**: Definir contratos explícitos e fortemente tipados em `app/schemas.py` para todas as requisições, respostas e estruturas de dados de domínio.
4. **Código Enxuto, Simples e Documentado**: Manter arquivos com responsabilidade única e adicionar docstrings detalhadas em formato Standard/Google em **100% das funções, classes e métodos**.
5. **Cobertura Total de Testes**: Garantir testes unitários e de integração com `pytest` para toda a esteira e novos endpoints.

---

## 🗺️ Fases do Projeto

- **Fase 1: Estabilização Inicial & Contrato de Webhook** (Concluída)
- **Fase 2: Arquitetura, Contratos Rígidos (Pydantic) e Separação de Módulos**
- **Fase 3: Módulo Guardian & Background Scheduler (Unificação)**
- **Fase 4: Cobertura de Testes Unitários e Validação Estrita**
- **Fase 5: Documentação Técnica Completa e Integração Compose**

---

## 📅 Fase 1: Estabilização Inicial & Contrato de Webhook ✅
- [x] **1.1. Tratamento Tolerante a Payload de Webhooks no Endpoint `/api/v1/event`**:
  - Aceitar os schemas nativos de webhooks do Bazarr, Radarr e Sonarr, extraindo dinamicamente o caminho da mídia (`path` / `movie.path` / `episode.path` / `episodeFile.path`).
  - Rejeitar com elegância eventos não relacionados à mídia (`200 OK`, `status: ignored`), eliminando erros **HTTP 422**.
- [ ] **1.2. Execução da Varredura em Lote (Batch Missing)**:
  - Processar mídias com legendas ausentes (`pt-BR`) sob demanda quando acionado.

---

## 📅 Fase 2: Arquitetura, Contratos Rígidos (Pydantic) e Separação de Módulos ✅
- [x] **2.1. Estruturação do Módulo Domain / Schemas (`app/schemas.py`)**:
  - Criar DTOs Pydantic v2 estritos para todas as entradas e saídas da API (Probe, Webhooks, Generate, Batch, Guardian Audit).
  - Eliminar o uso de dicionários genéricos `dict[str, Any]` em retornos de rotas.
- [x] **2.2. Separação de Serviços Core (Responsabilidade Única & Código Enxuto)**:
  - `app/config.py`: Variáveis de ambiente validadas com tipos explícitos.
  - `app/probe.py`: Inspeção `ffprobe` com parsing defensivo e tipos isolados.
  - `app/extract.py`: Extração isolada de faixas legendadas via FFmpeg.
  - `app/translate.py`: Tradução de legendas mantendo sintaxe SRT.
  - `app/transcribe.py`: Engine Whisper ASR encapsulado com gestão de memória GPU.
  - `app/pipeline.py`: Orquestrador de decisão do fluxo de legenda.
- [x] **2.3. Docstrings Standard em 100% das Funções**:
  - Documentar parâmetros, retornos esperados e exceções em todas as funções/classes.

---

## 📅 Fase 3: Módulo Guardian & Background Scheduler (Unificação) ✅
- [x] **3.1. Módulo Guardian (`app/guardian.py`)**:
  - Incorporar a validação de sincronia de legendas no banco do Bazarr.
  - Implementar varredura e purga de legendas `.srt` órfãs (sem arquivo de vídeo correspondente).
  - Criar endpoint `POST /api/v1/guardian/audit` para disparo sob demanda.
- [x] **3.2. Background Scheduler (`app/scheduler.py`)**:
  - Implementar background tasks assíncronas no FastAPI orientadas a configuração flexível no `.env`:
    - `SCHEDULE_BATCH_MISSING_INTERVAL_MINUTES` (default: `30` minutos — rápido para pegar pendências curtas do Bazarr)
    - `SCHEDULE_GUARDIAN_INTERVAL_HOURS` (default: `6` horas — auditoria de sintonia e limpeza de órfãos)

---

## 📅 Fase 4: Cobertura de Testes Unitários e Validação Estrita ✅
- [x] **4.1. Testes de Integração da API (`tests/test_api.py`)**:
  - Testes com `httpx` / `TestClient` para todos os endpoints (`/health`, `/probe`, `/generate`, `/event`, `/batch-missing`, `/guardian/audit`).
- [x] **4.2. Testes de Módulos e Mocks (`tests/test_guardian.py`, `tests/test_pipeline.py`)**:
  - Testar parsing de sincronia do Bazarr DB, identificação de órfãos e mocks de Whisper/FFmpeg.

---

## 📅 Fase 5: Documentação Técnica Completa e Integração Compose 👈 (Em andamento)
- [x] **5.1. Atualização do `README.md` e `AGENTS.md`**:
  - Especificação completa da API, schemas, variáveis de ambiente e agendamentos.
- [ ] **5.2. Atualização do `docker-compose.yml` e Desativação do Repositório Antigo**:
  - Garantir build limpo e variáveis de scheduler expostas no `media/docker-compose.yml`.
  - Documentar a obsolescência do repositório `subtitle-guardian`.


