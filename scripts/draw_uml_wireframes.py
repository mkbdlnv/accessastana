"""Draw the UML use-case diagram and low-fidelity UI wireframes as PNG.

Mermaid has no UML use-case notation (stick-figure actors, system boundary,
ellipses), so these two figures are drawn with matplotlib at fixed positions.
Usage: uv run python scripts/draw_uml_wireframes.py  →  docs/diagrams/png/
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "docs" / "diagrams" / "png"
INK, BLUE, FILL, GREY = "#0b0b0b", "#2a78d6", "#eef4fb", "#8a8984"


def actor(ax: plt.Axes, x: float, y: float, label: str) -> None:
    """UML stick figure with a label below."""
    ax.add_patch(plt.Circle((x, y + 0.42), 0.13, fill=False, lw=1.4, color=INK))
    ax.plot([x, x], [y + 0.29, y - 0.1], color=INK, lw=1.4)
    ax.plot([x - 0.25, x + 0.25], [y + 0.18, y + 0.18], color=INK, lw=1.4)
    ax.plot([x, x - 0.2], [y - 0.1, y - 0.42], color=INK, lw=1.4)
    ax.plot([x, x + 0.2], [y - 0.1, y - 0.42], color=INK, lw=1.4)
    ax.text(x, y - 0.62, label, ha="center", va="top", fontsize=10, color=INK)


def use_case_diagram() -> Path:
    fig, ax = plt.subplots(figsize=(13, 10))
    ax.set_xlim(0, 13.4)
    ax.set_ylim(0, 12.2)
    ax.axis("off")
    ax.add_patch(Rectangle((2.6, 0.3), 8.6, 11.5, fill=False, lw=1.3, color=INK))
    ax.text(6.9, 11.55, "Система AccessAstana", ha="center", fontsize=12, weight="bold")

    ucs = {  # id: (y, text) — ordered top→bottom to minimise crossing lines
        "UC-08": (10.7, "UC-08 Переключить язык kk / ru / en"),
        "UC-04": (9.75, "UC-04 Посмотреть 15-минутный индекс"),
        "UC-01": (8.8, "UC-01 Просмотреть карту времени пешком"),
        "UC-02": (7.85, "UC-02 Сравнить лето / зиму / мороз"),
        "UC-03": (6.9, "UC-03 Сравнить районы"),
        "UC-05": (5.95, "UC-05 Смоделировать сценарий"),
        "UC-06": (5.0, "UC-06 Получить рекомендации размещения"),
        "UC-07": (4.05, "UC-07 Скачать PDF-отчёт"),
        "UC-10": (3.1, "UC-10 Пересчитать доступность и отчёт"),
        "UC-09": (2.15, "UC-09 Загрузить / обновить данные города"),
        "UC-11": (1.2, "UC-11 Развернуть сервер, восстановить БД"),
    }
    cx, w, h = 6.5, 6.4, 0.72
    for _uid, (y, text) in ucs.items():
        ax.add_patch(Ellipse((cx, y), w, h, facecolor=FILL, edgecolor=BLUE, lw=1.3))
        ax.text(cx, y, text, ha="center", va="center", fontsize=9.5)

    actors = {
        "resident": (1.2, 9.6, "Житель /\nисследователь", ["UC-08", "UC-04", "UC-01", "UC-02"]),
        "planner": (1.2, 5.6, "Урбанист /\nсотрудник акимата", ["UC-01", "UC-02", "UC-03", "UC-05", "UC-06", "UC-07"]),
        "analyst": (12.3, 3.4, "Аналитик\nданных", ["UC-07", "UC-10", "UC-09"]),
        "devops": (12.3, 1.0, "DevOps-\nинженер", ["UC-11"]),
    }
    for x, y, label, links in actors.values():
        actor(ax, x, y, label)
        for uid in links:
            uy = ucs[uid][0]
            ex = cx - w / 2 if x < cx else cx + w / 2
            ax.plot([x + (0.3 if x < cx else -0.3), ex], [y + 0.15, uy], color=GREY, lw=1)

    def dashed(src: str, dst: str, label: str) -> None:
        """Dashed dependency arrow from `src` to `dst` along the right edge of the ellipses."""
        y0, y1 = ucs[src][0], ucs[dst][0]
        x = cx + w / 2
        ax.add_patch(FancyArrowPatch((x - 0.05, y0), (x - 0.05, y1), arrowstyle="-|>", mutation_scale=14,
                                     ls="--", lw=1.2, color=INK, connectionstyle="arc3,rad=0.9"))  # fmt: skip
        ax.text(x + 0.42, (y0 + y1) / 2, label, fontsize=9.5, ha="left", va="center")

    dashed("UC-02", "UC-01", "«extend»")
    dashed("UC-06", "UC-05", "«include»")
    path = OUT / "usecases.png"
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def box(ax: plt.Axes, x: float, y: float, w: float, h: float, text: str = "", fs: float = 9, dash: bool = False) -> None:
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fill=False,
                                lw=1.2, ls="--" if dash else "-", color=INK))  # fmt: skip
    if text:
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=INK)


def wireframe(title: str, panel: list[tuple[str, float]], map_note: str, fname: str) -> Path:
    """Low-fidelity wireframe: header, left panel with widgets, map area, footer."""
    fig, ax = plt.subplots(figsize=(12, 7.2))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7.2)
    ax.axis("off")
    box(ax, 0.1, 6.5, 11.8, 0.6)
    ax.text(0.3, 6.8, "AccessAstana", fontsize=12, weight="bold", va="center")
    box(ax, 8.1, 6.6, 1.9, 0.4, "Скачать отчёт PDF", 8)
    box(ax, 10.2, 6.6, 1.5, 0.4, "KK | RU | EN", 8)
    box(ax, 0.1, 0.6, 3.6, 5.8)
    ax.text(0.3, 6.15, title, fontsize=10, weight="bold")
    y = 5.75
    for label, hgt in panel:
        box(ax, 0.3, y - hgt, 3.2, hgt, label, 7.8)
        y -= hgt + 0.15
    box(ax, 3.9, 0.6, 8.0, 5.8)
    for i in range(6):  # hexagon placeholders
        for j in range(4):
            ax.add_patch(plt.Polygon([(5.2 + i * 0.75 + (j % 2) * 0.37 + 0.3 * __import__("math").cos(a),
                                       2.4 + j * 0.62 + 0.3 * __import__("math").sin(a))
                                      for a in [k * 3.1416 / 3 for k in range(6)]],
                                     fill=False, lw=0.8, color=GREY))  # fmt: skip
    ax.text(7.9, 5.9, map_note, ha="center", fontsize=9, color=INK)
    box(ax, 10.0, 0.8, 1.7, 1.2, "Легенда\n(минуты /\nиндекс)", 8)
    box(ax, 4.1, 0.8, 2.3, 0.45, "© OpenStreetMap …", 7.5, dash=True)
    box(ax, 0.1, 0.1, 11.8, 0.4, "Футер: источники данных и лицензии (ODbL, CC BY 4.0)", 8)
    path = OUT / fname
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print(use_case_diagram())
    tabs = ("Вкладки: Доступность | Сценарий | Оптимизация", 0.45)
    print(wireframe("Доступность", [
        ("Город ▾", 0.4), ("Категория ▾ (7 + индекс)", 0.4), ("Сезон: Лето | Зима | Мороз", 0.4), tabs,
        ("Таблица районов:\nнаселение, индекс, доля ≤ N мин", 1.6), ("☐ Показать границы районов", 0.4),
    ], "Карта: H3-ячейки, цвет = минуты до объекта; всплывающая подсказка", "wireframe_overview.png"))  # fmt: skip
    print(wireframe("Сценарий / Оптимизация", [
        ("Категория ▾  Сезон", 0.4), tabs, ("☐ Режим редактирования", 0.4),
        ("Добавлено: N · к удалению: M", 0.4), ("[ Рассчитать ]  [ Сбросить ]", 0.45),
        ("Таблица «до / после / изменение»", 1.1), ("k = [5]  метод ▾  [ Оптимизировать ]", 0.45),
    ], "Клик по карте = новый объект; клик по точке = удалить; № = рекомендуемые места",
        "wireframe_scenario.png"))  # fmt: skip


if __name__ == "__main__":
    main()
