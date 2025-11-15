<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import {
    filesApi,
    type DeviceSettings,
    type FileMeta,
    type PlotSettings,
  } from '../lib/filesApi';
  import { PRINT_DEFAULTS, BASE_PLOT_SETTINGS } from '../defaults/printPresets';
  import { DEVICE_DEFAULTS, BASE_DEVICE_SETTINGS } from '../defaults/devicePresets';
  import { showCommandToast } from '../lib/toastStore';
  import PenControls from './actions/PenControls.svelte';
  import DisableMotors from './actions/DisableMotors.svelte';
  import GetStatus from './actions/GetStatus.svelte';

  const NEXTDRAW_MODELS = [
    'AxiDraw V2, V3, or SE/A4',
    'AxiDraw V3/A3 or SE/A3',
    'AxiDraw V3 XLX',
    'AxiDraw MiniKit',
    'AxiDraw SE/A1',
    'AxiDraw SE/A2',
    'AxiDraw V3/B6',
    'Bantam Tools NextDraw™ 8511 (Default)',
    'Bantam Tools NextDraw™ 1117',
    'Bantam Tools NextDraw™ 2234',
  ];

  const PRINT_STORAGE_KEY = 'plotterstudio.printPresets';
  const DEVICE_STORAGE_KEY = 'plotterstudio.devicePresets';

  const readLocalPresets = <T>(key: string): Record<string, Partial<T>> => {
    if (typeof window === 'undefined' || typeof window.localStorage === 'undefined') {
      return {};
    }
    try {
      const raw = window.localStorage.getItem(key);
      if (!raw) {
        return {};
      }
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === 'object') {
        return parsed as Record<string, Partial<T>>;
      }
    } catch (error) {
      console.warn(`Failed to parse presets from ${key}`, error);
    }
    return {};
  };

  const writeLocalPresets = <T>(key: string, data: Record<string, Partial<T>>) => {
    if (typeof window === 'undefined' || typeof window.localStorage === 'undefined') {
      return;
    }
    try {
      window.localStorage.setItem(key, JSON.stringify(data));
    } catch (error) {
      console.warn(`Failed to save presets for ${key}`, error);
    }
  };

  const mergeProfiles = <T extends Record<string, unknown>>(
    defaults: Record<string, Partial<T>>,
    overrides: Record<string, Partial<T>>,
    base: T,
    fallbackName = 'Default'
  ): { name: string; settings: T; protected: boolean }[] => {
    const names = new Set([...Object.keys(defaults), ...Object.keys(overrides)]);
    if (names.size === 0) {
      names.add(fallbackName);
    }
    return Array.from(names)
      .map((name) => {
        const merged = {
          ...base,
          ...(defaults[name] ?? {}),
          ...(overrides[name] ?? {}),
        } as T;
        return {
          name,
          settings: merged,
          protected: Boolean(defaults[name]),
        };
      })
      .sort((a, b) => a.name.localeCompare(b.name));
  };

  type PlotProfile = { name: string; settings: PlotSettings; protected?: boolean };
  type DeviceProfile = { name: string; settings: DeviceSettings; protected?: boolean };
  type SectionKey = 'manage' | 'plot' | 'devices' | 'manual';

  const dispatch = createEventDispatcher<{ preview: string }>();

  let files: FileMeta[] = [];
  let selectedFile: string = '';
  let selectedMeta: FileMeta | undefined;
  let selectedDimensions = '';
  let isLoading = false;
  let uploadInProgress = false;
  let plotting = false;
  let rotating = false;
  let renaming = false;
  let stopping = false;
  let statusMessage: string | null = null;
  let statusTone: 'success' | 'error' | null = null;
  let dragActive = false;
  let renameValue = '';
  let plotProgress: number | null = null;
  let plotRunning = false;
  let plotElapsedSeconds: number | null = null;
  let plotDistanceMm: number | null = null;
  let previewLoading = false;
  let previewError: string | null = null;
  let previewTimeSeconds: number | null = null;
  let previewDistanceMm: number | null = null;
  let uploadInput: HTMLInputElement | null = null;
  let plotProfiles: PlotProfile[] = mergeProfiles(
    PRINT_DEFAULTS,
    {},
    BASE_PLOT_SETTINGS,
    'AxiDraw'
  );
  $: availablePlotProfiles =
    plotProfiles.length > 0
      ? plotProfiles
      : mergeProfiles(PRINT_DEFAULTS, {}, BASE_PLOT_SETTINGS, 'AxiDraw');
  let selectedProfile: string =
    plotProfiles.find((profile) => profile.name === 'AxiDraw')?.name ?? 'AxiDraw';
  let newProfileName = '';
  let deviceProfiles: DeviceProfile[] = mergeProfiles(
    DEVICE_DEFAULTS,
    {},
    BASE_DEVICE_SETTINGS,
    'Default Device'
  );
  $: availableDeviceProfiles =
    deviceProfiles.length > 0
      ? deviceProfiles
      : mergeProfiles(DEVICE_DEFAULTS, {}, BASE_DEVICE_SETTINGS, 'Default Device');
  let selectedDeviceProfile: string =
    deviceProfiles.find((profile) => profile.name === 'Default Device')?.name ?? 'Default Device';
  let newDeviceName = '';

  let handlingMode = BASE_PLOT_SETTINGS.handling ?? 1;
  let speedSetting = BASE_PLOT_SETTINGS.speed ?? 70;
  let speedPenDown = BASE_PLOT_SETTINGS.s_down;
  let speedPenUp = BASE_PLOT_SETTINGS.s_up;
  let penPosDown = BASE_PLOT_SETTINGS.p_down;
  let penPosUp = BASE_PLOT_SETTINGS.p_up;
