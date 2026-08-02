# Racing Line Optimizer — Contexto do Projeto

> Documento de contexto. Abrir/colar no início de sessões com assistente de código.

## 1. O que é

Aplicação (desktop ou web) para **cálculo de traçado otimizado (racing line) em circuitos**.

O usuário configura um veículo (potência, capacidade de frenagem, massa, aerodinâmica, tipo de pneu), escolhe uma pista, e a aplicação:

1. Calcula o **traçado ideal** dentro dos limites da pista.
2. Exibe o traçado **dividido em N pontos de controle ajustáveis** pelo usuário.
3. Recalcula o **tempo previsto de volta em tempo real** conforme o usuário arrasta os pontos ou altera a configuração do carro.

O diferencial é o loop interativo: não é só "calcule a linha ótima", é "veja quanto você perde/ganha ao desviar dela".

## 2. Conceitos-chave do domínio

- **Racing line / traçado**: trajetória percorrida pelo carro dentro dos limites da pista.
- **Linha central (center line)**: eixo da pista, com largura à esquerda e à direita em cada ponto.
- **Curvatura (κ)**: inverso do raio da curva. Curvatura alta = curva fechada = velocidade limitada.
- **Diagrama GG / GGV**: envelope de aceleração máxima combinada (longitudinal × lateral), opcionalmente em função da velocidade (V). Traduz "quanto grip o carro tem". Usar grip para frear/acelerar reduz o grip disponível para curvar (elipse de atrito).
- **Apex**: ponto de curvatura máxima do traçado dentro de uma curva.
- **Quasi-steady-state (QSS)**: modelo que assume equilíbrio dinâmico instantâneo em cada ponto. Muito mais barato que modelo transiente e suficientemente preciso para lap time.
- **Minimum Curvature vs Minimum Lap Time (MLTP)**: duas formulações de otimização. Curvatura mínima é QP rápido e boa aproximação; MLTP é controle ótimo, mais preciso (~4% mais rápido) e muito mais caro.

## 3. Pipeline técnico

```
Pista (x, y, w_left, w_right)
        ↓
Parametrização: traçado = center_line + alpha_i * normal_i   (alpha ∈ [-w_left, +w_right])
        ↓
Spline cúbica pelos pontos de controle → x(s), y(s)
        ↓
Curvatura κ(s) = (x'y'' - y'x'') / (x'² + y'²)^(3/2)
        ↓
Velocidade limitada por grip: v_max(s) = sqrt(a_y_max(v) / |κ(s)|)
        ↓
Forward pass  (limite de aceleração / potência)
Backward pass (limite de frenagem)
        ↓
Perfil de velocidade v(s) = min(v_grip, v_fwd, v_bwd)
        ↓
Tempo de volta = ∫ ds / v(s)
```

### 3.1 Cálculos por etapa

**Curvatura a partir da spline**
Derivadas primeira e segunda da spline paramétrica em função do comprimento de arco `s`.

**Velocidade limitada por grip**
`v_grip(s) = sqrt(a_y_max / |κ(s)|)`
Onde `a_y_max` vem do diagrama GG. Com downforce, `a_y_max` cresce com a velocidade → resolver iterativamente ou por ponto fixo.

**Forward-backward integration**
- Forward: partindo de cada apex, `v_{i+1}² = v_i² + 2·a_x_accel·Δs`, com `a_x_accel` limitado pelo menor entre (a) tração disponível no envelope GG dado o `a_y` já consumido pela curva, e (b) `F_motor(v)/m - arrasto/m`.
- Backward: mesma lógica no sentido inverso com `a_x_brake`.
- Combinação: elipse de atrito → `(a_x/a_x_max)² + (a_y/a_y_max)² ≤ 1`.

**Forças longitudinais**
- Tração: `F_x = min(torque_roda(v)/r_roda, μ·F_z)`
- Arrasto: `F_drag = 0.5·ρ·Cd·A·v²`
- Downforce: `F_down = 0.5·ρ·Cl·A·v²` → aumenta `F_z` → aumenta grip
- Resistência ao rolamento: `F_rr = Crr·m·g`

**Tempo de volta**
`t = Σ (Δs_i / v_médio_i)` — soma simples sobre os segmentos discretizados.

**Otimização do traçado (curvatura mínima)**
Minimizar `Σ κ(s)²` sujeito a `alpha_i ∈ [-w_left_i, w_right_i]`. Com spline linear nos `alpha`, vira um **problema quadrático (QP)** — resolvível com OSQP / quadprog em milissegundos.

## 4. Fontes de dados

### Pistas
| Fonte | Conteúdo |
|---|---|
| `TUMFTM/racetrack-database` | Center lines (x, y) + larguras esquerda/direita de 20+ circuitos F1/DTM. Formato CSV. Racelines de referência já otimizadas + perfis de curvatura. |
| OpenStreetMap | Traçados brutos de qualquer circuito mapeado (via Overpass API). Requer suavização e estimativa de largura. |

⚠️ A qualidade dos dados do racetrack-database varia por circuito (origem em GPS + imagens de satélite). Validar antes de usar em produção.

### Veículos e pneus
| Fonte | Conteúdo |
|---|---|
| `TUMFTM/laptime-simulation` (pasta inputs) | Parâmetros de veículos de referência + arquivos `ggv` e `ax_max_machines`. |
| Arquivos `.TIR` (Pacejka Magic Formula) | Coeficientes de pneu padrão da indústria. |
| FSAE Tire Test Consortium | Dados reais de teste de pneu (requer cadastro/licença). |
| FastF1 (Python) | Telemetria real de F1: velocidade, GPS, tempos de setor — **para validação**, não para input. |

