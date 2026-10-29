import heapq
import math
import random

from maspy import Agent, Belief, Goal, Environment, Any, gain, pl, add, focus, tell, broadcast

from arena_env import manhattan


def direcao_passo(origem, destino):
    dx, dy = destino[0] - origem[0], destino[1] - origem[1]
    if dx == 0 and dy == 0:
        return "stay"
    if abs(dy) >= abs(dx):
        return "down" if dy > 0 else "up"
    return "right" if dx > 0 else "left"


def astar_flanqueio(inicio, meta, limites, conhecidos, paredes, posicoes_guardioes):
    w, h = limites
    paredes = set(paredes)
    inicio = tuple(inicio)
    meta = tuple(meta)

    fila = [(0.0, inicio)]
    veio_de = {}
    custo_g = {inicio: 0.0}

    def heuristica(p):
        return abs(meta[0] - p[0]) + abs(meta[1] - p[1])

    def vizinhos(p):
        x, y = p
        for nx, ny in [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]:
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in paredes:
                yield (nx, ny)

    while fila:
        _, atual = heapq.heappop(fila)
        if atual == meta:
            caminho = [atual]
            while atual in veio_de:
                atual = veio_de[atual]
                caminho.append(atual)
            caminho.reverse()
            return caminho

        adj_conhecidos = conhecidos.get(atual, set())
        for prox in vizinhos(atual):
            passo = 1.0 if prox in adj_conhecidos else 1.25
            # Penalidade dinamica perto dos 2 Guardioes para induzir flanqueio pelas brechas
            if posicoes_guardioes and prox != meta:
                menor_dist = min(manhattan(prox, pg) for pg in posicoes_guardioes)
                if menor_dist == 0:
                    passo += 6.0
                elif menor_dist == 1:
                    passo += 2.0

            novo_custo = custo_g[atual] + passo
            if prox not in custo_g or novo_custo < custo_g[prox]:
                custo_g[prox] = novo_custo
                veio_de[prox] = atual
                heapq.heappush(fila, (novo_custo + heuristica(prox), prox))

    return None


class Guardiao(Agent):
    """Simple Reflex Agent em BDI puro: cada regra condicao-acao e um plano @pl selecionado pelo contexto."""

    def __init__(self, name, arena: Environment):
        super().__init__(name, max_intentions=1)
        self.filter_perceptions(add, focus, [self.my_name, "publico"])
        self.connect_to(arena)

    def _outros_guardioes(self):
        gbs = self.get(Belief("guardiao_pos", (Any, Any, Any), "Arena"), all=True) or []
        if isinstance(gbs, Belief):
            gbs = [gbs]
        return {(b.values[1], b.values[2]) for b in gbs if b.values[0] != self.my_name}

    @pl(gain, Goal("patrulhar"), Belief("alvo_protegido_capturado", (Any, Any), "Arena"))
    def encerrar_ronda(self, src, pos_alvo):
        self.print(f"plano encerrar_ronda: alvo protegido {pos_alvo} ja foi capturado; encerrando patrulha.")
        self.stop_cycle()
        return True

    @pl(
        gain,
        Goal("patrulhar"),
        [
            Belief("walker_adjacente", (Any, Any, Any), "Arena"),
            Belief("agt_position", (Any, Any), "Arena"),
        ],
    )
    def interceptar(self, src, walker_adj, pos):
        w_name, wx, wy = walker_adj
        if (wx, wy) == pos:
            return False
        direcao = direcao_passo(pos, (wx, wy))
        self.print(f"plano interceptar: invasor {w_name} detectado em {(wx, wy)} -> mover_guardiao({direcao})")
        self.mover_guardiao(direcao)
        return False

    @pl(
        gain,
        Goal("patrulhar"),
        [
            Belief("agt_position", (Any, Any), "Arena"),
            Belief("anel_patrulha", Any, "Arena"),
            Belief("info_arena", (Any, Any), "Arena"),
        ],
    )
    def rondar(self, src, pos, anel, info):
        _, alvo_protegido = info
        cx, cy = alvo_protegido
        anel_set = set(anel)
        outros = self._outros_guardioes()

        vizinhos_anel = [
            (pos[0] + dx, pos[1] + dy)
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
            if (pos[0] + dx, pos[1] + dy) in anel_set
            and (pos[0] + dx, pos[1] + dy) not in outros
        ]
        ang_atual = math.atan2(pos[1] - cy, pos[0] - cx)
        horario = [
            (c, (math.atan2(c[1] - cy, c[0] - cx) - ang_atual) % (2 * math.pi))
            for c in vizinhos_anel
        ]
        frente = [par for par in horario if 0.01 < par[1] <= math.pi]
        if frente:
            escolhida = min(frente, key=lambda par: par[1])[0]
        elif vizinhos_anel:
            escolhida = random.choice(vizinhos_anel)
        else:
            escolhida = pos

        direcao = direcao_passo(pos, escolhida)
        self.print(f"plano rondar: patrulhando anel {pos} -> {escolhida} ({direcao})")
        self.mover_guardiao(direcao)
        return False

    @pl(gain, Belief("encerrar"))
    def encerrar(self, src):
        self.stop_cycle()


