import { createContext, useContext, type Dispatch } from 'react';
import type { AccessCategory, OptimizeResponse, ScenarioResponse, Season } from '../api/client';

export type Tab = 'overview' | 'scenario' | 'optimize';
export const TABS: readonly Tab[] = ['overview', 'scenario', 'optimize'];

/** A facility proposed by the user in scenario mode. */
export interface ProposedFacility {
  id: number; // local id, only for React keys
  lon: number;
  lat: number;
  name: string;
}

export interface AppState {
  /** null = "first city returned by /cities" */
  city: string | null;
  category: AccessCategory;
  season: Season;
  tab: Tab;
  showDistricts: boolean;
  scenario: {
    editing: boolean;
    add: ProposedFacility[];
    /** ids of existing POIs (from /pois) to remove */
    remove: number[];
    result: ScenarioResponse | null;
  };
  optimize: OptimizeResponse | null;
}

export type Action =
  | { type: 'setCity'; city: string }
  | { type: 'setCategory'; category: AccessCategory }
  | { type: 'setSeason'; season: Season }
  | { type: 'setTab'; tab: Tab }
  | { type: 'setShowDistricts'; value: boolean }
  | { type: 'setEditing'; value: boolean }
  | { type: 'addFacility'; lon: number; lat: number; name: string }
  | { type: 'toggleRemove'; id: number }
  | { type: 'resetScenario' }
  | { type: 'scenarioResult'; result: ScenarioResponse }
  | { type: 'optimizeResult'; result: OptimizeResponse | null };

export const initialState: AppState = {
  city: null,
  category: 'index',
  season: 'summer',
  tab: 'overview',
  showDistricts: true,
  scenario: { editing: false, add: [], remove: [], result: null },
  optimize: null,
};

const emptyScenario: AppState['scenario'] = { editing: false, add: [], remove: [], result: null };

/**
 * All state transitions in one place. Important invariant: results of
 * /scenarios and /optimize are only valid for the (city, category, season)
 * they were computed for, so changing the selection discards them.
 */
export function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'setCity':
      return { ...state, city: action.city, scenario: emptyScenario, optimize: null };
    case 'setCategory':
      // POI ids marked for removal belong to the old category -> full reset.
      return { ...state, category: action.category, scenario: emptyScenario, optimize: null };
    case 'setSeason':
      // Edits stay valid for another season, only the computed numbers do not.
      return { ...state, season: action.season, scenario: { ...state.scenario, result: null }, optimize: null };
    case 'setTab':
      // Leaving the scenario tab switches off edit mode so map clicks do nothing unexpected.
      return {
        ...state,
        tab: action.tab,
        scenario: action.tab === 'scenario' ? state.scenario : { ...state.scenario, editing: false },
      };
    case 'setShowDistricts':
      return { ...state, showDistricts: action.value };
    case 'setEditing':
      return { ...state, scenario: { ...state.scenario, editing: action.value } };
    case 'addFacility': {
      const id = state.scenario.add.reduce((m, f) => Math.max(m, f.id), 0) + 1;
      const add = [...state.scenario.add, { id, lon: action.lon, lat: action.lat, name: action.name }];
      return { ...state, scenario: { ...state.scenario, add, result: null } };
    }
    case 'toggleRemove': {
      const { remove } = state.scenario;
      const next = remove.includes(action.id) ? remove.filter((x) => x !== action.id) : [...remove, action.id];
      return { ...state, scenario: { ...state.scenario, remove: next, result: null } };
    }
    case 'resetScenario':
      return { ...state, scenario: { ...emptyScenario, editing: state.scenario.editing } };
    case 'scenarioResult':
      return { ...state, scenario: { ...state.scenario, result: action.result } };
    case 'optimizeResult':
      return { ...state, optimize: action.result };
  }
}

export interface AppStateValue {
  state: AppState;
  dispatch: Dispatch<Action>;
}

export const AppStateContext = createContext<AppStateValue | null>(null);

export function useAppState(): AppStateValue {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error('useAppState must be used inside <AppStateProvider>');
  return ctx;
}
