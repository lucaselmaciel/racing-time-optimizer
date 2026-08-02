# Racing Line Optimizer

Aplicação web para cálculo interativo de traçado (racing line) e tempo de volta em circuitos.
Contexto completo do domínio em [.claude/CONTEXT.md](.claude/CONTEXT.md).

## Stack

- **Engine** (`engine/`): núcleo de cálculo puro em numpy/scipy — splines, curvatura, modelo QSS de veículo (GG constante), forward-backward integration.
- **API** (`app/`): FastAPI + SQLAlchemy + PostgreSQL.
- **UI** (`ui/`): HTML/JS vanilla com canvas — pontos de controle criáveis/arrastáveis e recálculo do lap time em tempo real.

## Como rodar

Com `make` (instalável via `winget install ezwinports.make`):

```powershell
make install   # venv + dependências (uma vez)
make dev       # Postgres (Docker) + seed + servidor
```

Ou manualmente:

```powershell
docker compose up -d --wait                            # banco
python -m venv .venv                                   # ambiente
.\.venv\Scripts\pip install -e ".[dev]"
.\.venv\Scripts\python -m app.seed                     # tabelas + migrações + dados
.\.venv\Scripts\python -m uvicorn app.main:app --port 8000
```

Abra <http://localhost:8000>. Outros alvos: `make test`, `make seed`, `make db-down`, `make help`.

Configuração via `.env` (ver `.env.example`); padrão: `postgresql+psycopg://racing:racing@localhost:5432/racing_line`.

## Uso da UI

- **Clique** na pista cria um ponto de controle (mínimo 3 para calcular).
- **Arraste** um ponto para ajustar o traçado — o tempo de volta recalcula em tempo real.
- **Duplo clique** remove o ponto.
- **Otimizar traçado** roda o QP de curvatura mínima e substitui os pontos pelo traçado ótimo (96 pontos, editáveis); o traçado anterior fica em cinza para comparação, com o delta no rodapé.
- O painel lateral permite trocar pista/veículo, editar os parâmetros do carro (recálculo reativo, sem persistir) e salvar traçados nomeados no banco. O campo **Cl·A** controla o downforce: o grip cresce com a velocidade (GGV).
- O traçado é colorido pela velocidade (escuro = lento, claro = rápido); o gráfico inferior mostra o perfil de velocidade e o limite de grip.
- Traçados que "cortariam" a curva por fora dos limites são projetados de volta para dentro da pista antes do cálculo — o lap time é sempre de uma linha legal.

## Testes

```powershell
.\.venv\Scripts\python -m pytest
```

## Pistas e veículos

O seed cadastra os **25 circuitos** do
[TUMFTM/racetrack-database](https://github.com/TUMFTM/racetrack-database) (Silverstone, Spa,
Monza, Suzuka, Interlagos/Sao Paulo, Austin, etc. — center line medida por GPS + larguras) e
**12 categorias de veículo**, do kart ao F1 (Fórmula, IndyCar, LMP/Hypercar, Fórmula E,
Fórmula 4, GT, Stock Car Brasil, TCR, MotoGP, kart e dois carros de rua), com parâmetros
aproximados de massa, potência, grip mecânico e downforce por categoria.

Para adicionar outra pista, coloque um CSV no formato TUM
(`x_m, y_m, w_tr_right_m, w_tr_left_m`) em `data/tracks/` e rode `python -m app.seed`
de novo — o seed é idempotente.
