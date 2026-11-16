/**
 * English dictionary. It is the reference: its keys define `DictKey`,
 * and ru.ts / kk.ts must provide exactly the same keys (checked by the
 * compiler via the `Dict` type and by src/i18n/i18n.test.ts).
 * Placeholders in braces, e.g. {n}, are replaced by `t(key, { n: 5 })`.
 */
const en = {
  'app.title': 'AccessAstana',
  'app.subtitle': 'Climate-adjusted walking accessibility',
  'lang.label': 'Language',

  'controls.city': 'City',
  'controls.category': 'Category',
  'controls.season': 'Season',

  'category.school': 'Schools',
  'category.kindergarten': 'Kindergartens',
  'category.clinic': 'Clinics',
  'category.pharmacy': 'Pharmacies',
  'category.transit_stop': 'Transit stops',
  'category.grocery': 'Grocery stores',
  'category.park': 'Parks',
  'category.index': '15-minute index',

  'season.summer': 'Summer',
  'season.winter': 'Winter',
  'season.winter_severe': 'Severe frost',
  'season.hint': 'Walking speed {v} km/h, threshold {n} min',

  'tabs.overview': 'Accessibility',
  'tabs.scenario': 'Scenario',
  'tabs.optimize': 'Optimization',

  'status.loading': 'Loading…',
  'status.error': 'Error',
  'status.retry': 'Retry',
  'status.noCells': 'No cells for this selection.',

  'legend.minutes': 'Walking time, min',
  'legend.index': 'Share of categories within {n} min',
  'legend.noData': 'Unreachable (> 60 min)',
  'legend.noValue': 'No data',
  'legend.threshold': 'Threshold: {n} min',
  'legend.more': 'more than {n} min',

  'tooltip.value': 'Value',
  'tooltip.minutes': '{n} min',
  'tooltip.population': 'Population',
  'tooltip.before': 'Before',
  'tooltip.after': 'After',
  'tooltip.gain': 'Population gain',
  'tooltip.facility': 'Facility',
  'tooltip.removeHint': 'Click to mark for removal',

  'districts.title': 'Districts',
  'districts.name': 'District',
  'districts.population': 'Population',
  'districts.index': 'Index',
  'districts.within': '≤ {n} min',
  'districts.mean': 'Mean, min',
  'districts.cityTotal': 'City total',
  'districts.showOutlines': 'Show district boundaries',
  'districts.indexHint': 'Choose a facility category to see shares within the threshold.',

  'scenario.help':
    'Turn on edit mode, click the map to add a proposed facility, click an existing facility (small point) to mark it for removal, then press “Compute”.',
  'scenario.editMode': 'Edit mode',
  'scenario.added': 'Proposed facilities: {n}',
  'scenario.removed': 'Marked for removal: {n}',
  'scenario.compute': 'Compute',
  'scenario.computing': 'Computing…',
  'scenario.reset': 'Reset',
  'scenario.needCategory': 'Scenarios and optimization work with one facility category. Please choose a category instead of the index.',
  'scenario.newFacility': 'New facility {n}',
  'scenario.changed': 'Changed cells: {n} (outlined on the map)',
  'scenario.existing': 'Existing facilities',
  'scenario.proposed': 'Proposed',
  'scenario.toRemove': 'To remove',
  'scenario.nothing': 'Add or remove at least one facility first.',

  'metrics.metric': 'Metric',
  'metrics.before': 'Before',
  'metrics.after': 'After',
  'metrics.delta': 'Change',
  'metrics.population': 'Population within threshold',
  'metrics.share': 'Share of population',
  'metrics.mean': 'Mean walking time, min',
  'metrics.pp': 'p.p.',

  'optimize.help': 'Find k new locations that improve accessibility the most for the selected category and season.',
  'optimize.k': 'Number of new facilities (k)',
  'optimize.method': 'Method',
  'optimize.max_covering': 'Maximal covering (max population within threshold)',
  'optimize.p_median': 'p-median (min mean walking time)',
  'optimize.run': 'Optimize',
  'optimize.running': 'Solving…',
  'optimize.status': 'Solver status: {s}, {t} s',
  'optimize.locations': 'Recommended locations',
  'optimize.gain': 'Population gain',
  'optimize.clear': 'Clear result',


  'report.download': 'Download PDF report',
  'footer.sources': 'Data',
  'footer.basemap': 'Basemap',
} as const;

export type DictKey = keyof typeof en;
/** Shape every language must implement. */
export type Dict = Record<DictKey, string>;

const dict: Dict = en;
export default dict;
