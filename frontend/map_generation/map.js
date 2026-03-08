map.setTerrain({ source: 'mapbox-dem', exaggeration: 1.5 });

map.addLayer({
  id: '3d-buildings',
  source: 'composite',
  'source-layer': 'building',
  type: 'fill-extrusion',
  paint: {
    'fill-extrusion-color': '#aaa',
    'fill-extrusion-height': ['get', 'height']
  }
});