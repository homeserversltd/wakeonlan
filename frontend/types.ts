export interface WolTarget {
  name: string;
  mac: string;
  broadcast: string;
}

export interface DhcpLease {
  'ip-address': string;
  'hw-address': string;
  hostname?: string;
  expire?: string;
  state: string;
}

export interface DhcpLeasesResponse {
  success: boolean;
  leases?: DhcpLease[];
  error?: string;
}

export interface WakeonlanTargetsResponse {
  success: boolean;
  targets?: WolTarget[];
  error?: string;
}

export interface WakeonlanWakeResponse {
  success: boolean;
  woke?: { name: string; mac: string }[];
  error?: string;
}

export interface WakeonlanAddTargetResponse {
  success: boolean;
  message?: string;
  error?: string;
}

export interface WakeonlanRemoveTargetResponse {
  success: boolean;
  message?: string;
  error?: string;
}

export interface WakeonlanStatusResponse {
  success: boolean;
  status?: string;
  csv_path?: string;
  target_count?: number;
  message?: string;
  error?: string;
}
