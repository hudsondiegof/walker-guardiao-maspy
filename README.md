# Walkers vs. Guardiões — Arena Competitiva em BDI Puro (MASPY)

Projeto independente e minimalista para a atividade de **Sistemas Multiagentes** (baseado no exemplo *Navigation on 2D Grid* da Wiki do MASPY), modelando deliberação **BDI pura** com seleção de múltiplos planos `@pl` por contexto, sem lógica decisória embutida no `Environment` e sem agentes burocráticos.

## Ideia e Arquitetura

Apenas **2 tipos legítimos de agentes** atuam fisicamente no ambiente `Arena(Environment)`:

| Componente | Classificação (Russell & Norvig) | Papel no sistema |
|---|---|---|
| **`Walker`** (`N` instâncias) | **Utility-based + Goal-based Agent** | O motor BDI seleciona por contexto entre os planos `capturar`, `reavaliar_risco`, `escolher_alvo` e `navegar`; mantém crenças explícitas (`Path_Graph`, `Wall_Set`, `vezes_interceptado`, `alvo_escolhido`), reage por evento à descoberta de paredes (`registrar_parede`), avalia $U(a) = \text{valor} - 1,1 \cdot d - \text{risco}$ (migrando autonomamente do alvo `50` para `10` após interceptação) e planeja rotas com flanqueio via **A\***. |
| **`Guardiao`** (`2` instâncias: `G1`, `G2`) | **Simple Reflex Agent** (sem estado) | Sem memória interna nem busca: cada regra condição-ação é um plano `@pl` distinto (`encerrar_ronda`, `interceptar`, `rondar`) selecionado pelo contexto sensorial (`walker_adjacente`, `agt_position`, `anel_patrulha`) acionando unicamente o atuador físico `mover_guardiao(direcao)`. |
| **`Arena`** (`Environment`) | Ambiente parcialmente observável, dinâmico e discreto | Expõe apenas sensores físicos (`Percept` com grupos `"oculto"`, `"publico"` e privado por agente) e atuadores físicos atômicos protegidos por `RLock` (`mover_walker`, `mover_guardiao`, `reivindicar_alvo`, `confirmar_alerta_interceptacao`). |

### Como os recursos nativos do MASPY são usados
- **Seleção de planos BDI por contexto (`@pl`):** tanto `Walker` quanto `Guardiao` possuem múltiplos planos concorrentes para seu objetivo (`Goal("agir")` e `Goal("patrulhar")`), cabendo ao motor BDI do MASPY escolher qual plano instanciar a cada ciclo conforme as crenças ativas.
- **Base de Crenças (`Belief` + eventos `gain`):** `Path_Graph`, `Wall_Set`, `vezes_interceptado` e `alvo_escolhido` vivem na *Belief Base* do `Walker`; colisões geram `Belief("parede_descoberta", ...)` disparando o plano reativo `registrar_parede`.
- **`Percept` com grupos + `filter_perceptions(add, focus, ...)`:** cada agente enxerga apenas seus sensores privados e os elementos públicos, mantendo as paredes no grupo `"oculto"`.
- **Comunicação KQML direta (`broadcast` + `tell`):** ao capturar um alvo, o Walker transmite `alvo_capturado` pelo `Channel` para replanejamento imediato dos rivais.

## Como rodar

```powershell
cd C:\Users\Hudson\.gemini\antigravity\scratch\walker-guardiao-maspy
.\.venv\Scripts\python.exe main.py            # Menu + visualizacao Pygame (delay inicial 0.8s)
.\.venv\Scripts\python.exe main.py --sem-gui  # Modo terminal rapido com log BDI completo
```

## Modelagem no PDT 3.2b (Prometheus Design Tool)

A pasta `pdt/` contém o projeto nativo `Walker_Guardiao_MASPY.pd` (validado sem alertas no *Crosscheck*) e os diagramas exportados (`pdt_system_overview.png`, `pdt_walker_overview.png`, `pdt_guardiao_overview.png`, `pdt_goal_overview.png`). Para abrir diretamente no PDT 3.2b já com o projeto carregado:

```powershell
.\pdt\abrir_pdt.bat
```
