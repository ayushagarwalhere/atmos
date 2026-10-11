export const ORIGINAL_SCENARIO = {
  direction: null, speed: null, multiplier: 1, rain_mm: null, cloud_cover_pct: null,
  humidity_pct: null, temperature_c: null, boundary_layer_height: null,
  smoke_factor: 1, burning: 'unspecified',
};

export const SCENARIO_PRESETS = {
  calm: { name: 'Stagnant burning', description: 'More burning, weak winds and a shallow mixing layer.', icon: 'fire', category: 'Stress test', values: { speed: 2, multiplier: 2, rain_mm: 0, cloud_cover_pct: 75, boundary_layer_height: 150, smoke_factor: 1.5, burning: 'crop_residue' } },
  rain: { name: 'Rain arrives', description: 'Explore an 8 mm rain hour with humid, cloudy conditions.', icon: 'rain', category: 'Weather shift', values: { speed: 18, rain_mm: 8, cloud_cover_pct: 95, humidity_pct: 90 } },
  wind: { name: 'Better ventilation', description: 'Stronger wind and a deeper mixing layer.', icon: 'wind', category: 'Weather shift', values: { speed: 32, rain_mm: 0, cloud_cover_pct: 10, boundary_layer_height: 1500 } },
  half: { name: 'Cut burning by 50%', description: 'Reduce the fire activity proxy while holding weather constant.', icon: 'leaf', category: 'Mitigation', values: { multiplier: 0.5 } },
  stop: { name: 'Pause regional burning', description: 'Remove the regional fire proxy. Other pollution sources remain.', icon: 'leaf', category: 'Mitigation', values: { multiplier: 0, smoke_factor: 0 } },
  shift: { name: 'Wind changes course', description: 'Turn the wind to arrive from the southwest and reroute the plume.', icon: 'wind', category: 'Transport', values: { direction: 230, speed: 18 } },
  night: { name: 'Shallow night-time layer', description: 'Low mixing height, humid air and slow wind.', icon: 'moon', category: 'Stress test', values: { boundary_layer_height: 100, humidity_pct: 90, temperature_c: 16, speed: 3, rain_mm: 0 } },
  surge: { name: 'Fire activity doubles', description: 'Double fire activity with the original weather inputs.', icon: 'fire', category: 'Stress test', values: { multiplier: 2, burning: 'crop_residue' } },
};

export const presetValues = key => ({ ...ORIGINAL_SCENARIO, ...SCENARIO_PRESETS[key].values });
