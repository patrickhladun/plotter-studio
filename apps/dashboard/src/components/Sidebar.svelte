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
  import { showCommandToast, pushToast } from '../lib/toastStore';
  import { NEXTDRAW_MODELS, NEXTDRAW_MODEL_NUMBERS, NEXTDRAW_MODEL_MAP, DEFAULT_MODEL_NUMBER, getModelNumber, getModelName } from '../lib/nextdrawCommands';
  import { model } from '../lib/model';
  import WalkX from './actions/WalkX.svelte';
  import WalkY from './actions/WalkY.svelte';
import PenRaise from './actions/PenRaise.svelte';
import PenLower from './actions/PenLower.svelte';
  import EnableMotors from './actions/EnableMotors.svelte';
  import DisableMotors from './actions/DisableMotors.svelte';
  import WalkHome from './actions/WalkHome.svelte';
  import UploadImage from './sidebar/UploadImage.svelte';
  import EditImage from './sidebar/EditImage.svelte';
  import Plot from './sidebar/Plot.svelte';
  import PrintSettings from './sidebar/PrintSettings.svelte';
  import DevicePresets from './sidebar/DevicePresets.svelte';

  // Settings are now stored on the server in JSON files, not in browser localStorage
  // Removed localStorage functions - all settings now use API endpoints

  // Legacy unused function (kept for reference, will be removed)
  const readLocalPresets_UNUSED = <T>(key: string): Record<string, Partial<T>> => {
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

  // Legacy unused function (kept for reference, will be removed)
  const writeLocalPresets_UNUSED = <T>(key: string, data: Record<string, Partial<T>>) => {
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

  const dispatch = createEventDispatcher<{ preview: string }>();

  let files: FileMeta[] = [];
  let selectedFile: string = '';
  let selectedMeta: FileMeta | undefined;
  let selectedDimensions = '';
  let isLoading = false;
  let plotting = false;
  let rotating = false;
  let renaming = false;
  let stopping = false;
  let renameValue = '';
  let plotProgress: number | null = null;
  let plotRunning = false;
  let plotElapsedSeconds: number | null = null;
  let plotDistanceMm: number | null = null;
  let previewLoading = false;
  let previewError: string | null = null;
  let previewTimeSeconds: number | null = null;
  let previewDistanceMm: number | null = null;
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
    'Default Preset'
  );
  $: availableDeviceProfiles =
    deviceProfiles.length > 0
      ? deviceProfiles
      : mergeProfiles(DEVICE_DEFAULTS, {}, BASE_DEVICE_SETTINGS, 'Default Preset');
  let selectedDeviceProfile: string =
    deviceProfiles.find((profile) => profile.name === 'Default Preset')?.name ?? 'Default Preset';
  let newDeviceName = '';

  let handlingMode = BASE_PLOT_SETTINGS.handling ?? 1;
  let speedSetting = BASE_PLOT_SETTINGS.speed ?? 70;
  let speedPenDown = BASE_PLOT_SETTINGS.s_down;
  let speedPenUp = BASE_PLOT_SETTINGS.s_up;
  let penPosDown = BASE_PLOT_SETTINGS.p_down;
  let penPosUp = BASE_PLOT_SETTINGS.p_up;
  let selectedLayer: string | null = null;
let devicePenliftMode = BASE_DEVICE_SETTINGS.penlift ?? 1;
let deviceNoHoming = BASE_DEVICE_SETTINGS.no_homing ?? false;
let deviceAxicliPath = BASE_DEVICE_SETTINGS.axicli_path ?? '';
let deviceHomeOffsetX = BASE_DEVICE_SETTINGS.home_offset_x ?? 0;
let deviceHomeOffsetY = BASE_DEVICE_SETTINGS.home_offset_y ?? 0;
let deviceNotes = BASE_DEVICE_SETTINGS.notes ?? '';
let deviceNextdrawModel: number = BASE_DEVICE_SETTINGS.nextdraw_model ?? DEFAULT_MODEL_NUMBER;

  // Keep model store in sync with deviceNextdrawModel
  $: if (deviceNextdrawModel !== undefined) {
    model.set(deviceNextdrawModel);
  }

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
      const errorMessage = error instanceof Error ? error.message : 'Failed to load files';
      const errorUrl = (error as any)?.url;
      const isTimeout = (error as any)?.isTimeout;
      
      let message = errorMessage;
      if (isTimeout) {
        message = 'Request timeout - API server may not be reachable';
      } else if (errorMessage.includes('Failed to fetch') || errorMessage.includes('NetworkError')) {
        message = 'Cannot connect to API server - check network connection and CORS settings';
      }
      
      pushToast(`Load failed: ${message}${errorUrl ? ` (${errorUrl})` : ''}`, { tone: 'error' });
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
      // Load presets from server
      const overrides = await filesApi.getPrintPresets();
      plotProfiles = mergeProfiles(PRINT_DEFAULTS, overrides, BASE_PLOT_SETTINGS, 'AxiDraw');
      
      // Load selected profile from server
      const savedProfiles = await filesApi.getSelectedProfiles();
      if (savedProfiles.printProfile) {
        const hasSavedProfile = plotProfiles.some((profile) => profile.name === savedProfiles.printProfile);
        if (hasSavedProfile) {
          selectedProfile = savedProfiles.printProfile!;
        }
      }
      
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
    // Always use deviceNextdrawModel state variable (it's the source of truth)
    // Validate it's a valid model number, otherwise use default
    const modelNumber = (deviceNextdrawModel >= 1 && deviceNextdrawModel <= 10) 
      ? deviceNextdrawModel 
      : DEFAULT_MODEL_NUMBER;
    const modelName = getModelName(modelNumber);
    return {
      ...getPrintProfilePayload(),
      penlift: penliftValue,
      brushless: penliftValue === 3,
      no_homing: Boolean(device.no_homing),
      model: modelName, // PlotSettings still uses string for backward compatibility with API
      layer: selectedLayer,
    };
  };

  const currentDeviceSettings = (): DeviceSettings => {
    const settings: DeviceSettings = {
    axicli_path: deviceAxicliPath || null,
    home_offset_x: Number.isFinite(Number(deviceHomeOffsetX)) ? Number(deviceHomeOffsetX) : 0,
    home_offset_y: Number.isFinite(Number(deviceHomeOffsetY)) ? Number(deviceHomeOffsetY) : 0,
    notes: deviceNotes || null,
    penlift: devicePenliftMode,
    no_homing: deviceNoHoming,
      nextdraw_model: deviceNextdrawModel || null,
    };
    console.log('[currentDeviceSettings] Returning settings with model:', settings.nextdraw_model);
    return settings;
  };

  const handleSaveProfile = async () => {
    const trimmed = newProfileName.trim() || selectedProfile;
    if (!trimmed) {
      pushToast('Provide a name for the settings preset.', { tone: 'error' });
      return;
    }
    try {
      const saved = getPrintProfilePayload();
      const overrides = await filesApi.getPrintPresets();
      overrides[trimmed] = saved;
      await filesApi.savePrintPresets(overrides);
      selectedProfile = trimmed;
      newProfileName = '';
      await saveSelectedProfiles(undefined, trimmed);
      pushToast(`Saved settings "${trimmed}"`, { tone: 'success' });
      await loadProfiles();
    } catch (error) {
      console.error('Failed to save settings', error);
      const message = error instanceof Error ? error.message : 'Failed to save settings';
      pushToast(message, { tone: 'error' });
    }
  };

  const handleDeleteProfile = async () => {
    const profile = plotProfiles.find((item) => item.name === selectedProfile);
    if (!profile || profile.protected) {
      pushToast('Cannot delete the default settings preset.', { tone: 'error' });
      return;
    }
    try {
      const overrides = await filesApi.getPrintPresets();
      delete overrides[profile.name];
      await filesApi.savePrintPresets(overrides);
      pushToast(`Deleted settings "${profile.name}"`, { tone: 'success' });
      selectedProfile = 'AxiDraw';
      await saveSelectedProfiles(undefined, 'AxiDraw');
      await loadProfiles(true);
    } catch (error) {
      console.error('Failed to delete settings', error);
      const message = error instanceof Error ? error.message : 'Failed to delete settings';
      pushToast(message, { tone: 'error' });
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

  const handleDevicePenliftChange = async (event: Event) => {
    const target = event.currentTarget as HTMLSelectElement | null;
    const value = target ? Number(target.value) : devicePenliftMode;
    devicePenliftMode = Number.isNaN(value) ? devicePenliftMode : value;
    
    // Save to server when settings change
    try {
      const settings = currentDeviceSettings();
      const overrides = await filesApi.getDevicePresets();
      overrides[selectedDeviceProfile] = {
        ...overrides[selectedDeviceProfile],
        ...settings,
      };
      await filesApi.saveDevicePresets(overrides);
    } catch (error) {
      console.warn('Failed to save device settings:', error);
    }
    
    if (selectedFile) {
      fetchPreview(selectedFile);
    }
  };

  const handleDevicePresetChange = async (event: Event) => {
    const target = event.currentTarget as HTMLSelectElement | null;
    const value = target ? target.value : selectedDeviceProfile;
    await applyDeviceProfile(value);
    if (selectedFile) {
      fetchPreview(selectedFile);
    }
  };

  const handleNextdrawModelChange = async (event: Event) => {
    const target = event.currentTarget as HTMLSelectElement | null;
    const modelNumber = target ? Number(target.value) : DEFAULT_MODEL_NUMBER;
    if (!isNaN(modelNumber) && modelNumber >= 1 && modelNumber <= 10) {
      deviceNextdrawModel = modelNumber;
    } else {
      deviceNextdrawModel = DEFAULT_MODEL_NUMBER;
    }
    
    // Save to server when settings change
    try {
      const settings = currentDeviceSettings();
      const overrides = await filesApi.getDevicePresets();
      overrides[selectedDeviceProfile] = {
        ...overrides[selectedDeviceProfile],
        ...settings,
      };
      await filesApi.saveDevicePresets(overrides);
    } catch (error) {
      console.warn('Failed to save device settings:', error);
    }
    
    if (selectedFile) {
      fetchPreview(selectedFile);
    }
  };

  const applyDeviceProfile = async (name: string, skipSave = false) => {
    const profile = deviceProfiles.find((item) => item.name === name) ?? deviceProfiles[0];
    const settings = profile?.settings ?? BASE_DEVICE_SETTINGS;
    deviceAxicliPath = settings.axicli_path ?? BASE_DEVICE_SETTINGS.axicli_path ?? '';
    deviceHomeOffsetX = settings.home_offset_x ?? BASE_DEVICE_SETTINGS.home_offset_x ?? 0;
    deviceHomeOffsetY = settings.home_offset_y ?? BASE_DEVICE_SETTINGS.home_offset_y ?? 0;
    deviceNotes = settings.notes ?? BASE_DEVICE_SETTINGS.notes ?? '';
    devicePenliftMode = settings.penlift ?? BASE_DEVICE_SETTINGS.penlift ?? 1;
    deviceNoHoming =
      typeof settings.no_homing === 'boolean'
        ? settings.no_homing
        : Boolean(BASE_DEVICE_SETTINGS.no_homing);
    const savedModel = settings.nextdraw_model ?? BASE_DEVICE_SETTINGS.nextdraw_model ?? DEFAULT_MODEL_NUMBER;
    // Convert to number (handles both string and number for backward compatibility)
    const modelNumber = getModelNumber(savedModel);
    deviceNextdrawModel = modelNumber ?? DEFAULT_MODEL_NUMBER;
    // Update model store
    model.set(deviceNextdrawModel);
    console.log('[applyDeviceProfile] Loaded model from profile:', savedModel);
    console.log('[applyDeviceProfile] Validated model number:', deviceNextdrawModel);
    if (profile) {
      selectedDeviceProfile = profile.name;
      // Save selected profile to server (unless this is during initial load)
      if (!skipSave) {
        await saveSelectedProfiles(profile.name);
      }
    }
  };

  // Save selected profiles to server
  const saveSelectedProfiles = async (deviceProfile?: string, printProfile?: string) => {
    try {
      const current = await filesApi.getSelectedProfiles();
      await filesApi.saveSelectedProfiles({
        deviceProfile: deviceProfile ?? current.deviceProfile ?? null,
        printProfile: printProfile ?? current.printProfile ?? null,
      });
    } catch (error) {
      console.warn('Failed to save selected profiles:', error);
    }
  };

  const loadDeviceProfiles = async (initial = false) => {
    try {
      // Load presets from server
      const overrides = await filesApi.getDevicePresets();
      
      // Apply overrides to DEVICE_DEFAULTS
      let effectiveDefaults = { ...DEVICE_DEFAULTS };
      if (overrides['Default Preset']) {
        effectiveDefaults['Default Preset'] = {
          ...effectiveDefaults['Default Preset'],
          ...overrides['Default Preset'],
        };
      }
      
      deviceProfiles = mergeProfiles(effectiveDefaults, overrides, BASE_DEVICE_SETTINGS, 'Default Preset');
      
      // Load selected profile from server
      const savedProfiles = await filesApi.getSelectedProfiles();
      if (savedProfiles.deviceProfile) {
        const hasSavedProfile = deviceProfiles.some((profile) => profile.name === savedProfiles.deviceProfile);
        if (hasSavedProfile) {
          selectedDeviceProfile = savedProfiles.deviceProfile!;
        }
      }

      const hasSelection = deviceProfiles.some((profile) => profile.name === selectedDeviceProfile);
      if (!hasSelection) {
        selectedDeviceProfile =
          deviceProfiles.find((profile) => profile.name === 'Default Preset')?.name ??
          deviceProfiles[0]?.name ??
          'Default Preset';
      }
      if (initial || !hasSelection) {
        await applyDeviceProfile(selectedDeviceProfile, initial);
      }
    } catch (error) {
      console.error('Failed to load device settings', error);
      if (deviceProfiles.length === 0) {
        deviceProfiles = mergeProfiles(DEVICE_DEFAULTS, {}, BASE_DEVICE_SETTINGS, 'Default Preset');
        await applyDeviceProfile(deviceProfiles[0].name, true);
      }
    }
  };

  const handleDeviceSave = async () => {
    // If name is empty, save to currently selected profile (usually "Default Preset")
    const trimmed = newDeviceName.trim() || selectedDeviceProfile;
    if (!trimmed) {
      pushToast('Provide a name for the device preset.', { tone: 'error' });
      return;
    }
    try {
      const settings = currentDeviceSettings();
      console.log('[handleDeviceSave] Saving device settings:', {
        profile: trimmed,
        model: settings.nextdraw_model,
        deviceNextdrawModel,
        allSettings: settings,
      });
      
      // Validate model number before saving
      const modelNumber = getModelNumber(settings.nextdraw_model);
      if (modelNumber === null || modelNumber < 1 || modelNumber > 10) {
        console.error('[handleDeviceSave] Invalid model number in settings:', settings.nextdraw_model);
        pushToast(`Invalid model number: ${settings.nextdraw_model}`, { tone: 'error' });
        return;
      }
      // Ensure we save as number
      settings.nextdraw_model = modelNumber;
      
      // Save to server
      const overrides = await filesApi.getDevicePresets();
      overrides[trimmed] = settings;
      await filesApi.saveDevicePresets(overrides);
      console.log('[handleDeviceSave] Saved to server:', overrides[trimmed]);
      
      newDeviceName = '';
      selectedDeviceProfile = trimmed;
      
      // Save selected profile to server
      await saveSelectedProfiles(trimmed);
      
      // Reload profiles to ensure everything is in sync
      await loadDeviceProfiles();
      console.log('[handleDeviceSave] After reload, deviceNextdrawModel:', deviceNextdrawModel);
      pushToast(`Saved device "${trimmed}"`, { tone: 'success' });
    } catch (error) {
      console.error('Failed to save device settings', error);
      const message = error instanceof Error ? error.message : 'Failed to save device settings';
      pushToast(message, { tone: 'error' });
    }
  };

  const handleDeviceDelete = async () => {
    const profile = deviceProfiles.find((item) => item.name === selectedDeviceProfile);
    if (!profile) {
      pushToast('Select a device preset to delete.', { tone: 'error' });
      return;
    }
    if (profile.protected) {
      pushToast('Repo-managed device presets cannot be deleted.', { tone: 'error' });
      return;
    }
    try {
      const overrides = await filesApi.getDevicePresets();
      delete overrides[profile.name];
      await filesApi.saveDevicePresets(overrides);
      
      // Save selected profile
      await saveSelectedProfiles('Default Preset');
      
      pushToast(`Deleted device "${profile.name}"`, { tone: 'success' });
      selectedDeviceProfile = 'Default Preset';
      await loadDeviceProfiles(true);
    } catch (error) {
      console.error('Failed to delete device settings', error);
      const message = error instanceof Error ? error.message : 'Failed to delete device settings';
      pushToast(message, { tone: 'error' });
    }
  };


  let lastSessionUpdate: number | null = null;
  let sessionPollInterval: ReturnType<typeof setInterval> | null = null;
  let isApplyingSessionState = false;

  const pollSessionState = async () => {
    try {
      const state = await filesApi.getSessionState();
      const serverUpdateTime = state?.last_updated || 0;
      
      // Only apply if the server state is newer than our last update
      if (serverUpdateTime && (!lastSessionUpdate || serverUpdateTime > lastSessionUpdate)) {
        isApplyingSessionState = true;
        
        // Update selected file if different
        if (state.selected_file !== undefined && state.selected_file !== selectedFile) {
          if (state.selected_file && files.some((f) => f.name === state.selected_file)) {
            selectedFile = state.selected_file;
            renameValue = state.selected_file;
            requestFullPreview(state.selected_file);
          } else if (!state.selected_file) {
            selectedFile = '';
            renameValue = '';
            dispatch('preview', '');
            clearPreview();
          }
        }
        
        // Update selected layer if different
        if (state.selected_layer !== undefined && state.selected_layer !== selectedLayer) {
          selectedLayer = state.selected_layer;
          if (selectedFile) {
            fetchPreview(selectedFile);
            previewFile(selectedFile);
          }
        }
        
        isApplyingSessionState = false;
        lastSessionUpdate = serverUpdateTime;
      }
    } catch (error) {
      // Silently fail - session sync is optional
      console.debug('Session state poll failed:', error);
    }
  };

  const updateSessionState = async () => {
    if (isApplyingSessionState) {
      return; // Don't update server while applying server state
    }
    
    try {
      await filesApi.updateSessionState({
        selected_file: selectedFile || null,
        selected_layer: selectedLayer || null,
      });
      lastSessionUpdate = Date.now() / 1000; // Convert to seconds
    } catch (error) {
      console.debug('Failed to update session state:', error);
    }
  };

  onMount(() => {
    // Load initial session state first, then fetch files
    (async () => {
      await pollSessionState();
      await fetchFiles();
    })();
    
    pollStatus();
    loadProfiles(true);
    loadDeviceProfiles(true);
    
    // Start session state polling for multi-device sync (every 2 seconds)
    sessionPollInterval = setInterval(pollSessionState, 2000);
    
    return () => {
      if (sessionPollInterval) {
        clearInterval(sessionPollInterval);
      }
      if (syncTimeout) {
        clearTimeout(syncTimeout);
      }
    };
  });

  $: selectedMeta = files.find((file) => file.name === selectedFile);
  $: selectedDimensions = describeDimensions(selectedMeta);

  // Sync state changes to server (debounced to avoid too many updates)
  let syncTimeout: ReturnType<typeof setTimeout> | null = null;
  $: if (selectedFile !== undefined && !isApplyingSessionState) {
    if (syncTimeout) {
      clearTimeout(syncTimeout);
    }
    syncTimeout = setTimeout(() => {
      updateSessionState();
    }, 300); // Debounce by 300ms
  }
  
  $: if (selectedLayer !== undefined && !isApplyingSessionState) {
    if (syncTimeout) {
      clearTimeout(syncTimeout);
    }
    syncTimeout = setTimeout(() => {
      updateSessionState();
    }, 300); // Debounce by 300ms
  }

  const handlePlotStart = () => {
    plotting = true;
    plotRunning = true;
    plotProgress = 0;
    plotElapsedSeconds = 0;
    plotDistanceMm = previewDistanceMm;
  };

  const handlePlotComplete = (payload: any) => {
    plotting = false;
    const completed = Boolean(payload?.completed);
    if (completed) {
      plotRunning = false;
      plotProgress = 100;
      plotElapsedSeconds = 0;
    }
  };

  const handlePlotError = (error: string) => {
    plotting = false;
    plotRunning = false;
    plotProgress = null;
    plotElapsedSeconds = null;
  };


  const handleStopPlot = async () => {
    try {
      stopping = true;
      await filesApi.cancelPlot();
      pushToast('Plot canceled.', { tone: 'success' });
      plotRunning = false;
      plotProgress = null;
      pollStatus();
    } catch (error) {
      console.error('Stop failed', error);
      const message = error instanceof Error ? error.message : 'Failed to stop plot';
      pushToast(message, { tone: 'error' });
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
      if (errorMessage) {
        pushToast(errorMessage, { tone: 'error' });
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

  function filterSvgByLayer(svgContent: string, layerId: string | null): string {
    if (!layerId || !svgContent) {
      return svgContent;
    }

    try {
      const parser = new DOMParser();
      const doc = parser.parseFromString(svgContent, 'image/svg+xml');
      const svg = doc.querySelector('svg');
      if (!svg) {
        return svgContent;
      }

      // Find the layer element with the matching ID
      const layerElement = svg.querySelector(`#${CSS.escape(layerId)}`);
      if (!layerElement) {
        // Layer not found, return original
        return svgContent;
      }

      // Hide all direct children of SVG that are not the selected layer
      const directChildren = Array.from(svg.children);
      directChildren.forEach((child) => {
        const childId = child.getAttribute('id');
        if (childId !== layerId) {
          // Check if this child contains the layer element
          const containsLayer = child.contains(layerElement);
          if (!containsLayer) {
            // Hide elements that don't contain the selected layer
            const style = child.getAttribute('style') || '';
            if (!style.includes('display:none') && !style.includes('display: none')) {
              child.setAttribute('style', style ? `${style}; display: none` : 'display: none');
            }
          }
        } else {
          // This is the selected layer, ensure it's visible
          const style = child.getAttribute('style') || '';
          const cleanedStyle = style.replace(/display\s*:\s*none\s*;?/gi, '').trim();
          if (cleanedStyle) {
            child.setAttribute('style', cleanedStyle);
          } else {
            child.removeAttribute('style');
          }
        }
      });

      return new XMLSerializer().serializeToString(doc);
    } catch (error) {
      console.error('Failed to filter SVG by layer:', error);
      return svgContent;
    }
  }

  async function previewFile(name: string) {
    try {
      const svg = await filesApi.raw(name);
      const filteredSvg = filterSvgByLayer(svg, selectedLayer);
      dispatch('preview', filteredSvg);
    } catch (error) {
      console.error('Preview failed', error);
      pushToast('Preview failed', { tone: 'error' });
    }
  }


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

<div class="text-xs text-neutral-200 bg-neutral-700 p-2 h-screen flex flex-col w-full">
  <div class="mb-3 text-center text-sm font-semibold uppercase tracking-wide text-neutral-100 flex-shrink-0">
    Plotter Studio
  </div>

  <div class="flex-1 min-w-0 space-y-4 px-4 py-3 overflow-y-auto">
    <UploadImage
      {files}
      {selectedFile}
      {isLoading}
      on:uploaded={(e) => fetchFiles(e.detail)}
      on:fileSelected={(e) => {
        selectedFile = e.detail;
        renameValue = e.detail;
        requestFullPreview(e.detail);
      }}
      on:deleted={() => fetchFiles()}
      on:refresh={() => fetchFiles()}
    />

    <EditImage
      {selectedFile}
      {selectedDimensions}
      bind:renameValue
      bind:renaming
      bind:rotating
      on:renamed={(e) => {
        selectedFile = e.detail;
        renameValue = e.detail;
        fetchFiles(e.detail);
      }}
      on:rotated={() => fetchFiles(selectedFile)}
    />

    <PrintSettings
      {selectedFile}
      bind:selectedProfile
      {availablePlotProfiles}
      bind:newProfileName
      bind:handlingMode
      bind:speedSetting
      bind:speedPenDown
      bind:speedPenUp
      bind:penPosDown
      bind:penPosUp
      bind:selectedLayer
      bind:devicePenliftMode
      {previewLoading}
      {previewError}
      {previewTimeSeconds}
      {previewDistanceMm}
      on:profileChange={(e) => {
        applyProfileSettings(e.detail);
        if (selectedFile) {
          fetchPreview(selectedFile);
        }
      }}
      on:profileSave={handleSaveProfile}
      on:profileDelete={handleDeleteProfile}
      on:handlingChange={(e) => {
        handlingMode = e.detail;
        if (selectedFile) {
          fetchPreview(selectedFile);
        }
      }}
      on:speedChange={(e) => {
        speedSetting = e.detail;
        if (selectedFile) {
          fetchPreview(selectedFile);
        }
      }}
      on:layerChange={(e) => {
        selectedLayer = e.detail;
        if (selectedFile) {
          // Refresh both the preview metrics and the canvas display
          fetchPreview(selectedFile);
          previewFile(selectedFile);
        }
      }}
      on:penliftChange={async (e) => {
        devicePenliftMode = e.detail;
        // Save to server when settings change
        try {
          const settings = currentDeviceSettings();
          const overrides = await filesApi.getDevicePresets();
          overrides[selectedDeviceProfile] = {
            ...overrides[selectedDeviceProfile],
            ...settings,
          };
          await filesApi.saveDevicePresets(overrides);
        } catch (error) {
          console.warn('Failed to save device settings:', error);
        }
        if (selectedFile) {
          fetchPreview(selectedFile);
        }
      }}
      on:settingsChange={() => {
        if (selectedFile) {
          fetchPreview(selectedFile);
        }
      }}
    />

    <DevicePresets
      bind:selectedDeviceProfile
      {availableDeviceProfiles}
      bind:newDeviceName
      bind:deviceNextdrawModel
      bind:deviceAxicliPath
      bind:deviceHomeOffsetX
      bind:deviceHomeOffsetY
      bind:deviceNotes
      bind:devicePenliftMode
      bind:deviceNoHoming
      on:presetChange={async (e) => {
        await applyDeviceProfile(e.detail);
        if (selectedFile) {
          fetchPreview(selectedFile);
        }
      }}
      on:presetSave={handleDeviceSave}
      on:presetDelete={handleDeviceDelete}
      on:modelChange={async (e) => {
        const newModelNumber = e.detail;
        console.log('[modelChange] New model number selected:', newModelNumber);
        
        // Validate the model number is in valid range
        if (typeof newModelNumber !== 'number' || newModelNumber < 1 || newModelNumber > 10) {
          console.error('[modelChange] Invalid model number:', newModelNumber);
          pushToast(`Invalid model number: ${newModelNumber}`, { tone: 'error' });
          return;
        }
        
        deviceNextdrawModel = newModelNumber;
        // Update model store
        model.set(deviceNextdrawModel);
        
        // Save to device profile (server)
        try {
          const settings = currentDeviceSettings();
          const overrides = await filesApi.getDevicePresets();
          overrides[selectedDeviceProfile] = {
            ...overrides[selectedDeviceProfile],
            ...settings,
          };
          await filesApi.saveDevicePresets(overrides);
          
          // Also update the deviceProfiles array
          const profileIndex = deviceProfiles.findIndex((p) => p.name === selectedDeviceProfile);
          if (profileIndex >= 0) {
            deviceProfiles[profileIndex].settings = { ...deviceProfiles[profileIndex].settings, ...settings };
          }
        } catch (error) {
          console.error('[modelChange] Failed to save model to profile:', error);
        }
        
        // Settings are already saved to server above
        
        if (selectedFile) {
          fetchPreview(selectedFile);
        }
      }}
      on:penliftChange={async (e) => {
        devicePenliftMode = e.detail;
        // Save to server when settings change
        try {
          const settings = currentDeviceSettings();
          const overrides = await filesApi.getDevicePresets();
          overrides[selectedDeviceProfile] = {
            ...overrides[selectedDeviceProfile],
            ...settings,
          };
          await filesApi.saveDevicePresets(overrides);
        } catch (error) {
          console.warn('Failed to save device settings:', error);
        }
        if (selectedFile) {
          fetchPreview(selectedFile);
        }
      }}
      on:settingsChange={() => {
        if (selectedFile) {
          fetchPreview(selectedFile);
        }
      }}
    />

    <!-- Manual Controls -->
    <div class="space-y-3 border-t border-neutral-700">
          <div class="py-4 border-b border-neutral-600 text-xs text-neutral-200">
            <h2 class="font-semibold mb-2 text-sm text-white">Manual Controls</h2>
            <div class="flex flex-wrap gap-2">
              <PenRaise />
              <PenLower />
              <EnableMotors />
              <DisableMotors />
              <WalkHome />
            </div>
          </div>
          <div class="py-4 border-b border-neutral-600 text-xs text-neutral-200">
            <h2 class="font-semibold mb-2 text-sm text-white">Move Pen</h2>
            <div class="space-y-2">
              <WalkX />
              <WalkY />
            </div>
          </div>
        </div>
    </div>

  <!-- Plot section fixed at bottom -->
  <div class="flex-shrink-0 border-t border-neutral-600 px-4 py-3">
    <Plot
      {selectedFile}
      plotSettings={buildPlotPayload()}
      {plotProgress}
      {plotElapsedSeconds}
      {plotDistanceMm}
      {previewTimeSeconds}
      {previewDistanceMm}
      {plotting}
      {plotRunning}
      {rotating}
      {stopping}
      on:plotStart={handlePlotStart}
      on:plotComplete={(e) => handlePlotComplete(e.detail)}
      on:plotError={(e) => handlePlotError(e.detail)}
      on:statusPoll={pollStatus}
      on:stopPlot={handleStopPlot}
    />
  </div>
</div>
