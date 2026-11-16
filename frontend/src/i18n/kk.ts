import type { Dict } from './en';

const kk: Dict = {
  'app.title': 'AccessAstana',
  'app.subtitle': 'Климатты ескеретін жаяу қолжетімділік',
  'lang.label': 'Тіл',

  'controls.city': 'Қала',
  'controls.category': 'Санат',
  'controls.season': 'Маусым',

  'category.school': 'Мектептер',
  'category.kindergarten': 'Балабақшалар',
  'category.clinic': 'Емханалар',
  'category.pharmacy': 'Дәріханалар',
  'category.transit_stop': 'Аялдамалар',
  'category.grocery': 'Азық-түлік дүкендері',
  'category.park': 'Саябақтар',
  'category.index': '15 минуттық индекс',

  'season.summer': 'Жаз',
  'season.winter': 'Қыс',
  'season.winter_severe': 'Қатты аяз',
  'season.hint': 'Жүру жылдамдығы {v} км/сағ, шекті мән {n} мин',

  'tabs.overview': 'Қолжетімділік',
  'tabs.scenario': 'Сценарий',
  'tabs.optimize': 'Оңтайландыру',

  'status.loading': 'Жүктелуде…',
  'status.error': 'Қате',
  'status.retry': 'Қайталау',
  'status.noCells': 'Таңдалған параметрлер бойынша ұяшықтар жоқ.',

  'legend.minutes': 'Жаяу жүру уақыты, мин',
  'legend.index': '{n} мин ішіндегі санаттар үлесі',
  'legend.noData': 'Қолжетімсіз (> 60 мин)',
  'legend.noValue': 'Деректер жоқ',
  'legend.threshold': 'Шекті мән: {n} мин',
  'legend.more': '{n} минуттан көп',

  'tooltip.value': 'Мәні',
  'tooltip.minutes': '{n} мин',
  'tooltip.population': 'Халық саны',
  'tooltip.before': 'Дейін',
  'tooltip.after': 'Кейін',
  'tooltip.gain': 'Қосымша қамтылған халық',
  'tooltip.facility': 'Нысан',
  'tooltip.removeHint': 'Жоюға белгілеу үшін басыңыз',

  'districts.title': 'Аудандар',
  'districts.name': 'Аудан',
  'districts.population': 'Халық саны',
  'districts.index': 'Индекс',
  'districts.within': '≤ {n} мин',
  'districts.mean': 'Орташа, мин',
  'districts.cityTotal': 'Қала бойынша барлығы',
  'districts.showOutlines': 'Аудан шекараларын көрсету',
  'districts.indexHint': 'Шекті мән ішіндегі үлестерді көру үшін нысан санатын таңдаңыз.',

  'scenario.help':
    'Өңдеу режимін қосыңыз: ұсынылатын нысанды қосу үшін картаны басыңыз, бар нысанды (кішкене нүкте) жоюға белгілеу үшін соны басыңыз, содан кейін «Есептеу» батырмасын басыңыз.',
  'scenario.editMode': 'Өңдеу режимі',
  'scenario.added': 'Ұсынылған нысандар: {n}',
  'scenario.removed': 'Жоюға белгіленгені: {n}',
  'scenario.compute': 'Есептеу',
  'scenario.computing': 'Есептелуде…',
  'scenario.reset': 'Тазарту',
  'scenario.needCategory': 'Сценарийлер мен оңтайландыру бір нысан санатымен жұмыс істейді. Индекстің орнына санатты таңдаңыз.',
  'scenario.newFacility': 'Жаңа нысан {n}',
  'scenario.changed': 'Өзгерген ұяшықтар: {n} (картада контурмен белгіленген)',
  'scenario.existing': 'Бар нысандар',
  'scenario.proposed': 'Ұсынылған',
  'scenario.toRemove': 'Жоюға',
  'scenario.nothing': 'Алдымен кемінде бір нысанды қосыңыз немесе жойыңыз.',

  'metrics.metric': 'Көрсеткіш',
  'metrics.before': 'Дейін',
  'metrics.after': 'Кейін',
  'metrics.delta': 'Өзгеріс',
  'metrics.population': 'Шекті мән ішіндегі халық',
  'metrics.share': 'Халық үлесі',
  'metrics.mean': 'Орташа жаяу жүру уақыты, мин',
  'metrics.pp': 'п.т.',

  'optimize.help': 'Таңдалған санат пен маусым үшін қолжетімділікті ең көп жақсартатын k жаңа орынды табу.',
  'optimize.k': 'Жаңа нысандар саны (k)',
  'optimize.method': 'Әдіс',
  'optimize.max_covering': 'Максималды қамту (шекті мән ішіндегі халықты барынша көбейту)',
  'optimize.p_median': 'p-медиана (орташа жаяу жүру уақытын барынша азайту)',
  'optimize.run': 'Оңтайландыру',
  'optimize.running': 'Шешілуде…',
  'optimize.status': 'Шешуші күйі: {s}, {t} с',
  'optimize.locations': 'Ұсынылатын орындар',
  'optimize.gain': 'Қамту өсімі',
  'optimize.clear': 'Нәтижені тазарту',


  'report.download': 'PDF есепті жүктеп алу',
  'footer.sources': 'Деректер',
  'footer.basemap': 'Негізгі карта',
};

export default kk;