let devicePenliftMode = BASE_DEVICE_SETTINGS.penlift ?? 1;
let deviceNoHoming = BASE_DEVICE_SETTINGS.no_homing ?? false;
let deviceHost = BASE_DEVICE_SETTINGS.host ?? 'localhost';
let devicePort = BASE_DEVICE_SETTINGS.port ?? 2222;
let deviceAxicliPath = BASE_DEVICE_SETTINGS.axicli_path ?? '';
let deviceHomeOffsetX = BASE_DEVICE_SETTINGS.home_offset_x ?? 0;
let deviceHomeOffsetY = BASE_DEVICE_SETTINGS.home_offset_y ?? 0;
let deviceNotes = BASE_DEVICE_SETTINGS.notes ?? '';
let deviceNextdrawModel = BASE_DEVICE_SETTINGS.nextdraw_model ?? NEXTDRAW_MODELS[0];

  let openSection: SectionKey = 'manage';

  const sections: { key: SectionKey; icon: string; label: string }[] = [
    { key: 'manage', icon: '📁', label: 'Manage Files' },
    { key: 'plot', icon: '🖊️', label: 'Plot & Settings' },
    { key: 'devices', icon: '🛠️', label: 'Devices' },
    { key: 'manual', icon: '🤖', label: 'Manual Commands' },
  ];

  const selectSection = (key: SectionKey) => {
    openSection = key;
  };


  const setStatus = (message: string, tone: 'success' | 'error') => {
    statusMessage = message;
    statusTone = tone;
  };

  const clearStatus = () => {
    statusMessage = null;
    statusTone = null;
  };

  const clearPreview = () => {
    previewLoading = false;
    previewError = null;
    previewTimeSeconds = null;
    previewDistanceMm = null;
    if (!plotRunning) {
      plotElapsedSeconds = null;
      plotDistanceMm = null;
    }
  };

  const requestFullPreview = (name: string | undefined, includeSvg = true) => {
    if (!name) {
      dispatch('preview', '');
      clearPreview();
      return;
    }
    if (includeSvg) {
      previewFile(name);
    }
    fetchPreview(name);
  };

  const fetchFiles = async (preferred?: string) => {
    isLoading = true;
    try {
      const data = await filesApi.list();
      files = Array.isArray(data) ? data : [];

      if (files.length === 0) {
        selectedFile = '';
        renameValue = '';
        dispatch('preview', '');
        clearPreview();
        return;
      }

      const preferredMatch = preferred && files.find((file) => file.name === preferred);
      if (preferredMatch) {
        selectedFile = preferredMatch.name;
        renameValue = preferredMatch.name;
        requestFullPreview(preferredMatch.name);
        return;
      }

      if (!selectedFile || !files.some((file) => file.name === selectedFile)) {
        selectedFile = files[0].name;
        renameValue = selectedFile;
        requestFullPreview(selectedFile);
      } else {
        renameValue = selectedFile;
        fetchPreview(selectedFile);
      }
    } catch (error) {
      console.error('Failed to load files', error);
      const message = error instanceof Error ? error.message : 'Failed to load files';
      setStatus(message, 'error');
    } finally {
      isLoading = false;
    }
  };

  const applyProfileSettings = (name: string) => {
    const profile = plotProfiles.find((item) => item.name === name) ?? plotProfiles[0];
    const settings = profile?.settings ?? BASE_PLOT_SETTINGS;
    handlingMode = settings.handling ?? BASE_PLOT_SETTINGS.handling ?? 1;
    speedSetting = settings.speed ?? BASE_PLOT_SETTINGS.speed ?? 70;
    speedPenDown = settings.s_down ?? BASE_PLOT_SETTINGS.s_down;
    speedPenUp = settings.s_up ?? BASE_PLOT_SETTINGS.s_up;
    penPosDown = settings.p_down ?? BASE_PLOT_SETTINGS.p_down;
    penPosUp = settings.p_up ?? BASE_PLOT_SETTINGS.p_up;
    if (profile) {
      selectedProfile = profile.name;
    }
  };

  const loadProfiles = async (initial = false) => {
    try {
      const overrides = readLocalPresets<PlotSettings>(PRINT_STORAGE_KEY);
      plotProfiles = mergeProfiles(PRINT_DEFAULTS, overrides, BASE_PLOT_SETTINGS, 'AxiDraw');
      const hasSelection = plotProfiles.some((profile) => profile.name === selectedProfile);
      if (!hasSelection) {
        selectedProfile =
          plotProfiles.find((profile) => profile.name === 'AxiDraw')?.name ??
          plotProfiles[0]?.name ??
          'AxiDraw';
      }
      if (initial || !hasSelection) {
        applyProfileSettings(selectedProfile);
      }
    } catch (error) {
      console.error('Failed to load settings', error);
      if (plotProfiles.length === 0) {
        plotProfiles = mergeProfiles(PRINT_DEFAULTS, {}, BASE_PLOT_SETTINGS, 'AxiDraw');
        applyProfileSettings(plotProfiles[0].name);
      }
    }
  };

  const getPrintProfilePayload = (): PlotSettings => ({
    ...BASE_PLOT_SETTINGS,
    handling: handlingMode,
    speed: speedSetting,
    s_down: speedPenDown,
    s_up: speedPenUp,
    p_down: penPosDown,
    p_up: penPosUp,
  });

  const buildPlotPayload = (): PlotSettings => {
    const device = currentDeviceSettings();
    const penliftValue = Number.isFinite(Number(device.penlift)) ? Number(device.penlift) : 1;
    return {
      ...getPrintProfilePayload(),
      penlift: penliftValue,
      brushless: penliftValue === 3,
      no_homing: Boolean(device.no_homing),
      model: device.nextdraw_model || NEXTDRAW_MODELS[0],
    };
  };

  const currentDeviceSettings = (): DeviceSettings => ({
    host: deviceHost || null,
    port: Number.isFinite(Number(devicePort)) ? Number(devicePort) : null,
    axicli_path: deviceAxicliPath || null,
    home_offset_x: Number.isFinite(Number(deviceHomeOffsetX)) ? Number(deviceHomeOffsetX) : 0,
    home_offset_y: Number.isFinite(Number(deviceHomeOffsetY)) ? Number(deviceHomeOffsetY) : 0,
    notes: deviceNotes || null,
    penlift: devicePenliftMode,
    no_homing: deviceNoHoming,
    nextdraw_model: deviceNextdrawModel,
  });

  const handleSaveProfile = async () => {
    const trimmed = newProfileName.trim() || selectedProfile;
    if (!trimmed) {
      setStatus('Provide a name for the settings preset.', 'error');
      return;
    }
    try {
      const saved = getPrintProfilePayload();
      const overrides = readLocalPresets<PlotSettings>(PRINT_STORAGE_KEY);
      overrides[trimmed] = saved;
      writeLocalPresets(PRINT_STORAGE_KEY, overrides);
      selectedProfile = trimmed;
      newProfileName = '';
      setStatus(`Saved settings "${trimmed}"`, 'success');
      await loadProfiles();
    } catch (error) {
      console.error('Failed to save settings', error);
      const message = error instanceof Error ? error.message : 'Failed to save settings';
      setStatus(message, 'error');
    }
  };

  const handleDeleteProfile = async () => {
    const profile = plotProfiles.find((item) => item.name === selectedProfile);
    if (!profile || profile.protected) {
      setStatus('Cannot delete the default settings preset.', 'error');
      return;
    }
    try {
      const overrides = readLocalPresets<PlotSettings>(PRINT_STORAGE_KEY);
      delete overrides[profile.name];
      writeLocalPresets(PRINT_STORAGE_KEY, overrides);
      setStatus(`Deleted settings "${profile.name}"`, 'success');
      selectedProfile = 'AxiDraw';
      await loadProfiles(true);
    } catch (error) {
      console.error('Failed to delete settings', error);
      const message = error instanceof Error ? error.message : 'Failed to delete settings';
      setStatus(message, 'error');
    }
  };

  const handleProfileChange = (event: Event) => {
    const target = event.currentTarget as HTMLSelectElement | null;
    const value = target ? target.value : selectedProfile;
    applyProfileSettings(value);
    if (selectedFile) {
      fetchPreview(selectedFile);
    }
  };

  const handleHandlingChange = (event: Event) => {
    const target = event.currentTarget as HTMLSelectElement | null;
    const value = target ? Number(target.value) : handlingMode;
    handlingMode = Number.isNaN(value) ? handlingMode : value;
    if (selectedFile) {
      fetchPreview(selectedFile);
    }
  };

  const handleDevicePenliftChange = (event: Event) => {
    const target = event.currentTarget as HTMLSelectElement | null;
    const value = target ? Number(target.value) : devicePenliftMode;
    devicePenliftMode = Number.isNaN(value) ? devicePenliftMode : value;
    if (selectedFile) {
      fetchPreview(selectedFile);
    }
  };

  const handleDevicePresetChange = (event: Event) => {
    const target = event.currentTarget as HTMLSelectElement | null;
    const value = target ? target.value : selectedDeviceProfile;
    applyDeviceProfile(value);
    if (selectedFile) {
      fetchPreview(selectedFile);
    }
  };

  const handleNextdrawModelChange = (event: Event) => {
    const target = event.currentTarget as HTMLSelectElement | null;
    deviceNextdrawModel = target?.value || NEXTDRAW_MODELS[0];
    if (selectedFile) {
      fetchPreview(selectedFile);
    }
  };

  const applyDeviceProfile = (name: string) => {
    const profile = deviceProfiles.find((item) => item.name === name) ?? deviceProfiles[0];
    const settings = profile?.settings ?? BASE_DEVICE_SETTINGS;
    deviceHost = settings.host ?? BASE_DEVICE_SETTINGS.host ?? 'localhost';
    devicePort = settings.port ?? BASE_DEVICE_SETTINGS.port ?? 2222;
    deviceAxicliPath = settings.axicli_path ?? BASE_DEVICE_SETTINGS.axicli_path ?? '';
    deviceHomeOffsetX = settings.home_offset_x ?? BASE_DEVICE_SETTINGS.home_offset_x ?? 0;
    deviceHomeOffsetY = settings.home_offset_y ?? BASE_DEVICE_SETTINGS.home_offset_y ?? 0;
    deviceNotes = settings.notes ?? BASE_DEVICE_SETTINGS.notes ?? '';
    devicePenliftMode = settings.penlift ?? BASE_DEVICE_SETTINGS.penlift ?? 1;
    deviceNoHoming =
      typeof settings.no_homing === 'boolean'
        ? settings.no_homing
        : Boolean(BASE_DEVICE_SETTINGS.no_homing);
    deviceNextdrawModel =
      settings.nextdraw_model ?? BASE_DEVICE_SETTINGS.nextdraw_model ?? NEXTDRAW_MODELS[0];
    if (profile) {
      selectedDeviceProfile = profile.name;
    }
  };

  const loadDeviceProfiles = async (initial = false) => {
    try {
      const overrides = readLocalPresets<DeviceSettings>(DEVICE_STORAGE_KEY);
      deviceProfiles = mergeProfiles(DEVICE_DEFAULTS, overrides, BASE_DEVICE_SETTINGS, 'Default Device');
      const hasSelection = deviceProfiles.some((profile) => profile.name === selectedDeviceProfile);
      if (!hasSelection) {
        selectedDeviceProfile =
          deviceProfiles.find((profile) => profile.name === 'Default Device')?.name ??
          deviceProfiles[0]?.name ??
          'Default Device';
      }
      if (initial || !hasSelection) {
        applyDeviceProfile(selectedDeviceProfile);
      }
    } catch (error) {
      console.error('Failed to load device settings', error);
      if (deviceProfiles.length === 0) {
        deviceProfiles = mergeProfiles(DEVICE_DEFAULTS, {}, BASE_DEVICE_SETTINGS, 'Default Device');
        applyDeviceProfile(deviceProfiles[0].name);
      }
    }
  };

  const handleDeviceSave = async () => {
    const trimmed = newDeviceName.trim() || selectedDeviceProfile;
    if (!trimmed) {
      setStatus('Provide a name for the device preset.', 'error');
      return;
    }
    try {
      const overrides = readLocalPresets<DeviceSettings>(DEVICE_STORAGE_KEY);
      overrides[trimmed] = currentDeviceSettings();
      writeLocalPresets(DEVICE_STORAGE_KEY, overrides);
      newDeviceName = '';
      selectedDeviceProfile = trimmed;
      await loadDeviceProfiles();
      setStatus(`Saved device "${trimmed}"`, 'success');
    } catch (error) {
      console.error('Failed to save device settings', error);
      const message = error instanceof Error ? error.message : 'Failed to save device settings';
      setStatus(message, 'error');
    }
  };

  const handleDeviceDelete = async () => {
    const profile = deviceProfiles.find((item) => item.name === selectedDeviceProfile);
    if (!profile) {
      setStatus('Select a device preset to delete.', 'error');
      return;
    }
    if (profile.protected) {
      setStatus('Repo-managed device presets cannot be deleted.', 'error');
      return;
    }
    try {
      const overrides = readLocalPresets<DeviceSettings>(DEVICE_STORAGE_KEY);
      delete overrides[profile.name];
      writeLocalPresets(DEVICE_STORAGE_KEY, overrides);
      setStatus(`Deleted device "${profile.name}"`, 'success');
      selectedDeviceProfile = 'Default Device';
      await loadDeviceProfiles(true);
    } catch (error) {
      console.error('Failed to delete device settings', error);
      const message = error instanceof Error ? error.message : 'Failed to delete device settings';
      setStatus(message, 'error');
    }
  };

  onMount(() => {
    fetchFiles();
    pollStatus();
    loadProfiles(true);
    loadDeviceProfiles(true);
  });

  $: selectedMeta = files.find((file) => file.name === selectedFile);
  $: selectedDimensions = describeDimensions(selectedMeta);

  const performUpload = async (file: File | undefined | null) => {
    if (!file) {
      return;
    }

    clearStatus();
    let saved: FileMeta | null = null;
    const startTime = Date.now();
    try {
      uploadInProgress = true;
      console.log('[FileManager] Starting upload:', file.name, file.size, 'bytes');
      saved = await filesApi.upload(file);
      const duration = Date.now() - startTime;
      console.log('[FileManager] Upload successful:', saved?.name, `(${duration}ms)`);
      setStatus(`Uploaded ${saved?.name ?? file.name}`, 'success');
    } catch (error) {
      const duration = Date.now() - startTime;
      console.error('[FileManager] Upload failed after', duration, 'ms', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      const errorUrl = (error as any)?.url;
      const errorStatus = (error as any)?.status;
      const isTimeout = (error as any)?.isTimeout;
      console.error('[FileManager] Upload error details:', { 
        errorMessage, 
        errorUrl, 
        errorStatus,
        isTimeout,
        duration,
        error: error instanceof Error ? {
          name: error.name,
          message: error.message,
          stack: error.stack,
        } : error,
      });
      
      let displayMessage = errorMessage;
      if (isTimeout) {
        displayMessage = 'Upload timeout - API server may not be running or reachable';
      } else if (errorMessage.includes('Failed to fetch')) {
        displayMessage = 'Cannot connect to API server - check if it\'s running on port 2222';
      }
      
      setStatus(`Upload failed: ${displayMessage}${errorUrl ? ` (${errorUrl})` : ''}`, 'error');
      return;
    } finally {
      uploadInProgress = false;
    }
    const preferred = saved?.name ?? undefined;
    setTimeout(() => {
      fetchFiles(preferred).catch((error) => {
        console.error('Post-upload refresh failed', error);
        const message = error instanceof Error ? error.message : 'Failed to refresh file list';
        setStatus(message, 'error');
      });
    }, 0);
  };

  const handleUpload = async (event: Event) => {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    await performUpload(file);
    if (input) {
      input.value = '';
    }
  };

  const handleDrop = async (event: DragEvent) => {
    event.preventDefault();
    dragActive = false;
    const file = event.dataTransfer?.files?.[0];
    await performUpload(file);
  };

  const handleDragOver = (event: DragEvent) => {
    event.preventDefault();
    dragActive = true;
  };

  const handleDragLeave = (event: DragEvent) => {
    event.preventDefault();
    dragActive = false;
  };

  const handleSelectChange = (event: Event) => {
    const target = event.currentTarget as HTMLSelectElement | null;
    const value = target ? target.value : '';
    if (value) {
      selectedFile = value;
      renameValue = value;
      requestFullPreview(value);
    }
  };

  const handlePlot = async () => {
    if (!selectedFile) {
      setStatus('Select a file before starting a plot.', 'error');
      return;
    }

    clearStatus();

    try {
      plotting = true;
      plotRunning = true;
      plotProgress = 0;
      plotElapsedSeconds = 0;
      plotDistanceMm = previewDistanceMm;
      const payload = await filesApi.plot(selectedFile, buildPlotPayload());

      const pid = typeof payload?.pid === 'number' ? payload.pid : undefined;
      const completed = Boolean(payload?.completed);
      const rawOutput = payload?.output;
      const outputSnippet = typeof rawOutput === 'string'
        ? (() => {
            const trimmed = rawOutput.trim();
            if (!trimmed) {
              return '';
            }
            const lines = trimmed.split('\n').map((line) => line.trim()).filter(Boolean);
            if (lines.length === 0) {
              return '';
            }
            if (lines.length >= 2 && lines[0].endsWith(':')) {
              return `${lines[0]} ${lines[1]}`;
            }
            return lines[0];
          })()
        : '';

      if (completed) {
        const summary = outputSnippet ? ` (${outputSnippet})` : '';
        setStatus(`Plot completed immediately for ${selectedFile}${summary}`, 'success');
        plotRunning = false;
        plotProgress = 100;
        plotElapsedSeconds = 0;
        pollStatus();
        if (payload && typeof payload.cmd === 'string') {
          showCommandToast('Plot command (offline)', payload.cmd);
        }
        return;
      }

      if (payload && typeof payload.cmd === 'string') {
        showCommandToast(`Plot command${pid ? ` (pid ${pid})` : ''}`, payload.cmd);
      }
      const pidLabel = pid ? ` (pid ${pid})` : '';
      setStatus(`Plot started for ${selectedFile}${pidLabel}`, 'success');
      pollStatus();
    } catch (error) {
      console.error('Plot failed', error);
      const message = error instanceof Error ? error.message : 'Plot start failed';
      setStatus(message, 'error');
      plotRunning = false;
      plotProgress = null;
      plotElapsedSeconds = null;
    } finally {
      plotting = false;
    }
  };

  const handleRotate = async (angle: number) => {
    if (!selectedFile) {
      setStatus('Select a file before rotating.', 'error');
      return;
    }

    clearStatus();

    try {
      rotating = true;
      await filesApi.rotate(selectedFile, angle);
      await fetchFiles(selectedFile);
      setStatus(`Rotated ${selectedFile}`, 'success');
    } catch (error) {
      console.error('Rotation failed', error);
      const message = error instanceof Error ? error.message : 'Rotation failed';
      setStatus(message, 'error');
    } finally {
      rotating = false;
    }
  };

  const handleRename = async () => {
    if (!selectedFile) {
      setStatus('Select a file before renaming.', 'error');
      return;
    }

    const trimmed = renameValue.trim();
    if (!trimmed) {
      setStatus('Filename cannot be empty.', 'error');
      return;
    }

    clearStatus();

    try {
      renaming = true;
      const updated = await filesApi.rename(selectedFile, trimmed);
      selectedFile = updated.name;
      renameValue = updated.name;
      await fetchFiles(updated.name);
      setStatus(`Renamed to ${updated.name}`, 'success');
    } catch (error) {
      console.error('Rename failed', error);
      const message = error instanceof Error ? error.message : 'Rename failed';
      setStatus(message, 'error');
    } finally {
      renaming = false;
    }
  };

  const handleStopPlot = async () => {
    clearStatus();
    try {
      stopping = true;
      await filesApi.cancelPlot();
      setStatus('Plot canceled.', 'success');
      plotRunning = false;
      plotProgress = null;
      pollStatus();
    } catch (error) {
      console.error('Stop failed', error);
      const message = error instanceof Error ? error.message : 'Failed to stop plot';
      setStatus(message, 'error');
    } finally {
      stopping = false;
    }
  };

  const pollStatus = async () => {
    try {
      const data = await filesApi.status();
      plotRunning = Boolean(data?.running);
      const rawProgress = data?.progress;
      plotProgress = typeof rawProgress === 'number' ? rawProgress : null;
      const rawElapsed = data?.elapsed_seconds;
      plotElapsedSeconds = typeof rawElapsed === 'number' ? rawElapsed : null;
      const rawDistance = data?.distance_mm;
      plotDistanceMm = typeof rawDistance === 'number' ? rawDistance : plotDistanceMm;
      if (!plotRunning && plotDistanceMm == null && previewDistanceMm != null) {
        plotDistanceMm = previewDistanceMm;
      }
      const errorMessage = typeof data?.error === 'string' ? data.error : null;
      if (errorMessage && statusMessage !== errorMessage) {
        setStatus(errorMessage, 'error');
        plotRunning = false;
        plotProgress = null;
        plotElapsedSeconds = null;
      }
    } catch (error) {
      // ignore status polling errors
    }
  };

  const formatDuration = (value: number) => {
    if (!Number.isFinite(value) || value < 0) {
      return '—';
    }
    const totalSeconds = Math.round(value);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    if (hours > 0) {
      return `${hours}h ${minutes}m ${seconds}s`;
    }
    if (minutes > 0) {
      return `${minutes}m ${seconds}s`;
    }
    return `${seconds}s`;
  };

  const formatDistance = (mm: number) => {
    if (!Number.isFinite(mm) || mm < 0) {
      return '—';
    }
    if (mm >= 1000) {
      return `${(mm / 1000).toFixed(2)} m`;
    }
    if (mm >= 10) {
      return `${(mm / 10).toFixed(1)} cm`;
    }
    return `${mm.toFixed(1)} mm`;
  };

  async function fetchPreview(name: string | undefined) {
    if (!name) {
      clearPreview();
      return;
    }

    previewLoading = true;
    previewError = null;
    try {
      const payload = buildPlotPayload();
      const data = await filesApi.preview(name, {
        handling: payload.handling,
        speed: payload.speed,
        penlift: payload.penlift,
        model: payload.model ?? null,
      });
      const timeValue = data?.estimated_seconds;
      const distanceValue = data?.distance_mm;
      previewTimeSeconds = typeof timeValue === 'number' ? timeValue : null;
      previewDistanceMm = typeof distanceValue === 'number' ? distanceValue : null;
      if (!plotRunning) {
        plotElapsedSeconds = previewTimeSeconds;
        plotDistanceMm = previewDistanceMm;
      }
    } catch (error) {
      console.error('Preview failed', error);
      previewError = 'Unable to estimate plot time.';
      previewTimeSeconds = null;
      previewDistanceMm = null;
    } finally {
      previewLoading = false;
    }
  }

  async function previewFile(name: string) {
    try {
      const svg = await filesApi.raw(name);
      dispatch('preview', svg);
    } catch (error) {
      console.error('Preview failed', error);
      setStatus('Preview failed', 'error');
    }
  }

  const handleDelete = async (name: string) => {
    clearStatus();
    try {
      await filesApi.remove(name);
      setStatus(`Deleted ${name}`, 'success');
      await fetchFiles();
    } catch (error) {
      console.error('Delete failed', error);
      setStatus('Delete failed', 'error');
    }
  };

  const formatSize = (value: number) => {
    if (value < 1024) {
      return `${value} B`;
    }
    if (value < 1024 * 1024) {
      return `${(value / 1024).toFixed(1)} KB`;
    }
    return `${(value / (1024 * 1024)).toFixed(1)} MB`;
  };

  type LengthInfo = { mm: number; approx: boolean } | null;

  const lengthToMm = (value?: string | null): LengthInfo => {
    if (!value) {
      return null;
    }

    const match = value.trim().match(/^([+-]?(?:\d+\.\d+|\d+|\.\d+)(?:[eE][+-]?\d+)?)\s*([a-zA-Z%]*)$/);
    if (!match) {
      return null;
    }

    const numeric = Number(match[1]);
    if (!Number.isFinite(numeric)) {
      return null;
    }

    const unit = match[2].toLowerCase();
    const mmPerUnit: Record<string, { factor: number; approx?: boolean }> = {
      mm: { factor: 1 },
      millimeter: { factor: 1 },
      millimeters: { factor: 1 },
      cm: { factor: 10 },
      centimeter: { factor: 10 },
      centimeters: { factor: 10 },
      m: { factor: 1000 },
      meter: { factor: 1000 },
      meters: { factor: 1000 },
      in: { factor: 25.4 },
      inch: { factor: 25.4 },
      inches: { factor: 25.4 },
      pt: { factor: 25.4 / 72, approx: true },
      pc: { factor: 25.4 / 6, approx: true },
      px: { factor: 25.4 / 96, approx: true },
      q: { factor: 0.25 },
    };

    if (!unit) {
      return null;
    }

    const mapping = mmPerUnit[unit];
    if (!mapping) {
      return null;
    }

    return { mm: numeric * mapping.factor, approx: Boolean(mapping.approx) };
  };

  const formatMm = (value: number) => {
    if (!Number.isFinite(value)) {
      return '';
    }
    if (Math.abs(value) >= 1) {
      return value.toFixed(2).replace(/\.0+$/, '').replace(/(\.\d*[1-9])0+$/, '$1');
    }
    return value.toFixed(3).replace(/0+$/, '').replace(/\.$/, '');
  };

  const describeDimensions = (file: FileMeta | undefined) => {
    if (!file) {
      return '';
    }

    const { width, height, viewBox } = file;
    const widthMm = lengthToMm(width || undefined);
    const heightMm = lengthToMm(height || undefined);

    if (widthMm && heightMm) {
      const approx = widthMm.approx || heightMm.approx;
      const prefix = approx ? '≈ ' : '';
      return `${prefix}${formatMm(widthMm.mm)} × ${formatMm(heightMm.mm)} mm`;
    }

    if (viewBox) {
      const parts = viewBox.split(/\s+/);
      if (parts.length === 4) {
        const widthVal = Number(parts[2]);
        const heightVal = Number(parts[3]);
        if (!Number.isNaN(widthVal) && !Number.isNaN(heightVal)) {
          return `${widthVal} × ${heightVal} (viewBox)`;
        }
      }
    }

    if (width && height) {
      return `${width} × ${height}`;
    }

    return viewBox ? `viewBox: ${viewBox}` : '';
  };
</script>

<div class="text-xs text-neutral-200">
  <div class="mb-3 text-center text-sm font-semibold uppercase tracking-wide text-neutral-100">
    Plotter Studio
  </div>
  {#if statusMessage}
    <p class={`mb-3 text-xs ${statusTone === 'success' ? 'text-green-400' : 'text-red-400'}`}>
      {statusMessage}
    </p>
  {/if}

  <div class="flex h-full">
    <nav class="flex w-12 flex-col items-center gap-2 py-2 bg-neutral-900/40">
      {#each sections as section}
        <button
          class={`flex h-10 w-10 items-center justify-center rounded ${
            openSection === section.key ? 'bg-neutral-600 text-white' : 'text-neutral-300 hover:bg-neutral-700'
          }`}
          type="button"
          aria-label={section.label}
          aria-pressed={openSection === section.key}
          on:click={() => selectSection(section.key)}
        >
          <span class="text-lg leading-none">{section.icon}</span>
        </button>
      {/each}
    </nav>

    <div class="flex-1 min-w-0 space-y-4 px-4 py-3">
      {#if openSection === 'manage'}
        <div class="space-y-3">
        <div
          class={`w-full border-2 border-dashed rounded px-4 py-8 text-center text-neutral-300 transition ${
            dragActive ? 'border-blue-400 bg-neutral-800/40' : 'border-neutral-600 bg-neutral-800/60'
          } ${uploadInProgress ? 'opacity-60' : ''}`}
            role="button"
            aria-label="Upload SVG by dragging or selecting a file"
            tabindex="0"
            on:dragover={handleDragOver}
            on:dragleave={handleDragLeave}
            on:drop={handleDrop}
            on:keydown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                uploadInput?.click();
              }
            }}
          >
            <p class="text-sm">Drag & drop an SVG here, or</p>
            <label class="inline-flex items-center justify-center mt-2">
              <span class="bg-blue-500 hover:bg-blue-400 text-white text-xs font-medium px-3 py-1 rounded cursor-pointer">
                {uploadInProgress ? 'Uploading…' : 'Browse Files'}
              </span>
              <input
                type="file"
                accept=".svg"
                on:change={handleUpload}
                class="hidden"
                disabled={uploadInProgress}
                bind:this={uploadInput}
              />
            </label>
          </div>

          <div class="space-y-2">
            <label class="flex flex-col">
              Select file
              <select
                class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
                bind:value={selectedFile}
                disabled={isLoading || files.length === 0}
                on:change={handleSelectChange}
              >
                <option value="" disabled>
                  {files.length === 0 ? 'No files available' : 'Choose a file'}
                </option>
                {#each files as file}
                  <option value={file.name}>{file.name} ({formatSize(file.size)})</option>
                {/each}
              </select>
            </label>

            <button
              class="text-blue-300 hover:text-blue-200 self-start text-xs"
              on:click={() => fetchFiles()}
              type="button"
              disabled={isLoading}
            >
              {isLoading ? 'Refreshing…' : 'Refresh file list'}
            </button>

            {#if selectedFile}
              <button
                class="bg-red-500 py-1 px-2 text-xs rounded cursor-pointer hover:bg-red-400 self-start"
                type="button"
                on:click={() => handleDelete(selectedFile)}
              >
                Delete selected
              </button>
            {/if}
          </div>
        </div>

        {#if selectedFile}
          <div class="space-y-3">
            {#if selectedDimensions}
              <p class="text-neutral-400 text-xs">Dimensions: {selectedDimensions}</p>
            {/if}

            <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-2">
              <input
                class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100 flex-1"
                type="text"
                bind:value={renameValue}
                placeholder="Filename"
                disabled={renaming}
              />
              <button
                class="bg-neutral-500 hover:bg-neutral-400 text-white text-xs font-medium px-3 py-1 rounded self-start sm:self-auto"
                type="button"
                on:click={handleRename}
                disabled={renaming}
              >
                {renaming ? 'Renaming…' : 'Save name'}
              </button>
            </div>

            <div class="flex gap-2">
              <button
                class="bg-neutral-600 py-1 px-2 text-xs rounded cursor-pointer hover:bg-neutral-500 self-start"
                type="button"
                on:click={() => handleRotate(-90)}
                disabled={rotating}
              >
                {rotating ? 'Rotating…' : 'Rotate -90°'}
              </button>
              <button
                class="bg-neutral-600 py-1 px-2 text-xs rounded cursor-pointer hover:bg-neutral-500 self-start"
                type="button"
                on:click={() => handleRotate(90)}
                disabled={rotating}
              >
                {rotating ? 'Rotating…' : 'Rotate +90°'}
              </button>
            </div>
          </div>
        {:else}
          <p class="text-neutral-400 text-xs">Select a file to edit its details.</p>
        {/if}

        
      {:else if openSection === 'plot'}
        {#if selectedFile}
          {#if plotProgress !== null}
            <div class="flex w-full items-center gap-2">
              <div class="h-2 flex-1 rounded bg-neutral-700">
                <div
                  class="h-full rounded bg-green-400 transition-all"
                  style={`width:${Math.max(0, Math.min(plotProgress, 100))}%`}
                ></div>
              </div>
              <span class="text-xs text-neutral-300">{Math.round(plotProgress)}%</span>
            </div>
          {/if}

          <div class="space-y-1 text-xs text-neutral-300">
            <p>Plot time: {plotElapsedSeconds !== null ? formatDuration(plotElapsedSeconds) : previewTimeSeconds !== null ? formatDuration(previewTimeSeconds) : '—'}</p>
            <p>Distance: {plotDistanceMm !== null ? formatDistance(plotDistanceMm) : previewDistanceMm !== null ? formatDistance(previewDistanceMm) : '—'}</p>
          </div>

          <div class="flex flex-wrap gap-2">
            <button
              class="bg-green-500 py-1 px-2 text-xs rounded cursor-pointer hover:bg-green-400"
              type="button"
              on:click={handlePlot}
              disabled={plotting || rotating || plotRunning}
            >
              {plotting ? 'Starting…' : 'Start Plot'}
            </button>
            <button
              class="text-blue-300 hover:text-blue-200 text-xs"
              type="button"
              on:click={pollStatus}
            >
              Refresh status
            </button>
            {#if plotRunning}
              <button
                class="bg-yellow-500 py-1 px-2 text-xs rounded cursor-pointer hover:bg-yellow-400"
                type="button"
                on:click={handleStopPlot}
                disabled={stopping}
              >
                {stopping ? 'Stopping…' : 'Stop Plot'}
              </button>
            {/if}
          </div>
          <div class="mt-4 border-t border-neutral-700 pt-4 space-y-3">
            <h3 class="text-xs font-semibold uppercase tracking-wide text-neutral-400">
              Print Settings
            </h3>
            <div class="space-y-1">
              <label class="flex flex-col text-xs text-neutral-300 gap-1">
                Preset
                <select
                  class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
                  bind:value={selectedProfile}
                  on:change={handleProfileChange}
                >
                  {#each availablePlotProfiles as profile}
                    <option value={profile.name}>{profile.name}</option>
                  {/each}
                </select>
              </label>
              <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
                <input
                  type="text"
                  class="flex-1 rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
                  placeholder="Preset name"
                  bind:value={newProfileName}
                />
                <button
                  class="bg-blue-500 hover:bg-blue-400 text-white text-xs font-medium px-3 py-1 rounded"
                  type="button"
                  on:click={handleSaveProfile}
                >
                  Save preset
                </button>
                {#if availablePlotProfiles.find((profile) => profile.name === selectedProfile)?.protected !== true}
                  <button
                    class="bg-red-500 hover:bg-red-400 text-white text-xs font-medium px-3 py-1 rounded"
                    type="button"
                    on:click={handleDeleteProfile}
                  >
                    Delete preset
                  </button>
                {/if}
              </div>
            </div>

            <label class="flex flex-col gap-1 text-xs text-neutral-300">
              <span>Handling mode</span>
              <select
                class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
                bind:value={handlingMode}
                on:change={handleHandlingChange}
              >
                <option value={1}>1 — Technical drawing (default)</option>
                <option value={2}>2 — Handwriting</option>
                <option value={3}>3 — Sketching</option>
                <option value={4}>4 — Constant speed</option>
                <option value={5}>5 — Off (no handling flag)</option>
              </select>
            </label>

            {#if handlingMode === 4}
              <label class="flex flex-col gap-1">
                <span>Speed: {speedSetting}%</span>
                <input
                  type="range"
                  min="1"
                  max="100"
                  bind:value={speedSetting}
                  on:change={() => fetchPreview(selectedFile)}
                />
              </label>
            {/if}

              <label class="flex flex-col gap-1 text-xs text-neutral-300">
                <span>Pen lift mode</span>
                <select
                  class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
                  bind:value={devicePenliftMode}
                  on:change={handleDevicePenliftChange}
                >
                  <option value={1}>1 — Default (AxiDraw)</option>
                  <option value={2}>2 — NextDraw Future</option>
                  <option value={3}>3 — Brushless upgrade</option>
                </select>
              </label>

            <div class="grid gap-2 sm:grid-cols-2">
              <label class="flex flex-col text-xs gap-1">
                <span>Pen-down speed (%)</span>
                <input
                  type="number"
                  min="1"
                  max="100"
                  step="1"
                  class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
                  bind:value={speedPenDown}
                />
              </label>
              <label class="flex flex-col text-xs gap-1">
                <span>Pen-up speed (%)</span>
                <input
                  type="number"
                  min="1"
                  max="100"
                  step="1"
                  class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
                  bind:value={speedPenUp}
                />
              </label>
              <label class="flex flex-col text-xs gap-1">
                <span>Pen-down position</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="1"
                  class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
                  bind:value={penPosDown}
                />
              </label>
              <label class="flex flex-col text-xs gap-1">
                <span>Pen-up position</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="1"
                  class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
                  bind:value={penPosUp}
                />
              </label>
            </div>

            {#if previewLoading}
              <p class="text-neutral-400 text-xs">Estimating plot time…</p>
            {:else if previewError}
              <p class="text-red-400 text-xs">{previewError}</p>
            {:else if previewTimeSeconds !== null || previewDistanceMm !== null}
              <div class="space-y-1 text-xs text-neutral-300">
                {#if previewTimeSeconds !== null}
                  <p>Estimated time: {formatDuration(previewTimeSeconds)}</p>
                {/if}
                {#if previewDistanceMm !== null}
                  <p>Estimated distance: {formatDistance(previewDistanceMm)}</p>
                {/if}
              </div>
            {/if}
          </div>
        {:else}
          <p class="text-neutral-400 text-xs">Select a file to view plotting controls and settings.</p>
        {/if}
      {:else if openSection === 'devices'}
        <div class="space-y-4 text-xs text-neutral-200">
          <div class="space-y-2">
            <label class="flex flex-col gap-1">
              Device preset
              <select
                class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
                bind:value={selectedDeviceProfile}
                on:change={handleDevicePresetChange}
              >
                {#each availableDeviceProfiles as profile}
                  <option value={profile.name}>{profile.name}</option>
                {/each}
              </select>
            </label>
            <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
              <input
                type="text"
                class="flex-1 rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
                placeholder="Preset name"
                bind:value={newDeviceName}
              />
              <button
                class="bg-blue-500 hover:bg-blue-400 text-white text-xs font-medium px-3 py-1 rounded"
                type="button"
                on:click={handleDeviceSave}
              >
                Save device
              </button>
              {#if availableDeviceProfiles.find((profile) => profile.name === selectedDeviceProfile)?.protected !== true}
                <button
                  class="bg-red-500 hover:bg-red-400 text-white text-xs font-medium px-3 py-1 rounded"
                  type="button"
                  on:click={handleDeviceDelete}
                >
                  Delete device
                </button>
              {/if}
            </div>
            <label class="flex flex-col gap-1">
              NextDraw model
              <select
                class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
                bind:value={deviceNextdrawModel}
                on:change={handleNextdrawModelChange}
              >
                {#each NEXTDRAW_MODELS as modelName}
                  <option value={modelName}>{modelName}</option>
                {/each}
              </select>
            </label>
          </div>

          <div class="grid gap-3 sm:grid-cols-2">
            <label class="flex flex-col gap-1">
              <span>Host</span>
              <input
                type="text"
                class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
                bind:value={deviceHost}
              />
            </label>
            <label class="flex flex-col gap-1">
              <span>Port</span>
              <input
                type="number"
                min="1"
                class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
                bind:value={devicePort}
              />
            </label>
            <label class="flex flex-col gap-1">
              <span>NextDraw/AxiCLI path</span>
              <input
                type="text"
                class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
                bind:value={deviceAxicliPath}
              />
            </label>
            <label class="flex flex-col gap-1">
              <span>Home offset X (mm)</span>
              <input
                type="number"
                step="0.1"
                class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
                bind:value={deviceHomeOffsetX}
              />
            </label>
            <label class="flex flex-col gap-1">
              <span>Home offset Y (mm)</span>
              <input
                type="number"
                step="0.1"
                class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
                bind:value={deviceHomeOffsetY}
              />
            </label>
          </div>
          <label class="flex flex-col gap-1">
            <span>Notes</span>
            <textarea
              class="min-h-[80px] rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
              bind:value={deviceNotes}
            />
          </label>
          <label class="flex items-center gap-2">
            <input type="checkbox" bind:checked={deviceNoHoming} />
            <span>Skip homing before plots (`--no_homing`)</span>
          </label>
        </div>
      {:else}
        <div class="space-y-3">
          <PenControls />
          <DisableMotors />
          <GetStatus />
        </div>
      {/if}
    </div>
  </div>
</div>
