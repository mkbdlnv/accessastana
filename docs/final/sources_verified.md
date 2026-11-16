# AccessAstana — проверенный список источников

Проверка выполнена 16.11.2026. Основные инструменты: Crossref REST API (`https://api.crossref.org/works/<DOI>`), DataCite/doi.org (content negotiation), OpenAlex/Semantic Scholar (тексты аннотаций), официальные страницы издателей и организаций. Для п. 12 прочитан полный текст статьи (открытая версия, CC BY 4.0, из репозитория NTNU Open / NVA).

Правило: в «Ключевых фактах» указано только то, что действительно прочитано (аннотация, полный текст или официальная страница). Если читались только метаданные, это сказано прямо.

Оформление записей следует шаблону, заданному в задании («Авторы. Заглавие // Журнал. – Год. – Vol. – No. – P./Art. – DOI»). При четырёх и более авторах названы первые три и добавлено «[et al.]».

---

## Проверенные источники

### А. Концепция «15-минутного города» и доступность

1. Moreno C., Allam Z., Chabaud D., Gall C., Pratlong F. Introducing the “15-Minute City”: Sustainability, Resilience and Place Identity in Future Post-Pandemic Cities // Smart Cities. – 2021. – Vol. 4, No. 1. – P. 93–111. – DOI: 10.3390/smartcities4010006.
   - Как проверено: https://api.crossref.org/works/10.3390/smartcities4010006; аннотация через Semantic Scholar API. Открытый доступ (CC BY).
   - Ключевые факты (аннотация): концепция «15-минутного города» была впервые предложена Карлосом Морено в 2016 г. и вновь стала востребованной во время пандемии COVID-19. В статье она описана как «хроно-урбанизм» (“chrono-urbanism”).

2. Pozoukidou G., Chatziyiannaki Z. 15-Minute City: Decomposing the New Urban Planning Eutopia // Sustainability. – 2021. – Vol. 13, No. 2. – Art. 928. – DOI: 10.3390/su13020928.
   - Как проверено: Crossref (поиск, DOI 10.3390/su13020928); аннотация через OpenAlex.
   - Ключевые факты (аннотация): рассмотрены три города, принявшие эту модель, по трём критериям: inclusion, safety, health. Авторы считают, что подход «не является радикально новой идеей», поскольку опирается на давно сложившиеся принципы планирования. Он смещает акцент с доступности городских функций из района на их близость внутри района.

3. Logan T. M., Hobbs M. H., Conrow L. C. [et al.] The x-minute city: Measuring the 10, 15, 20-minute city and an evaluation of its use for sustainable urban design // Cities. – 2022. – Vol. 131. – Art. 103924. – DOI: 10.1016/j.cities.2022.103924.
   - Как проверено: Crossref (поиск, DOI 10.1016/j.cities.2022.103924). Журнал — **Cities**, это подтверждено. Полный список авторов: Logan T.M., Hobbs M.H., Conrow L.C., Reid N.L., Young R.A., Anderson M.J.
   - Ключевые факты: прочитаны только метаданные (аннотация через API недоступна). Ссылаться только как на работу о метриках x-minute city, не приписывая ей конкретных цифр.

4. Geurs K. T., van Wee B. Accessibility evaluation of land-use and transport strategies: review and research directions // Journal of Transport Geography. – 2004. – Vol. 12, No. 2. – P. 127–140. – DOI: 10.1016/j.jtrangeo.2003.10.005.
   - Как проверено: Crossref (поиск, DOI 10.1016/j.jtrangeo.2003.10.005).
   - Ключевые факты: прочитаны только метаданные. Широко известное содержание (четыре компонента доступности) по первоисточнику не сверялось. Если оно нужно в отчёте, сначала проверить по тексту статьи.

5. Hansen W. G. How Accessibility Shapes Land Use // Journal of the American Institute of Planners. – 1959. – Vol. 25, No. 2. – P. 73–76. – DOI: 10.1080/01944365908978307.
   - Как проверено: Crossref (поиск, DOI 10.1080/01944365908978307); аннотация через OpenAlex.
   - Ключевые факты (аннотация): автор предлагает «операциональное определение» доступности и метод определения её пространственных паттернов в метрополиях. Доступность и наличие свободной земли используются как основа модели жилого землепользования.

6. Weiss D. J., Nelson A., Gibson H. S. [et al.] A global map of travel time to cities to assess inequalities in accessibility in 2015 // Nature. – 2018. – Vol. 553, No. 7688. – P. 333–336. – DOI: 10.1038/nature25181.
   - Как проверено: Crossref (поиск, DOI 10.1038/nature25181), 22 автора.
   - Ключевые факты: прочитаны только метаданные (страница Nature требует авторизации). Цифры из статьи не цитировать без сверки.

7. Willberg E., Fink C., Toivonen T. The 15-minute city for all? – Measuring individual and temporal variations in walking accessibility // Journal of Transport Geography. – 2023. – Vol. 106. – Art. 103521. – DOI: 10.1016/j.jtrangeo.2022.103521.
   - Как проверено: Crossref (DOI 10.1016/j.jtrangeo.2022.103521); аннотация через OpenAlex. Открытый доступ (CC BY). *(найдено по п. 26b — зимняя пешеходная доступность)*
   - Ключевые факты (аннотация): скорости ходьбы записаны в Хельсинкском столичном регионе (Финляндия) в сухой и зимний сезоны, затем встроены в модель доступности. По отдельности наибольший эффект даёт суточная вариация (часы работы), а не сезон или возраст. В худшем комбинированном сценарии только 34 % пожилых людей имеют 15-минутный пеший доступ к ближайшему продуктовому магазину, при базовом уровне 93 %.

### Б. Размещение объектов (location-allocation)

8. Church R., ReVelle C. The maximal covering location problem // Papers of the Regional Science Association. – 1974. – Vol. 32, No. 1. – P. 101–118. – DOI: 10.1007/BF01942293.
   - Как проверено: Crossref (поиск, DOI 10.1007/bf01942293).
   - Ключевые факты: только метаданные. Это первоисточник постановки MCLP.

9. Hakimi S. L. Optimum Locations of Switching Centers and the Absolute Centers and Medians of a Graph // Operations Research. – 1964. – Vol. 12, No. 3. – P. 450–459. – DOI: 10.1287/opre.12.3.450.
   - Как проверено: Crossref (поиск, DOI 10.1287/opre.12.3.450); аннотация через OpenAlex.
   - Ключевые факты (аннотация): понятия «центра» и «медианной вершины» графа обобщены до «absolute center» и «absolute median» взвешенного графа. Показано, что оптимальное положение switching center всегда находится в вершине сети, а оптимальное положение полицейского участка — не обязательно на перекрёстке.

10. ReVelle C. S., Swain R. W. Central Facilities Location // Geographical Analysis. – 1970. – Vol. 2, No. 1. – P. 30–42. – DOI: 10.1111/j.1538-4632.1970.tb00142.x.
    - Как проверено: Crossref (поиск, DOI 10.1111/j.1538-4632.1970.tb00142.x).
    - Ключевые факты: только метаданные. Стандартная ссылка на ЦЛП-формулировку p-median.

### В. OpenStreetMap и инструменты

11. Boeing G. OSMnx: New methods for acquiring, constructing, analyzing, and visualizing complex street networks // Computers, Environment and Urban Systems. – 2017. – Vol. 65. – P. 126–139. – DOI: 10.1016/j.compenvurbsys.2017.05.004.
    - Как проверено: Crossref (поиск, DOI 10.1016/j.compenvurbsys.2017.05.004); аннотация через Semantic Scholar.
    - Ключевые факты (аннотация): OSMnx выполняет автоматическую загрузку и построение уличной сети из OpenStreetMap, алгоритмическую коррекцию топологии, сохранение (shapefile, GraphML, SVG) и анализ сети, включая расчёт маршрутов.

12. Barrington-Leigh C., Millard-Ball A. The world’s user-generated road map is more than 80% complete // PLOS ONE. – 2017. – Vol. 12, No. 8. – Art. e0180698. – DOI: 10.1371/journal.pone.0180698.
    - Как проверено: Crossref (поиск, DOI 10.1371/journal.pone.0180698); аннотация через OpenAlex.
    - Примечание: в 2019 г. опубликована поправка: Correction // PLOS ONE. – 2019. – Vol. 14, No. 10. – Art. e0224742. – DOI: 10.1371/journal.pone.0224742. Её можно упомянуть при необходимости.
    - Ключевые факты (аннотация): по оценке авторов, глобально OSM «∼83% complete». Более чем в 40 % стран уличная сеть картирована полностью. Использованы два независимых метода: визуальная оценка по спутниковым снимкам с MRP-моделью и аппроксимация кривых насыщения.

13. Haklay M. How Good is Volunteered Geographical Information? A Comparative Study of OpenStreetMap and Ordnance Survey Datasets // Environment and Planning B: Planning and Design. – 2010. – Vol. 37, No. 4. – P. 682–703. – DOI: 10.1068/b35097.
    - Как проверено: Crossref (поиск, DOI 10.1068/b35097); аннотация через OpenAlex.
    - Ключевые факты (аннотация): сравнение OSM с данными Ordnance Survey для Лондона и Англии. Позиционная точность OSM в среднем около 6 м. Перекрытие объектов категории motorway — примерно 80 %.

14. Virtanen P., Gommers R., Oliphant T. E. [et al.] SciPy 1.0: fundamental algorithms for scientific computing in Python // Nature Methods. – 2020. – Vol. 17, No. 3. – P. 261–272. – DOI: 10.1038/s41592-019-0686-2.
    - Как проверено: https://api.crossref.org/works/10.1038/s41592-019-0686-2 (112 авторов в записи).
    - Ключевые факты (аннотация): SciPy — open-source библиотека для научных вычислений на Python, впервые выпущенная в 2001 г.

15. Perron L., Furnon V. OR-Tools [Электронный ресурс] : software, version v9.12 / Google. – 2025. – URL: https://developers.google.com/optimization/ (дата обращения: 16.11.2026).
    - Как проверено: официальная страница «How to cite OR-Tools and its solvers»: https://developers.google.com/optimization/support/cite. Последний релиз на GitHub — v9.15 (12.01.2026, https://api.github.com/repos/google/or-tools/releases/latest).
    - Ключевые факты: Google рекомендует такую BibTeX-запись: `@software{ortools, title = {OR-Tools}, version = { v9.12 }, author = {Laurent Perron and Vincent Furnon}, organization = {Google}, url = {https://developers.google.com/optimization/}, date = { 2025-02-17 }}`. Версию и дату следует заменить на фактически использованную версию (см. `pip show ortools`). Для CP-SAT и Routing Library на той же странице даны отдельные записи.

16. H3: Hexagonal hierarchical geospatial indexing system [Электронный ресурс] : документация. – URL: https://h3geo.org/docs/ (дата обращения: 16.11.2026).
    - Как проверено: https://h3geo.org/docs/ (страница «Introduction | H3»).
    - Ключевые факты: на сайте H3 описан как «a geospatial indexing system that partitions the world into hexagonal cells». Там же сказано: «H3 was developed to address the challenges of Uber's data science needs». Таблица разрешений находится по адресу https://h3geo.org/docs/core-library/restable.

### Г. Климат и ходьба зимой

17. Fossum M., Ryeng E. O. The walking speed of pedestrians on various pavement surface conditions during winter // Transportation Research Part D: Transport and Environment. – 2021. – Vol. 97. – Art. 102934. – DOI: 10.1016/j.trd.2021.102934.
    - Как проверено: https://api.crossref.org/works/10.1016/j.trd.2021.102934. Полный текст прочитан по открытой версии (Published Version, CC BY 4.0) из NTNU Open: https://hdl.handle.net/11250/2978451.
    - Ключевые факты (полный текст): данные собраны в Тронхейме (Норвегия) с ноября 2019 по март 2020 г. при температуре от −12 до +8 °C (разд. 2.2, с. 6). Средние скорости на ровной поверхности приведены в Table 3 на с. 11 (подробно — в разделе ответов ниже). На чистом льду время в пути примерно на 2 мин/км больше, чем на асфальте (аннотация).

18. Liang S., Leng H., Yuan Q., Wang B., Yuan C. How does weather and climate affect pedestrian walking speed during cool and cold seasons in severely cold areas? // Building and Environment. – 2020. – Vol. 175. – Art. 106811. – DOI: 10.1016/j.buildenv.2020.106811.
    - Как проверено: Crossref (поиск, DOI 10.1016/j.buildenv.2020.106811); аннотация через Semantic Scholar.
    - Ключевые факты (аннотация): видеонаблюдение с компьютерным зрением. Средняя скорость ходьбы отрицательно коррелирует с мгновенной apparent temperature, причём эффект проявляется с временным лагом. На заснеженной поверхности средняя скорость примерно на 0,102 м/с ниже, чем на чистой.
    - **Внимание:** в аннотации город исследования (Харбин) **не назван**. Указывать Харбин только после сверки с полным текстом.

19. Knoblauch R. L., Pietrucha M. T., Nitzburg M. Field Studies of Pedestrian Walking Speed and Start-Up Time // Transportation Research Record: Journal of the Transportation Research Board. – 1996. – Vol. 1538, No. 1. – P. 27–38. – DOI: 10.1177/0361198196153800104.
    - Как проверено: https://api.crossref.org/works/10.1177/0361198196153800104 (полная аннотация). Действующий DOI имеет префикс SAGE **10.1177/0361198196153800104**. DOI вида 10.3141/1538-04 не подтверждён, использовать его нельзя.
    - Ключевые факты: см. раздел ответов (п. 14) ниже.

20. Osczevski R., Bluestein M. The New Wind Chill Equivalent Temperature Chart // Bulletin of the American Meteorological Society. – 2005. – Vol. 86, No. 10. – P. 1453–1458. – DOI: 10.1175/BAMS-86-10-1453.
    - Как проверено: Crossref (поиск, DOI 10.1175/bams-86-10-1453); аннотация через OpenAlex.
    - Ключевые факты (аннотация): формула, по которой в США и Канаде выражают совместное действие ветра и низкой температуры, была изменена в ноябре 2001 г. Новая формула основана на модели теплового потока с наветренной стороны цилиндра размером с голову, движущегося со скоростью ходьбы против ветра. Сама формула WCI в аннотации не приведена: при цитировании формулы ссылаться на полный текст (с указанием страницы после сверки) или на документ ECCC.

21. Environment and Climate Change Canada. Wind chill and the Wind Chill Index [Электронный ресурс]. – URL: https://www.canada.ca/en/services/environment/weather/severeweather/wind-chill-index.html (дата обращения: 16.11.2026).
    - Как проверено: страница прочитана 16.11.2026, в «Page details» указана дата 2025-12-16.
    - Ключевые факты: шкала риска приведена в разделе ответов (п. 15). Формулы на этой странице нет.

22. Hersbach H., Bell B., Berrisford P. [et al.] The ERA5 global reanalysis // Quarterly Journal of the Royal Meteorological Society. – 2020. – Vol. 146, No. 730. – P. 1999–2049. – DOI: 10.1002/qj.3803.
    - Как проверено: https://api.crossref.org/works/10.1002/qj.3803 (43 автора).
    - Ключевые факты (аннотация): ERA5 выпускает ECMWF в рамках Copernicus Climate Change Service (C3S). Горизонтальное разрешение 31 км (у ERA-Interim было 80 км), выдача данных ежечасная. Модель основана на IFS Cy41r2.

23. Zippenfenig P. Open-Meteo.com Weather API [Электронный ресурс] : software. – Zenodo, 2024. – DOI: 10.5281/zenodo.7970649. – URL: https://open-meteo.com/ (дата обращения: 16.11.2026).
    - Как проверено: файл CITATION.cff в официальном репозитории (https://raw.githubusercontent.com/open-meteo/open-meteo/main/CITATION.cff) и разрешение DOI через doi.org (DataCite).
    - Ключевые факты: в CITATION.cff сказано: «If you are using the Open-Meteo weather API, please cite using the following metadata». Автор — Patrick Zippenfenig. DOI 10.5281/zenodo.7970649 описан как «Latest release of the Open-Meteo weather API», лицензия CC-BY-4.0. DOI указывает на последний выпуск, и на момент проверки DataCite выдаёт дату 2024-12-31. По README данные API распространяются под CC BY 4.0, код — под AGPLv3.

### Д. Население

24. Kontur. Kazakhstan: Population Density for 400m H3 Hexagons [Электронный ресурс] : dataset. – Humanitarian Data Exchange (HDX), 2023. – URL: https://data.humdata.org/dataset/kontur-population-kazakhstan (дата обращения: 16.11.2026).
    - Как проверено: HDX CKAN API https://data.humdata.org/api/3/action/package_show?id=kontur-population-kazakhstan (веб-страница вернула 403, использованы метаданные API).
    - Ключевые факты: организация — Kontur. Лицензия — «Creative Commons Attribution International (CC BY)». Файл ресурса — `kontur_population_KZ_20231101.gpkg` (last_modified 2023-10-31); есть и более ранний `kontur_population_KZ_20220630.gpkg`. Указанный в задании выпуск 2023-11-01 подтверждён. Методология: население получено объединением GHSL и Facebook HRSL с OSM-ограничениями (в данных также используются Microsoft Buildings и Copernicus Land Cover) на гексагонах H3 размером 400 м. Поля: `h3`, `population`, `geom` (EPSG:3857). Оговорка источника: набор «primarily designed to support visualization behind https://disaster.ninja project and may not be suitable for your specific needs».

### Е. Методология проекта и стандарты

25. Schwaber K., Sutherland J. The 2020 Scrum Guide [Электронный ресурс]. – 2020. – URL: https://scrumguides.org/scrum-guide.html (дата обращения: 16.11.2026).
    - Как проверено: https://scrumguides.org/scrum-guide.html
    - Ключевые факты: версия от ноября 2020 г., лицензия CC BY-SA 4.0. Определение: «Scrum is a lightweight framework that helps people, teams and organizations generate value through adaptive solutions for complex problems».

26. Beck K., Beedle M., van Bennekum A. [et al.] Manifesto for Agile Software Development [Электронный ресурс]. – 2001. – URL: https://agilemanifesto.org/ (дата обращения: 16.11.2026).
    - Как проверено: https://agilemanifesto.org/ («© 2001, the above authors»; 17 подписантов).
    - Ключевые факты: четыре ценности: «Individuals and interactions over processes and tools»; «Working software over comprehensive documentation»; «Customer collaboration over contract negotiation»; «Responding to change over following a plan».

27. ГОСТ 7.32–2017. Система стандартов по информации, библиотечному и издательскому делу. Отчет о научно-исследовательской работе. Структура и правила оформления : межгосударственный стандарт : введен впервые с 01.07.2018 взамен ГОСТ 7.32–2001 / Федеральное агентство по техническому регулированию и метрологии. – Москва : Стандартинформ, 2017.
    - Как проверено: https://legalacts.ru/doc/gost-732-2017-mezhgosudarstvennyi-standart-sistema-standartov-po-informatsii-bibliotechnomu/
    - Ключевые факты: англ. название — «System of standards on information, librarianship and publishing. The research report. Structure and rules of presentation». Введён в действие с 01.07.2018 приказом Росстандарта от 24.10.2017 № 1494-ст.
    - Примечание: выходные данные издания («Москва : Стандартинформ, 2017») я не проверял. Указывать их только после сверки с титулом стандарта, иначе ограничиться обозначением и заглавием.

28. ГОСТ Р 7.0.100–2018. Система стандартов по информации, библиотечному и издательскому делу. Библиографическая запись. Библиографическое описание. Общие требования и правила составления : национальный стандарт Российской Федерации : введен 01.07.2019.
    - Как проверено: методические рекомендации Научной библиотеки ГИТИС (2022), https://www.gitis.net/upload/iblock/d8d/ioszkapyc6i6ky000o67ui1p1ykla9ez/gost_r_7.0.100–2018.pdf
    - Ключевые факты: заглавие «Библиографическая запись. Библиографическое описание. Общие требования и правила составления» подтверждено. Стандарт утверждён приказом Росстандарта № 1050-ст от 03.12.2018 и действует с 01.07.2019. На правила составления библиографических *ссылок* он не распространяется: для них действует ГОСТ Р 7.0.5–2008.
    - Примечание: префикс «Система стандартов по информации, библиотечному и издательскому делу» добавлен по аналогии с серией СИБИД, по титулу самого стандарта я его не проверял.

### Ж. Дополнительно (п. 26): Казахстан / Астана и сезонная доступность

29. Atakhanova Z., Baigaliyeva M. Kazakhstan’s Infrastructure Programs and Urban Sustainability Analysis of Astana // Urban Science. – 2025. – Vol. 9, No. 4. – Art. 100. – DOI: 10.3390/urbansci9040100.
    - Как проверено: https://api.crossref.org/works/10.3390/urbansci9040100 (с аннотацией). Открытый доступ (CC BY).
    - Ключевые факты (аннотация): Астана — столица с 1997 г. Благодаря крупным государственным инвестициям в городе достигнуты низкий уровень бедности, высокий доход и «broad access to social services». Строительный бум привёл к потере «green and blue lands». Это контекстная работа об Астане, а не исследование пешеходной доступности.

30. Kontsevik G., Gubina A., Tikhevich V., Mityagin S. Environment-framed networks: seasonal reconfiguration of service accessibility in Arctic transport systems // Applied Network Science. – 2026. – Vol. 11, No. 1. – Art. 35. – DOI: 10.1007/s41109-026-00783-6.
    - Как проверено: Crossref (DOI 10.1007/s41109-026-00783-6, с аннотацией).
    - Ключевые факты (аннотация): модель учитывает сезонную, зависящую от температуры реконфигурацию транспортной сети, включая ледовые дороги, в четырёх арктических регионах. До 40 % поселений меняют поставщика услуг, 15–20 % временно изолированы на 2–4 месяца. Работа о региональном (не пешеходном) транспорте: использовать только как пример сезонного моделирования доступности.

(Также зимняя доступность — см. п. 7, Willberg et al., 2023.)

---

## Не подтверждено — не цитировать

1. **«Is Almaty a 15-minute city? Walking access to six everyday places from 170,838 buildings in the city's eight districts»**. Запись найдена только на Zenodo (https://zenodo.org/records/23758495, DOI 10.5281/zenodo.23758495), с указанием «Central Asian Scientific Journal», 2026, vol. 1, no. 4(32), pp. 643–650. Рецензируемость журнала и полный текст проверить не удалось, в Crossref и Semantic Scholar записи нет. Не цитировать как рецензируемую работу.
2. **Рецензируемые статьи о пешеходной доступности / 15-минутном городе именно в Астане (Нур-Султане)**: в Crossref и при веб-поиске таких работ не найдено. Найденная Abdrassilova G., Murzagaliyeva E. (2020, DOI 10.17512/bozpe.2020.1.04, Алматы) посвящена архитектурной доступности (accessibility as a quality criterion of the architectural environment), а не сетевой пешеходной доступности. Её содержание не читалось, поэтому в список не включена.
3. **DOI 10.3141/1538-04 для Knoblauch et al. (1996)**: не подтверждён. Действующий DOI — 10.1177/0361198196153800104.
4. **Отчёт FHWA-RD-00-103 как источник скоростей ходьбы**: по этому номеру опубликован другой отчёт, «Pedestrian Crosswalk Case Studies: Richmond, Virginia; Buffalo, New York; Stillwater, Minnesota» (August 2001, https://www.fhwa.dot.gov/publications/research/safety/00103/00103.pdf). Он не содержит данных Knoblauch о средних скоростях. Не ссылаться на него как на источник скоростей ходьбы.
5. **Харбин как место исследования Liang et al. (2020)**: в аннотации не указан (см. п. 18 выше). Не упоминать без сверки с полным текстом.
6. **Формула WCI с конкретной страницей Osczevski & Bluestein (2005)**: сам источник подтверждён, но текст формулы и номер страницы не сверены (полный текст закрыт).
7. **Конкретные цифры из Weiss et al. (2018), Logan et al. (2022), Geurs & van Wee (2004), Church & ReVelle (1974), ReVelle & Swain (1970)**: сами источники подтверждены, но их содержание сверх метаданных не читалось. Цитировать только как общую ссылку.

---

## Ответы на конкретные вопросы

### П. 12 — Fossum & Ryeng (2021): скорости по типам покрытия

Источник: открытая версия статьи (Published Version, CC BY 4.0), https://hdl.handle.net/11250/2978451. Данные собраны в Тронхейме, ноябрь 2019 — март 2020, −12…+8 °C. Измерения проводились вручную секундомером на отрезке в среднем 18,2 м (с. 3); всего 2 498 наблюдений (с. 4).

**Table 3 (с. 11), «Average walking speeds…», ровная поверхность (Model 1, вся выборка, N = 1 631).** Скорости — предсказанные средние (predictive margins модели OLS), а не сырые средние по группам:

| Покрытие | Средняя скорость, м/с | Время, с/км | Δ к асфальту, с/км | N наблюдений (Table A4 / Fig. 6) |
|---|---|---|---|---|
| Asphalt | 1.511 | 662 | 0 (base) | 459 |
| Compact snow | 1.403 | 713 | +51 (+7.7%) | 437 |
| Loose snow (2–8 cm) | 1.378 | 726 | +64 (+9.7%) | 275 |
| Gritted ice | 1.361 | 735 | +73 (+11.0%) | 157 |
| Ice (clean ice) | 1.257 | 796 | +134 (+20.2%) | 303 |

- Без пожилых пешеходов (Table 3, «Flat ground*»): 1.607 / 1.499 / 1.476 / 1.467 / 1.351 м/с.
- Текст статьи (разд. 3.3, с. 14): «Walking on compact snow, on average, reduces the walking speed of pedestrians by 0.11 m/s compared to walking on asphalt… loose snow… or gritted ice, the average walking speed is 0.13 m/s and 0.15 m/s slower… On an ice-covered surface, the average walking speed is 0.26 m/s slower than on an asphalt surface.»
- Описательная статистика (Table A3 / A5, с. 18–19): средняя скорость по всей выборке на ровной поверхности 1.40 м/с (SD 0.26, min 0.48, max 2.17, N = 1 631).
- Прочие эффекты (Model 1, разд. 3.3, с. 10): −0.01 м/с на каждый +1 °C в наблюдённом интервале (−12…8 °C), то есть в холод ходят немного быстрее. Мужчины быстрее женщин на 0.08 м/с.

### П. 14 — Knoblauch et al. (1996): что реально сказано и верно ли «mean free-flow walking speeds in the 1.25–1.51 m/s range»

**Аннотация статьи (Crossref, DOI 10.1177/0361198196153800104), дословно:**
> «The 15th-percentile walking speed for younger pedestrians (ages 14 to 64) was 1.25 m/sec (4.09 ft/sec); for older pedestrians (ages 65 and over) it was 0.97 m/sec (3.19 ft/sec). For design purposes values of 1.22 m/sec (4 ft/sec) for younger pedestrians and 0.91 m/sec (3 ft/sec) for older pedestrians are appropriate.»

Измерения проводились на 16 регулируемых пешеходных переходах в четырёх городах.

**Средние скорости** в аннотации **не приведены**. Они есть во вторичных источниках:
- Road Engineering Journal (TranSafety), 01.10.1997, «Study Compares Older and Younger Pedestrian Walking Speeds», https://www.usroads.com/journals/p/rej/9710/re971001/: «The average walking speed for older pedestrians was 4.11 feet per second, compared with 4.95 for younger pedestrians». В метрах в секунду это ≈1.25 и ≈1.51 м/с (пересчёт мой: ×0.3048). Наблюдалось 7 123 пешехода, из них 3 665 в возрасте 65+.
- Fossum & Ryeng (2021), Table 4, с. 12, со ссылкой на Knoblauch et al. (1996): younger «dry» = 1.47, «snow» = 1.60, «low temp» = 1.60, «high temp» = 1.48; older «dry» = 1.23, «snow» = 1.34, «low temp» = 1.34, «high temp» = 1.24 м/с. По Fossum & Ryeng (с. 2), при −12.8…6.0 °C пешеходы шли примерно на 0.1 м/с быстрее, чем при температуре выше 14.5 °C.

**Вывод.** Диапазон 1.25–1.51 м/с численно совпадает со средними скоростями пожилых (≈1.25) и молодых (≈1.51) пешеходов. Но формулировка в конфиге неточна в трёх местах:
1. Это скорости **перехода улицы на регулируемых перекрёстках**, а не «free-flow» ходьба по тротуару.
2. 1.25 — это **среднее для пешеходов 65+**, а не нижняя граница «общих» средних. При этом 1.25 м/с в аннотации — это **15-й процентиль для молодых**, так что легко спутать.
3. Средние значения взяты из вторичного источника, в аннотации их нет.

Предлагаемая корректная формулировка: «Knoblauch et al. (1996) report mean crosswalk walking speeds of about 1.51 m/s (4.95 ft/s) for pedestrians aged 14–64 and 1.25 m/s (4.11 ft/s) for pedestrians 65+, with 15th-percentile speeds of 1.25 and 0.97 m/s and recommended design values of 1.22 and 0.91 m/s». Если первоисточник средних не сверен, безопаснее опираться только на цифры из аннотации (15-й процентиль и проектные значения).

Отчёт FHWA-RD-00-103 источником этих цифр **не является** (см. «Не подтверждено», п. 4).

### П. 15 — ECCC: пороги Wind Chill Index

Страница: https://www.canada.ca/en/services/environment/weather/severeweather/wind-chill-index.html («Wind chill and the Wind Chill Index», Page details: 2025-12-16, прочитана 16.11.2026). Шкала риска:

| Wind chill | Риск | Ключевая формулировка |
|---|---|---|
| 0 to −9 | Low | Slight increase in discomfort |
| −10 to −27 | Moderate | Discomfort; risk of hypothermia and frostbite after long periods outdoors without adequate protection |
| **−28 to −39** | **High** | **«Exposed skin can freeze in 10 to 30 minutes»**; high risk of frostnip or frostbite; check face and extremities for numbness or whiteness |
| −40 to −47 | Very high | «Exposed skin can freeze in 5 to 10 minutes» |
| −48 to −54 | Severe | «Exposed skin can freeze in 2 to 5 minutes» |
| −55 or colder | Extreme | «Exposed skin can freeze in less than 2 minutes»; «DANGER! outdoor conditions are hazardous» |

Примечание на странице: при устойчивом ветре свыше 50 км/ч обморожение может наступить быстрее, чем указано.

**Вывод:** утверждение проекта «от −28 до −39 — exposed skin can freeze in 10 to 30 minutes» **подтверждено** и соответствует категории «High risk». Формулы WCI на этой странице нет. Источник формулы — Osczevski & Bluestein (2005), п. 20, но страницу с формулой нужно сверить по полному тексту.
