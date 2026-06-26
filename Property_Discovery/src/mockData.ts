export interface TitleChainNode {
  year: string;
  type: string;
  partyA: string;
  partyB: string;
  value: string;
  docNo: string;
  registrar: string;
}

export interface LitigationCase {
  caseNo: string;
  court: string;
  status: 'Active' | 'Disposed';
  type: string;
  description: string;
  partyA: string;
  partyB: string;
}

export interface TaxRecord {
  year: string;
  amount: string;
  status: 'Paid' | 'Pending';
  receiptNo: string;
}

export interface Property {
  id: string;
  name: string;
  location: string;
  surveyNo: string;
  ownerName: string;
  reraId: string;
  pinCode: string;
  status: 'low' | 'medium' | 'high';
  riskScore: number;
  titleStatus: string;
  litigationCount: string;
  financialStatus: string;
  zone: string;
  areaAcres: number;
  latLong: string;
  elevation: string;
  nearbyWaterbody: string;
  reraProgress: number;
  reraDeveloper: string;
  reraFilingDate: string;
  reraApprovedArea: string;
  boundaryShape: { x: number; y: number; w: number; h: number };
  titleChain: TitleChainNode[];
  litigations: LitigationCase[];
  taxCompliance: TaxRecord[];
}

export const MOCK_PROPERTIES: Property[] = [];
