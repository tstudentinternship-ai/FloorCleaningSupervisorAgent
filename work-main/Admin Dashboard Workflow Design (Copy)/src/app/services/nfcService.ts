import { Capacitor } from '@capacitor/core';
import { CapacitorNfc } from '@capgo/capacitor-nfc';

export type NfcScanErrorKind =
  | 'unsupported'
  | 'disabled'
  | 'busy'
  | 'timeout'
  | 'invalid-tag'
  | 'scan-failed'
  | 'canceled';

export class NfcScanError extends Error {
  kind: NfcScanErrorKind;

  constructor(kind: NfcScanErrorKind, message: string) {
    super(message);
    this.name = 'NfcScanError';
    this.kind = kind;
  }
}

export interface NfcAvailability {
  platform: string;
  supported: boolean | null;
  enabled: boolean | null;
}

export interface ScanNfcOptions {
  timeoutMs?: number;
}

type ActiveScanSession = {
  cancel: () => Promise<void>;
};

type NfcEvent = {
  type?: string;
  tag?: {
    id?: number[];
    ndefMessage?: unknown;
  };
};

let activeScanSession: ActiveScanSession | null = null;

function isAndroidPlatform() {
  return Capacitor.getPlatform() === 'android';
}

function bytesToHexUid(bytes: number[] | null | undefined) {
  if (!Array.isArray(bytes) || bytes.length === 0) {
    return '';
  }

  return bytes
    .map(byte => Number(byte).toString(16).padStart(2, '0').toUpperCase())
    .join(':');
}

function extractTagUid(event: NfcEvent): string {
  return bytesToHexUid(event.tag?.id).trim();
}

function buildScanError(error: unknown): NfcScanError {
  if (error instanceof NfcScanError) {
    return error;
  }

  if (error instanceof Error && error.message) {
    return new NfcScanError('scan-failed', error.message);
  }

  return new NfcScanError('scan-failed', 'Unable to read the NFC tag.');
}

function describeAvailability(availability: NfcAvailability) {
  if (availability.supported === false) {
    return 'NFC is not supported on this device.';
  }

  if (availability.enabled === false) {
    return 'NFC is turned off. Enable NFC in device settings and try again.';
  }

  return '';
}

export function getNfcErrorMessage(error: unknown) {
  if (error instanceof NfcScanError) {
    switch (error.kind) {
      case 'unsupported':
        return 'NFC is not supported on this device.';
      case 'disabled':
        return 'NFC is turned off. Enable NFC in device settings and try again.';
      case 'busy':
        return 'An NFC scan is already in progress.';
      case 'timeout':
        return 'NFC scan timed out. Please tap the tag again.';
      case 'invalid-tag':
        return 'The scanned tag could not be read. Try another tag.';
      case 'canceled':
        return 'NFC scan canceled.';
      case 'scan-failed':
      default:
        return error.message || 'Unable to read the NFC tag.';
    }
  }

  return error instanceof Error && error.message ? error.message : 'Unable to read the NFC tag.';
}

export function isNfcScanError(error: unknown): error is NfcScanError {
  return error instanceof NfcScanError;
}

export function describeNfcAvailability(availability: NfcAvailability) {
  return describeAvailability(availability);
}

export async function getNfcAvailability(): Promise<NfcAvailability> {
  if (!isAndroidPlatform()) {
    return {
      platform: Capacitor.getPlatform(),
      supported: false,
      enabled: false,
    };
  }

  try {
    const { supported } = await CapacitorNfc.isSupported();
    if (!supported) {
      return {
        platform: 'android',
        supported: false,
        enabled: false,
      };
    }

    const { status } = await CapacitorNfc.getStatus();
    return {
      platform: 'android',
      supported: true,
      enabled: status !== 'NFC_DISABLED',
    };
  } catch {
    return {
      platform: 'android',
      supported: false,
      enabled: false,
    };
  }
}

export async function openNfcSettings() {
  if (!isAndroidPlatform()) {
    throw new NfcScanError('unsupported', 'NFC settings are only available on Android.');
  }

  await CapacitorNfc.showSettings();
}

export async function cancelActiveNfcScan() {
  if (!activeScanSession) {
    return;
  }

  const session = activeScanSession;
  activeScanSession = null;
  await session.cancel();
}

export async function scanNfcUid(options: ScanNfcOptions = {}): Promise<string> {
  if (!isAndroidPlatform()) {
    throw new NfcScanError('unsupported', 'NFC scanning is only available on Android.');
  }

  if (activeScanSession) {
    throw new NfcScanError('busy', 'An NFC scan is already in progress.');
  }

  const availability = await getNfcAvailability();
  if (availability.supported === false) {
    throw new NfcScanError('unsupported', 'NFC is not supported on this device.');
  }
  if (availability.enabled === false) {
    throw new NfcScanError('disabled', 'NFC is turned off. Enable NFC in device settings and try again.');
  }

  const timeoutMs = options.timeoutMs ?? 30000;
  let settled = false;
  let timeoutId: ReturnType<typeof setTimeout> | undefined;
  let resolvePromise: (uid: string) => void = () => undefined;
  let rejectPromise: (error: unknown) => void = () => undefined;
  const listenerHandles: Array<{ remove: () => Promise<void> }> = [];

  const cleanup = async () => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }

    await Promise.allSettled(listenerHandles.map(handle => handle.remove()));
    await CapacitorNfc.stopScanning().catch(() => undefined);
    activeScanSession = null;
  };

  const settleSuccess = async (uid: string) => {
    if (settled) {
      return;
    }

    settled = true;
    try {
      await cleanup();
    } finally {
      resolvePromise(uid);
    }
  };

  const settleError = async (error: unknown) => {
    if (settled) {
      return;
    }

    settled = true;
    const nextError = buildScanError(error);
    try {
      await cleanup();
    } finally {
      rejectPromise(nextError);
    }
  };

  const scanPromise = new Promise<string>((resolve, reject) => {
    resolvePromise = resolve;
    rejectPromise = reject;
  });

  activeScanSession = {
    cancel: async () => {
      if (settled) {
        return;
      }

      settled = true;
      try {
        await cleanup();
      } finally {
        rejectPromise(new NfcScanError('canceled', 'NFC scan canceled.'));
      }
    },
  };

  try {
    listenerHandles.push(await CapacitorNfc.addListener('nfcEvent', async (event: NfcEvent) => {
      const uid = extractTagUid(event);
      if (!uid) {
        await settleError(new NfcScanError('invalid-tag', 'The scanned tag did not expose a UID.'));
        return;
      }

      await settleSuccess(uid);
    }));

    timeoutId = setTimeout(() => {
      void settleError(new NfcScanError('timeout', 'NFC scan timed out. Please try again.'));
    }, timeoutMs);

    await CapacitorNfc.startScanning({
      invalidateAfterFirstRead: true,
      alertMessage: 'Tap the NFC tag now.',
    });
  } catch (error) {
    await settleError(error);
  }

  return scanPromise;
}
