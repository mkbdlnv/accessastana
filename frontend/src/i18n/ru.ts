import type { Dict } from './en';

const ru: Dict = {
  'app.title': 'AccessAstana',
  'app.subtitle': 'Пешеходная доступность с учётом климата',
  'lang.label': 'Язык',

  'controls.city': 'Город',
  'controls.category': 'Категория',
  'controls.season': 'Сезон',

  'category.school': 'Школы',
  'category.kindergarten': 'Детские сады',
  'category.clinic': 'Поликлиники',
  'category.pharmacy': 'Аптеки',
  'category.transit_stop': 'Остановки',
  'category.grocery': 'Продуктовые магазины',
  'category.park': 'Парки',
  'category.index': '15-минутный индекс',

  'season.summer': 'Лето',
  'season.winter': 'Зима',
  'season.winter_severe': 'Сильный мороз',
  'season.hint': 'Скорость ходьбы {v} км/ч, порог {n} мин',

  'tabs.overview': 'Доступность',
  'tabs.scenario': 'Сценарий',
  'tabs.optimize': 'Оптимизация',

  'status.loading': 'Загрузка…',
  'status.error': 'Ошибка',
  'status.retry': 'Повторить',
  'status.noCells': 'Нет ячеек для выбранных параметров.',

  'legend.minutes': 'Время пешком, мин',
  'legend.index': 'Доля категорий в пределах {n} мин',
  'legend.noData': 'Недоступно (> 60 мин)',
  'legend.noValue': 'Нет данных',
  'legend.threshold': 'Порог: {n} мин',
  'legend.more': 'более {n} мин',

  'tooltip.value': 'Значение',
  'tooltip.minutes': '{n} мин',
  'tooltip.population': 'Население',
  'tooltip.before': 'До',
  'tooltip.after': 'После',
  'tooltip.gain': 'Прирост охвата населения',
  'tooltip.facility': 'Объект',
  'tooltip.removeHint': 'Нажмите, чтобы отметить для удаления',

  'districts.title': 'Районы',
  'districts.name': 'Район',
  'districts.population': 'Население',
  'districts.index': 'Индекс',
  'districts.within': '≤ {n} мин',
  'districts.mean': 'Среднее, мин',
  'districts.cityTotal': 'Город в целом',
  'districts.showOutlines': 'Показать границы районов',
  'districts.indexHint': 'Выберите категорию объектов, чтобы увидеть доли в пределах порога.',

  'scenario.help':
    'Включите режим редактирования, нажмите на карту, чтобы добавить предлагаемый объект, нажмите на существующий объект (маленькая точка), чтобы отметить его для удаления, затем нажмите «Рассчитать».',
  'scenario.editMode': 'Режим редактирования',
  'scenario.added': 'Предлагаемых объектов: {n}',
  'scenario.removed': 'Отмечено для удаления: {n}',
  'scenario.compute': 'Рассчитать',
  'scenario.computing': 'Расчёт…',
  'scenario.reset': 'Сбросить',
  'scenario.needCategory': 'Сценарии и оптимизация работают с одной категорией объектов. Выберите категорию вместо индекса.',
  'scenario.newFacility': 'Новый объект {n}',
  'scenario.changed': 'Изменившихся ячеек: {n} (обведены на карте)',
  'scenario.existing': 'Существующие объекты',
  'scenario.proposed': 'Предлагаемые',
  'scenario.toRemove': 'К удалению',
  'scenario.nothing': 'Сначала добавьте или удалите хотя бы один объект.',

  'metrics.metric': 'Показатель',
  'metrics.before': 'До',
  'metrics.after': 'После',
  'metrics.delta': 'Изменение',
  'metrics.population': 'Население в пределах порога',
  'metrics.share': 'Доля населения',
  'metrics.mean': 'Среднее время пешком, мин',
  'metrics.pp': 'п.п.',

  'optimize.help': 'Поиск k новых мест, которые сильнее всего улучшают доступность для выбранной категории и сезона.',
  'optimize.k': 'Количество новых объектов (k)',
  'optimize.method': 'Метод',
  'optimize.max_covering': 'Максимальное покрытие (макс. населения в пределах порога)',
  'optimize.p_median': 'p-медиана (мин. среднего времени пешком)',
  'optimize.run': 'Оптимизировать',
  'optimize.running': 'Решение…',
  'optimize.status': 'Статус решателя: {s}, {t} с',
  'optimize.locations': 'Рекомендуемые места',
  'optimize.gain': 'Прирост охвата',
  'optimize.clear': 'Очистить результат',


  'report.download': 'Скачать отчёт PDF',
  'footer.sources': 'Данные',
  'footer.basemap': 'Подложка',
};

export default ru;
