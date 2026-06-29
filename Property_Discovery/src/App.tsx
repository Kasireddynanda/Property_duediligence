import { useState, useEffect, useRef } from 'react';
import { MOCK_PROPERTIES } from './mockData';
import type { Property } from './mockData';
import TelanganaMapModal from './TelanganaMapModal';
import { API_BASE_URL } from './apiConfig';
import {
  Search,
  Globe,
  MapPin,
  ShieldCheck,
  ArrowRight,
  ChevronDown,
  Map,
  ArrowLeft,
  FileText,
  Building,
  X,
  Loader2,
  Sparkles,
  Users,
  Monitor,
  CheckCircle2,
  Info,
  Newspaper
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
  { code: 'DL', label: 'Delhi (DL)' },
  { code: 'TN', label: 'Tamil Nadu (TN)' },
  { code: 'MP', label: 'Madhya Pradesh (MP)' },
  { code: 'KA', label: 'Karnataka (KA)' },
] as const;

const PROJECT_REPORT_INCLUDES = [
  {
    title: 'Litigations related to the project',
    description: 'Active and disposed litigation flags linked to this RERA registration.',
  },
  {
    title: 'Promotors other projects',
    description: 'Portfolio view of the promoter’s other registered projects and their completion status.',
  },
  {
    title: 'Risk indicators',
    description: 'Key risk takeaways from registry filings, financial disclosures, and compliance signals.',
  },
  {
    title: 'A detailed report on the project',
    description: 'Full project dossier covering land parcels, bank details, address, and registration data.',
  },
] as const;

const PROPRIETOR_REPORT_INCLUDES = [
  {
    title: 'Company Identity & Status',
    description: 'Public Limited Company, CIN, age of the company, active status, and location.',
  },
  {
    title: 'Compliance & Registrations',
    description: 'GST, ESIC, EPF, PAN, TAN, and other statutory registrations.',
  },
  {
    title: 'Ownership & Management',
    description: 'Number of directors, signatories, and promoter quality.',
  },
  {
    title: 'Risk Indicators',
    description: 'Financial health, credit history, defaults, blacklists, sanctions, PEP checks, litigation history, and market sentiment.',
  },
  {
    title: 'Business Operations',
    description: 'Core business activities, nature of business, import/export activities, number of employees, contact details, and operational footprint.',
  },
] as const;

