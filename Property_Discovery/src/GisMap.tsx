import React, { useState } from 'react';
import type { Property } from './mockData';
import { ZoomIn, ZoomOut, Compass, Info } from 'lucide-react';

interface GisMapProps {
  property: Property;
}

type LayerType = 'satellite' | 'boundary' | 'zoning' | 'elevation';

export const GisMap: React.FC<GisMapProps> = ({ property }) => {
  const [activeLayer, setActiveLayer] = useState<LayerType>('boundary');
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [hoveredFeature, setHoveredFeature] = useState<string | null>(null);

  const handleZoomIn = () => setZoomLevel((prev) => Math.min(prev + 10, 150));
  const handleZoomOut = () => setZoomLevel((prev) => Math.max(prev - 10, 70));

  // Render SVG based on property
  const renderSvgMapContent = () => {
    const scaleStyle = {
      transform: `scale(${zoomLevel / 100})`,
      transformOrigin: 'center',
      transition: 'transform 0.3s ease',
    };

    if (property.id === 'prop-1') {
      // Prestige Tech Park
      return (
        <g style={scaleStyle}>
          {/* Backgrounds based on layers */}
          {activeLayer === 'satellite' && (
            <rect x="0" y="0" width="100%" height="100%" fill="#1e293b" opacity="0.9" />
          )}
          {activeLayer === 'zoning' && (
            <rect x="0" y="0" width="100%" height="100%" fill="#eff6ff" />
          )}
          {activeLayer === 'elevation' && (
            <rect x="0" y="0" width="100%" height="100%" fill="#fafafa" />
          )}

          {/* Grids for satellite/others */}
          {activeLayer === 'satellite' && (
            <>
              {/* Fake roads and building outlines in dark colors */}
              <line x1="0" y1="50" x2="500" y2="50" stroke="#475569" strokeWidth="40" />
              <line x1="400" y1="0" x2="400" y2="400" stroke="#475569" strokeWidth="30" />
              {/* Lake representation */}
              <path d="M 0,320 Q 150,280 250,380 L 0,400 Z" fill="#0c4a6e" opacity="0.8" />
              <text x="30" y="360" fill="#38bdf8" fontSize="10" fontWeight="bold">BELLANDUR LAKE CANAL</text>
            </>
          )}

          {activeLayer === 'zoning' && (
            <>
              {/* Zoning overlays */}
              <rect x="0" y="0" width="500" height="80" fill="#bfdbfe" opacity="0.6" /> {/* Commercial road zone */}
              <path d="M 0,260 Q 150,230 280,380 L 0,400 Z" fill="#bbf7d0" opacity="0.6" /> {/* Eco Buffer Zone */}
              <text x="20" y="30" fill="#1d4ed8" fontSize="10" fontWeight="bold">COMMERCIAL ROAD FRONTAGE ZONE</text>
              <text x="20" y="320" fill="#166534" fontSize="10" fontWeight="bold">ECO-FRAGILE BUFFER ZONE (85M)</text>
            </>
          )}

          {activeLayer === 'elevation' && (
            <>
              {/* Contours */}
              <path d="M -50,100 Q 200,80 550,120" fill="none" stroke="#cbd5e1" strokeWidth="1" strokeDasharray="4" />
              <path d="M -50,180 Q 200,160 550,200" fill="none" stroke="#cbd5e1" strokeWidth="1" strokeDasharray="4" />
              <path d="M -50,260 Q 200,240 550,280" fill="none" stroke="#cbd5e1" strokeWidth="1" strokeDasharray="4" />
              <text x="420" y="95" fill="#94a3b8" fontSize="9">894m</text>
              <text x="420" y="175" fill="#94a3b8" fontSize="9">892m (MSL)</text>
              <text x="420" y="255" fill="#94a3b8" fontSize="9">890m</text>
            </>
          )}

          {/* Neighboring plots */}
          <rect x="40" y="120" width="100" height="120" fill="#cbd5e1" fillOpacity="0.15" stroke="#94a3b8" strokeWidth="1" strokeDasharray="2" />
          <text x="50" y="180" fill="#94a3b8" fontSize="10">PLOT 111</text>

          <rect x="360" y="120" width="100" height="120" fill="#cbd5e1" fillOpacity="0.15" stroke="#94a3b8" strokeWidth="1" strokeDasharray="2" />
          <text x="375" y="180" fill="#94a3b8" fontSize="10">PLOT 114</text>

          {/* Core Property Parcels (Survey Nos) */}
          {/* Survey 112/1 */}
          <polygon 
            points="150,120 250,120 250,240 150,240" 
            fill={activeLayer === 'satellite' ? 'rgba(37, 99, 235, 0.2)' : 'rgba(59, 130, 246, 0.08)'}
            stroke={hoveredFeature === '112/1' ? '#2563eb' : '#3b82f6'}
            strokeWidth={hoveredFeature === '112/1' ? '3' : '2'}
            style={{ cursor: 'pointer', transition: 'all 0.2s' }}
            onMouseEnter={() => setHoveredFeature('112/1')}
            onMouseLeave={() => setHoveredFeature(null)}
          />
          <text x="165" y="170" fill={hoveredFeature === '112/1' ? '#1d4ed8' : '#475569'} fontSize="11" fontWeight="bold">Sy. 112/1</text>
          <text x="165" y="185" fill="#10b981" fontSize="9" fontWeight="600">Clear • 4.2 Ac</text>

          {/* Survey 112/2 */}
          <polygon 
            points="250,120 350,120 350,200 250,200" 
            fill={activeLayer === 'satellite' ? 'rgba(37, 99, 235, 0.2)' : 'rgba(59, 130, 246, 0.08)'}
            stroke={hoveredFeature === '112/2' ? '#2563eb' : '#3b82f6'}
            strokeWidth={hoveredFeature === '112/2' ? '3' : '2'}
            style={{ cursor: 'pointer', transition: 'all 0.2s' }}
            onMouseEnter={() => setHoveredFeature('112/2')}
            onMouseLeave={() => setHoveredFeature(null)}
          />
          <text x="265" y="150" fill={hoveredFeature === '112/2' ? '#1d4ed8' : '#475569'} fontSize="11" fontWeight="bold">Sy. 112/2</text>
          <text x="265" y="165" fill="#10b981" fontSize="9" fontWeight="600">Clear • 3.5 Ac</text>

          {/* Survey 113 */}
          <polygon 
            points="150,240 350,200 350,280 150,280" 
            fill={activeLayer === 'satellite' ? 'rgba(245, 158, 11, 0.2)' : 'rgba(245, 158, 11, 0.08)'}
            stroke={hoveredFeature === '113' ? '#d97706' : '#f59e0b'}
            strokeWidth={hoveredFeature === '113' ? '3' : '2'}
            style={{ cursor: 'pointer', transition: 'all 0.2s' }}
            onMouseEnter={() => setHoveredFeature('113')}
            onMouseLeave={() => setHoveredFeature(null)}
          />
          <text x="220" y="245" fill={hoveredFeature === '113' ? '#b45309' : '#b45309'} fontSize="11" fontWeight="bold">Sy. 113 (Boundary Dispute)</text>
          <text x="220" y="260" fill="#d97706" fontSize="9" fontWeight="600">Active Litigation • 4.7 Ac</text>

          {/* Main project boundary box */}
          <rect x="145" y="110" width="210" height="180" fill="none" stroke="#2563eb" strokeWidth="1" strokeDasharray="6 4" opacity="0.7" />
        </g>
      );
    } else if (property.id === 'prop-2') {
      // Aurelia Commercial Tower
      return (
        <g style={scaleStyle}>
          {/* Backgrounds based on layers */}
          {activeLayer === 'satellite' && (
            <rect x="0" y="0" width="100%" height="100%" fill="#1e293b" opacity="0.9" />
          )}
          {activeLayer === 'zoning' && (
            <rect x="0" y="0" width="100%" height="100%" fill="#fef8f8" />
          )}
          {activeLayer === 'elevation' && (
            <rect x="0" y="0" width="100%" height="100%" fill="#fafafa" />
          )}

          {activeLayer === 'satellite' && (
            <>
              {/* Noida Metro lines and highway */}
              <line x1="0" y1="350" x2="500" y2="350" stroke="#334155" strokeWidth="30" />
              <line x1="0" y1="350" x2="500" y2="350" stroke="#0284c7" strokeWidth="6" strokeDasharray="15 10" />
              <text x="20" y="380" fill="#38bdf8" fontSize="9" fontWeight="bold">NOIDA SECTOR 62 METRO CORRIDOR</text>
            </>
          )}

          {activeLayer === 'zoning' && (
            <>
              <rect x="0" y="280" width="500" height="120" fill="#e0f2fe" opacity="0.7" /> {/* Infrastructure zone */}
              <rect x="0" y="0" width="500" height="280" fill="#fee2e2" opacity="0.5" /> {/* Commercial Mixed Use */}
              <text x="20" y="30" fill="#b91c1c" fontSize="10" fontWeight="bold">COMMERCIAL BUSINESS DISTRICT (CBD) ZONE</text>
            </>
          )}

          {activeLayer === 'elevation' && (
            <>
              <path d="M -50,150 Q 250,160 550,150" fill="none" stroke="#cbd5e1" strokeWidth="1" strokeDasharray="4" />
              <text x="420" y="145" fill="#94a3b8" fontSize="9">201m (MSL)</text>
            </>
          )}

          {/* Plot Boundaries */}
          <polygon 
            points="180,100 320,100 320,280 180,280" 
            fill={activeLayer === 'satellite' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(239, 68, 68, 0.05)'}
            stroke={hoveredFeature === 'B-24/A' ? '#dc2626' : '#ef4444'}
            strokeWidth={hoveredFeature === 'B-24/A' ? '3' : '2'}
            style={{ cursor: 'pointer', transition: 'all 0.2s' }}
            onMouseEnter={() => setHoveredFeature('B-24/A')}
            onMouseLeave={() => setHoveredFeature(null)}
          />
          <text x="200" y="150" fill="#b91c1c" fontSize="12" fontWeight="bold">Plot B-24/A</text>
          <text x="200" y="170" fill="#e11d48" fontSize="10" fontWeight="600">RERA Delayed • 5.8 Ac</text>
          <text x="200" y="190" fill="#475569" fontSize="9">Build Progress: 75%</text>

          {/* Interactive structural tower block */}
          <rect x="210" y="210" width="80" height="50" fill="#475569" stroke="#334155" strokeWidth="1" opacity="0.8" />
          <text x="220" y="235" fill="white" fontSize="9" fontWeight="bold">Tower A & B</text>

          <text x="40" y="180" fill="#cbd5e1" fontSize="10" stroke="#94a3b8" strokeWidth="0.5">Plot B-23</text>
          <text x="380" y="180" fill="#cbd5e1" fontSize="10" stroke="#94a3b8" strokeWidth="0.5">Plot B-24/B</text>
        </g>
      );
    } else {
      // Royal Palms Residency
      return (
        <g style={scaleStyle}>
          {/* Backgrounds based on layers */}
          {activeLayer === 'satellite' && (
            <rect x="0" y="0" width="100%" height="100%" fill="#1e293b" opacity="0.9" />
          )}
          {activeLayer === 'zoning' && (
            <rect x="0" y="0" width="100%" height="100%" fill="#fffbeb" />
          )}
          {activeLayer === 'elevation' && (
            <rect x="0" y="0" width="100%" height="100%" fill="#fafafa" />
          )}

          {activeLayer === 'satellite' && (
            <>
              {/* Malkam Cheruvu Lake Body */}
              <path d="M 300,0 Q 220,100 450,220 L 500,220 L 500,0 Z" fill="#0284c7" opacity="0.75" />
              <text x="350" y="80" fill="#e0f2fe" fontSize="10" fontWeight="bold">MALKAM CHERUVU LAKE</text>
            </>
          )}

          {activeLayer === 'zoning' && (
            <>
              <path d="M 280,0 Q 200,100 430,220 L 500,220 L 500,0 Z" fill="#fee2e2" opacity="0.6" /> {/* FTL Buffer */}
              <rect x="0" y="120" width="220" height="280" fill="#fef08a" opacity="0.5" /> {/* Residential zone */}
              <text x="320" y="120" fill="#b91c1c" fontSize="9" fontWeight="bold">LAKE FTL BUFFER ZONE (NO-BUILD)</text>
              <text x="20" y="150" fill="#a16207" fontSize="10" fontWeight="bold">RESIDENTIAL HIGH-RISE ZONE</text>
            </>
          )}

          {activeLayer === 'elevation' && (
            <>
              <path d="M -50,300 Q 200,280 550,310" fill="none" stroke="#cbd5e1" strokeWidth="1" strokeDasharray="4" />
              <text x="420" y="295" fill="#94a3b8" fontSize="9">542m (MSL)</text>
            </>
          )}

          {/* Neighbors */}
          <text x="50" y="80" fill="#94a3b8" fontSize="10">PLOT 41</text>
          <text x="50" y="340" fill="#94a3b8" fontSize="10">PLOT 43</text>

          {/* Survey 42/A */}
          <polygon 
            points="120,100 220,120 220,250 120,230" 
            fill={activeLayer === 'satellite' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(239, 68, 68, 0.05)'}
            stroke={hoveredFeature === '42/A' ? '#dc2626' : '#ef4444'}
            strokeWidth={hoveredFeature === '42/A' ? '3' : '2'}
            style={{ cursor: 'pointer', transition: 'all 0.2s' }}
            onMouseEnter={() => setHoveredFeature('42/A')}
            onMouseLeave={() => setHoveredFeature(null)}
          />
          <text x="140" y="160" fill="#b91c1c" fontSize="11" fontWeight="bold">Sy. 42/A</text>
          <text x="140" y="175" fill="#d97706" fontSize="9" fontWeight="600">Title Dispute</text>

          {/* Survey 42/B - High Risk ED attachment */}
          <polygon 
            points="220,120 320,140 300,270 220,250" 
            fill={hoveredFeature === '42/B' ? 'rgba(220, 38, 38, 0.35)' : 'rgba(220, 38, 38, 0.2)'}
            stroke="#dc2626"
            strokeWidth="3"
            strokeDasharray={activeLayer === 'zoning' ? 'none' : '4 2'}
            style={{ cursor: 'pointer', transition: 'all 0.2s' }}
            className="blink-edge"
            onMouseEnter={() => setHoveredFeature('42/B')}
            onMouseLeave={() => setHoveredFeature(null)}
          />
          <text x="235" y="180" fill="#7f1d1d" fontSize="11" fontWeight="bold">Sy. 42/B</text>
          <text x="235" y="195" fill="#dc2626" fontSize="9" fontWeight="800">ED SEIZED</text>
          <text x="235" y="210" fill="#b91c1c" fontSize="8" fontWeight="600">FTL Encroachment</text>
        </g>
      );
    }
  };

  return (
    <div className="map-card-container">
      {/* Map Pane */}
      <div className="map-view-pane">
        {/* SVG Wrapper */}
        <svg 
          viewBox="0 0 500 400" 
          width="100%" 
          height="100%" 
          style={{ backgroundColor: activeLayer === 'satellite' ? '#0f172a' : '#f8fafc' }}
        >
          {renderSvgMapContent()}
        </svg>

        <div className="map-grid-overlay"></div>

        {/* Legend Overlay */}
        <div className="map-legend-overlay">
          <div className="map-legend-item">
            <div className="map-legend-color" style={{ backgroundColor: '#2563eb' }}></div>
            <span>Verified Clear Plot</span>
          </div>
          <div className="map-legend-item">
            <div className="map-legend-color" style={{ backgroundColor: '#f59e0b' }}></div>
            <span>Disputed Boundary</span>
          </div>
          <div className="map-legend-item">
            <div className="map-legend-color" style={{ backgroundColor: '#ef4444' }}></div>
            <span>Seized / Locked Parcel</span>
          </div>
          {hoveredFeature && (
            <div className="map-legend-item" style={{ marginTop: '4px', paddingTop: '4px', borderTop: '1px solid #e2e8f0', color: '#1e293b', fontWeight: 'bold' }}>
              <span>Focused: {hoveredFeature}</span>
            </div>
          )}
        </div>

        {/* Layer Selector */}
        <div className="map-layer-selector">
          <button 
            className={`map-layer-btn ${activeLayer === 'boundary' ? 'active' : ''}`}
            onClick={() => setActiveLayer('boundary')}
          >
            Boundary
          </button>
          <button 
            className={`map-layer-btn ${activeLayer === 'satellite' ? 'active' : ''}`}
            onClick={() => setActiveLayer('satellite')}
          >
            Satellite
          </button>
          <button 
            className={`map-layer-btn ${activeLayer === 'zoning' ? 'active' : ''}`}
            onClick={() => setActiveLayer('zoning')}
          >
            Zoning
          </button>
          <button 
            className={`map-layer-btn ${activeLayer === 'elevation' ? 'active' : ''}`}
            onClick={() => setActiveLayer('elevation')}
          >
            Contours
          </button>
        </div>

        {/* Zoom Controls */}
        <div className="map-controls">
          <button className="map-btn" onClick={handleZoomIn} title="Zoom In"><ZoomIn size={16} /></button>
          <button className="map-btn" onClick={handleZoomOut} title="Zoom Out"><ZoomOut size={16} /></button>
          <button className="map-btn" title="Map Orientation"><Compass size={16} /></button>
        </div>
      </div>

      {/* Details Side Panel */}
      <div className="map-details-pane">
        <h4 style={{ fontFamily: 'var(--font-heading)', fontSize: '14px', fontWeight: '700', color: 'var(--slate-800)', borderBottom: '1px solid var(--slate-200)', paddingBottom: '8px' }}>
          Spatial Metadata
        </h4>
        <div className="map-detail-item">
          <span className="map-detail-label">Geo-Coordinates</span>
          <span className="map-detail-val">{property.latLong}</span>
        </div>
        <div className="map-detail-item">
          <span className="map-detail-label">Total Survey Area</span>
          <span className="map-detail-val">{property.areaAcres} Acres</span>
        </div>
        <div className="map-detail-item">
          <span className="map-detail-label">Elevation Profile</span>
          <span className="map-detail-val">{property.elevation}</span>
        </div>
        <div className="map-detail-item">
          <span className="map-detail-label">Hydrology/Canal Offset</span>
          <span className="map-detail-val" style={{ color: property.nearbyWaterbody.includes('Warning') ? 'var(--danger)' : 'inherit' }}>
            {property.nearbyWaterbody}
          </span>
        </div>
        <div style={{ marginTop: 'auto', backgroundColor: '#f1f5f9', borderRadius: '6px', padding: '10px', fontSize: '11px', color: 'var(--slate-500)', display: 'flex', gap: '6px' }}>
          <Info size={14} style={{ flexShrink: 0, color: 'var(--primary)' }} />
          <span>Interactive GIS map: Click layers to filter. Hover parcels to view individual survey ratings.</span>
        </div>
      </div>
    </div>
  );
};
