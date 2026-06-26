import { useState, useEffect, useRef } from 'react';
import { MOCK_PROPERTIES } from './mockData';
import type { Property } from './mockData';
import TelanganaMapModal from './TelanganaMapModal';
import { 
  Search, 
  Globe, 
  MapPin, 
  ShieldCheck, 
  ArrowRight, 
  Download, 
  CheckCircle2, 
  ChevronDown,
  Map
} from 'lucide-react';

interface UnifiedSuggestion {
  id: string;
  type: 'property' | 'infra_project';
  name: string;
  subtitle: string;
  badgeText: string;
  riskStatus: 'low' | 'medium' | 'high';
  score: number;
  originalData: any;
}

// Client-side fuzzy matching algorithm for ranking suggestions
function fuzzyScore(query: string, target: string): number {
  const q = query.toLowerCase().trim();
  const t = target.toLowerCase().trim();
  
  if (!q) return 0;
  if (q === t) return 100; // Exact match
  
  if (t.startsWith(q)) return 80; // Prefix match
  
  const tWords = t.split(/\s+/);
  const qWords = q.split(/\s+/);
  
  let matches = 0;
  for (const qw of qWords) {
    if (tWords.includes(qw)) {
      matches++;
    }
  }
  if (matches === qWords.length) return 70; // Word matches
  
  if (t.includes(q)) return 50; // Substring match
  
  // Subsequence match (in-order character matches)
  let qIdx = 0;
  let tIdx = 0;
  let matchesInOrder = 0;
  while (qIdx < q.length && tIdx < t.length) {
    if (q[qIdx] === t[tIdx]) {
      qIdx++;
      matchesInOrder++;
    }
    tIdx++;
  }
  if (matchesInOrder === q.length) return 30;
  
  // Overlap ratio for typos
  let commonChars = 0;
  const tChars = new Set(t);
  for (const c of q) {
    if (tChars.has(c)) commonChars++;
  }
  const overlap = commonChars / Math.max(q.length, t.length);
  if (overlap > 0.4) {
    return Math.floor(overlap * 20);
  }
  
  return 0;
}

const STATE_OPTIONS = [
  { code: 'TS', label: 'Telangana (TS)' },
  { code: 'TN', label: 'Tamil Nadu (TN)' },
  { code: 'MP', label: 'Madhya Pradesh (MP)' },
  { code: 'KA', label: 'Karnataka (KA)' },
] as const;

// Map RERA scraped projects search items into a uniform Property structure
function transformInfraToProperty(project: any): Property {
  const pId = project.registration_no || project.detail_url?.match(/project_id=([^&]+)/)?.[1] || 'RERA-' + Math.floor(100000 + Math.random() * 900000);
  return {
    id: `infra-project-${project.project_name.toLowerCase().replace(/[^a-z0-9]/g, '-')}`,
    name: project.project_name || 'Unknown RERA Project',
    location: (project.search?.district_name || 'District Registry') + ', India',
    surveyNo: 'Pending land parcel boundary partition SRO check',
    ownerName: project.promoter_name || 'Unknown Promoter',
    reraId: pId,
    pinCode: 'N/A',
    status: 'medium',
    riskScore: 70,
    titleStatus: 'Under construction',
    litigationCount: '0 Active (Awaiting manual check)',
    financialStatus: 'Promoter: ' + (project.promoter_name || 'N/A'),
    zone: project.search?.project_type_name || 'Residential/Commercial Development',
    areaAcres: 4.8,
    latLong: project.latitude && project.longitude ? `${project.latitude}° N, ${project.longitude}° E` : '12.9716° N, 77.5946° E',
    elevation: 'N/A',
    nearbyWaterbody: 'Buffer zone compliance check pending',
    reraProgress: 80,
    reraDeveloper: project.promoter_name || 'Regulatory Board Registered',
    reraFilingDate: project.registration_date || project.last_modified || 'N/A',
    reraApprovedArea: 'Files logged in regional RERA portal',
    boundaryShape: { x: 0, y: 0, w: 120, h: 120 },
    titleChain: [
      {
        year: project.last_modified?.split('-')?.[0] || '2026',
        type: 'RERA Registration Allotment',
        partyA: project.promoter_name || 'Promoter',
        partyB: 'State RERA Authority',
        value: 'Development Approved',
        docNo: 'RERA-' + (project.search?.district_id || '01'),
        registrar: 'RERA Registrar Office'
      }
    ],
    litigations: [],
    taxCompliance: []
  };
}

