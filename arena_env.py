import math
import random
from collections import deque
from random import randint
from threading import RLock

from maspy import Environment, Percept, Any


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def gerar_mapa_conectado(largura, altura, alvos, prob_paredes=0.2, max_tentativas=2000):
    def vizinhos(x, y):
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < largura and 0 <= ny < altura:
                yield nx, ny

    alvo_maior = alvos[-1]
    for _ in range(max_tentativas):
        paredes = {
            (x, y)
            for x in range(largura)
            for y in range(altura)
            if random.random() < prob_paredes and (x, y) not in alvos
        }

        # Garante que o alvo protegido tenha pelo menos 2 entradas livres e anel >= 4 celulas para os 2 Guardioes
        entradas_livres = [v for v in vizinhos(*alvo_maior) if v not in paredes]
        anel_livre = [
            (x, y)
            for x in range(largura)
            for y in range(altura)
            if (x, y) != alvo_maior
            and (x, y) not in paredes
            and 1 <= manhattan((x, y), alvo_maior) <= 2
        ]
        if len(entradas_livres) < 2 or len(anel_livre) < 4:
            continue

        fila = deque([alvos[0]])
        alcancaveis = {alvos[0]}
        while fila:
            cx, cy = fila.popleft()
            for nx, ny in vizinhos(cx, cy):
                if (nx, ny) not in paredes and (nx, ny) not in alcancaveis:
                    alcancaveis.add((nx, ny))
                    fila.append((nx, ny))

        if len(alcancaveis) == largura * altura - len(paredes):
            return paredes

    raise RuntimeError("Nao foi possivel gerar um mapa valido conectado.")


