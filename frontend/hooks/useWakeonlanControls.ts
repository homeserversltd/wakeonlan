import { useState, useCallback } from 'react';
import type { WolTarget, DhcpLease, DhcpLeasesResponse, WakeonlanTargetsResponse, WakeonlanWakeResponse, WakeonlanAddTargetResponse, WakeonlanRemoveTargetResponse } from '../types';

export const useWakeonlanControls = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleError = (err: unknown) => {
    const message = err instanceof Error ? err.message : 'Unknown error';
    setError(message);
    setIsLoading(false);
    throw err;
  };

  const getTargets = useCallback(async (): Promise<WolTarget[]> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/wakeonlan/targets');
      const data: WakeonlanTargetsResponse = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Failed to load targets');
      }
      setIsLoading(false);
      return data.targets ?? [];
    } catch (err) {
      handleError(err);
      throw err;
    }
  }, []);

  const wake = useCallback(async (name: string): Promise<WakeonlanWakeResponse> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/wakeonlan/wake', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      const data: WakeonlanWakeResponse = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Wake failed');
      }
      setIsLoading(false);
      return data;
    } catch (err) {
      handleError(err);
      throw err;
    }
  }, []);

  const wakeAll = useCallback(async (): Promise<WakeonlanWakeResponse> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/wakeonlan/wake', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ wake_all: true }),
      });
      const data: WakeonlanWakeResponse = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Wake all failed');
      }
      setIsLoading(false);
      return data;
    } catch (err) {
      handleError(err);
      throw err;
    }
  }, []);

  const getLeases = useCallback(async (): Promise<DhcpLease[]> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/dhcp/leases');
      const data: DhcpLeasesResponse = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Failed to load leases');
      }
      setIsLoading(false);
      return data.leases ?? [];
    } catch (err) {
      handleError(err);
      throw err;
    }
  }, []);

  const addTarget = useCallback(async (name: string, mac: string, broadcast?: string, ip?: string): Promise<WakeonlanAddTargetResponse> => {
    setIsLoading(true);
    setError(null);
    try {
      const body: { name: string; mac: string; broadcast?: string; ip?: string } = { name, mac };
      if (broadcast) body.broadcast = broadcast;
      if (ip) body.ip = ip;
      const response = await fetch('/api/wakeonlan/targets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data: WakeonlanAddTargetResponse = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.error || data.message || 'Add target failed');
      }
      setIsLoading(false);
      return data;
    } catch (err) {
      handleError(err);
      throw err;
    }
  }, []);

  const removeTarget = useCallback(async (name: string): Promise<WakeonlanRemoveTargetResponse> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/wakeonlan/targets/${encodeURIComponent(name)}`, {
        method: 'DELETE',
      });
      const data: WakeonlanRemoveTargetResponse = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.error || data.message || 'Remove target failed');
      }
      setIsLoading(false);
      return data;
    } catch (err) {
      handleError(err);
      throw err;
    }
  }, []);

  return { getTargets, wake, wakeAll, getLeases, addTarget, removeTarget, isLoading, error };
};
