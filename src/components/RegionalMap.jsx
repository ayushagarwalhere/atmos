import { useEffect, useState } from 'react';

const projected = ([lon, lat]) => `${((lon - 73.2) / 9.2 * 100).toFixed(3)},${((33.5 - lat) / 7.8 * 100).toFixed(3)}`;
const ringPath = rings => rings.map(ring => 'M' + ring.map(projected).join('L') + 'Z').join(' ');

export default function RegionalMap() {
  const [regions, setRegions] = useState([]);
  useEffect(() => {
    const controller = new AbortController();
    fetch('/regional-boundaries.json', { signal: controller.signal }).then(response => {
      if (!response.ok) throw new Error('Map outlines unavailable');
      return response.json();
    }).then(data => setRegions(data.features)).catch(() => {});
    return () => controller.abort();
  }, []);
  return <svg className="regional-map-outlines" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
    {regions.map(region => <path key={region.properties.name} d={region.geometry.type === 'MultiPolygon' ? region.geometry.coordinates.map(ringPath).join(' ') : ringPath(region.geometry.coordinates)} fillRule="evenodd"/>)}
  </svg>;
}
