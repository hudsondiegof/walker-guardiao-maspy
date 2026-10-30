import sys
from threading import Thread

from maspy import Admin, Channel, Goal

from arena_env import Arena
from agentes import Walker, Guardiao

NUM_GUARDIOES = 2
DELAY_INICIAL = 0.8
PADRAO = ((10, 10), 0.15, 4, (10, 50))


def criar_sistema(map_size, walls_prob, num_walkers, valores):
    arena = Arena(map_size, walls_prob, valores)
    guardioes = [Guardiao("Guardiao", arena) for _ in range(NUM_GUARDIOES)]
    walkers = [Walker("Walker", arena) for _ in range(num_walkers)]

    for g in guardioes:
        g.add(Goal("patrulhar"))
    for w in walkers:
        w.add(Goal("agir"))
    return arena


if __name__ == "__main__":
    Admin(listener_log=True)
    Admin().sys_settings(cycle_speed=0.1)
    Channel().show_exec = True

    if "--sem-gui" in sys.argv:
        arena = criar_sistema(*PADRAO)
        Admin().slow_cycle_by(0.02)
        Admin().start_system()
        print("\n=== RESULTADO FINAL ===")
        print(arena.resumo_final())
    else:
        from Pygame_Screens import MapVisualizer, MenuScreen

        settings = MenuScreen().loop()
        if settings:
            arena = criar_sistema(*settings)
            Admin().slow_cycle_by(DELAY_INICIAL)
            Thread(target=Admin().start_system, daemon=True).start()
            MapVisualizer(arena).loop()