### Formato de entrada do TUM (referência)
- `tracks/*.csv`: `[x_m, y_m, w_tr_right_m, w_tr_left_m]`
- `veh_dyn_info/ggv.csv`: envelope de aceleração por velocidade
- `veh_dyn_info/ax_max_machines.csv`: aceleração máxima do trem de força **sem arrasto** (`F_x_drivetrain / m_veh`)
- `frictionmaps/`: mapas de atrito espacialmente resolvidos (opcional)

## 5. Repositórios de referência

| Repo | Uso |
|---|---|
| `TUMFTM/racetrack-database` | Dados de pistas |
| `TUMFTM/global_racetrajectory_optimization` | Otimização de traçado (curvatura mínima, shortest path, MLTP) |
| `TUMFTM/laptime-simulation` | Simulação QSS de tempo de volta em Python |
| `TUMFTM/trajectory_planning_helpers` | Funções auxiliares: splines, vetores normais, curvatura |

## 6. Arquitetura proposta

```
racing-line-optimizer/
├── engine/              # núcleo de cálculo (puro, sem UI)
│   ├── track/           # parsing, spline da center line, normais, larguras
│   ├── geometry/        # spline do traçado, curvatura, comprimento de arco
│   ├── vehicle/         # modelo do carro, GG diagram, forças
│   ├── solver/          # forward-backward, lap time
│   └── optimizer/       # QP de curvatura mínima
├── api/                 # camada de serviço (se web)
├── ui/                  # canvas interativo, pontos arrastáveis
└── data/                # pistas e veículos
```

**Decisão de stack pendente.** Opções:
- **Python (protótipo) → Go (produção)**: valida a matemática rápido com numpy/scipy, depois porta o hot path.
- **Go + WASM**: engine compilada para o browser, recálculo local sem round-trip de rede.
- **Python + FastAPI + frontend web**: mais rápido de entregar, mas latência de rede no loop interativo.

**Requisito não-funcional crítico:** o recálculo do tempo de volta ao arrastar um ponto precisa ser < ~16ms para parecer "tempo real". O forward-backward é O(n) sobre os pontos discretizados — viável. A otimização QP completa é mais lenta e deve ficar num botão explícito ("Otimizar"), não no loop de arrasto.

## 7. Roadmap

### Fase 1 — Pesquisa e baseline
- [ ] Clonar e rodar `laptime-simulation` e `global_racetrajectory_optimization`
- [ ] Entender os formatos de entrada (track CSV, ggv, ax_max_machines)
- [ ] Reproduzir um tempo de volta conhecido de um circuito do database
- [ ] Documentar as premissas do modelo QSS deles

### Fase 2 — Motor próprio (MVP)
- [ ] Parser de pista (CSV do TUM) + spline da center line + vetores normais
- [ ] Representação do traçado por deslocamento lateral `alpha` nos pontos de controle
- [ ] Cálculo de curvatura da spline
- [ ] Modelo de veículo simples: massa, potência, `a_x_brake_max`, `a_y_max` constante
- [ ] Forward-backward integration + tempo de volta
- [ ] **Critério de aceite:** dado um traçado fixo, o tempo calculado bate com o do TUM dentro de uma margem aceitável

### Fase 3 — Interatividade
- [ ] Renderização da pista + traçado em canvas
- [ ] Pontos de controle arrastáveis com clamp nos limites da pista
- [ ] Recálculo do lap time no drag (< 16ms)
- [ ] Painel de configuração do veículo com recálculo reativo
- [ ] Visualização do perfil de velocidade e do delta vs. traçado de referência

### Fase 4 — Otimização
- [ ] QP de curvatura mínima → botão "Otimizar traçado"
- [ ] Comparação visual: traçado do usuário vs. traçado ótimo
- [ ] Modelo de veículo refinado: downforce, GGV dependente de velocidade, curva de torque, marchas

### Fase 5 — Dados reais
- [ ] Importação de pistas via OpenStreetMap
- [ ] Suporte a coeficientes Pacejka via `.TIR`
- [ ] Validação contra telemetria FastF1

## 8. Riscos e pontos de atenção

- **Precisão do modelo:** QSS ignora transientes (transferência de carga, resposta do pneu). Aceitável para comparação relativa de traçados; não confiar em valores absolutos de lap time sem validação.
- **Qualidade dos dados de pista:** larguras extraídas de satélite têm erro. Elevação e banking geralmente não estão nos datasets — o modelo assume pista plana por padrão.
- **Performance no loop interativo:** cuidado com recálculo de spline completa a cada frame; considerar recálculo local apenas no segmento afetado.
- **Licenças:** verificar licença dos repos TUM antes de reusar código ou dados.

## 9. Decisões tomadas (2026-08-02)

- **Stack:** Python + FastAPI + frontend web (HTML/JS vanilla, canvas).
- **Plataforma:** aplicação web.
- **Modelo de veículo:** GG constante na Fase 2; dependência de velocidade (downforce/GGV) fica para a Fase 4.
- **Pontos de controle:** o usuário cria os próprios pontos clicando na pista (mínimo 3); arrasta para ajustar, duplo clique remove.
- **Persistência:** PostgreSQL (Docker Compose) via SQLAlchemy; dados iniciais via seed idempotente (`python -m app.seed`) — pista Silverstone (TUM) + 2 veículos de exemplo + traçado padrão na center line.