class Arena(Environment):
    """Ambiente fisico Grid 2D: expoe apenas sensores (Percepts) e aplica atuadores fisicos."""

    def __init__(self, map_size=(10, 10), walls_prob=0.2, valores=(10, 50)):
        super().__init__()
        self.arena_lock = RLock()
        self.map_size = map_size
        self.moves = {
            "up": (0, -1),
            "down": (0, 1),
            "left": (-1, 0),
            "right": (1, 0),
            "stay": (0, 0),
        }
        self.origens = {}
        self.placar = {}
        self.interceptacoes = {}
        self.total_interceptacoes = 0
        self.guardioes = []
        self._sensor_sobre_alvo = {}
        self._sensor_walker_adj = {}
        self._sensor_alerta = {}

        valores_ordenados = tuple(sorted(valores))
        alvos = self._sortear_alvos(len(valores_ordenados))
        self.paredes = gerar_mapa_conectado(map_size[0], map_size[1], alvos, walls_prob)

        # O ultimo alvo e sempre o de maior valor (protegido pelos 2 Guardioes)
        self.alvo_protegido = alvos[-1]
        self.rota_patrulha = self._calcular_rota_patrulha(self.alvo_protegido)

        self.create(Percept("info_arena", (map_size, self.alvo_protegido), "publico"))
        self.create(Percept("anel_patrulha", (list(self.rota_patrulha),), "publico"))
        self.create(Percept("alvo_protegido_livre", self.alvo_protegido, "publico"))

        for (x, y), valor in zip(alvos, valores_ordenados):
            self.print(f"Alvo de valor {valor} criado em {(x, y)}")
            self.create(Percept("alvo", (x, y, valor, None), "publico"))

        for parede in self.paredes:
            self.create(Percept("wall", parede, "oculto"))

    def _sortear_alvos(self, n):
        w, h = self.map_size
        alvos = []
        while len(alvos) < n:
            pos = (randint(0, w - 1), randint(0, h - 1))
            if all(manhattan(pos, a) >= (w + h) // 3 for a in alvos):
                alvos.append(pos)
        return alvos

    def _calcular_rota_patrulha(self, centro):
        cx, cy = centro
        w, h = self.map_size
        anel = [
            (x, y)
            for x in range(w)
            for y in range(h)
            if (x, y) != centro
            and (x, y) not in self.paredes
            and 1 <= manhattan((x, y), centro) <= 2
        ]
        anel.sort(key=lambda p: math.atan2(p[1] - cy, p[0] - cx))
        return anel

    def _alvos(self):
        percepts = self.get(Percept("alvo", (Any, Any, Any, Any), "publico"), all=True) or []
        if isinstance(percepts, Percept):
            percepts = [percepts]
        return [p.values for p in percepts]

    def _protegido_esta_livre(self):
        return any(a[:2] == self.alvo_protegido and a[3] is None for a in self._alvos())

    def _posicoes_guardioes(self, exceto=None):
        if not self.guardioes:
            return set()
        percepts = self.get(Percept("guardiao_pos", (Any, Any, Any), "publico"), all=True) or []
        if isinstance(percepts, Percept):
            percepts = [percepts]
        return {
            (p.values[1], p.values[2])
            for p in percepts
            if p.values[0] != exceto
        }

    def _atualizar_sensor_sobre_alvo(self, w_name, pos):
        atual_p = self._sensor_sobre_alvo.get(w_name)
        alvo_livre = None
        for tx, ty, valor, dono in self._alvos():
            if dono is None and (tx, ty) == pos:
                alvo_livre = (tx, ty, valor)
                break

        if alvo_livre is not None:
            if atual_p is not None:
                atual_p.change(values=alvo_livre)
            else:
                novo = Percept("sobre_alvo", alvo_livre, w_name)
                self.create(novo)
                self._sensor_sobre_alvo[w_name] = novo
        elif atual_p is not None:
            self.delete(atual_p)
            self._sensor_sobre_alvo.pop(w_name, None)

    def _atualizar_sensores_guardioes(self):
        protegido_livre = self._protegido_esta_livre()
        for g_name in self.guardioes:
            sensor_adj = self._sensor_walker_adj.get(g_name)
            if not protegido_livre:
                if sensor_adj is not None:
                    self.delete(sensor_adj)
                    self._sensor_walker_adj.pop(g_name, None)
                continue

            pos_g = self.get(Percept("agt_position", (Any, Any), g_name), ck_group=True)
            if not isinstance(pos_g, Percept):
                continue
            gx, gy = pos_g.values
            outros_g = self._posicoes_guardioes(exceto=g_name)

            detectado = None
            for w_name in self.origens:
                wp = self.get(Percept("agt_position", (Any, Any), w_name), ck_group=True)
                if not isinstance(wp, Percept):
                    continue
                wpos = wp.values
                if (
                    wpos != self.alvo_protegido
                    and wpos not in outros_g
                    and manhattan((gx, gy), wpos) == 1
                    and manhattan(wpos, self.alvo_protegido) <= 2
                ):
                    detectado = (w_name, wpos[0], wpos[1])
                    break

            if detectado is not None:
                if sensor_adj is not None:
                    sensor_adj.change(values=detectado)
                else:
                    novo = Percept("walker_adjacente", detectado, g_name)
                    self.create(novo)
                    self._sensor_walker_adj[g_name] = novo
            elif sensor_adj is not None:
                self.delete(sensor_adj)
                self._sensor_walker_adj.pop(g_name, None)

    def _registrar_interceptacao(self, w_name, wp, msg):
        origem = self.origens[w_name]
        wp.change(values=origem)
        self.interceptacoes[w_name] += 1
        self.total_interceptacoes += 1
        total_w = self.interceptacoes[w_name]
        self._atualizar_sensor_sobre_alvo(w_name, origem)

        alerta = self._sensor_alerta.get(w_name)
        if alerta is not None:
            alerta.change(values=(total_w,))
        else:
            novo = Percept("alerta_interceptacao", (total_w,), w_name)
            self.create(novo)
            self._sensor_alerta[w_name] = novo
        self.print(msg)

    def confirmar_alerta_interceptacao(self, agt):
        with self.arena_lock:
            alerta = self._sensor_alerta.pop(agt, None)
            if alerta is not None:
                self.delete(alerta)

    def on_connect(self, agt):
        with self.arena_lock:
            if agt.startswith("Guardiao"):
                ordem = len(self.guardioes)
                idx = (ordem * len(self.rota_patrulha) // 2) % len(self.rota_patrulha)
                ocupadas = self._posicoes_guardioes()
                while self.rota_patrulha[idx] in ocupadas:
                    idx = (idx + 1) % len(self.rota_patrulha)
                self.guardioes.append(agt)
                pos_inicial = self.rota_patrulha[idx]
                self.create(Percept("agt_position", pos_inicial, agt))
                self.create(Percept("guardiao_pos", (agt, pos_inicial[0], pos_inicial[1]), "publico"))
                self.print(f"{agt} posicionado na patrulha em {pos_inicial} (protegendo {self.alvo_protegido})")
                self._atualizar_sensores_guardioes()
                return

            if not agt.startswith("Walker"):
                return

            alvos_xy = {a[:2] for a in self._alvos()}
            pos_guardioes = self._posicoes_guardioes()

            w, h = self.map_size
            start_pos = (0, 0)
            for tentativa in range(1000):
                cand = (randint(0, w - 1), randint(0, h - 1))
                longe = min(manhattan(cand, a) for a in alvos_xy) > w / 3 or tentativa > 500
                livre = cand not in self.paredes and cand not in alvos_xy and cand not in pos_guardioes
                if livre and longe:
                    start_pos = cand
                    break

            self.origens[agt] = start_pos
            self.placar[agt] = 0
            self.interceptacoes[agt] = 0
            self.create(Percept("agt_position", start_pos, agt))
            self._atualizar_sensor_sobre_alvo(agt, start_pos)
            self._atualizar_sensores_guardioes()

    def mover_walker(self, agt, direction):
        with self.arena_lock:
            pos_percept = self.get(Percept("agt_position", (Any, Any), agt), ck_group=True)
            if not isinstance(pos_percept, Percept):
                return None

            x, y = pos_percept.values
            dx, dy = self.moves.get(direction, (0, 0))
            nx = max(0, min(x + dx, self.map_size[0] - 1))
            ny = max(0, min(y + dy, self.map_size[1] - 1))
            nova = (nx, ny)

            if nova == (x, y) or nova in self.paredes:
                if direction != "stay" and nova in self.paredes:
                    self.print(f"{agt} bateu na parede {nova}")
                return (x, y), nova in self.paredes

            pos_guardioes = self._posicoes_guardioes()
            if nova in pos_guardioes and self._protegido_esta_livre():
                origem = self.origens[agt]
                self._registrar_interceptacao(
                    agt, pos_percept, f"{agt} esbarrou num Guardiao em {nova} e voltou para {origem}!"
                )
                self._atualizar_sensores_guardioes()
                return origem, False

            pos_percept.change(values=nova)
            self._atualizar_sensor_sobre_alvo(agt, nova)
            self._atualizar_sensores_guardioes()
            return nova, False

    def mover_guardiao(self, agt, direction):
        """Atuador puramente fisico do Guardiao: desloca 1 celula na direcao escolhida pelo plano BDI."""
        with self.arena_lock:
            if not self._protegido_esta_livre():
                return None

            pos_g = self.get(Percept("agt_position", (Any, Any), agt), ck_group=True)
            pub_g = self.get(Percept("guardiao_pos", (agt, Any, Any), "publico"), ck_group=True)
            if not isinstance(pos_g, Percept) or not isinstance(pub_g, Percept):
                return None

            gx, gy = pos_g.values
            dx, dy = self.moves.get(direction, (0, 0))
            nx = max(0, min(gx + dx, self.map_size[0] - 1))
            ny = max(0, min(gy + dy, self.map_size[1] - 1))
            nova_g = (nx, ny)

            outros_g = self._posicoes_guardioes(exceto=agt)
            if nova_g in self.paredes or nova_g == self.alvo_protegido or nova_g in outros_g:
                self._atualizar_sensores_guardioes()
                return (gx, gy)

            if nova_g != (gx, gy):
                pos_g.change(values=nova_g)
                pub_g.change(values=(agt, nova_g[0], nova_g[1]))

            for w_name, origem in self.origens.items():
                wp = self.get(Percept("agt_position", (Any, Any), w_name), ck_group=True)
                if isinstance(wp, Percept) and wp.values == nova_g:
                    self._registrar_interceptacao(
                        w_name, wp, f"{agt} interceptou {w_name} em {nova_g}! {w_name} voltou para {origem}"
                    )

            self._atualizar_sensores_guardioes()
            return nova_g

    def reivindicar_alvo(self, agt, x, y):
        with self.arena_lock:
            alvo = self.get(Percept("alvo", (x, y, Any, Any), "publico"), ck_group=True)
            pos = self.get(Percept("agt_position", (Any, Any), agt), ck_group=True)
            if not isinstance(alvo, Percept) or not isinstance(pos, Percept):
                return False, 0, self._contar_livres()
            _, _, valor, dono = alvo.values
            if dono is not None or pos.values != (x, y):
                self._atualizar_sensor_sobre_alvo(agt, pos.values)
                return False, 0, self._contar_livres()

            alvo.change(values=(x, y, valor, agt))
            self.placar[agt] = self.placar.get(agt, 0) + valor
            self._atualizar_sensor_sobre_alvo(agt, pos.values)

            if (x, y) == self.alvo_protegido:
                p_livre = self.get(Percept("alvo_protegido_livre", (Any, Any), "publico"), ck_group=True)
                if isinstance(p_livre, Percept):
                    self.delete(p_livre)
                self.create(Percept("alvo_protegido_capturado", self.alvo_protegido, "publico"))

            self._atualizar_sensores_guardioes()
            restam = self._contar_livres()
            self.print(f"{agt} CAPTUROU o alvo de valor {valor} em {(x, y)}! (restam {restam})")
            return True, valor, restam

    def _contar_livres(self):
        return sum(1 for _, _, _, dono in self._alvos() if dono is None)

    def resumo_final(self):
        ranking = sorted(self.placar.items(), key=lambda item: (-item[1], self.interceptacoes[item[0]]))
        partes = [f"{w}={pts}pts ({self.interceptacoes[w]} intercept.)" for w, pts in ranking]
        return " | ".join(partes)
