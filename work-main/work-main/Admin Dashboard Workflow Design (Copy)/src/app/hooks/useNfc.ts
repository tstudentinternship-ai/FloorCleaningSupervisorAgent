import { useEffect, useState } from 'react';
import {
  cancelActiveNfcScan,
  describeNfcAvailability,
  getNfcAvailability,
  getNfcErrorMessage,
  isNfcScanError,
  openNfcSettings,
  scanNfcUid,
  type NfcAvailability,
  type ScanNfcOptions,
} from '../services/nfcService';

export function useNfc() {
  const [availability, setAvailability] = useState<NfcAvailability>({
    platform: 'unknown',
    supported: null,
    enabled: null,
  });
  const [availabilityMessage, setAvailabilityMessage] = useState('');

  useEffect(() => {
    let mounted = true;

    void (async () => {
      const nextAvailability = await getNfcAvailability();
      if (!mounted) {
        return;
      }

      setAvailability(nextAvailability);
      setAvailabilityMessage(describeNfcAvailability(nextAvailability));
    })();

    return () => {
      mounted = false;
      void cancelActiveNfcScan();
    };
  }, []);

  const refreshAvailability = async () => {
    const nextAvailability = await getNfcAvailability();
    setAvailability(nextAvailability);
    setAvailabilityMessage(describeNfcAvailability(nextAvailability));
    return nextAvailability;
  };

  const startScan = async (options?: ScanNfcOptions) => scanNfcUid(options);

  return {
    availability,
    availabilityMessage,
    startScan,
    refreshAvailability,
    cancelScan: cancelActiveNfcScan,
    openSettings: openNfcSettings,
    isNfcScanError,
    getNfcErrorMessage,
  };
}
