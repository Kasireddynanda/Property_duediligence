import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';
import 'leaflet/dist/leaflet.css';
import { ArrowLeft, MapPin, Loader2 } from 'lucide-react';
import { API_BASE_URL } from './apiConfig';

export interface MapProjectPoint {
  mongo_id: string;
  id: number;
  name: string;
  lat: number;
  lng: number;
  locality?: string;
  street?: string;
  district?: string;
  registration_no?: string;
  boundaries?: {
    east?: string;
    west?: string;
    north?: string;
    south?: string;
  };
}

interface TelanganaMapModalProps {
  isOpen: boolean;
  onClose: () => void;
  searchQuery?: string;
  apiBaseUrl?: string;
}

const INDIA_CENTER: [number, number] = [20.5937, 78.9629];
const INDIA_ZOOM = 5;

const MAP_EXCLUDED_PROJECTS = new Set(['HEARTLAND ONE','SAI GOKULAM','THE DISTRICT','SWARNA']);

function isVisibleOnMap(point: MapProjectPoint): boolean {
  const name = (point.name || '').trim().toUpperCase();
  return (
    typeof point.lat === 'number' &&
    typeof point.lng === 'number' &&
    !Number.isNaN(point.lat) &&
    !Number.isNaN(point.lng) &&
    !MAP_EXCLUDED_PROJECTS.has(name)
  );
}

const LOCATION_ICON = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

function buildPopupHtml(point: MapProjectPoint): string {
  const lines = [
    `<strong>${point.name || 'Unnamed project'}</strong>`,
    point.district ? `District: ${point.district}` : '',
    point.locality ? `Locality: ${point.locality}` : '',
    point.registration_no ? `RERA: ${point.registration_no}` : '',
    point.street ? `Street: ${point.street}` : '',
  ].filter(Boolean);

  return `<div style="font-size:12px;line-height:1.45;min-width:180px">${lines.join('<br/>')}</div>`;
}

export default function TelanganaMapModal({
  isOpen,
  onClose,
  searchQuery = '',
  apiBaseUrl = API_BASE_URL,
}: TelanganaMapModalProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);

  const [points, setPoints] = useState<MapProjectPoint[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;

    const fetchPoints = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams({ limit: '2000' });
        if (searchQuery.trim()) {
          params.set('q', searchQuery.trim());
        }
        const res = await fetch(`${apiBaseUrl}/api/map/telangana/points?${params}`);
        if (!res.ok) {
          throw new Error(`Map API returned ${res.status}`);
        }
        const data = await res.json();
        const results = (data.results || []).filter((p: MapProjectPoint) => isVisibleOnMap(p));
        setPoints(results);
        setTotalCount(data.total_count ?? results.length);
      } catch (err) {
        console.error(err);
        setError('Could not load map projects. Ensure the Telangana API is running on port 8000.');
        setPoints([]);
        setTotalCount(0);
      } finally {
        setIsLoading(false);
      }
    };

    fetchPoints();
  }, [isOpen, searchQuery, apiBaseUrl]);

  useEffect(() => {
    if (!isOpen || !mapContainerRef.current) return;

    if (!mapRef.current) {
      mapRef.current = L.map(mapContainerRef.current, {
        zoomControl: true,
        attributionControl: true,
      });
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 19,
      }).addTo(mapRef.current);
      markersLayerRef.current = L.layerGroup().addTo(mapRef.current);
    }

    mapRef.current.setView(INDIA_CENTER, INDIA_ZOOM);

    setTimeout(() => {
      mapRef.current?.invalidateSize();
    }, 100);
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen || !mapRef.current || !markersLayerRef.current) return;

    markersLayerRef.current.clearLayers();

    for (const point of points) {
      const marker = L.marker([point.lat, point.lng], { icon: LOCATION_ICON });
      marker.bindPopup(buildPopupHtml(point));
      marker.addTo(markersLayerRef.current);
    }
  }, [isOpen, points]);

  useEffect(() => {
    if (isOpen) return;
    if (mapRef.current) {
      mapRef.current.remove();
      mapRef.current = null;
      markersLayerRef.current = null;
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="map-fullpage">
      <div className="map-fullpage-toolbar">
        <button type="button" className="map-back-btn" onClick={onClose}>
          <ArrowLeft size={16} />
          <span>Back to Discovery</span>
        </button>

        <div className="map-fullpage-title-wrap">
          <h2 className="map-fullpage-title">
            <MapPin size={18} />
            India Project Map
          </h2>
          <p className="map-fullpage-subtitle">
            {isLoading
              ? 'Loading project locations...'
              : `${points.length} locations plotted of ${totalCount} projects${searchQuery.trim() ? ` matching "${searchQuery.trim()}"` : ''}`}
          </p>
        </div>
      </div>

      {error && <div className="map-fullpage-error">{error}</div>}

      <div className="map-fullpage-body">
        {isLoading && (
          <div className="map-loading-overlay">
            <Loader2 size={28} className="map-spinner" />
            <span>Fetching map pins from INFRA.Map_telangana...</span>
          </div>
        )}
        <div ref={mapContainerRef} className="india-leaflet-map" />
      </div>
    </div>
  );
}