class Walker(Agent):
    """Utility-based + Goal-based Agent em BDI puro: selecao de planos por contexto + crencas MASPY."""

    def __init__(self, name, arena: Environment):
        super().__init__(name, max_intentions=1)
        self.filter_perceptions(add, focus, [self.my_name, "publico"])
        self.connect_to(arena)
        self.add(Belief("Path_Graph", dict()), False)
        self.add(Belief("Wall_Set", []), False)
        self.add(Belief("vezes_interceptado", (0,)), False)
        self.add(Belief("ultimo_valor_alvo", (0,)), False)
        self.add(Belief("alvo_ativo", (0,)), False)

    def _alvos_livres(self):
        percepts = self.get(Belief("alvo", (Any, Any, Any, Any), "Arena"), all=True) or []
        if isinstance(percepts, Belief):
            percepts = [percepts]
        return [(x, y, v) for x, y, v, dono in (b.values for b in percepts) if dono is None]

    def _posicoes_guardioes(self):
        gbs = self.get(Belief("guardiao_pos", (Any, Any, Any), "Arena"), all=True) or []
        if isinstance(gbs, Belief):
            gbs = [gbs]
        return [(b.values[1], b.values[2]) for b in gbs]

    def utilidade(self, alvo, pos, posicoes_guardioes, alvo_protegido, vezes_interceptado):
        ax, ay, valor = alvo
        dist = manhattan(pos, (ax, ay))
        risco = 0.0
        # Penalidade calibrada frente a diferenca 50 vs 10: logo apos ser interceptado U(10) supera U(50)
        if (ax, ay) == alvo_protegido and posicoes_guardioes:
            risco = 8.0 + 36.0 * vezes_interceptado
            if min(manhattan(pos, pg) for pg in posicoes_guardioes) <= 2:
                risco += 4.0
        return valor - 1.1 * dist - risco

    def _descartar_alvo_atual(self):
        b_ativo = self.get(Belief("alvo_ativo", Any))
        if b_ativo is not None and b_ativo.values:
            atual = self.get(Belief("alvo_escolhido", (Any, Any, Any)))
            if atual is not None:
                self.rm(atual)
            b_ativo.change(values=(0,))

    @pl(gain, Goal("agir"), Belief("sobre_alvo", (Any, Any, Any), "Arena"))
    def capturar(self, src, sobre):
        tx, ty, valor_sensor = sobre
        ok, valor, restam = self.reivindicar_alvo(tx, ty)
        self._descartar_alvo_atual()
        if ok:
            self.print(f"plano capturar: reivindicou alvo {valor} em {(tx, ty)}!")
            self.send(broadcast, tell, Belief("alvo_capturado", (tx, ty, valor, self.my_name)))
            if restam == 0:
                self.print("ultimo alvo capturado! Encerrando disputa.")
                self.send(broadcast, tell, Belief("encerrar"))
                self.stop_cycle()
                return True
        return False

    @pl(gain, Goal("agir"), Belief("alerta_interceptacao", Any, "Arena"))
    def reavaliar_risco(self, src, total_interc):
        self.get(Belief("vezes_interceptado", Any)).change(values=(total_interc,))
        self._descartar_alvo_atual()
        self.confirmar_alerta_interceptacao()
        self.print(f"plano reavaliar_risco: barrado ({total_interc}x)! Recalculando utilidade dos alvos...")
        return False

    @pl(
        gain,
        Goal("agir"),
        [~Belief("alvo_escolhido", (Any, Any, Any)), Belief("agt_position", (Any, Any), "Arena")],
    )
    def escolher_alvo(self, src, x, y):
        pos = (x, y)
        livres = self._alvos_livres()
        if not livres:
            self.stop_cycle()
            return True

        _, alvo_protegido = self.get(Belief("info_arena", (Any, Any), "Arena")).values
        vezes_interc = self.get(Belief("vezes_interceptado", Any)).values
        pos_g = self._posicoes_guardioes()

        avaliacoes = [
            (round(self.utilidade(a, pos, pos_g, alvo_protegido, vezes_interc), 1), a)
            for a in livres
        ]
        melhor_u, escolhido = max(avaliacoes, key=lambda par: par[0])

        b_ult_val = self.get(Belief("ultimo_valor_alvo", Any))
        ant_val = b_ult_val.values
        b_ult_val.change(values=(escolhido[2],))
        self.add(Belief("alvo_escolhido", escolhido), False)
        self.get(Belief("alvo_ativo", Any)).change(values=(1,))

        resumo_u = ", ".join(f"alvo {a[2]}: U={u}" for u, a in sorted(avaliacoes, key=lambda p: -p[1][2]))
        if ant_val and ant_val != escolhido[2] and len(livres) > 1:
            self.print(
                f"plano escolher_alvo: MIGROU do alvo {ant_val} para alvo {escolhido[2]} em {escolhido[:2]} ({resumo_u})"
            )
        else:
            self.print(f"plano escolher_alvo: selecionou alvo {escolhido[2]} em {escolhido[:2]} ({resumo_u})")
        return False

    @pl(
        gain,
        Goal("agir"),
        [Belief("alvo_escolhido", (Any, Any, Any)), Belief("agt_position", (Any, Any), "Arena")],
    )
    def navegar(self, src, alvo, pos):
        livres_xy = {a[:2] for a in self._alvos_livres()}
        if alvo[:2] not in livres_xy:
            self._descartar_alvo_atual()
            return False

        map_size, _ = self.get(Belief("info_arena", (Any, Any), "Arena")).values
        b_grafo = self.get(Belief("Path_Graph", Any))
        b_paredes = self.get(Belief("Wall_Set", Any))
        pos_g = self._posicoes_guardioes()

        caminho = astar_flanqueio(pos, alvo[:2], map_size, b_grafo.values, b_paredes.values, pos_g)
        prox = caminho[1] if caminho and len(caminho) > 1 else alvo[:2]
        direcao = direcao_passo(pos, prox)

        resultado = self.mover_walker(direcao)
        if resultado is None:
            return False
        nova_pos, bateu_parede = resultado

        if bateu_parede and direcao != "stay":
            deltas = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
            dx, dy = deltas[direcao]
            parede = (pos[0] + dx, pos[1] + dy)
            if parede not in b_paredes.values:
                self.add(Belief("parede_descoberta", parede))
        elif nova_pos != pos:
            grafo = b_grafo.values
            grafo.setdefault(pos, set()).add(nova_pos)
            grafo.setdefault(nova_pos, set()).add(pos)
            b_grafo.change(values=grafo)

        return False

    @pl(gain, Belief("parede_descoberta", (Any, Any)))
    def registrar_parede(self, src, parede):
        b_paredes = self.get(Belief("Wall_Set", Any))
        paredes = list(b_paredes.values)
        if parede not in paredes:
            paredes.append(parede)
            b_paredes.change(values=paredes)
            self.print(f"plano registrar_parede: parede {parede} gravada em Wall_Set")
        b_ev = self.get(Belief("parede_descoberta", parede))
        if b_ev is not None:
            self.rm(b_ev)

    @pl(gain, Belief("alvo_capturado", (Any, Any, Any, Any)))
    def on_alvo_capturado(self, src, info):
        x, y, valor, vencedor = info
        if vencedor != self.my_name:
            b_ativo = self.get(Belief("alvo_ativo", Any))
            if b_ativo is not None and b_ativo.values:
                atual = self.get(Belief("alvo_escolhido", (Any, Any, Any)))
                if atual is not None and atual.values[:2] == (x, y):
                    self.rm(atual)
                    b_ativo.change(values=(0,))
                    self.print(f"plano on_alvo_capturado: rival {vencedor} levou alvo {valor} em {(x, y)}; replanejando!")
                elif atual is not None:
                    self.print(
                        f"plano on_alvo_capturado: rival {vencedor} levou alvo {valor}; mantendo foco no alvo {atual.values[2]}"
                    )

    @pl(gain, Belief("encerrar"))
    def encerrar(self, src):
        self.stop_cycle()