function ProjectReportIncludes({
  variant = 'list',
  reportType = 'project',
}: {
  variant?: 'list' | 'tooltip' | 'points';
  reportType?: 'project' | 'proprietor';
}) {
  const includes = reportType === 'project' ? PROJECT_REPORT_INCLUDES : PROPRIETOR_REPORT_INCLUDES;
  const heading = reportType === 'project' ? 'Project Report includes' : 'Promoter Report includes';

  if (variant === 'tooltip') {
    return (
      <div className="report-includes-tooltip">
        <p className="report-includes-tooltip-heading">{heading}</p>
        <ul className="report-includes-tooltip-list">
          {includes.map((item) => (
            <li key={item.title}>{item.title}</li>
          ))}
        </ul>
      </div>
    );
  }

  if (variant === 'points') {
    return (
      <ul className="report-includes-points">
        {includes.map((item) => (
          <li key={item.title}>
            <CheckCircle2 size={16} className="report-includes-point-icon" />
            <div>
              <span className="report-includes-point-title">{item.title}</span>
              <span className="report-includes-point-desc">{item.description}</span>
            </div>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <ul className="report-includes-hover-list">
      {includes.map((item) => (
        <li key={item.title} className="report-includes-hover-item">
          <div className="report-includes-hover-row">
            <CheckCircle2 size={15} className="report-includes-hover-icon" />
            <span>{item.title}</span>
            <Info size={14} className="report-includes-info-icon" />
          </div>
          <p className="report-includes-hover-desc">{item.description}</p>
        </li>
      ))}
    </ul>
  );
}

const REPORT_TYPE_LABELS: Record<string, string> = {
  project: 'Project Report',
  proprietor: 'Promoter Report',
  none: 'Web Only',
};

interface LeadFormErrors {
  name?: string;
  email?: string;
  mobile?: string;
  submit?: string;
}

function validateLeadForm(form: {
  name: string;
  email: string;
  mobile: string;
}): LeadFormErrors {
  const errors: LeadFormErrors = {};
  const name = form.name.trim();

  if (name.length < 2) {
    errors.name = 'Name must be at least 2 characters';
  } else if (!/^[A-Za-z][A-Za-z\s'.-]{1,99}$/.test(name)) {
    errors.name = 'Name should contain only letters';
  }

  const email = form.email.trim();
  if (!email) {
    errors.email = 'Email is required';
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    errors.email = 'Enter a valid email address';
  }

  let mobile = form.mobile.replace(/[\s\-()]/g, '');
  if (mobile.startsWith('+91')) mobile = mobile.slice(3);
  else if (mobile.startsWith('91') && mobile.length === 12) mobile = mobile.slice(2);
  else if (mobile.startsWith('0') && mobile.length === 11) mobile = mobile.slice(1);

  if (!mobile) {
    errors.mobile = 'Mobile number is required';
  } else if (!/^[6-9]\d{9}$/.test(mobile)) {
    errors.mobile = 'Enter a valid 10-digit Indian mobile number';
  }

  return errors;
}

const TELANGANA_CERTIFICATE_BASE =
  'https://rerait.telangana.gov.in/SearchList/GetShowCertificateFileContent';

function buildTelanganaCertificateUrl(qstr?: string | null): string | undefined {
  if (!qstr) return undefined;
  return `${TELANGANA_CERTIFICATE_BASE}?QueryStringID=${encodeURIComponent(qstr)}`;
}

function resolveTelanganaCertificate(project: any): { download_url?: string } | undefined {
  if (project.certificate?.download_url) {
    return project.certificate;
  }
  const downloadUrl = buildTelanganaCertificateUrl(project.certificate_qstr);
  return downloadUrl ? { download_url: downloadUrl } : undefined;
}

function getProjectTimelineDates(property: Property): {
  approvedDate?: string;
  proposedCompletion?: string;
} {
  const details = property.liveDetails;
  const approvedDate =
    details?.project_information?.['Approved Date'] ||
    details?.['About the Project']?.['Project Start Date'] ||
    property.reraFilingDate ||
    undefined;
  const proposedCompletion =
    details?.project_information?.['Proposed Date of Completion'] ||
    details?.['About the Project']?.['Proposed/ Expected Date of Project Completion as specified in Form B'] ||
    undefined;

  return {
    approvedDate: approvedDate && approvedDate !== 'N/A' ? String(approvedDate) : undefined,
    proposedCompletion:
      proposedCompletion && proposedCompletion !== 'N/A' ? String(proposedCompletion) : undefined,
  };
}

const TELANGANA_DETAIL_SECTIONS = [
  'promoter_information',
  'project_information',
  'land_details',
  'built_up_area_details',
  'bank_details',
  'address_details',
  'member_information',
] as const;

function buildTelanganaLiveDetails(project: any): Record<string, Record<string, unknown>> {
  const sections: Record<string, Record<string, unknown>> = {};
  for (const key of TELANGANA_DETAIL_SECTIONS) {
    const value = project[key];
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      sections[key] = value;
    }
  }
  if (project.certificate && typeof project.certificate === 'object') {
    sections.certificate = project.certificate;
  } else {
    const cert = resolveTelanganaCertificate(project);
    if (cert) {
      sections.certificate = cert;
    }
  }
  return sections;
}

function hasTelanganaDetailedSections(payload: any): boolean {
  return Boolean(
    payload?.project_information ||
      payload?.promoter_information ||
      payload?.land_details ||
      payload?.bank_details
  );
}

function applyTelanganaDbRecord(base: Property, dbRecord: any): Property {
  const liveDetails = buildTelanganaLiveDetails(dbRecord);
  const address = dbRecord.address_details || {};
  const locationParts = [
    address['Street Name'],
    address.Locality,
    address.District,
    address.State,
  ].filter(Boolean);

  return {
    ...base,
    name: dbRecord.project_name || base.name,
    ownerName:
      dbRecord.promoter_organization_name ||
      dbRecord.promoter_information?.['Organization Name'] ||
      dbRecord.promoter_name ||
      base.ownerName,
    reraId:
      dbRecord.rera_registration_id ||
      dbRecord.project_information?.['Registration Number'] ||
      base.reraId,
    location: locationParts.length > 0 ? locationParts.join(', ') : base.location,
    reraFilingDate:
      dbRecord.project_information?.['Approved Date'] ||
      dbRecord.registration_date ||
      dbRecord.last_modified ||
      base.reraFilingDate,
    zone:
      dbRecord.project_information?.['Project Type'] ||
      dbRecord.search?.project_type_name ||
      base.zone,
    financialStatus: dbRecord.bank_details?.['Bank Name']
      ? `Financed by ${dbRecord.bank_details['Bank Name']}`
      : base.financialStatus,
    liveDetails: Object.keys(liveDetails).length > 0 ? liveDetails : base.liveDetails,
    originalData: {
      ...dbRecord,
      certificate: dbRecord.certificate || resolveTelanganaCertificate(dbRecord),
    },
  };
}

// Map RERA scraped projects search items into a uniform Property structure
function transformInfraToProperty(project: any): Property {
  let detailedPayload = project;

  // Extract Madhya Pradesh certificate URL which is often hidden inside the Registration Number
  if (project.project_info && project.project_info['Registration Number'] && !project.certificate_url) {
    const regStr = String(project.project_info['Registration Number']);
    if (regStr.includes('http')) {
      project.certificate_url = regStr.split(';')[0].trim();
    }
  }

  if (project.tabs) {
    const flattened: Record<string, Record<string, string>> = {};

    Object.entries(project.tabs).forEach(([, tabVal]: [string, any]) => {
      if (tabVal && tabVal.sections && Array.isArray(tabVal.sections)) {
        tabVal.sections.forEach((sec: any) => {
          if (sec.heading) {
            const heading = sec.heading;

            // Skip excessively noisy or verbose infrastructure tables from Delhi RERA
            if (
              heading.includes('Project Building/ Tower/ Block') ||
              heading.includes('Parking Details') ||
              heading.includes('Internal Infrastructure') ||
              heading.includes('External Infrastructure') ||
              heading === 'Section'
            ) {
              return;
            }

            flattened[heading] = flattened[heading] || {};

            if (sec.fields) {
              Object.assign(flattened[heading], sec.fields);
            }
            if (sec.rows && Array.isArray(sec.rows)) {
              sec.rows.forEach((row: any, idx: number) => {
                Object.entries(row).forEach(([k, v]) => {
                  flattened[heading][`${k} (Item ${idx + 1})`] = String(v);
                });
              });
            }
          }
        });
      }
    });

    if (project.document_links && Array.isArray(project.document_links)) {
      flattened['All Document Links'] = {};
      project.document_links.forEach((doc: any, idx: number) => {
        if (doc.url && doc.title) {
          flattened['All Document Links'][`${doc.title} (${idx + 1})`] = doc.url;
        }
      });
    }

    detailedPayload = Object.keys(flattened).length > 0 ? flattened : project;
  } else if (hasTelanganaDetailedSections(project)) {
    detailedPayload = buildTelanganaLiveDetails(project);
  } else if (!project.project_info && !project.project_information && !project.promoter_organization_name) {
    detailedPayload = undefined;
  }

  const address = project.address_details || {};
  const locationParts = [
    address['Street Name'],
    address.Locality,
    address.District,
    address.State,
  ].filter(Boolean);
  const location =
    locationParts.length > 0
      ? locationParts.join(', ')
      : (project.search?.district_name || project.district || 'District Registry') + ', India';

  const pId =
    project.rera_registration_id ||
    project.registration_no ||
    project.project_information?.['Registration Number'] ||
    project.detail_url?.match(/project_id=([^&]+)/)?.[1] ||
    'RERA-' + Math.floor(100000 + Math.random() * 900000);
  return {
    id: `infra-project-${(project.project_name || 'unknown').toLowerCase().replace(/[^a-z0-9]/g, '-')}`,
    name: project.project_name || 'Unknown RERA Project',
    location,
    surveyNo: 'Pending land parcel boundary partition SRO check',
    ownerName:
      project.promoter_organization_name ||
      project.promoter_information?.['Organization Name'] ||
      project.promoter_name ||
      'Unknown Promoter',
    reraId: pId,
    pinCode: 'N/A',
    status: 'medium',
    riskScore: 70,
    titleStatus: 'Under construction',
    litigationCount: '0 Active (Awaiting manual check)',
    financialStatus: 'Promoter: ' + (project.promoter_name || 'N/A'),
    zone:
      project.project_information?.['Project Type'] ||
      project.search?.project_type_name ||
      'Residential/Commercial Development',
    areaAcres: 4.8,
    latLong: project.latitude && project.longitude ? `${project.latitude}° N, ${project.longitude}° E` : '12.9716° N, 77.5946° E',
    elevation: 'N/A',
    nearbyWaterbody: 'Buffer zone compliance check pending',
    reraProgress: 80,
    reraDeveloper: project.promoter_name || 'Regulatory Board Registered',
    reraFilingDate:
      project.project_information?.['Approved Date'] ||
      project.registration_date ||
      project.last_modified ||
      'N/A',
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
    taxCompliance: [],
    liveDetails: detailedPayload,
    originalData: project
  };
}

function getPromoterName(property: Property): string {
  return (
    property.ownerName ||
    property.liveDetails?.promoter_organization_name ||
    property.liveDetails?.promoter_information?.['Organization Name'] ||
    property.liveDetails?.promoter_information?.Name ||
    property.liveDetails?.promoter_name ||
    property.originalData?.promoter_organization_name ||
    property.originalData?.promoter_name ||
    ''
  ).trim();
}

function getPromoterGst(property: Property): string {
  const info = property.liveDetails?.promoter_information || {};
  return (
    info['GST Number'] ||
    info.CompanyGSTIN ||
    property.originalData?.promoter_information?.['GST Number'] ||
    ''
  )
    .trim()
    .toUpperCase();
}

function getPromoterPan(property: Property): string {
  const info = property.liveDetails?.promoter_information || {};
  const pan = (
    info.CompanyPanNo ||
    info['Pan No.'] ||
    info['PAN Number'] ||
    property.originalData?.promoter_information?.CompanyPanNo ||
    ''
  )
    .trim()
    .toUpperCase();
  if (pan) return pan;
  const gst = getPromoterGst(property);
  return gst.length >= 12 ? gst.substring(2, 12) : '';
}

async function submitDiscoveryReportRequest(payload: {
  entity_name: string;
  user: { name: string; email: string; mobile: string };
  report_type: string;
  state: string;
  rera_id?: string;
  promoter_name?: string;
  promoter_gst?: string;
  promoter_pan?: string;
  report_includes: string[];
}): Promise<{ report_id: string; message: string }> {
  const res = await fetch(`${API_BASE_URL}/api/discovery/place-report`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join(', ')
          : 'Failed to place report';
    throw new Error(message || 'Failed to place report');
  }

  return data;
}

interface NameSuggestion {
  id: string;
  name: string;
  originalData: any;
}

function getCollectionForState(state: string): string | null {
  if (state === 'DL') return 'Delhi_allprojects_detailed';
  if (state === 'MP') return 'MP_detailed';
  if (state === 'TS') return 'Telangana_Detailed';
  return null;
}

async function fetchInfraSearchResults(query: string, state: string, signal?: AbortSignal): Promise<any[]> {
  const collection = getCollectionForState(state);
  if (collection) {
    const params = new URLSearchParams({
      q: query,
      collection,
      page: '1',
      page_size: '8',
    });
    const res = await fetch(`${API_BASE_URL}/api/generic/search?${params}`, { signal });
    if (res.ok) {
      const data = await res.json();
      return data.results || [];
    }
    return [];
  }

  const params = new URLSearchParams({ q: query, page: '1', page_size: '8' });
  const res = await fetch(`${API_BASE_URL}/api/infra/search?${params}`, { signal });
  if (res.ok) {
    const data = await res.json();
    return data.results || [];
  }
  return [];
}

function projectNeedsDetailFetch(project: any, state: string, prop: Property): boolean {
  if (state === 'TS') {
    return !hasTelanganaDetailedSections(prop.liveDetails);
  }
  if (state === 'DL' || state === 'MP') {
    return !prop.liveDetails || (!project.tabs && !project.project_information);
  }
  return !prop.liveDetails;
}

async function loadPropertyWithFullDetails(project: any, state: string): Promise<Property> {
  let prop = transformInfraToProperty(project);

  if (!projectNeedsDetailFetch(project, state, prop)) {
    return prop;
  }

  const collection = getCollectionForState(state);
  if (!collection) {
    return prop;
  }

  const params = new URLSearchParams({
    project_name: project.project_name || prop.name,
    collection,
  });
  const reraId = project.rera_registration_id || prop.reraId;
  if (reraId && !String(reraId).startsWith('RERA-')) {
    params.set('rera_id', String(reraId));
  }

  const res = await fetch(`${API_BASE_URL}/api/generic/details?${params}`);
  if (!res.ok) {
    return prop;
  }

  const result = await res.json();
  if (result.status === 'success' && result.data) {
    if (state === 'TS') {
      prop = applyTelanganaDbRecord(prop, result.data);
    } else {
      prop = transformInfraToProperty(result.data);
    }
  }

  return prop;
}

const RERA_FACTS = [
  "RERA stands for Real Estate (Regulation and Development) Act, 2016.",
  "The Act was passed by the Indian Parliament in 2016 and became fully effective on 1 May 2017.",
  "RERA was introduced to bring transparency, accountability, and efficiency to the real estate sector.",
  "Every state and union territory has its own Real Estate Regulatory Authority (RERA).",
  "Most real estate projects with more than 8 apartments or over 500 sq. meters of land must be registered under RERA.",
  "Builders cannot advertise, market, or sell a project without RERA registration.",
  "Developers must deposit 70% of buyers' funds in a separate escrow account for construction and land costs.",
  "Properties must be sold based on Carpet Area, not super built-up area.",
  "Developers are required to provide regular project updates on the state RERA portal.",
  "Buyers have the right to know project approvals, layout plans, completion timelines, and litigation details.",
  "If a builder delays possession, buyers can seek compensation or request a refund with interest.",
  "Builders are responsible for structural defects for five years after possession.",
  "RERA has established a dedicated dispute resolution mechanism through the Authority and Appellate Tribunal.",
  "Non-compliance with RERA can result in heavy penalties, cancellation of registration, or imprisonment.",
  "RERA has significantly improved homebuyer protection and developer accountability in India.",
  "State RERA portals contain millions of property and developer records, making them valuable for due diligence and real estate analytics.",
  "RERA data can be used for property verification, developer risk assessment, fraud detection, and investment intelligence.",
  "Maharashtra has the highest number of RERA-registered projects in India.",
  "RERA has increased trust and transparency in India's real estate market.",
  "The Act empowers homebuyers by giving them legal rights and access to reliable project information."
];

function App() {
  const [selectedProperty, setSelectedProperty] = useState<Property | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const searchCacheRef = useRef<Record<string, UnifiedSuggestion[]>>({});
  const headerSearchCacheRef = useRef<Record<string, NameSuggestion[]>>({});

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/recent-searches`)
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          setRecentSearches(data.data);
        }
      })
      .catch(err => console.warn('Failed to fetch recent searches', err));
  }, []);

  const saveRecentSearch = async (query: string, propName?: string, reraId?: string) => {
    if (!query.trim() && !propName) return;
    try {
      await fetch(`${API_BASE_URL}/api/recent-searches`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          state: selectedState,
          property_name: propName,
          rera_id: reraId
        })
      });
    } catch (e) {
      console.warn("Failed to save recent search", e);
    }
  };
  const [suggestions, setSuggestions] = useState<UnifiedSuggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const [selectedState, setSelectedState] = useState<string>('TS');
  const [showStateDropdown, setShowStateDropdown] = useState<boolean>(false);
  const [showNewsModal, setShowNewsModal] = useState<boolean>(false);
  const [newsData, setNewsData] = useState<any[]>([]);
  const [isNewsLoading, setIsNewsLoading] = useState<boolean>(false);
  const [showMapModal, setShowMapModal] = useState<boolean>(false);

  // New States for Lead Capture and Details View
  const [viewMode, setViewMode] = useState<'search' | 'details'>('search');
  const [showLeadModal, setShowLeadModal] = useState<boolean>(false);
  const [showPlaceReportModal, setShowPlaceReportModal] = useState<boolean>(false);
  const [showReportDropdown, setShowReportDropdown] = useState<boolean>(false);
  const [placeReportType, setPlaceReportType] = useState<'project' | 'proprietor'>('project');
  const [projectReportPlaced, setProjectReportPlaced] = useState<boolean>(false);
  const [isPlacingReport, setIsPlacingReport] = useState<boolean>(false);
  const [placeReportError, setPlaceReportError] = useState<string | null>(null);
  const [leadForm, setLeadForm] = useState({ name: '', email: '', mobile: '', reportType: 'project' });
  const [leadFormErrors, setLeadFormErrors] = useState<LeadFormErrors>({});
  const [isSubmittingLead, setIsSubmittingLead] = useState<boolean>(false);
  const [leadSubmitSuccess, setLeadSubmitSuccess] = useState<string | null>(null);
  const [isCrawling, setIsCrawling] = useState<boolean>(false);
  const [displayedSummary, setDisplayedSummary] = useState<string>('');

  const [headerSearchActive, setHeaderSearchActive] = useState<boolean>(false);
  const [headerSearchQuery, setHeaderSearchQuery] = useState<string>('');
  const [headerSuggestions, setHeaderSuggestions] = useState<NameSuggestion[]>([]);
  const [headerSearchLoading, setHeaderSearchLoading] = useState<boolean>(false);
  const [showHeaderSuggestions, setShowHeaderSuggestions] = useState<boolean>(false);

  const [currentFactIndex, setCurrentFactIndex] = useState(0);

  useEffect(() => {
    if (isLoading || headerSearchLoading || isNewsLoading) {
      const interval = setInterval(() => {
        setCurrentFactIndex((prev) => (prev + 1) % RERA_FACTS.length);
      }, 10000);
      return () => clearInterval(interval);
    }
  }, [isLoading, headerSearchLoading, isNewsLoading]);

  const headerSearchRef = useRef<HTMLDivElement>(null);
  const headerInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (viewMode === 'details' && selectedProperty?.liveDetails && !isCrawling) {
      const pName = selectedProperty.name || 'This property';
      const pType = selectedProperty.liveDetails?.project_information?.['Project Type'] || selectedProperty.liveDetails?.['About the Project']?.['Type of Project'] || selectedProperty.zone || 'real estate';
      const promoter = selectedProperty.ownerName || 'its promoter';
      const reraId = selectedProperty.reraId || 'a registered ID';
      const approved = selectedProperty.liveDetails?.project_information?.['Approved Date'] || selectedProperty.liveDetails?.['About the Project']?.['Project Start Date'] || selectedProperty.reraFilingDate || 'an unknown date';
      const target = selectedProperty.liveDetails?.project_information?.['Proposed Date of Completion'] || selectedProperty.liveDetails?.['About the Project']?.['Proposed/ Expected Date of Project Completion as specified in Form B'] || 'the future';
      const area = selectedProperty.liveDetails?.land_details?.['Net Area(In sqmts)'] || selectedProperty.liveDetails?.['Project Land Details']?.['Total Area of Land Proposed to be developed (in sqr mtrs)'] || selectedProperty.areaAcres;
      const dist = selectedProperty.liveDetails?.address_details?.District || selectedProperty.location || 'the local';
      
      const cost = selectedProperty.liveDetails?.['About the Project']?.['Project Cost (in rupees)'] || selectedProperty.liveDetails?.project_info?.['Total Cost Of Project'] || 'an undisclosed amount';
      const bank = selectedProperty.liveDetails?.['Bank Account Details of the Special/Separate Account to be maintained in a Schedule Bank']?.['Bank Name'] || selectedProperty.liveDetails?.bank_details?.['Bank Name'] || 'a scheduled bank';

      let litsText = 'no active litigations';
      if (selectedProperty.liveDetails?.project_information?.['Litigations related to the project ?'] === 'Yes' || selectedProperty.litigationCount?.includes('Active')) {
         litsText = 'active litigations';
      }

      const fullText = `Based on the RERA registry database, ${pName} (Registration: ${reraId}) is a ${pType} project officially registered under ${promoter}. The project's development was authorized on ${approved} and has a proposed completion timeline targeting ${target}. The property spans an area of ${area} in the ${dist} region. According to the latest financial disclosures, the project is banking with ${bank} with a declared project cost of ${cost}. Furthermore, our preliminary scan of the registry indicates that there are currently ${litsText} flagged against this project. This AI-generated overview verifies the project's foundational legitimacy, providing immediate transparency into its regulatory standing within the state's framework.`;

      const words = fullText.split(' ');
      let index = 0;
      setDisplayedSummary('');

      const timer = setInterval(() => {
        if (index < words.length) {
          const currentWord = words[index];
          setDisplayedSummary(prev => prev + (prev ? ' ' : '') + currentWord);
          index++;
        } else {
          clearInterval(timer);
        }
      }, 50);

      return () => clearInterval(timer);
    } else {
      setDisplayedSummary('');
    }
  }, [viewMode, selectedProperty, isCrawling]);

  const searchBoxRef = useRef<HTMLDivElement>(null);
  const stateSelectorRef = useRef<HTMLDivElement>(null);

  const selectedStateLabel =
    STATE_OPTIONS.find((s) => s.code === selectedState)?.label ?? 'Telangana (TS)';

  // Debounced fuzzy search effect integrating the APIs from rera-scraper & hi-extension
  useEffect(() => {
    if (!searchQuery.trim() || searchQuery.trim().length < 3) {
      setSuggestions([]);
      return;
    }

    const queryKey = `${selectedState}-${searchQuery.trim().toLowerCase()}`;
    if (searchCacheRef.current[queryKey]) {
      setSuggestions(searchCacheRef.current[queryKey]);
      return;
    }

    setIsLoading(true);
    const abortController = new AbortController();

    const delayDebounceFn = setTimeout(async () => {
      const query = searchQuery.trim();
      const resultsList: UnifiedSuggestion[] = [];

      // Fetch from local RERA Search API
      try {
        if (selectedState === 'DL' || selectedState === 'MP' || selectedState === 'TS') {
          const collectionName =
            selectedState === 'DL'
              ? 'Delhi_allprojects_detailed'
              : selectedState === 'MP'
                ? 'MP_detailed'
                : 'Telangana_Detailed';
          const params = new URLSearchParams({
            q: query,
            collection: collectionName,
            page: "1",
            page_size: "5"
          });
          const res = await fetch(`${API_BASE_URL}/api/generic/search?${params}`, { signal: abortController.signal });
          if (res.ok) {
            const data = await res.json();
            if (data && data.results) {
              const infraMatches = data.results.map((project: any) => {
                const score = Math.max(
                  fuzzyScore(query, project.project_name || ''),
                  fuzzyScore(query, project.promoter_name || ''),
                  fuzzyScore(query, project.promoter_organization_name || ''),
                  fuzzyScore(query, project.rera_registration_id || '')
                );
                return {
                  id: `infra-${(project.project_name || 'unknown').replace(/\s+/g, '_')}`,
                  type: 'infra_project' as const,
                  name: project.project_name || 'Unknown Project',
                  subtitle: `Promoter: ${project.promoter_organization_name || project.promoter_name || 'Unknown'} | District: ${project.address_details?.District || project.district || project.search?.district_name || 'N/A'}`,
                  badgeText: selectedState === 'TS' ? 'RERA project' : 'Live Data',
                  riskStatus: 'medium' as const,
                  score,
                  originalData: project
                };
              });
              resultsList.push(...infraMatches);
            }
          }
        } else {
          // Fallback to legacy listing API for TN, KA
          const params = new URLSearchParams({
            q: query,
            page: "1",
            page_size: "5"
          });
          const res = await fetch(`${API_BASE_URL}/api/infra/search?${params}`, { signal: abortController.signal });
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
        }
      } catch (err: any) {
        if (err.name !== 'AbortError') {
          console.warn("Local RERA Search API is currently unreachable", err);
        }
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
      searchCacheRef.current[queryKey] = uniqueResults;
      setIsLoading(false);
    }, 300);

    return () => {
      clearTimeout(delayDebounceFn);
      abortController.abort();
    };
  }, [searchQuery, selectedState]);

  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (searchBoxRef.current && !searchBoxRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
      if (stateSelectorRef.current && !stateSelectorRef.current.contains(e.target as Node)) {
        setShowStateDropdown(false);
      }
      if (headerSearchRef.current && !headerSearchRef.current.contains(e.target as Node)) {
        setShowHeaderSuggestions(false);
        setHeaderSearchActive(false);
        setHeaderSearchQuery('');
        setHeaderSuggestions([]);
      }
    };
    document.addEventListener('click', handleOutsideClick);
    return () => document.removeEventListener('click', handleOutsideClick);
  }, []);

  useEffect(() => {
    if (headerSearchActive) {
      headerInputRef.current?.focus();
    }
  }, [headerSearchActive]);

  useEffect(() => {
    if (!headerSearchActive || !headerSearchQuery.trim() || headerSearchQuery.trim().length < 3) {
      setHeaderSuggestions([]);
      setHeaderSearchLoading(false);
      return;
    }

    const queryKey = `${selectedState}-${headerSearchQuery.trim().toLowerCase()}`;
    if (headerSearchCacheRef.current[queryKey]) {
      setHeaderSuggestions(headerSearchCacheRef.current[queryKey]);
      return;
    }

    setHeaderSearchLoading(true);
    const abortController = new AbortController();

    const delayDebounceFn = setTimeout(async () => {
      const query = headerSearchQuery.trim();
      try {
        const results = await fetchInfraSearchResults(query, selectedState, abortController.signal);
        const names: NameSuggestion[] = results.map((project: any) => ({
          id: `header-${(project.project_name || 'unknown').replace(/\s+/g, '_')}`,
          name: project.project_name || 'Unknown Project',
          originalData: project,
        }));

        const unique: NameSuggestion[] = [];
        const seen = new Set<string>();
        for (const item of names) {
          const key = item.name.toLowerCase();
          if (!seen.has(key)) {
            seen.add(key);
            unique.push(item);
          }
        }

        setHeaderSuggestions(unique);
        headerSearchCacheRef.current[queryKey] = unique;
      } catch (err: any) {
        if (err.name !== 'AbortError') {
          console.warn('Header search failed', err);
          setHeaderSuggestions([]);
        }
      } finally {
        setHeaderSearchLoading(false);
      }
    }, 300);

    return () => {
      clearTimeout(delayDebounceFn);
      abortController.abort();
    };
  }, [headerSearchQuery, headerSearchActive, selectedState]);

  const handleHeaderSuggestionSelect = async (item: NameSuggestion) => {
    setShowHeaderSuggestions(false);
    setHeaderSearchActive(false);
    setHeaderSearchQuery('');
    setHeaderSuggestions([]);
    setIsCrawling(true);

    try {
      const fullProp = await loadPropertyWithFullDetails(item.originalData, selectedState);
      setSelectedProperty(fullProp);
      setViewMode('details');
      saveRecentSearch(item.name, fullProp.name, fullProp.reraId);
    } catch (err) {
      console.error('Failed to load property details', err);
    } finally {
      setIsCrawling(false);
    }
  };

  const handlePlaceReportConfirm = async () => {
    if (!selectedProperty || isPlacingReport) return;

    setIsPlacingReport(true);
    setPlaceReportError(null);
    try {
      const reportIncludes = placeReportType === 'project' 
        ? PROJECT_REPORT_INCLUDES.map((item) => item.title)
        : PROPRIETOR_REPORT_INCLUDES.map((item) => item.title);
      const localId = selectedProperty.id.replace(/[^a-zA-Z0-9-]/g, '') || 'project';

      await submitDiscoveryReportRequest({
        entity_name: selectedProperty.name,
        promoter_name: getPromoterName(selectedProperty) || undefined,
        user: {
          name: 'Property Discovery',
          email: `place-report+${localId}@local.dev`,
          mobile: '9000000000',
        },
        report_type: placeReportType,
        state: selectedState,
        rera_id:
          selectedProperty.reraId && !selectedProperty.reraId.startsWith('RERA-')
            ? selectedProperty.reraId
            : undefined,
        report_includes: reportIncludes,
      });

      setProjectReportPlaced(true);
      setShowPlaceReportModal(false);
    } catch (err) {
      setPlaceReportError(err instanceof Error ? err.message : 'Failed to place report');
    } finally {
      setIsPlacingReport(false);
    }
  };

  const activateHeaderSearch = () => {
    setHeaderSearchActive(true);
    setHeaderSearchQuery('');
    setShowHeaderSuggestions(false);
    setHeaderSuggestions([]);
  };

  const handleLeadFormSubmit = async () => {
    const errors = validateLeadForm(leadForm);
    setLeadFormErrors(errors);
    setLeadSubmitSuccess(null);
    if (Object.keys(errors).length > 0 || !selectedProperty) {
      return;
    }

    setIsSubmittingLead(true);
    try {
      let mobile = leadForm.mobile.replace(/[\s\-()]/g, '');
      if (mobile.startsWith('+91')) mobile = mobile.slice(3);
      else if (mobile.startsWith('91') && mobile.length === 12) mobile = mobile.slice(2);
      else if (mobile.startsWith('0') && mobile.length === 11) mobile = mobile.slice(1);

      const reportIncludes =
        leadForm.reportType === 'project'
          ? PROJECT_REPORT_INCLUDES.map((item) => item.title)
          : PROPRIETOR_REPORT_INCLUDES.map((item) => item.title);

      await submitDiscoveryReportRequest({
        entity_name: selectedProperty.name,
        promoter_name: getPromoterName(selectedProperty) || undefined,
        promoter_gst: getPromoterGst(selectedProperty) || undefined,
        promoter_pan: getPromoterPan(selectedProperty) || undefined,
        user: {
          name: leadForm.name.trim(),
          email: leadForm.email.trim(),
          mobile,
        },
        report_type: leadForm.reportType,
        state: selectedState,
        rera_id:
          selectedProperty.reraId && !selectedProperty.reraId.startsWith('RERA-')
            ? selectedProperty.reraId
            : undefined,
        report_includes: reportIncludes,
      });

      setLeadSubmitSuccess(
        leadForm.reportType === 'proprietor'
          ? 'Promoter report saved. Portfolio and RiskMaster wishlist are being created.'
          : 'Report request saved. Promoter portfolio is being loaded.',
      );
      setShowLeadModal(false);
      setViewMode('details');

      if (leadForm.reportType === 'project') {
        setProjectReportPlaced(true);
      }

      if (leadForm.reportType === 'none' && selectedProperty) {
        const collection = getCollectionForState(selectedState);
        if (collection && projectNeedsDetailFetch(selectedProperty.originalData || {}, selectedState, selectedProperty)) {
          setIsCrawling(true);
          loadPropertyWithFullDetails(
            selectedProperty.originalData || { project_name: selectedProperty.name },
            selectedState,
          )
            .then((fullProp) => setSelectedProperty(fullProp))
            .catch((err) => console.error('Details load error:', err))
            .finally(() => setIsCrawling(false));
        }
      }
    } catch (err) {
      setLeadFormErrors({
        submit: err instanceof Error ? err.message : 'Failed to place report. Please try again.',
      });
    } finally {
      setIsSubmittingLead(false);
    }
  };

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
            <span style={{ fontWeight: 700, fontSize: '15px', letterSpacing: '-0.3px', color: '#e2e8f0' }}></span>
            <span style={{ fontWeight: 400, fontSize: '11px', color: '#64748b', letterSpacing: '0.5px', textTransform: 'uppercase' }}>Properties</span>
          </div>
        </div>

        <div className="nav-actions">

          {selectedState === 'TS' && (
            <button
              type="button"
              className="map-header-btn"
              data-tooltip="Property News"
              onClick={async () => {
                setShowNewsModal(true);
                if (newsData.length === 0) {
                  setIsNewsLoading(true);
                  try {
                    const res = await fetch(`${API_BASE_URL}/api/news`);
                    const data = await res.json();
                    if (data.status === 'success') {
                      setNewsData(data.data);
                    }
                  } catch (e) {
                    console.error('Failed to load news', e);
                  } finally {
                    setIsNewsLoading(false);
                  }
                }
              }}
            >
              <Newspaper size={16} />
            </button>
          )}

          {selectedState === 'TS' && (
            <button
              type="button"
              className="map-header-btn"
              data-tooltip="Open Telangana project map"
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

      {viewMode === 'search' ? (
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
              <button className="search-button" onClick={() => saveRecentSearch(searchQuery)}>
                <span>Search</span>
                
              </button>
            </div>
            
            {/* Recent Searches Row */}
            {recentSearches.length > 0 && !showSuggestions && (
              <div style={{ marginTop: '16px', display: 'flex', flexWrap: 'wrap', gap: '8px', justifyContent: 'center' }}>
                <span style={{ fontSize: '12px', color: 'rgba(255, 255, 255, 0.7)', display: 'flex', alignItems: 'center' }}>Recent:</span>
                {recentSearches.slice(0, 5).map((search, idx) => (
                  <span 
                    key={idx} 
                    onClick={() => {
                       setSearchQuery(search);
                       setShowSuggestions(true);
                    }}
                    style={{ 
                      fontSize: '12px', padding: '4px 12px', backgroundColor: 'transparent', color: '#ffffff', 
                      borderRadius: '12px', cursor: 'pointer', border: '1px solid rgba(255, 255, 255, 0.3)', transition: 'all 0.2s' 
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.1)'; e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.6)'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.3)'; }}
                  >
                    {search}
                  </span>
                ))}
              </div>
            )}

            {/* Autocomplete Dropdown List */}
            {showSuggestions && searchQuery.trim() !== '' && (
              <div className="suggestions-dropdown">
                <div className="suggestion-header">Matched Records</div>
                {isLoading ? (
                  <div style={{ padding: '16px 18px', fontSize: '13px', color: 'var(--slate-500)', display: 'flex', alignItems: 'flex-start', gap: '8px', lineHeight: 1.4 }}>
                    <div className="loader-ring" style={{ width: 14, height: 14, flexShrink: 0, marginTop: '2px' }}></div>
                    <span style={{ fontStyle: 'italic' }}>
                      <strong>Quick Fact:</strong> <span style={{ fontWeight: 500, color: 'var(--slate-700)' }}>{RERA_FACTS[currentFactIndex]}</span>
                    </span>
                  </div>
                ) : suggestions.length > 0 ? (
                  suggestions.map(item => (
                    <div
                      key={item.id}
                      className="suggestion-row"
                      onClick={() => {
                        let prop: Property | undefined;
                        if (item.type === 'property') {
                          prop = item.originalData as Property;
                          setSelectedProperty(prop);
                        } else if (item.type === 'infra_project') {
                          prop = transformInfraToProperty(item.originalData);
                          setSelectedProperty(prop);
                        }
                        
                        if (prop) {
                           saveRecentSearch(searchQuery, prop.name, prop.reraId);
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
                  Registry match verified via  node.
                </span>
                <button className="button-link" onClick={() => {
                  setLeadFormErrors({});
                  setLeadSubmitSuccess(null);
                  setShowLeadModal(true);
                }}>
                  <ArrowRight size={14} />
                  <span>View Full Details</span>
                </button>
              </div>
            </div>
          )}
        </main>
      ) : (
        <main className="details-container">
          {selectedProperty && (
            isCrawling ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '80vh', width: '100%' }}>
                <Loader2 size={64} className="map-spinner" style={{ color: 'var(--brand-blue)', marginBottom: '24px' }} />
                <h2 style={{ color: '#0f172a', marginBottom: '12px', fontSize: '24px', fontWeight: 'bold' }}>Loading RERA Details...</h2>
                <p style={{ color: '#64748b', fontSize: '16px', maxWidth: '500px', textAlign: 'center', lineHeight: '1.5' }}>
                  Fetching promoter history, structural data, and land parcels from the registry database.
                </p>
              </div>
            ) : (
              <div className="details-content-wrapper">
                <div className="details-top-bar">
                  <div className="details-title-row">
                    <button className="back-btn-simple" onClick={() => setViewMode('search')}>
                      <ArrowLeft size={20} />
                    </button>

                    <div className="details-title-search" ref={headerSearchRef}>
                      {headerSearchActive ? (
                        <input
                          ref={headerInputRef}
                          type="text"
                          className="details-title-input"
                          value={headerSearchQuery}
                          onChange={(e) => {
                            setHeaderSearchQuery(e.target.value);
                            setShowHeaderSuggestions(true);
                          }}
                          onFocus={() => setShowHeaderSuggestions(true)}
                          placeholder="Search by project name..."
                          onKeyDown={(e) => {
                            if (e.key === 'Escape') {
                              setHeaderSearchActive(false);
                              setHeaderSearchQuery('');
                              setShowHeaderSuggestions(false);
                              setHeaderSuggestions([]);
                            }
                          }}
                        />
                      ) : (
                        <h1 className="details-main-title">{selectedProperty.name.toUpperCase()}</h1>
                      )}
                      <button
                        type="button"
                        className="details-title-search-btn"
                        title="Search another project"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (headerSearchActive) {
                            setHeaderSearchActive(false);
                            setHeaderSearchQuery('');
                            setShowHeaderSuggestions(false);
                            setHeaderSuggestions([]);
                          } else {
                            activateHeaderSearch();
                          }
                        }}
                      >
                        <Search size={18} />
                      </button>

                      {headerSearchActive && showHeaderSuggestions && headerSearchQuery.trim() !== '' && (
                        <div className="details-header-suggestions">
                          {headerSearchLoading ? (
                            <div className="details-header-suggestion-loading">
                              <Loader2 size={14} className="map-spinner" />
                              <span>Searching projects...</span>
                            </div>
                          ) : headerSuggestions.length > 0 ? (
                            headerSuggestions.map((item) => (
                              <button
                                key={item.id}
                                type="button"
                                className="details-header-suggestion-item"
                                onClick={() => handleHeaderSuggestionSelect(item)}
                              >
                                {item.name}
                              </button>
                            ))
                          ) : (
                            <div className="details-header-suggestion-empty">No projects match your query.</div>
                          )}
                        </div>
                      )}
                    </div>

                    <div className="details-actions">
                      {(() => {
                        const { approvedDate, proposedCompletion } = getProjectTimelineDates(selectedProperty);
                        return (
                          <>
                            {approvedDate && (
                              <div className="details-date-chip">
                                <span className="details-date-label">Approved Date</span>
                                <span className="details-date-value">{approvedDate}</span>
                              </div>
                            )}
                            {proposedCompletion && (
                              <div className="details-date-chip">
                                <span className="details-date-label">Proposed Date of Completion</span>
                                <span className="details-date-value">{proposedCompletion}</span>
                              </div>
                            )}
                          </>
                        );
                      })()}
                      {(selectedProperty.liveDetails?.certificate?.download_url || selectedProperty.originalData?.certificate?.download_url || selectedProperty.originalData?.certificate_url) && (
                        <a 
                          href={selectedProperty.liveDetails?.certificate?.download_url || selectedProperty.originalData?.certificate?.download_url || selectedProperty.originalData?.certificate_url} 
                          target="_blank" 
                          rel="noreferrer"
                          style={{
                            display: 'inline-flex', alignItems: 'center', gap: '6px', 
                            padding: '8px 14px', backgroundColor: '#f0fdf4', color: '#16a34a', 
                            borderRadius: '6px', border: '1px solid #bbf7d0', 
                            fontWeight: 600, fontSize: '13px', textDecoration: 'none'
                          }}
                        >
                          <FileText size={16} /> RERA Certificate
                        </a>
                      )}
                      <div className="report-order-dropdown-wrapper" style={{ position: 'relative' }}>
                        <button
                          type="button"
                          className="primary-dropdown-btn"
                          onClick={() => setShowReportDropdown(!showReportDropdown)}
                        >
                          Place Order <ChevronDown size={16} />
                        </button>
                        {showReportDropdown && (
                          <div className="report-dropdown-menu" style={{
                            position: 'absolute',
                            top: '100%',
                            right: 0,
                            marginTop: '8px',
                            background: '#fff',
                            border: '1px solid #e2e8f0',
                            borderRadius: '8px',
                            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                            zIndex: 50,
                            minWidth: '220px',
                            display: 'flex',
                            flexDirection: 'column',
                            overflow: 'hidden'
                          }}>
                            <button
                              type="button"
                              className="report-dropdown-item"
                              style={{
                                padding: '12px 16px',
                                background: 'transparent',
                                border: 'none',
                                textAlign: 'left',
                                fontSize: '13px',
                                fontWeight: 600,
                                color: '#1e293b',
                                cursor: 'pointer',
                                borderBottom: '1px solid #e2e8f0',
                                transition: 'background 0.2s'
                              }}
                              onClick={() => {
                                setPlaceReportType('project');
                                setShowPlaceReportModal(true);
                                setShowReportDropdown(false);
                              }}
                              onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#f1f5f9'}
                              onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                            >
                              Place Project Report
                            </button>
                            <button
                              type="button"
                              className="report-dropdown-item"
                              style={{
                                padding: '12px 16px',
                                background: 'transparent',
                                border: 'none',
                                textAlign: 'left',
                                fontSize: '13px',
                                fontWeight: 600,
                                color: '#1e293b',
                                cursor: 'pointer',
                                transition: 'background 0.2s'
                              }}
                              onClick={() => {
                                setPlaceReportType('proprietor');
                                setShowPlaceReportModal(true);
                                setShowReportDropdown(false);
                              }}
                              onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#f1f5f9'}
                              onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                            >
                              Place Promoter Report
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="details-meta-row">
                    <span><span className="meta-lbl">Industry:</span> Real Estate Development</span>
                    <span><span className="meta-lbl">Location:</span> {selectedProperty.location.split(',')[0]}</span>
                    <span><span className="meta-lbl">RERA/CIN:</span> {selectedProperty.reraId}</span>
                    <span><span className="meta-lbl">Updated On:</span> {selectedProperty.reraFilingDate}</span>
                  </div>
                </div>

                <div className="details-white-card">
                  {leadSubmitSuccess && (
                    <div className="lead-success-banner">
                      <CheckCircle2 size={16} />
                      <span>{leadSubmitSuccess}</span>
                    </div>
                  )}
                  {projectReportPlaced && (
                    <div className="details-table-card report-includes-card">
                      <div className="table-card-header report-includes-card-header">
                        <FileText size={16} />
                        <span>Your Project Report Includes</span>
                      </div>
                      <div className="report-includes-card-body">
                        <ProjectReportIncludes variant="points" />
                      </div>
                    </div>
                  )}

                  {!selectedProperty.liveDetails && (
                    <>
                      <div className="details-table-card">
                        <div className="table-card-header">Property Information</div>
                        <div className="prop-data-grid">
                          <div className="prop-data-group">
                            <span className="prop-lbl">Project Name</span>
                            <span className="prop-val">{selectedProperty.name.toUpperCase()}</span>
                          </div>
                          <div className="prop-data-group">
                            <span className="prop-lbl">RERA / CIN</span>
                            <span className="prop-val">{selectedProperty.reraId}</span>
                          </div>
                          <div className="prop-data-group">
                            <span className="prop-lbl">Project Status</span>
                            <span className="prop-val"><span className={`status-text-${selectedProperty.status === 'low' ? 'active' : selectedProperty.status}`}>{selectedProperty.status === 'low' ? 'Active' : 'Under Review'}</span></span>
                          </div>
                          <div className="prop-data-group">
                            <span className="prop-lbl">Project Category</span>
                            <span className="prop-val">{selectedProperty.zone}</span>
                          </div>
                          <div className="prop-data-group">
                            <span className="prop-lbl">Ownership Type</span>
                            <span className="prop-val">{selectedProperty.titleStatus}</span>
                          </div>
                          <div className="prop-data-group">
                            <span className="prop-lbl">Total Area</span>
                            <span className="prop-val">{selectedProperty.areaAcres} Acres</span>
                          </div>
                          <div className="prop-data-group">
                            <span className="prop-lbl">Survey Numbers</span>
                            <span className="prop-val">{selectedProperty.surveyNo}</span>
                          </div>
                          <div className="prop-data-group">
                            <span className="prop-lbl">Financial State</span>
                            <span className="prop-val">{selectedProperty.financialStatus}</span>
                          </div>
                          <div className="prop-data-group" style={{ gridColumn: '1 / -1', borderBottom: 'none' }}>
                            <span className="prop-lbl">Address</span>
                            <span className="prop-val">{selectedProperty.location}, PIN: {selectedProperty.pinCode}</span>
                          </div>
                        </div>
                      </div>

                      {selectedProperty.litigations && selectedProperty.litigations.length > 0 && (
                        <div className="details-table-card" style={{ marginTop: '24px' }}>
                          <div className="table-card-header" style={{ backgroundColor: '#fee2e2' }}>Litigation & Disputes ({selectedProperty.litigationCount})</div>
                          <div style={{ padding: '0' }}>
                            {selectedProperty.litigations.map((lit, idx) => (
                              <div key={idx} style={{ padding: '16px 24px', borderBottom: '1px solid #e2e8f0' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                                  <span style={{ fontWeight: 600, color: '#0f172a', fontSize: '14px' }}>{lit.caseNo}</span>
                                  <span className={`badge badge-${lit.status === 'Active' ? 'high' : 'low'}`}>{lit.status}</span>
                                </div>
                                <div style={{ fontSize: '13px', color: '#64748b', marginBottom: '8px' }}>{lit.court}</div>
                                <div style={{ fontSize: '14px', color: '#334155' }}>{lit.description}</div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  )}

                  {/* AI Summary Banner */}
                  {selectedProperty.liveDetails && (
                    <div className="details-table-card" style={{ marginTop: '0px', marginBottom: '24px', background: 'linear-gradient(to right, #f0f9ff, #f8fafc)', borderLeft: '4px solid #3b82f6', padding: '24px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                        <Sparkles size={20} style={{ color: '#3b82f6' }} />
                        <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#1e40af', margin: 0 }}>Discovery Summary</h3>
                      </div>
                      <p style={{ fontSize: '15px', color: '#334155', lineHeight: '1.6', margin: 0, minHeight: '80px' }}>
                        {displayedSummary}
                        <span style={{ opacity: displayedSummary ? 1 : 0, animation: 'pulse 1s infinite', marginLeft: '2px', color: '#3b82f6' }}>▋</span>
                      </p>
                    </div>
                  )}

                  {/* Dynamic Live Details Rendering */}
                  {selectedProperty.liveDetails && Object.entries(selectedProperty.liveDetails)
                    .map(([key, value]) => {
                      if (typeof value !== 'object' || value === null || Array.isArray(value)) return null;
                      if (
                        key === 'directions' || 
                        key === 'certificate' || 
                        key === 'extension_certificate' ||
                        key.toLowerCase().includes('bank')
                      ) return null;

                      return (
                        <div key={key} className="details-table-card" style={{ marginTop: '24px' }}>
                          <div className="table-card-header" style={{ backgroundColor: '#f8fafc', color: '#1e293b' }}>
                            {key.replace(/_/g, ' ').toUpperCase()}
                          </div>
                          <div className="prop-data-grid">
                            {Object.entries(value as Record<string, any>).map(([subKey, subVal]) => {
                              if (typeof subVal === 'object') return null;

                              const valStr = String(subVal);
                              const isUrl = valStr.startsWith('http') || valStr.includes('.pdf') || subKey.toLowerCase().includes('url') || subKey.toLowerCase().includes('document') || key.toLowerCase().includes('document');

                              return (
                                <div key={subKey} className="prop-data-group">
                                  <span className="prop-lbl">{subKey.replace(/_/g, ' ')}</span>
                                  <span className="prop-val">
                                    {isUrl && valStr.trim() !== '' && valStr !== '-' && valStr !== 'N/A' && valStr !== 'None' ? (
                                      <a href={valStr.startsWith('http') ? valStr : `https://${valStr}`} target="_blank" rel="noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: '#ef4444', textDecoration: 'none', fontWeight: 500, backgroundColor: '#fee2e2', padding: '4px 10px', borderRadius: '4px', fontSize: '13px' }}>
                                        <FileText size={14} />
                                        <span>PDF Document</span>
                                      </a>
                                    ) : (
                                      valStr || '-'
                                    )}
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })
                  }

                </div>
              </div>
            )
          )}
        </main>
      )}

      {/* Place Report Confirmation Modal */}
      {showPlaceReportModal && selectedProperty && (
        <div className="modal-overlay" onClick={() => setShowPlaceReportModal(false)}>
          <div className="modal-content place-report-modal" onClick={(e) => e.stopPropagation()}>
            <div className="place-report-modal-header">
              <div className="place-report-modal-icon">
                <FileText size={22} />
              </div>
              <div>
                <h3 className="modal-title">Place Report</h3>
                <p className="place-report-modal-subtitle">Confirm report request for this project</p>
              </div>
              <button
                type="button"
                className="place-report-close-btn"
                onClick={() => setShowPlaceReportModal(false)}
                aria-label="Close"
              >
                <X size={18} />
              </button>
            </div>

            <div className="modal-body place-report-modal-body">
              <p>
                Do you want to place a due diligence report on{' '}
                <strong>{placeReportType === 'proprietor' ? (getPromoterName(selectedProperty) || selectedProperty.ownerName || 'this promoter') : selectedProperty.name}</strong>?
              </p>

              <div className="place-report-includes-block">
                <p className="place-report-includes-label">Your {placeReportType === 'project' ? 'Project' : 'Promoter'} Report will include:</p>
                <ProjectReportIncludes variant="list" reportType={placeReportType} />
              </div>

              <p className="place-report-modal-note">
                Hover each item for more detail. All projects by this promoter will be loaded from the RERA database.
              </p>
              {placeReportError && (
                <p className="field-error-text" style={{ marginTop: '12px' }}>{placeReportError}</p>
              )}
            </div>

            <div className="modal-footer place-report-modal-footer">
              <button
                type="button"
                className="place-report-cancel-btn"
                onClick={() => setShowPlaceReportModal(false)}
                disabled={isPlacingReport}
              >
                Cancel
              </button>
              <button
                type="button"
                className="place-report-confirm-btn"
                onClick={handlePlaceReportConfirm}
                disabled={isPlacingReport}
              >
                {isPlacingReport ? 'Placing Report...' : 'Confirm'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Lead Capture Modal */}
      {showLeadModal && selectedProperty && (
        <div className="modal-overlay">
          <div className="modal-content lead-modal-content" style={{ maxWidth: '680px', borderRadius: '24px', overflow: 'hidden', border: '1px solid #e2e8f0', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)' }}>
            <div className="modal-header" style={{ background: 'linear-gradient(135deg, rgb(39, 99, 197), rgb(18, 81, 229))', padding: '28px 24px', borderBottom: 'none' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                    <div style={{ backgroundColor: 'rgba(59, 130, 246, 0.2)', padding: '8px', borderRadius: '10px' }}>
                      <ShieldCheck size={22} style={{ color: '#60a5fa' }} />
                    </div>
                    <h3 className="modal-title" style={{ color: '#ffffff', fontSize: '20px', letterSpacing: '-0.5px', margin: 0 }}>Unlock Due Diligence Report</h3>
                  </div>
                  <p style={{ color: '#94a3b8', fontSize: '14px', margin: 0, marginTop: '8px', lineHeight: 1.5 }}>
                    Access complete RERA compliance history, litigation checks, and structural data for <strong style={{ color: '#ffffff', fontWeight: 600 }}>{selectedProperty.name}</strong>.
                  </p>
                </div>
                <button
                  className="icon-btn"
                  style={{ width: 32, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8', background: 'rgba(255,255,255,0.1)', borderRadius: '50%', border: 'none', cursor: 'pointer' }}
                  onClick={() => setShowLeadModal(false)}
                >
                  <X size={16} />
                </button>
              </div>
            </div>
            
            <div className="modal-body" style={{ padding: '32px 24px', backgroundColor: '#ffffff' }}>
              {leadFormErrors.submit && (
                <div className="lead-form-error-banner">{leadFormErrors.submit}</div>
              )}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label" style={{ fontWeight: 600, color: '#334155', fontSize: '13px' }}>Full Name</label>
                  <input
                    type="text"
                    value={leadForm.name}
                    onChange={e => {
                      setLeadForm({ ...leadForm, name: e.target.value });
                      if (leadFormErrors.name) setLeadFormErrors({ ...leadFormErrors, name: undefined });
                    }}
                    className={`form-input ${leadFormErrors.name ? 'form-input-error' : ''}`}
                    style={{ padding: '12px 16px', borderRadius: '10px', border: '1px solid #cbd5e1', backgroundColor: '#f8fafc', fontSize: '14px', width: '100%', boxSizing: 'border-box' }}
                    placeholder="e.g. John Doe"
                  />
                  {leadFormErrors.name && <span className="field-error-text">{leadFormErrors.name}</span>}
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label" style={{ fontWeight: 600, color: '#334155', fontSize: '13px' }}>Work Email</label>
                  <input
                    type="email"
                    value={leadForm.email}
                    onChange={e => {
                      setLeadForm({ ...leadForm, email: e.target.value });
                      if (leadFormErrors.email) setLeadFormErrors({ ...leadFormErrors, email: undefined });
                    }}
                    className={`form-input ${leadFormErrors.email ? 'form-input-error' : ''}`}
                    style={{ padding: '12px 16px', borderRadius: '10px', border: '1px solid #cbd5e1', backgroundColor: '#f8fafc', fontSize: '14px', width: '100%', boxSizing: 'border-box' }}
                    placeholder="john@company.com"
                  />
                  {leadFormErrors.email && <span className="field-error-text">{leadFormErrors.email}</span>}
                </div>
                <div className="form-group" style={{ marginBottom: 0, gridColumn: '1 / -1' }}>
                  <label className="form-label" style={{ fontWeight: 600, color: '#334155', fontSize: '13px' }}>Mobile Number</label>
                  <input
                    type="tel"
                    value={leadForm.mobile}
                    onChange={e => {
                      setLeadForm({ ...leadForm, mobile: e.target.value });
                      if (leadFormErrors.mobile) setLeadFormErrors({ ...leadFormErrors, mobile: undefined });
                    }}
                    className={`form-input ${leadFormErrors.mobile ? 'form-input-error' : ''}`}
                    style={{ padding: '12px 16px', borderRadius: '10px', border: '1px solid #cbd5e1', backgroundColor: '#f8fafc', fontSize: '14px', width: '100%', boxSizing: 'border-box' }}
                    placeholder="+91 98765 43210"
                  />
                  {leadFormErrors.mobile && <span className="field-error-text">{leadFormErrors.mobile}</span>}
                </div>
              </div>

              <div style={{ marginTop: '28px' }}>
                <label className="form-label" style={{ fontWeight: 600, color: '#334155', marginBottom: '12px', display: 'block', fontSize: '13px' }}>Select Report Scope</label>
                <div className="report-options-grid">
                  <label className={`report-option-card report-option-has-tooltip ${leadForm.reportType === 'project' ? 'selected' : ''}`}>
                    <input
                      type="radio"
                      name="reportType"
                      className="hidden-radio"
                      checked={leadForm.reportType === 'project'}
                      onChange={() => setLeadForm({ ...leadForm, reportType: 'project' })}
                    />
                    <ProjectReportIncludes variant="tooltip" reportType="project" />
                    <div className="option-icon-wrapper blue-icon">
                      <Building size={28} strokeWidth={1.75} />
                    </div>
                    <span className="option-title">Project Report</span>
                    <span className="option-desc">Hover to see what’s included</span>
                  </label>

                  <label className={`report-option-card report-option-has-tooltip ${leadForm.reportType === 'proprietor' ? 'selected' : ''}`}>
                    <input
                      type="radio"
                      name="reportType"
                      className="hidden-radio"
                      checked={leadForm.reportType === 'proprietor'}
                      onChange={() => setLeadForm({ ...leadForm, reportType: 'proprietor' })}
                    />
                    <ProjectReportIncludes variant="tooltip" reportType="proprietor" />
                    <div className="option-icon-wrapper purple-icon">
                      <Users size={28} strokeWidth={1.75} />
                    </div>
                    <span className="option-title">Promoter Report</span>
                    <span className="option-desc">Hover to see what’s included</span>
                  </label>

                  <label className={`report-option-card ${leadForm.reportType === 'none' ? 'selected' : ''}`}>
                    <input
                      type="radio"
                      name="reportType"
                      className="hidden-radio"
                      checked={leadForm.reportType === 'none'}
                      onChange={() => setLeadForm({ ...leadForm, reportType: 'none' })}
                    />
                    <div className="option-icon-wrapper slate-icon">
                      <Monitor size={28} strokeWidth={1.75} />
                    </div>
                    <span className="option-title">Web Only</span>
                    <span className="option-desc">Just view details here</span>
                  </label>
                </div>
              </div>
            </div>
            <div className="modal-footer" style={{ padding: '20px 24px', backgroundColor: '#f8fafc', borderTop: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '12px', color: '#64748b', display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 500 }}>
                <ShieldCheck size={14} style={{ color: '#10b981' }}/> Secure Encrypted Request
              </span>
              <button
                className="search-button"
                style={{ borderRadius: '8px', padding: '10px 20px', fontSize: '14px', fontWeight: 600, background: 'linear-gradient(to right, #2563eb, #3b82f6)', boxShadow: '0 4px 14px 0 rgba(59, 130, 246, 0.39)', border: 'none', color: '#fff', cursor: isSubmittingLead ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', gap: '8px', opacity: isSubmittingLead ? 0.7 : 1 }}
                disabled={isSubmittingLead}
                onClick={() => void handleLeadFormSubmit()}
              >
                {isSubmittingLead ? (
                  <>
                    <Loader2 size={16} className="map-spinner" />
                    <span>Submitting...</span>
                  </>
                ) : (
                  <>
                    <span>{leadForm.reportType === 'none' ? 'View Details' : `Place ${REPORT_TYPE_LABELS[leadForm.reportType] || 'Report'}`}</span>
                    <ArrowRight size={16} />
                  </>
                )}
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

      {/* News Modal */}
      {showNewsModal && (
        <div className="modal-overlay" onClick={() => setShowNewsModal(false)} style={{ zIndex: 1000, display: 'flex', justifyContent: 'flex-end', backgroundColor: 'rgba(15, 23, 42, 0.4)' }}>
          <div 
            className="news-panel" 
            onClick={(e) => e.stopPropagation()} 
            style={{ width: '100%', maxWidth: '420px', backgroundColor: '#fff', height: '100%', display: 'flex', flexDirection: 'column', boxShadow: '-5px 0 25px rgba(0,0,0,0.1)', animation: 'slideInRight 0.3s ease-out' }}
          >
            <div style={{ padding: '20px', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#f8fafc' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Newspaper size={20} color="#3b82f6" />
                <h2 style={{ fontSize: '18px', fontWeight: 600, color: '#0f172a', margin: 0 }}>Real Estate News</h2>
              </div>
              <button 
                onClick={() => setShowNewsModal(false)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px', color: '#64748b' }}
              >
                <X size={18} />
              </button>
            </div>
            
            <div style={{ flex: 1, overflowY: 'auto', padding: '20px', backgroundColor: '#f1f5f9' }}>
              {isNewsLoading ? (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '200px', color: '#64748b' }}>
                  <Loader2 size={24} className="map-spinner" style={{ marginBottom: '12px', color: '#3b82f6' }} />
                  <div style={{ padding: '0 20px', textAlign: 'center', fontSize: '13px', fontStyle: 'italic' }}>
                    <strong>Quick Fact:</strong> <span style={{ fontWeight: 500 }}>{RERA_FACTS[currentFactIndex]}</span>
                  </div>
                </div>
              ) : newsData.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {newsData.map((news, idx) => (
                    <div key={idx} style={{ backgroundColor: '#fff', borderRadius: '8px', overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', border: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column' }}>
                      <a href={news.link} target="_blank" rel="noreferrer" style={{ textDecoration: 'none', color: 'inherit', display: 'flex', flexDirection: 'column' }}>
                        <img 
                          src={`https://loremflickr.com/400/200/india,skyscraper,modern?lock=${idx + 30}`} 
                          alt="Modern Skyscraper" 
                          style={{ width: '100%', height: '180px', objectFit: 'cover' }} 
                        />
                        <div style={{ padding: '16px' }}>
                          <h3 style={{ margin: '0 0 8px 0', fontSize: '15px', color: '#1e40af', lineHeight: 1.4, fontWeight: 600 }}>{news.title}</h3>
                          <p style={{ margin: '0 0 12px 0', fontSize: '13px', color: '#475569', lineHeight: 1.5 }}>{news.snippet}</p>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px', color: '#94a3b8' }}>
                            <span style={{ fontWeight: 500 }}>By {news.author}</span>
                            <span>{news.date}</span>
                          </div>
                        </div>
                      </a>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ textAlign: 'center', color: '#64748b', padding: '40px 20px' }}>
                  No news available right now.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

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
        <span>&copy; 2026  Property Discovery. Enterprise Due Diligence.</span>
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
