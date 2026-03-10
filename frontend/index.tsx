import React, { useState, useEffect, useCallback } from 'react';
import './PortalCard.css';
import { createComponentLogger } from '../../../src/utils/debug';
import { Button } from '../../../src/components/ui';
import { useWakeonlanControls } from './hooks/useWakeonlanControls';
import type { WolTarget, DhcpLease } from './types';

const logger = createComponentLogger('WakeonlanTablet');

const WakeonlanTablet: React.FC = () => {
  const { getTargets, wake, wakeAll, getLeases, addTarget, removeTarget, isLoading, error } = useWakeonlanControls();
  const [targets, setTargets] = useState<WolTarget[]>([]);
  const [leases, setLeases] = useState<DhcpLease[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  const loadTargets = useCallback(async () => {
    try {
      const list = await getTargets();
      setTargets(list);
      setMessage(null);
      logger.info('Targets loaded', { count: list.length });
    } catch (err) {
      logger.error('Failed to load targets', err);
      setTargets([]);
      setMessage(err instanceof Error ? err.message : 'Failed to load targets');
    }
  }, [getTargets]);

  const loadLeases = useCallback(async () => {
    try {
      const list = await getLeases();
      setLeases(list);
      logger.info('Leases loaded', { count: list.length });
    } catch (err) {
      logger.error('Failed to load leases', err);
      setLeases([]);
    }
  }, [getLeases]);

  useEffect(() => {
    loadTargets();
    loadLeases();
  }, [loadTargets, loadLeases]);

  const handleWake = async (name: string) => {
    setMessage(null);
    try {
      await wake(name);
      setMessage(`Sent WoL to ${name}. Wait 30–60 s then connect.`);
      logger.info('WoL sent', { name });
    } catch (err) {
      logger.error('Wake failed', err);
      setMessage(err instanceof Error ? err.message : 'Wake failed');
    }
  };

  const handleWakeAll = async () => {
    setMessage(null);
    try {
      const res = await wakeAll();
      const count = res.woke?.length ?? 0;
      setMessage(`Sent WoL to ${count} target(s). Wait 30–60 s then connect.`);
      logger.info('WoL wake-all sent', { count });
    } catch (err) {
      logger.error('Wake all failed', err);
      setMessage(err instanceof Error ? err.message : 'Wake all failed');
    }
  };

  const handleAddFromLease = async (lease: DhcpLease) => {
    setMessage(null);
    try {
      const name = lease.hostname || lease['ip-address'];
      await addTarget(name, lease['hw-address'], undefined, lease['ip-address']);
      setMessage(`Added ${name} to WoL targets`);
      logger.info('Added target from lease', { name, mac: lease['hw-address'] });
      // Reload targets to show the new one
      await loadTargets();
    } catch (err) {
      logger.error('Add target from lease failed', err);
      setMessage(err instanceof Error ? err.message : 'Add target failed');
    }
  };

  const handleRemoveTarget = async (name: string) => {
    setMessage(null);
    try {
      await removeTarget(name);
      setMessage(`Removed ${name} from WoL targets`);
      logger.info('Removed WoL target', { name });
      // Reload targets to remove from list
      await loadTargets();
    } catch (err) {
      logger.error('Remove target failed', err);
      setMessage(err instanceof Error ? err.message : 'Remove target failed');
    }
  };

  // Get MAC addresses already in targets for filtering leases
  const targetMacs = new Set(targets.map(t => t.mac.toLowerCase()));

  return (
    <div className="wakeonlan-tablet">
      <h2>Wake on LAN</h2>
      <p>Targets from <code>premium/wakeonlan.csv</code>. One tap to send magic packet from phone over Tailscale.</p>

      {error && (
        <div className="wakeonlan-message error">{error}</div>
      )}

      {/* Current WoL Targets Section */}
      <div className="wakeonlan-section">
        <h3>WoL Targets</h3>
        {isLoading && targets.length === 0 ? (
          <p className="wakeonlan-empty">Loading targets…</p>
        ) : targets.length === 0 ? (
          <p className="wakeonlan-empty">No targets. Add from DHCP leases below.</p>
        ) : (
          <>
            <ul className="wakeonlan-targets">
              {targets.map((t) => (
                <li key={t.name} className="wakeonlan-target-item">
                  <div className="wakeonlan-target-info">
                    <span className="wakeonlan-target-name">{t.name}</span>
                    <div className="wakeonlan-target-mac">{t.mac}</div>
                  </div>
                  <div className="wakeonlan-target-actions">
                    <Button variant="primary" onClick={() => handleWake(t.name)} disabled={isLoading}>
                      Wake
                    </Button>
                    <Button variant="outline" onClick={() => handleRemoveTarget(t.name)} disabled={isLoading}>
                      Remove
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
            {targets.length > 1 && (
              <div className="wakeonlan-actions">
                <Button variant="secondary" onClick={handleWakeAll} disabled={isLoading}>
                  Wake all
                </Button>
              </div>
            )}
          </>
        )}
      </div>

      {/* DHCP Leases Section */}
      <div className="wakeonlan-section">
        <h3>DHCP Leases</h3>
        {leases.length === 0 ? (
          <p className="wakeonlan-empty">No DHCP leases found.</p>
        ) : (
          <ul className="wakeonlan-leases">
            {leases
              .filter(lease => !targetMacs.has(lease['hw-address'].toLowerCase()))
              .map((lease) => (
                <li key={lease['ip-address']} className="wakeonlan-lease-item">
                  <div className="wakeonlan-lease-info">
                    <span className="wakeonlan-lease-name">{lease.hostname || lease['ip-address']}</span>
                    <div className="wakeonlan-lease-details">
                      IP: {lease['ip-address']} | MAC: {lease['hw-address']}
                    </div>
                  </div>
                  <Button variant="outline" onClick={() => handleAddFromLease(lease)} disabled={isLoading}>
                    Add as WoL Target
                  </Button>
                </li>
              ))}
          </ul>
        )}
      </div>

      {message && (
        <div className="wakeonlan-message">{message}</div>
      )}

      <div className="wakeonlan-actions" style={{ marginTop: '1rem' }}>
        <Button variant="secondary" onClick={() => { loadTargets(); loadLeases(); }} disabled={isLoading}>
          Refresh
        </Button>
      </div>
    </div>
  );
};

export default WakeonlanTablet;
