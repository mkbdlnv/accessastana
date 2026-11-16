"""Model grant budget for AccessAstana (educational project; model figures only).

One source of truth for all budget numbers in the explanatory note:
- writes budget.xlsx with FORMULAS (not values), so every number can be checked in Excel or LibreOffice;
- computes the same values in Python and writes budget_tables.md for the note.

Norms (references are to the prompt, part C):
- C1: grant competition 2026–2028, 36 months, limits 30 / 40 / 40 mln KZT, ≥ 30% of the team ≤ 40 years old.
- C2: order of the Minister of Science and Higher Education No. 592 (25.12.2024, as amended by No. 424 of 04.09.2026):
  DO = DS × Kp; DS = Sbase × Kdo; Sbase = 190 000; Kp = Kvid × Ktip × Kruk × Kdos (p. 6);
  part-time P = G × DO (p. 14); degree bonuses in MRP (p. 12, annex 7).
- C3: Government decree No. 256 (11.05.2018, as amended to 14.07.2026 No. 615): domestic per diem 2 MRP/day,
  accommodation in Almaty ≤ 7 MRP/night (p. 3); abroad per country norms (p. 7).
Everything team-specific is a MODEL ASSUMPTION marked [ЗАПОЛНИТЬ] until the team provides real data.

Usage: uv run --group docs python docs/final/budget/budget_model.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

HERE = Path(__file__).resolve().parent
YEARS = (2026, 2027, 2028)
LIMITS = {2026: 30_000_000, 2027: 40_000_000, 2028: 40_000_000}  # C1
SBASE = 190_000  # C2, p. 6
MRP = 4_325  # C3: 2026; used for 2027–2028 as an assumption
K_VID = {"фундаментальные": 1.0, "прикладные": 1.15}
K_TIP = {"грантовое": 2.0, "программно-целевое": 2.15, "базовое (фундаментальные)": 0.67}
K_RUK = {"научный руководитель": 1.25, "исполнитель": 1.0}
K_DOS = {0: 1.0, 1: 1.10, 2: 1.20, 3: 1.30, 4: 1.40, 5: 1.50}
STAZH = ["0-1", "1-2", "2-3", "3-5", "5-7", "7-10", "10-13", "13-16", "16-20", "20-25", ">25"]
K_DO = {  # C2, annex 2: class → coefficients by experience band
    1: [1.60, 1.63, 1.66, 1.69, 1.73, 1.76, 1.79, 1.83, 1.86, 1.89, 1.93],
    2: [1.45, 1.48, 1.51, 1.54, 1.57, 1.60, 1.63, 1.66, 1.69, 1.72, 1.75],
    3: [1.30, 1.35, 1.37, 1.40, 1.42, 1.45, 1.48, 1.51, 1.54, 1.57, 1.59],
    4: [1.02, 1.04, 1.06, 1.08, 1.10, 1.12, 1.14, 1.16, 1.18, 1.21, 1.23],
    5: [0.91, 0.94, 0.96, 0.98, 1.00, 1.02, 1.04, 1.06, 1.08, 1.10, 1.12],
    6: [0.88, 0.90, 0.91, 0.93, 0.95, 0.97, 0.99, 1.01, 1.02, 1.04, 1.06],
    7: [0.86, 0.87, 0.89, 0.91, 0.92, 0.94, 0.96, 0.97, 0.99, 1.01, 1.03],
}
DEGREE_MRP = {"нет": 0, "PhD / кандидат наук": 17, "доктор наук": 34}  # C2, p. 12, annex 7
KIND, TYPE = "прикладные", "грантовое"


@dataclass
class Member:
    role: str  # project role
    position: str  # position by annex 1
    cls: int
    stazh: str
    kruk: str
    kdos_level: int
    g: float  # share of working time on the project (p. 14)
    months: tuple[int, int, int]
    degree: str
    young: str  # "да" / "нет" / "[ЗАПОЛНИТЬ]"
    name: str = "[ЗАПОЛНИТЬ: ФИО]"

    def kdo(self) -> float:
        return K_DO[self.cls][STAZH.index(self.stazh)]

    def ds(self) -> float:
        return SBASE * self.kdo()

    def kp(self) -> float:
        return K_VID[KIND] * K_TIP[TYPE] * K_RUK[self.kruk] * K_DOS[self.kdos_level]

    def do(self) -> float:
        return self.ds() * self.kp()

    def p(self) -> float:
        return self.g * self.do()

    def degree_month(self) -> float:
        return DEGREE_MRP[self.degree] * MRP

    def year_sum(self, i: int) -> float:
        return self.months[i] * (self.p() + self.degree_month())


# MODEL TEAM (assumptions until the team provides real data): a scientific leader and four master's
# students as junior researchers, everyone at 0.5 FTE for 36 months.
TEAM = [
    Member("Научный руководитель", "ведущий научный сотрудник", 2, "10-13", "научный руководитель", 0, 0.5,
           (12, 12, 12), "PhD / кандидат наук", "[ЗАПОЛНИТЬ]"),
    *[Member(r, "младший научный сотрудник", 5, "0-1", "исполнитель", 0, 0.5, (12, 12, 12), "нет", "да")
      for r in ("Project Manager / исполнитель", "Developer / исполнитель", "Data Analyst / BA / исполнитель",
                "Tester / DevOps / исполнитель")],
]  # fmt: skip

# Payroll taxes and contributions: NOT in the norms of part C (Tax Code 2026) → parameters to fill in.
TAXES = [
    ("Социальный налог (работодатель)", None),
    ("Социальные отчисления (работодатель)", None),
    ("Взносы на ОСМС (работодатель)", None),
    ("Обязательные пенсионные взносы работодателя (ОПВР)", None),
    ("Резерв на отпускные", None),
]


@dataclass
class Trip:
    year: int
    purpose: str
    place: str
    people: int
    days: int
    nights: int
    per_diem: float  # per day per person, in `currency`
    lodging: float  # per night per person (limit), in `currency`
    currency: str  # MRP | USD | EUR
    norm: str


TRIPS = [
    Trip(2026, "Доклад на республиканской конференции [ЗАПОЛНИТЬ: название]", "Алматы", 2, 3, 2,
         2, 7, "MRP", "C3 п.3: суточные 2 МРП/день; проживание ≤ 7 МРП/сутки (Алматы)"),
    Trip(2027, "Доклад на международной конференции [ЗАПОЛНИТЬ: название]", "Турция", 2, 5, 4,
         100, 180, "USD", "C3 п.7: Турция 100 / 180 USD"),
    Trip(2028, "Доклад на международной конференции [ЗАПОЛНИТЬ: название]", "Германия", 2, 5, 4,
         80, 165, "EUR", "C3 п.7: Германия 80 / 165 EUR"),
]  # fmt: skip

OTHER = [  # (article, item, year, justification) — amounts are price quotes to be supplied [ЗАПОЛНИТЬ]
    (3, "Оргвзносы за участие в конференциях (3 поездки)", "по годам", "по ценовым предложениям организаторов"),
    (3, "Публикация статей в открытом доступе (APC), 2 статьи", "2027–2028", "ценовые предложения журналов"),
    (4, "Рабочая станция для обработки данных (1 шт.)", "2026", "ценовое предложение поставщика"),
    (5, "Облачный сервер (EC2 t3.medium или аналог) для демонстрационного стенда, 36 мес.", "2026–2028",
     "тариф провайдера"),
    (5, "Хранение архива исходных данных (объектное хранилище)", "2026–2028", "тариф провайдера"),
]  # fmt: skip

REFERENCE_SHARES = {  # C1: approved application of the National Scientific Council, 2023–2025
    "1. Оплата труда": 61.88, "2. Командировки": 15.05, "3. Научно-организационное сопровождение": 1.53,
    "4. Оборудование и ПО": 16.53, "5. Эксплуатационные расходы": 5.00,
}  # fmt: skip


def fmt(v: float) -> str:
    return f"{v:,.0f}".replace(",", " ")


def dec(v: float, nd: int = 2) -> str:
    """Russian decimal comma."""
    return f"{v:.{nd}f}".replace(".", ",")


def build_workbook(path: Path) -> None:
    wb = Workbook()
    bold = Font(bold=True)
    fill = PatternFill("solid", fgColor="FFF2CC")  # cells to fill in

    # ---- Parameters
    p = wb.active
    p.title = "Параметры"
    rows = [
        ("Параметр", "Значение", "Источник / примечание"),
        ("Сбаз, тг", SBASE, "C2 п.6"),
        ("Квид (прикладные)", K_VID[KIND], "C2 п.6"),
        ("Ктип (грантовое)", K_TIP[TYPE], "C2 п.6"),
        ("МРП 2026, тг", MRP, "C3; для 2027–2028 — допущение"),
        ("Курс USD/KZT", None, "[ЗАПОЛНИТЬ: курс НБРК на дату перечисления]"),
        ("Курс EUR/KZT", None, "[ЗАПОЛНИТЬ: курс НБРК на дату перечисления]"),
    ]
    for r in rows:
        p.append(r)
    p.append(())
    p.append(("Налоги и обязательные платежи с ФОТ (доля, напр. 0,095)", None, "[ЗАПОЛНИТЬ: ставки уточнить в бухгалтерии университета]"))
    tax_first = p.max_row + 1
    for name, val in TAXES:
        p.append((name, val, "[ЗАПОЛНИТЬ]"))
    tax_last = p.max_row
    for row in range(2, tax_last + 1):
        if p.cell(row, 2).value is None and p.cell(row, 1).value:
            p.cell(row, 2).fill = fill
    for c in "ABC":
        p.column_dimensions[c].width = {"A": 58, "B": 14, "C": 60}[c]
    p["A1"].font = p["B1"].font = p["C1"].font = bold
    # named cells (by address) used below
    SB, KV, KT, MR, USD, EUR = "Параметры!$B$2", "Параметры!$B$3", "Параметры!$B$4", "Параметры!$B$5", "Параметры!$B$6", "Параметры!$B$7"
    TAX_SUM = f"SUM(Параметры!$B${tax_first}:$B${tax_last})"

    # ---- Kdo table (annex 2)
    k = wb.create_sheet("Кдо")
    k.append(("Класс \\ стаж", *STAZH))
    for cls, vals in K_DO.items():
        k.append((cls, *vals))
    k.append(())
    k.append(("Источник: C2, приложение 2",))

    # ---- Payroll
    s = wb.create_sheet("Оплата труда")
    head = ["Роль", "ФИО", "Должность (прил. 1)", "Класс", "Стаж", "Кдо", "ДС", "Квид", "Ктип", "Крук", "Уровень Кдос",
            "Кдос", "ДО", "Г (доля)", "П = Г × ДО", "Доплата за степень, тг/мес (п.12)", "Мес. 2026", "Мес. 2027",
            "Мес. 2028", "Сумма 2026", "Сумма 2027", "Сумма 2028", "≤ 40 лет"]  # fmt: skip
    s.append(head)
    for c in s[1]:
        c.font = bold
        c.alignment = Alignment(wrap_text=True, vertical="top")
    for m in TEAM:
        r = s.max_row + 1
        band = STAZH.index(m.stazh) + 2  # column in the Кдо sheet
        s.append([m.role, m.name, m.position, m.cls, m.stazh,
                  f"=INDEX(Кдо!$B$2:$L$8,D{r},MATCH(E{r},Кдо!$B$1:$L$1,0))",
                  f"={SB}*F{r}", f"={KV}", f"={KT}", K_RUK[m.kruk], m.kdos_level,
                  f"=CHOOSE(K{r}+1,1,1.1,1.2,1.3,1.4,1.5)", f"=G{r}*H{r}*I{r}*J{r}*L{r}", m.g, f"=N{r}*M{r}",
                  f"={DEGREE_MRP[m.degree]}*{MR}", *m.months,
                  f"=Q{r}*(O{r}+P{r})", f"=R{r}*(O{r}+P{r})", f"=S{r}*(O{r}+P{r})", m.young])  # fmt: skip
        _ = band
        s.cell(r, 2).fill = fill
        s.cell(r, 11).fill = fill
        if m.young.startswith("["):
            s.cell(r, 23).fill = fill
    last = s.max_row
    s.append(["Итого ФОТ без налогов", *[""] * 18, f"=SUM(T2:T{last})", f"=SUM(U2:U{last})", f"=SUM(V2:V{last})"])
    tot = s.max_row  # row number taken AFTER writing (an empty append may not create a row)
    s.append(["Налоги и обязательные платежи", *[""] * 18, f"=T{tot}*{TAX_SUM}", f"=U{tot}*{TAX_SUM}", f"=V{tot}*{TAX_SUM}"])
    s.append(["Статья 1. Оплата труда, всего", *[""] * 18, f"=T{tot}+T{tot + 1}", f"=U{tot}+U{tot + 1}", f"=V{tot}+V{tot + 1}"])
    for row in range(tot, tot + 3):
        s.cell(row, 1).font = bold
    s.append([])
    s.append(["Доля молодых учёных (≤ 40 лет) в группе", f'=COUNTIF(W2:W{last},"да")/COUNTA(A2:A{last})', "требование C1: ≥ 30%"])
    for i in range(1, len(head) + 1):
        s.column_dimensions[get_column_letter(i)].width = 14
    s.column_dimensions["A"].width = 32
    s.column_dimensions["C"].width = 26
    PAY_TOTAL = {y: f"'Оплата труда'!{c}{tot + 2}" for y, c in zip(YEARS, "TUV", strict=True)}

    # ---- Travel
    t = wb.create_sheet("Командировки")
    t.append(["Год", "Цель", "Место", "Чел.", "Дней", "Ночей", "Суточные/день", "Проживание/ночь (норма)", "Валюта",
              "Суточные, валюта", "Проживание, валюта", "Курс к KZT", "Суточные, тг", "Проживание, тг",
              "Билеты на всех, тг", "Итого, тг", "Норма"])  # fmt: skip
    for c in t[1]:
        c.font = bold
        c.alignment = Alignment(wrap_text=True, vertical="top")
    for tr in TRIPS:
        r = t.max_row + 1
        rate = {"MRP": MR, "USD": USD, "EUR": EUR}[tr.currency]
        t.append([tr.year, tr.purpose, tr.place, tr.people, tr.days, tr.nights, tr.per_diem, tr.lodging, tr.currency,
                  f"=D{r}*E{r}*G{r}", f"=D{r}*F{r}*H{r}", f"={rate}", f"=J{r}*L{r}", f"=K{r}*L{r}", None,
                  f"=M{r}+N{r}+O{r}", tr.norm])  # fmt: skip
        t.cell(r, 15).fill = fill
    tl = t.max_row
    t.append([])
    t.append(["Билеты: ценовые предложения перевозчиков [ЗАПОЛНИТЬ]; ж/д — купе, авиа — эконом (C3 п.3, п.7)"])
    t.column_dimensions["B"].width = 48
    t.column_dimensions["Q"].width = 50
    TRAVEL = {y: f'SUMIF(Командировки!$A$2:$A${tl},{y},Командировки!$P$2:$P${tl})' for y in YEARS}

    # ---- Other articles
    o = wb.create_sheet("Прочие статьи")
    o.append(["Статья", "Позиция", "Период", "Обоснование", "2026, тг", "2027, тг", "2028, тг"])
    for c in o[1]:
        c.font = bold
    for art, item, period, just in OTHER:
        r = o.max_row + 1
        o.append([art, item, period, just, None, None, None])
        for col in (5, 6, 7):
            o.cell(r, col).fill = fill
    ol = o.max_row
    o.column_dimensions["B"].width = 60
    o.column_dimensions["D"].width = 36
    OTH = {(a, y): f"SUMIF('Прочие статьи'!$A$2:$A${ol},{a},'Прочие статьи'!{c}$2:{c}${ol})"
           for a in (3, 4, 5) for y, c in zip(YEARS, "EFG", strict=True)}  # fmt: skip

    # ---- Summary
    v = wb.create_sheet("Свод", 0)
    v.append(["Статья расходов (C1, табл. 2)", *[str(y) for y in YEARS], "Всего", "Доля, %", "Ориентир ННС, %"])
    for c in v[1]:
        c.font = bold
    arts = [("1. Оплата труда", [f"={PAY_TOTAL[y]}" for y in YEARS]),
            ("2. Командировки", [f"={TRAVEL[y]}" for y in YEARS]),
            ("3. Научно-организационное сопровождение", [f"={OTH[(3, y)]}" for y in YEARS]),
            ("4. Оборудование и ПО", [f"={OTH[(4, y)]}" for y in YEARS]),
            ("5. Эксплуатационные расходы", [f"={OTH[(5, y)]}" for y in YEARS])]  # fmt: skip
    for name, cells in arts:
        r = v.max_row + 1
        v.append([name, *cells, f"=SUM(B{r}:D{r})", f"=IF($E$7=0,0,E{r}/$E$7*100)", REFERENCE_SHARES[name]])
    v.append(["ИТОГО", "=SUM(B2:B6)", "=SUM(C2:C6)", "=SUM(D2:D6)", "=SUM(E2:E6)", "=IF(E7=0,0,100)", 100])
    v.append(["Лимит (C1)", *[LIMITS[y] for y in YEARS], sum(LIMITS.values())])
    v.append(["Остаток до лимита", "=B8-B7", "=C8-C7", "=D8-D7", "=E8-E7"])
    v.append(["Укладывается в лимит?", '=IF(B7<=B8,"да","НЕТ")', '=IF(C7<=C8,"да","НЕТ")', '=IF(D7<=D8,"да","НЕТ")'])
    v.append([])
    v.append(["Модельный бюджет учебного проекта. Ячейки с жёлтой заливкой — [ЗАПОЛНИТЬ] (данные команды, ставки, цены)."])
    for r in (7, 8):
        v.cell(r, 1).font = bold
    v.column_dimensions["A"].width = 44
    for c in "BCDEFG":
        v.column_dimensions[c].width = 16

    # ---- Plan vs fact
    f = wb.create_sheet("План-факт")
    f.append(["Статья", "План (модель), всего", "Факт", "Отклонение", "Отклонение, %", "Причина"])
    for c in f[1]:
        c.font = bold
    for i, (name, _) in enumerate(arts, start=2):
        r = f.max_row + 1
        f.append([name, f"=Свод!E{i}", None, f"=IF(C{r}=\"\",\"\",C{r}-B{r})",
                  f"=IF(OR(C{r}=\"\",B{r}=0),\"\",(C{r}-B{r})/B{r}*100)", "[ЗАПОЛНИТЬ: причина отклонения]"])  # fmt: skip
        f.cell(r, 3).fill = fill
    f.column_dimensions["A"].width = 44
    f.column_dimensions["F"].width = 50
    wb.save(path)


def markdown_tables() -> str:
    """The same numbers as the workbook, for the explanatory note."""
    out = ["<!-- generated by docs/final/budget/budget_model.py; do not edit -->", ""]
    out += ["**Таблица Д.1 — Оплата труда (модельная группа), тг**", "",
            "| Роль | Класс | Стаж, лет | Кдо | ДС | Квид | Ктип | Крук | Кдос | ДО | Г | П = Г × ДО | Доплата за степень/мес | 2026 | 2027 | 2028 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]  # fmt: skip
    totals = [0.0, 0.0, 0.0]
    for m in TEAM:
        ys = [m.year_sum(i) for i in range(3)]
        totals = [a + b for a, b in zip(totals, ys, strict=True)]
        out.append(f"| {m.role} | {m.cls} | {m.stazh} | {dec(m.kdo())} | {fmt(m.ds())} | {dec(K_VID[KIND])} "
                   f"| {dec(K_TIP[TYPE], 1)} | {dec(K_RUK[m.kruk])} | {dec(K_DOS[m.kdos_level])} | {fmt(m.do())} "
                   f"| {dec(m.g, 1)} | {fmt(m.p())} "
                   f"| {fmt(m.degree_month())} | {fmt(ys[0])} | {fmt(ys[1])} | {fmt(ys[2])} |")  # fmt: skip
    out.append(f"| **Итого ФОТ без налогов** | | | | | | | | | | | | | **{fmt(totals[0])}** | **{fmt(totals[1])}** | **{fmt(totals[2])}** |")
    out += ["| Налоги и обязательные платежи | | | | | | | | | | | | | [ЗАПОЛНИТЬ] | [ЗАПОЛНИТЬ] | [ЗАПОЛНИТЬ] |", ""]
    young = sum(1 for m in TEAM if m.young == "да")
    out.append(f"Доля молодых учёных (≤ 40 лет): не менее {young} из {len(TEAM)} = {100 * young / len(TEAM):.0f}% "
               "(возраст руководителя — [ЗАПОЛНИТЬ]); требование C1 — не менее 30%.")
    out.append("")
    share = [100 * totals[i] / LIMITS[y] for i, y in enumerate(YEARS)]
    out.append("ФОТ без налогов составляет " + ", ".join(f"{dec(s, 1)}% лимита {y} г." for s, y in zip(share, YEARS, strict=True))
               + f" (ориентир ННС для статьи 1 с налогами — {dec(REFERENCE_SHARES['1. Оплата труда'])}% бюджета).")
    out += ["", "**Таблица Д.2 — Командировки (нормы C3)**", "",
            "| Год | Цель | Место | Чел. | Дней / ночей | Суточные | Проживание (норма) | Суточные всего | Проживание всего | Билеты |",
            "|---|---|---|---:|---:|---|---|---:|---:|---|"]  # fmt: skip
    for tr in TRIPS:
        unit = "МРП" if tr.currency == "MRP" else tr.currency
        pd_total, lodge_total = tr.people * tr.days * tr.per_diem, tr.people * tr.nights * tr.lodging
        if tr.currency == "MRP":
            pd_s = f"{pd_total:g} МРП = {fmt(pd_total * MRP)} тг"
            lo_s = f"{lodge_total:g} МРП = {fmt(lodge_total * MRP)} тг"
        else:
            pd_s = f"{pd_total:g} {unit} × курс [ЗАПОЛНИТЬ]"
            lo_s = f"{lodge_total:g} {unit} × курс [ЗАПОЛНИТЬ]"
        out.append(f"| {tr.year} | {tr.purpose} | {tr.place} | {tr.people} | {tr.days} / {tr.nights} "
                   f"| {tr.per_diem:g} {unit}/день | {tr.lodging:g} {unit}/ночь | {pd_s} | {lo_s} | [ЗАПОЛНИТЬ: ценовые предложения] |")  # fmt: skip
    out += ["", "**Таблица Д.3 — Статьи 3–5 (суммы по ценовым предложениям)**", "",
            "| Статья | Позиция | Период | Обоснование | Сумма |", "|---:|---|---|---|---|"]
    for art, item, period, just in OTHER:
        out.append(f"| {art} | {item} | {period} | {just} | [ЗАПОЛНИТЬ] |")
    out += ["", "**Таблица Д.4 — Структура бюджета: ориентир ННС (C1) и проект**", "",
            "| Статья | Ориентир ННС, % | Проект, % |", "|---|---:|---:|"]
    for name, sh in REFERENCE_SHARES.items():
        out.append(f"| {name} | {dec(sh)} | [ЗАПОЛНИТЬ: после ввода цен — лист «Свод» в budget.xlsx] |")
    return "\n".join(out) + "\n"


def main() -> None:
    build_workbook(HERE / "budget.xlsx")
    (HERE / "budget_tables.md").write_text(markdown_tables(), encoding="utf-8")
    print("wrote", HERE / "budget.xlsx", "and", HERE / "budget_tables.md")


if __name__ == "__main__":
    main()