function App() {
  const [selectedProperty, setSelectedProperty] = useState<Property | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [suggestions, setSuggestions] = useState<UnifiedSuggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  
  const [selectedState, setSelectedState] = useState<string>('TS');
  const [showStateDropdown, setShowStateDropdown] = useState<boolean>(false);
  const [showMapModal, setShowMapModal] = useState<boolean>(false);
  
  // PDF download progress states
  const [isDownloading, setIsDownloading] = useState<boolean>(false);
  const [downloadStep, setDownloadStep] = useState<number>(0);
  const downloadTimerRef = useRef<number | null>(null);
  const searchBoxRef = useRef<HTMLDivElement>(null);
  const stateSelectorRef = useRef<HTMLDivElement>(null);

  const selectedStateLabel =
    STATE_OPTIONS.find((s) => s.code === selectedState)?.label ?? 'Telangana (TS)';

  // Debounced fuzzy search effect integrating the APIs from rera-scraper & hi-extension
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSuggestions([]);
      return;
    }

    setIsLoading(true);
    const delayDebounceFn = setTimeout(async () => {
      const query = searchQuery.trim();
      const resultsList: UnifiedSuggestion[] = [];

      // 1. Match against local mock database using fuzzy logic
      const localMatches = MOCK_PROPERTIES.map(p => {
        const score = Math.max(
          fuzzyScore(query, p.name),
          fuzzyScore(query, p.ownerName),
          fuzzyScore(query, p.surveyNo),
          fuzzyScore(query, p.location)
        );
        return {
          id: p.id,
          type: 'property' as const,
          name: p.name,
          subtitle: `Owner: ${p.ownerName} | Survey: ${p.surveyNo} | ${p.location}`,
          badgeText: `${p.status} risk`,
          riskStatus: p.status,
          score,
          originalData: p
        };
      }).filter(item => item.score > 10);
      resultsList.push(...localMatches);



      // 3. Fetch from local RERA Search API (from rera-scraper / run_api.py)
      try {
        const params = new URLSearchParams({
          q: query,
          page: "1",
          page_size: "5"
        });
        const port = selectedState === 'KA' ? '8002' : selectedState === 'TN' ? '8001' : selectedState === 'MP' ? '8003' : '8000';
        const res = await fetch(`http://localhost:${port}/api/infra/search?${params}`);
        if (res.ok) {
          const data = await res.json();
          if (data && data.results) {
            const infraMatches = data.results.map((project: any) => {
              const score = Math.max(
                fuzzyScore(query, project.project_name),
                fuzzyScore(query, project.promoter_name)
              );
              return {
                id: `infra-${project.project_name.replace(/\s+/g, '_')}`,
                type: 'infra_project' as const,
                name: project.project_name,
                subtitle: `Promoter: ${project.promoter_name} | District: ${project.search?.district_name || 'N/A'}`,
                badgeText: 'RERA project',
                riskStatus: 'medium' as const,
                score: score + 10,
                originalData: project
              };
            });
            resultsList.push(...infraMatches);
          }
        }
      } catch (err) {
        console.warn("Local RERA Search API is currently unreachable", err);
      }

      // Sort aggregated list by fuzzy score descending
      resultsList.sort((a, b) => b.score - a.score);

      // Deduplicate suggestions by unique ID
      const uniqueResults: UnifiedSuggestion[] = [];
      const seenIds = new Set<string>();
      for (const item of resultsList) {
        if (!seenIds.has(item.id)) {
          seenIds.add(item.id);
          uniqueResults.push(item);
        }
      }

      setSuggestions(uniqueResults);
      setIsLoading(false);
    }, 300);

    return () => clearTimeout(delayDebounceFn);
  }, [searchQuery, selectedState]);

  // Mock download runner
  const startDownloadReport = () => {
    if (!selectedProperty) return;
    setIsDownloading(true);
    setDownloadStep(0);
  };

  useEffect(() => {
    if (isDownloading) {
      downloadTimerRef.current = window.setInterval(() => {
        setDownloadStep((prev) => {
          if (prev >= 5) {
            if (downloadTimerRef.current) clearInterval(downloadTimerRef.current);
            triggerReportDownload();
            return 5;
          }
          return prev + 1;
        });
      }, 700);
    }
    return () => {
      if (downloadTimerRef.current) clearInterval(downloadTimerRef.current);
    };
  }, [isDownloading]);

  const triggerReportDownload = () => {
    if (!selectedProperty) return;
    const property = selectedProperty;
    const element = document.createElement("a");
    const reportText = `========================================================================
                 SIGNALX LEGAL & LAND DUE DILIGENCE REPORT
========================================================================
Report Generated : ${new Date().toLocaleString()}
Compliance Score : ${property.riskScore}/100
Risk Verdict     : ${property.status.toUpperCase()} RISK STATUS
Reference ID     : SIGX-DD-${property.id.toUpperCase()}-${Math.floor(1000 + Math.random() * 9000)}

------------------------------------------------------------------------
1. PROPERTY IDENTIFICATION
------------------------------------------------------------------------
Property Name    : ${property.name}
Zoning Category  : ${property.zone}
Survey Numbers   : ${property.surveyNo}
PIN Code         : ${property.pinCode}
Global Location  : ${property.location}
GIS Coordinates  : ${property.latLong}
Elevation Profile: ${property.elevation}
Total Plot Area  : ${property.areaAcres} Acres
Hydrology Buffer : ${property.nearbyWaterbody}

------------------------------------------------------------------------
2. CURRENT RECOGNIZED OWNERSHIP
------------------------------------------------------------------------
Registered Owner : ${property.ownerName}
Title Status     : ${property.titleStatus}
Financial State  : ${property.financialStatus}

------------------------------------------------------------------------
3. TITLE HISTORICAL AUDIT (30-YEAR CHAIN)
------------------------------------------------------------------------
${property.titleChain.map((n, i) => `[Deed Node #${i+1}]
Year             : ${n.year}
Transaction Type : ${n.type}
Transferor (A)   : ${n.partyA}
Transferee (B)   : ${n.partyB}
Consideration    : ${n.value}
Document Number  : ${n.docNo}
Registration SRO : ${n.registrar}
------------------------------------------------------------------------`).join('\n')}

------------------------------------------------------------------------
4. LITIGATION DISCLOSURE & SCREENING
------------------------------------------------------------------------
Litigation Index : ${property.litigations.length} Cases Screened
Active Disputes  : ${property.litigations.filter(c => c.status === 'Active').length} Cases
Disposed Cases   : ${property.litigations.filter(c => c.status === 'Disposed').length} Cases

${property.litigations.map((c, i) => `[Case Dossier #${i+1}]
Case Number      : ${c.caseNo}
Adjudicating Body: ${c.court}
Current Status   : ${c.status.toUpperCase()}
Action Type      : ${c.type}
Petitioner (A)   : ${c.partyA}
Respondent (B)   : ${c.partyB}
Case Abstract    : ${c.description}
------------------------------------------------------------------------`).join('\n')}

========================================================================
Disclaimer: This is a simulated Due Diligence Intelligence report pulled 
via the SignalX property verification API node.
========================================================================`;

    const file = new Blob([reportText], { type: 'text/plain;charset=utf-8' });
    element.href = URL.createObjectURL(file);
    element.download = `SignalX_DueDiligence_${property.name.replace(/[^a-zA-Z0-9]/g, "_")}.txt`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (searchBoxRef.current && !searchBoxRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
      if (stateSelectorRef.current && !stateSelectorRef.current.contains(e.target as Node)) {
        setShowStateDropdown(false);
      }
    };
    document.addEventListener('click', handleOutsideClick);
    return () => document.removeEventListener('click', handleOutsideClick);
  }, []);

  // const getStatusColorClass = (status: 'low' | 'medium' | 'high') => {
  //   return `badge-${status}`;
  // };

  const getRiskColor = (status: 'low' | 'medium' | 'high') => {
    if (status === 'low') return '#10b981';
    if (status === 'medium') return '#f59e0b';
    return '#ef4444';
  };

  return (
    <div className="discovery-page">
      {/* Background Gradients */}
      <div className="glowing-bg-1"></div>
      <div className="glowing-bg-2"></div>

      {/* Header Bar */}
      <header className="header-nav">
        {/* Branded Logo */}
        <div className="logo-area">
          <div className="logo-icon" style={{
            background: 'linear-gradient(135deg, #3b82f6 0%, #6366f1 100%)',
            borderRadius: '10px',
            width: '34px',
            height: '34px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 14px rgba(99,102,241,0.5)',
            flexShrink: 0,
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M3 9.5L12 4L21 9.5V20H15V14H9V20H3V9.5Z" fill="white" fillOpacity="0.95" />
              <circle cx="12" cy="10" r="2" fill="rgba(165,180,252,0.9)" />
            </svg>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.15 }}>
            <span style={{ fontWeight: 700, fontSize: '15px', letterSpacing: '-0.3px', color: '#e2e8f0' }}>SignalX</span>
            <span style={{ fontWeight: 400, fontSize: '11px', color: '#64748b', letterSpacing: '0.5px', textTransform: 'uppercase' }}>Properties</span>
          </div>
        </div>

        <div className="nav-actions">

          {selectedState === 'TS' && (
            <button
              type="button"
              className="map-header-btn"
              title="Open Telangana project map"
              onClick={() => setShowMapModal(true)}
            >
              <Map size={16} />
            </button>
          )}

          <div className="state-selector-wrapper" ref={stateSelectorRef}>
            <button
              type="button"
              className="country-selector"
              onClick={(e) => {
                e.stopPropagation();
                setShowStateDropdown((prev) => !prev);
              }}
            >
              <Globe size={14} style={{ color: '#94a3b8', flexShrink: 0 }} />
              <span>{selectedStateLabel}</span>
              <ChevronDown
                size={14}
                style={{
                  color: '#94a3b8',
                  transition: 'transform 0.2s ease',
                  transform: showStateDropdown ? 'rotate(180deg)' : 'rotate(0deg)',
                }}
              />
            </button>

            {showStateDropdown && (
              <div className="state-dropdown">
                {STATE_OPTIONS.map((state) => (
                  <div
                    key={state.code}
                    className={`state-dropdown-item ${selectedState === state.code ? 'active' : ''}`}
                    onClick={() => {
                      setSelectedState(state.code);
                      setShowStateDropdown(false);
                      if (state.code !== 'TS') {
                        setShowMapModal(false);
                      }
                    }}
                  >
                    <Globe size={13} style={{ opacity: 0.7 }} />
                    {state.label}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Centered Discovery Area */}
      <main className="discovery-container">
        <span className="hero-tagline">Registry Due Diligence</span>
        <h1 className="hero-title">Institutional Property Discovery & Screening</h1>
        <p className="hero-description">
          Search and verify property ownership logs, survey boundary litigation, developer RERA compliance, and financial encumbrances instantly.
        </p>

        {/* Global Search Box */}
        <div ref={searchBoxRef} className="search-box-wrapper">
          <div className="search-field-container">
            <Search className="search-icon" size={20} />
            <input 
              type="text"
              className="search-input"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setShowSuggestions(true);
              }}
              onFocus={() => setShowSuggestions(true)}
              placeholder="Search by Property Name, Proprietor Name"
            />
            <button className="search-button">
              <span>Analyze</span>
              <ArrowRight size={15} />
            </button>
          </div>

          {/* Autocomplete Dropdown List */}
          {showSuggestions && searchQuery.trim() !== '' && (
            <div className="suggestions-dropdown">
              <div className="suggestion-header">Fuzzy Matched Records</div>
              {isLoading ? (
                <div style={{ padding: '16px 18px', fontSize: '13px', color: 'var(--slate-500)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div className="loader-ring" style={{ width: 14, height: 14 }}></div>
                  <span>Fuzzy searching across databases...</span>
                </div>
              ) : suggestions.length > 0 ? (
                suggestions.map(item => (
                  <div 
                    key={item.id}
                    className="suggestion-row"
                    onClick={() => {
                      if (item.type === 'property') {
                        setSelectedProperty(item.originalData);
                      } else if (item.type === 'infra_project') {
                        setSelectedProperty(transformInfraToProperty(item.originalData));
                      }
                      setSearchQuery('');
                      setShowSuggestions(false);
                    }}
                  >
                    <div className="row-icon">
                      {item.type === 'property' && <MapPin size={16} style={{ color: '#6366f1' }} />}
                      {item.type === 'infra_project' && <MapPin size={16} style={{ color: '#ec4899' }} />}
                    </div>
                    <div className="row-content">
                      <div className="row-title">{item.name}</div>
                      <div className="row-subtitle">{item.subtitle}</div>
                    </div>
                    <span 
                      className="badge" 
                      style={{ 
                        backgroundColor: item.type === 'property' ? 'rgba(99, 102, 241, 0.1)' : 'rgba(236, 72, 153, 0.1)', 
                        color: item.type === 'property' ? '#6366f1' : '#ec4899', 
                        border: `1px solid ${item.type === 'property' ? 'rgba(99, 102, 241, 0.2)' : 'rgba(236, 72, 153, 0.2)'}` 
                      }}
                    >
                      {item.badgeText}
                    </span>
                  </div>
                ))
              ) : (
                <div style={{ padding: '16px 18px', fontSize: '13px', color: 'var(--slate-500)', textAlign: 'center' }}>
                  No records match your query. Try searching for "Prestige", "Aurelia", or "Royal Palms".
                </div>
              )}
            </div>
          )}
        </div>

        {/* Sample search tags */}
        {MOCK_PROPERTIES.length > 0 && (
          <div className="suggestion-labels">
            <span style={{ display: 'flex', alignItems: 'center', marginRight: '6px', color: 'var(--slate-400)' }}>Quick Audits:</span>
            {MOCK_PROPERTIES.map(p => (
              <span 
                key={p.id}
                className="suggestion-label-item"
                onClick={() => setSelectedProperty(p)}
              >
                {p.name.split(' (')[0]}
              </span>
            ))}
          </div>
        )}

        {/* Clean summary block right below search bar when selected */}
        {selectedProperty && (
          <div className="detail-overlay-card">
            <div className="detail-card-header">
              <div>
                <h3 className="detail-card-title">{selectedProperty.name}</h3>
                <p className="detail-card-subtitle">
                  <MapPin size={12} style={{ display: 'inline', marginRight: '4px', verticalAlign: 'middle', color: 'var(--primary)' }} />
                  {selectedProperty.location}
                </p>
              </div>
            </div>

            <div className="detail-card-grid">
              <div className="detail-grid-item">
                <span className="detail-label">Registered Owner</span>
                <span className="detail-value">{selectedProperty.ownerName}</span>
              </div>
            </div>

            <div className="detail-card-footer">
              <span style={{ fontSize: '11.5px', color: 'var(--slate-400)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <ShieldCheck size={14} style={{ color: getRiskColor(selectedProperty.status) }} />
                Registry match verified via SignalX node.
              </span>
              <button className="button-link" onClick={startDownloadReport}>
                <Download size={14} />
                <span>Download Compliance Report</span>
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Progress Compilation Modal */}
      {isDownloading && selectedProperty && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 className="modal-title">Generating Audited Dossier</h3>
            </div>

            <div className="modal-body">
              <p style={{ fontSize: '13.5px', color: 'var(--slate-500)', marginBottom: '20px' }}>
                Please wait while we audit all state records, court registries, and spatial zoning files for <strong>{selectedProperty.name}</strong>.
              </p>

              <div className="progress-list">
                <div className={`progress-step ${downloadStep >= 1 ? 'completed' : downloadStep === 0 ? 'active' : ''}`}>
                  {downloadStep >= 1 ? <CheckCircle2 size={16} /> : <div className="loader-ring" />}
                  <span>1. Fetching Registry Deed Logs from SRO...</span>
                </div>

                <div className={`progress-step ${downloadStep >= 2 ? 'completed' : downloadStep === 1 ? 'active' : ''}`}>
                  {downloadStep >= 2 ? <CheckCircle2 size={16} /> : downloadStep === 1 ? <div className="loader-ring" /> : <div style={{ width: 16 }} />}
                  <span>2. Scanning Litigation & Judicial Databases...</span>
                </div>

                <div className={`progress-step ${downloadStep >= 3 ? 'completed' : downloadStep === 2 ? 'active' : ''}`}>
                  {downloadStep >= 3 ? <CheckCircle2 size={16} /> : downloadStep === 2 ? <div className="loader-ring" /> : <div style={{ width: 16 }} />}
                  <span>3. Verifying RERA Promoter filings...</span>
                </div>

                <div className={`progress-step ${downloadStep >= 4 ? 'completed' : downloadStep === 3 ? 'active' : ''}`}>
                  {downloadStep >= 4 ? <CheckCircle2 size={16} /> : downloadStep === 3 ? <div className="loader-ring" /> : <div style={{ width: 16 }} />}
                  <span>4. Performing GIS zoning offset calculations...</span>
                </div>

                <div className={`progress-step ${downloadStep >= 5 ? 'completed' : downloadStep === 4 ? 'active' : ''}`}>
                  {downloadStep >= 5 ? <CheckCircle2 size={16} /> : downloadStep === 4 ? <div className="loader-ring" /> : <div style={{ width: 16 }} />}
                  <span>5. Compiling PDF report and checksum...</span>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button 
                className="search-button" 
                disabled={downloadStep < 5}
                onClick={() => setIsDownloading(false)}
                style={{ 
                  cursor: downloadStep < 5 ? 'not-allowed' : 'pointer', 
                  opacity: downloadStep < 5 ? 0.6 : 1 
                }}
              >
                <span>Complete</span>
              </button>
            </div>
          </div>
        </div>
      )}

      <TelanganaMapModal
        isOpen={showMapModal}
        onClose={() => setShowMapModal(false)}
        searchQuery={searchQuery}
      />

      {/* Background City Skyline (Blue vector outline art) */}
      <div className="skyline-container">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 300" preserveAspectRatio="none" style={{ width: '100%', height: '100%' }}>
          {/* Back Layer Skyline (Faint Blue Lines) */}
          <path 
            d="M 0 300 L 0 180 L 40 180 L 40 120 L 90 120 L 90 200 L 130 200 L 130 90 L 180 90 L 180 220 L 220 220 L 220 140 L 280 140 L 280 250 L 320 250 L 320 160 L 390 160 L 390 100 L 450 100 L 450 200 L 510 200 L 510 130 L 580 130 L 580 220 L 640 220 L 640 70 L 710 70 L 710 190 L 760 190 L 760 150 L 820 150 L 820 240 L 880 240 L 880 110 L 950 110 L 950 210 L 1020 210 L 1020 130 L 1080 130 L 1080 250 L 1140 250 L 1140 80 L 1210 80 L 1210 220 L 1260 220 L 1260 160 L 1320 160 L 1320 200 L 1390 200 L 1390 120 L 1460 120 L 1460 240 L 1520 240 L 1520 170 L 1600 170 L 1600 300 Z" 
            fill="none" 
            stroke="rgba(59, 130, 246, 0.1)" 
            strokeWidth="1.5" 
          />
          
          {/* Back layer building grids (faint window highlights) */}
          <line x1="65" y1="130" x2="65" y2="190" stroke="rgba(59, 130, 246, 0.08)" strokeWidth="1" strokeDasharray="3 6" />
          <line x1="155" y1="100" x2="155" y2="210" stroke="rgba(59, 130, 246, 0.08)" strokeWidth="1" strokeDasharray="3 6" />
          <line x1="420" y1="110" x2="420" y2="190" stroke="rgba(59, 130, 246, 0.08)" strokeWidth="1" strokeDasharray="3 6" />
          <line x1="675" y1="80" x2="675" y2="180" stroke="rgba(59, 130, 246, 0.08)" strokeWidth="1" strokeDasharray="3 6" />
          <line x1="1175" y1="90" x2="1175" y2="210" stroke="rgba(59, 130, 246, 0.08)" strokeWidth="1" strokeDasharray="3 6" />
          
          {/* Front Layer Skyline (Brighter Glowing Blue Lines) */}
          <path 
            d="M 0 300 L 0 220 L 60 220 L 60 160 L 110 160 L 110 240 L 160 240 L 160 150 L 240 150 L 240 210 L 300 210 L 300 110 L 360 110 L 360 260 L 410 260 L 410 170 L 480 170 L 480 200 L 530 200 L 530 90 L 610 90 L 610 240 L 670 240 L 670 140 L 740 140 L 740 210 L 790 210 L 790 120 L 860 120 L 860 230 L 920 230 L 920 160 L 980 160 L 980 220 L 1050 220 L 1050 70 L 1120 70 L 1120 250 L 1190 250 L 1190 140 L 1250 140 L 1250 210 L 1300 210 L 1300 180 L 1370 180 L 1370 110 L 1450 110 L 1450 260 L 1500 260 L 1500 190 L 1600 190 L 1600 300 Z" 
            fill="rgba(15, 23, 42, 0.2)" 
            stroke="rgba(96, 165, 250, 0.2)" 
            strokeWidth="1.5" 
          />

          {/* Front layer detailed building windows and accents */}
          <rect x="180" y="165" width="40" height="30" fill="none" stroke="rgba(96, 165, 250, 0.1)" strokeWidth="1" />
          <rect x="550" y="110" width="40" height="60" fill="none" stroke="rgba(96, 165, 250, 0.1)" strokeWidth="1" />
          <rect x="810" y="140" width="30" height="50" fill="none" stroke="rgba(96, 165, 250, 0.1)" strokeWidth="1" />
          <rect x="1070" y="90" width="35" height="120" fill="none" stroke="rgba(96, 165, 250, 0.1)" strokeWidth="1" />
          
          {/* Building Antennas */}
          <line x1="330" y1="110" x2="330" y2="70" stroke="rgba(96, 165, 250, 0.25)" strokeWidth="1.5" />
          <circle cx="330" cy="70" r="3" fill="#60a5fa" opacity="0.3" />
          
          <line x1="1085" y1="70" x2="1085" y2="40" stroke="rgba(96, 165, 250, 0.25)" strokeWidth="1.5" />
          <circle cx="1085" cy="40" r="3" fill="#60a5fa" opacity="0.3" />
        </svg>
      </div>

      {/* Footer */}
      <footer className="footer-bar">
        <span>&copy; 2026 SignalX Property Discovery. Enterprise Due Diligence.</span>
        <div style={{ display: 'flex', gap: '20px' }}>
          <span style={{ cursor: 'pointer' }}>Terms</span>
          <span style={{ cursor: 'pointer' }}>Privacy</span>
          <span style={{ cursor: 'pointer' }}>API</span>
        </div>
      </footer>
    </div>
  );
}

export default App;
