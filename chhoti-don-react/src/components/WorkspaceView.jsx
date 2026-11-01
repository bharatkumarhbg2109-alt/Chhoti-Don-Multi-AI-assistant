import React, { useCallback, useEffect, useRef, useState } from 'react';
import Icon from './Icon';
import CodeBlock from './CodeBlock';
import {
  getWorkspaceStatus,
  grantWorkspace,
  revokeWorkspace,
  getWorkspaceFiles,
  getWorkspaceFile,
  getWorkspaceServers,
  stopWorkspaceServer,
  startCodingBuild,
  pollCodingBuild,
  respondCodingBuild,
  abortCodingBuild,
  streamCodingBuild,
  isDesktop,
} from '../services/chatApi';

export default function WorkspaceView() {
  const [workspace, setWorkspace] = useState({ active: false, root: null });
  const [loading, setLoading] = useState(true);
  const [pathInput, setPathInput] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [files, setFiles] = useState([]);
  const [servers, setServers] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState('');
  const [loadingFile, setLoadingFile] = useState(false);

  // Build agent state
  const [buildTask, setBuildTask] = useState('');
  const [activeSession, setActiveSession] = useState(null);
  const [isBuilding, setIsBuilding] = useState(false);
  const [liveEvents, setLiveEvents] = useState([]);
  const [liveDiffs, setLiveDiffs] = useState([]);
  const [currentStep, setCurrentStep] = useState(null);
  const pollingRef = useRef(null);
  const streamCleanupRef = useRef(null);

  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
      if (streamCleanupRef.current) streamCleanupRef.current();
    };
  }, []);

  const fetchStatus = useCallback(async () => {
    try {
      setLoading(true);
      const res = await getWorkspaceStatus();
      if (res && res.status === 'success') {
        setWorkspace({ active: Boolean(res.active), root: res.root || null });
        setServers(res.servers || []);
        if (res.active) {
          fetchFiles();
        }
      }
    } catch (err) {
      setErrorMsg(err.message || 'Failed to check workspace status');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchFiles = useCallback(async () => {
    try {
      const res = await getWorkspaceFiles('.', 3);
      if (res && res.status === 'success') {
        setFiles(res.entries || res.items || []);
      }
    } catch {
      /* ignore background poll */
    }
  }, []);

  const fetchServers = useCallback(async () => {
    try {
      const res = await getWorkspaceServers();
      if (res && res.status === 'success') {
        setServers(res.servers || []);
      }
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const timer = setInterval(() => {
      if (workspace.active) {
        fetchServers();
      }
    }, 10000);
    return () => clearInterval(timer);
  }, [fetchStatus, fetchServers, workspace.active]);

  // Browse folder using native Electron picker if available
  const handleBrowseFolder = async () => {
    if (isDesktop() && window.chhotiDon?.selectDirectory) {
      try {
        const selected = await window.chhotiDon.selectDirectory();
        if (selected) {
          setPathInput(selected);
          handleGrant(selected);
        }
      } catch (err) {
        setErrorMsg('Folder picker error: ' + err.message);
      }
    }
  };

  const handleGrant = async (targetPath) => {
    const p = targetPath || pathInput.trim();
    if (!p) {
      setErrorMsg('Please enter or select a directory path.');
      return;
    }
    try {
      setErrorMsg('');
      setLoading(true);
      const res = await grantWorkspace(p);
      if (res && res.status === 'success') {
        setWorkspace({ active: true, root: res.root });
        setPathInput('');
        fetchFiles();
      } else {
        setErrorMsg(res.message || 'Could not grant workspace');
      }
    } catch (err) {
      setErrorMsg(err.message || 'Grant workspace failed');
    } finally {
      setLoading(false);
    }
  };

  const handleRevoke = async () => {
    try {
      setErrorMsg('');
      await revokeWorkspace();
      setWorkspace({ active: false, root: null });
      setFiles([]);
      setSelectedFile(null);
      setFileContent('');
    } catch (err) {
      setErrorMsg(err.message || 'Failed to revoke workspace');
    }
  };

  const handleReadFile = async (filePath) => {
    try {
      setSelectedFile(filePath);
      setLoadingFile(true);
      const res = await getWorkspaceFile(filePath);
      if (res && res.status === 'success') {
        setFileContent(res.content || '');
      } else {
        setFileContent(`// Error reading file: ${res.message || 'Unknown error'}`);
      }
    } catch (err) {
      setFileContent(`// Error: ${err.message}`);
    } finally {
      setLoadingFile(false);
    }
  };

  const handleStopServer = async (serverId) => {
    try {
      await stopWorkspaceServer(serverId);
      fetchServers();
    } catch (err) {
      setErrorMsg('Failed to stop server: ' + err.message);
    }
  };

  // Build Loop Handlers (SSE Streaming with Polling Fallback)
  const handleStartBuild = async () => {
    if (!buildTask.trim()) return;
    try {
      setErrorMsg('');
      setIsBuilding(true);
      setLiveEvents([]);
      setLiveDiffs([]);
      setCurrentStep(null);
      const res = await startCodingBuild(buildTask.trim(), null, 0);
      setActiveSession(res);
      startStreaming(res.session_id);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to start build');
      setIsBuilding(false);
    }
  };

  const startStreaming = (sessionId) => {
    if (streamCleanupRef.current) {
      streamCleanupRef.current();
      streamCleanupRef.current = null;
    }
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }

    const cleanup = streamCodingBuild(sessionId, {
      onEvent: (event) => {
        setLiveEvents((prev) => [...prev.slice(-49), event]);

        if (event.event === 'diff' && event.diff) {
          setLiveDiffs((prev) => {
            const exists = prev.some((d) => d.id === event.id);
            return exists ? prev : [...prev, { path: event.path, diff: event.diff, id: event.id, tool: event.tool }];
          });
        } else if (event.event === 'action_complete' && event.diff) {
          setLiveDiffs((prev) => {
            const exists = prev.some((d) => d.id === event.id);
            return exists ? prev : [...prev, { path: event.path || event.args?.path, diff: event.diff, id: event.id, tool: event.tool }];
          });
        }

        if (event.event === 'action_start') {
          setCurrentStep({ step: event.step, tool: event.tool, args: event.args });
        }

        if (event.event === 'pending_plan') {
          setActiveSession((prev) => ({
            ...(prev || {}),
            session_id: sessionId,
            status: 'pending_plan',
            state: 'pending_plan',
            plan: event.plan,
            prompt: event.prompt,
          }));
        } else if (event.event === 'pending_confirmation') {
          setActiveSession((prev) => ({
            ...(prev || {}),
            session_id: sessionId,
            status: 'pending_confirmation',
            state: 'pending_confirmation',
            proposal: event.proposal || { prompt: event.prompt, diff: event.diff },
          }));
        } else if (event.event === 'done') {
          setActiveSession((prev) => ({
            ...(prev || {}),
            session_id: sessionId,
            status: 'done',
            state: 'done',
            result: event.result,
          }));
          setIsBuilding(false);
          fetchFiles();
          fetchServers();
        } else if (event.event === 'error') {
          setActiveSession((prev) => ({
            ...(prev || {}),
            session_id: sessionId,
            status: 'error',
            state: 'error',
            message: event.message || event.error,
          }));
          setIsBuilding(false);
        } else if (event.event === 'aborted') {
          setActiveSession((prev) => ({
            ...(prev || {}),
            session_id: sessionId,
            status: 'aborted',
            state: 'aborted',
            message: event.message,
          }));
          setIsBuilding(false);
        } else if (
          event.event === 'plan_approved' ||
          event.event === 'step_start' ||
          event.event === 'planning'
        ) {
          setActiveSession((prev) => ({
            ...(prev || {}),
            session_id: sessionId,
            status: 'running',
            state: 'running',
          }));
        }
      },
      onDone: () => {
        setIsBuilding(false);
        fetchFiles();
        fetchServers();
      },
      onError: (err) => {
        console.warn('[WorkspaceView] SSE stream interrupted, falling back to polling:', err);
        startPolling(sessionId);
      },
    });

    streamCleanupRef.current = cleanup;
  };

  const startPolling = (sessionId) => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    pollingRef.current = setInterval(async () => {
      try {
        const snap = await pollCodingBuild(sessionId, 5);
        setActiveSession(snap);
        if (snap.status === 'done' || snap.status === 'error' || snap.status === 'aborted') {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
          setIsBuilding(false);
          fetchFiles();
          fetchServers();
        }
      } catch (err) {
        console.error('Build poll failed:', err);
      }
    }, 2000);
  };

  const handleRespond = async (approve) => {
    if (!activeSession?.session_id) return;
    try {
      setActiveSession((prev) => ({ ...prev, status: 'running', state: 'running' }));
      const snap = await respondCodingBuild(activeSession.session_id, approve, 0);
      if (snap && snap.status && snap.status !== 'running') {
        setActiveSession((prev) => ({ ...(prev || {}), ...snap }));
      }
    } catch (err) {
      setErrorMsg('Approval response failed: ' + err.message);
    }
  };

  const handleAbort = async () => {
    if (!activeSession?.session_id) return;
    try {
      if (streamCleanupRef.current) {
        streamCleanupRef.current();
        streamCleanupRef.current = null;
      }
      const snap = await abortCodingBuild(activeSession.session_id);
      setActiveSession(snap);
      if (pollingRef.current) clearInterval(pollingRef.current);
      setIsBuilding(false);
    } catch (err) {
      setErrorMsg('Abort failed: ' + err.message);
    }
  };

  return (
    <div className="w-full space-y-6 pb-12">
      {/* Top Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-2xl border border-brand-200/15 bg-gradient-to-br from-brand-400/20 via-brand-deep-500/15 to-brand-blue-600/20 shadow-brand">
            <Icon name="code" className="h-5 w-5 text-brand-100" />
          </div>
          <div>
            <h2 className="font-display text-base font-semibold text-white">Coding Agent Workspace</h2>
            <p className="text-[11px] text-slate-400">
              Autonomous Software Engineering & Path-Jailed Environment
            </p>
          </div>
        </div>

        {/* Active Badge */}
        <div className="flex items-center gap-2">
          {workspace.active ? (
            <div className="flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs text-emerald-400">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="font-mono text-[11px] truncate max-w-[280px]" title={workspace.root}>
                {workspace.root}
              </span>
              <button
                onClick={handleRevoke}
                className="ml-2 text-slate-400 hover:text-red-400 text-xs underline"
                title="Revoke active workspace access"
              >
                Revoke
              </button>
            </div>
          ) : (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-500/20 bg-amber-500/10 px-3 py-1 text-xs text-amber-300">
              <span className="h-2 w-2 rounded-full bg-amber-400" />
              No Workspace Granted
            </span>
          )}
        </div>
      </div>

      {errorMsg && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-300 flex items-center justify-between">
          <span>{errorMsg}</span>
          <button onClick={() => setErrorMsg('')} className="text-slate-400 hover:text-white">
            <Icon name="close" className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Grant Workspace Card (When no active workspace) */}
      {!workspace.active && (
        <div className="rounded-3xl border border-white/[0.07] bg-gradient-to-br from-white/[0.03] to-brand-400/[0.02] p-8 text-center">
          <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl border border-brand-200/15 bg-gradient-to-br from-brand-400/20 via-brand-deep-500/15 to-brand-blue-600/20">
            <Icon name="grid" className="h-7 w-7 text-brand-100" />
          </div>
          <h3 className="mt-4 text-lg font-semibold text-white">Grant a Project Workspace</h3>
          <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-400">
            Select a project folder on your machine. Chhoti Don's autonomous builder will operate
            strictly inside this folder with symlink containment and diff confirmation gates.
          </p>

          <div className="mx-auto mt-6 flex max-w-lg items-center gap-2">
            <input
              type="text"
              placeholder="e.g. C:\Users\name\Projects\myapp or e:\Chhoti Don"
              value={pathInput}
              onChange={(e) => setPathInput(e.target.value)}
              className="flex-1 rounded-xl border border-white/10 bg-slate-900/80 px-3.5 py-2.5 text-xs text-slate-100 placeholder-slate-500 focus:border-brand-300 focus:outline-none focus:ring-1 focus:ring-brand-300"
            />
            {isDesktop() && (
              <button
                onClick={handleBrowseFolder}
                className="rounded-xl border border-white/10 bg-white/5 px-3.5 py-2.5 text-xs font-medium text-slate-200 hover:bg-white/10"
              >
                Browse...
              </button>
            )}
            <button
              onClick={() => handleGrant(pathInput)}
              disabled={loading || !pathInput.trim()}
              className="rounded-xl bg-gradient-to-r from-brand-400 to-brand-deep-500 px-4 py-2.5 text-xs font-semibold text-slate-950 shadow-brand hover:brightness-110 disabled:opacity-50"
            >
              Grant Access
            </button>
          </div>
        </div>
      )}

      {/* Main Two-Column Workspace Layout (When active) */}
      {workspace.active && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          {/* Left Column: Explorer & Dev Servers (4 cols) */}
          <div className="space-y-6 lg:col-span-4">
            {/* File Tree Card */}
            <div className="rounded-2xl border border-white/[0.08] bg-slate-900/60 p-4 backdrop-blur">
              <div className="mb-3 flex items-center justify-between border-b border-white/5 pb-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Workspace Files
                </span>
                <button
                  onClick={fetchFiles}
                  className="p-1 text-slate-400 hover:text-white"
                  title="Refresh files"
                >
                  <Icon name="refresh" className="h-3.5 w-3.5" />
                </button>
              </div>

              <div className="max-h-[380px] overflow-y-auto space-y-1 font-mono text-xs">
                {files.length === 0 ? (
                  <p className="py-4 text-center text-slate-500">Empty folder</p>
                ) : (
                  files.map((item, idx) => {
                    const isDir = item.type === 'directory' || item.type === 'dir';
                    const isSelected = selectedFile === item.path;
                    return (
                      <div
                        key={idx}
                        onClick={() => !isDir && handleReadFile(item.path)}
                        className={`flex items-center justify-between px-2 py-1.5 rounded-lg cursor-pointer transition ${
                          isSelected
                            ? 'bg-brand-500/20 text-brand-200'
                            : 'text-slate-300 hover:bg-white/5'
                        }`}
                      >
                        <span className="flex items-center gap-2 truncate">
                          <span className="text-slate-500">{isDir ? '📁' : '📄'}</span>
                          <span className="truncate">{item.path}</span>
                        </span>
                        {!isDir && (
                          <span className="text-[10px] text-slate-500">
                            {item.size ? `${Math.round(item.size / 1024)}k` : ''}
                          </span>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Active Servers Card */}
            <div className="rounded-2xl border border-white/[0.08] bg-slate-900/60 p-4 backdrop-blur">
              <div className="mb-3 flex items-center justify-between border-b border-white/5 pb-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Local Dev Servers
                </span>
                <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] text-slate-300">
                  {servers.length} running
                </span>
              </div>

              {servers.length === 0 ? (
                <p className="py-2 text-center text-[11px] text-slate-500">
                  No background servers running.
                </p>
              ) : (
                <div className="space-y-2">
                  {servers.map((srv) => (
                    <div
                      key={srv.id}
                      className="flex items-center justify-between rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-2.5 text-xs"
                    >
                      <div className="truncate">
                        <p className="font-mono text-emerald-300 truncate">{srv.command}</p>
                        {srv.url && (
                          <a
                            href={srv.url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-[11px] text-brand-300 underline hover:text-brand-200"
                          >
                            {srv.url}
                          </a>
                        )}
                      </div>
                      <button
                        onClick={() => handleStopServer(srv.id)}
                        className="ml-2 rounded-lg bg-red-500/10 px-2.5 py-1 text-[11px] font-medium text-red-400 hover:bg-red-500/20"
                      >
                        Stop
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Autonomous Builder & File Viewer (8 cols) */}
          <div className="space-y-6 lg:col-span-8">
            {/* Autonomous Builder Panel */}
            <div className="rounded-3xl border border-white/[0.08] bg-slate-900/60 p-6 backdrop-blur">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h3 className="font-display text-sm font-semibold text-white">
                    Autonomous ReAct Builder
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    Proposes plans, scaffolds files, executes test suites, and self-heals bugs.
                  </p>
                </div>
                {isBuilding && (
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-brand-400 animate-ping" />
                    <span className="text-xs text-brand-300 font-mono">Running...</span>
                    <button
                      onClick={handleAbort}
                      className="ml-2 text-xs text-red-400 hover:underline"
                    >
                      Abort
                    </button>
                  </div>
                )}
              </div>

              {/* Task Input Box */}
              {!activeSession || activeSession.status === 'done' || activeSession.status === 'error' ? (
                <div className="space-y-3">
                  <textarea
                    rows={3}
                    placeholder="Describe what you want to build or modify in this workspace (e.g. 'Scaffold a FastAPI backend with health check and test suite')"
                    value={buildTask}
                    onChange={(e) => setBuildTask(e.target.value)}
                    className="w-full rounded-2xl border border-white/10 bg-slate-950/60 p-3.5 text-xs text-slate-100 placeholder-slate-500 focus:border-brand-300 focus:outline-none focus:ring-1 focus:ring-brand-300"
                  />
                  <div className="flex justify-end">
                    <button
                      onClick={handleStartBuild}
                      disabled={isBuilding || !buildTask.trim()}
                      className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-brand-400 to-brand-deep-500 px-5 py-2.5 text-xs font-semibold text-slate-950 shadow-brand hover:brightness-110 disabled:opacity-50"
                    >
                      <Icon name="sparkles" className="h-4 w-4" />
                      Build in Workspace
                    </button>
                  </div>
                </div>
              ) : null}

              {/* Active Build Status / Plan Approval Checkpoint */}
              {activeSession && (
                <div className="mt-4 space-y-4">
                  {/* Live Streaming Build Progress (SSE) */}
                  {(isBuilding || activeSession.status === 'running') && (
                    <div className="rounded-2xl border border-brand-500/30 bg-brand-500/5 p-5 space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-brand-300 font-semibold text-xs">
                          <span className="h-2 w-2 rounded-full bg-brand-400 animate-pulse" />
                          <span>Real-Time SSE Build Stream Active</span>
                        </div>
                        {currentStep && (
                          <span className="rounded-md bg-brand-500/20 px-2 py-0.5 text-[10px] font-mono text-brand-200">
                            Step {currentStep.step}: {currentStep.tool}
                          </span>
                        )}
                      </div>

                      {/* Live Event Activity Feed */}
                      {liveEvents.length > 0 && (
                        <div className="space-y-1.5">
                          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                            Live Execution Log:
                          </p>
                          <div className="max-h-36 overflow-y-auto space-y-1 rounded-xl bg-slate-950/80 p-2.5 font-mono text-[10px] text-slate-300 border border-white/5">
                            {liveEvents.slice(-10).map((evt, idx) => (
                              <div key={idx} className="flex items-start gap-2 truncate">
                                <span className="text-slate-500">[{new Date((evt.timestamp || Date.now() / 1000) * 1000).toLocaleTimeString()}]</span>
                                <span className="text-brand-300 font-bold">{evt.event}</span>
                                <span className="text-slate-400 truncate">
                                  {evt.tool ? `${evt.tool} ${JSON.stringify(evt.args || {})}` : (evt.task || evt.prompt || evt.summary || evt.status || '')}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Live Streamed Diffs */}
                      {liveDiffs.length > 0 && (
                        <div className="space-y-2">
                          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                            Live Code Diffs ({liveDiffs.length}):
                          </p>
                          <div className="max-h-52 overflow-y-auto space-y-2 rounded-xl bg-slate-950/90 p-3 font-mono text-[11px] border border-white/5">
                            {liveDiffs.map((d, idx) => (
                              <div key={idx} className="space-y-1">
                                <div className="text-emerald-400 font-semibold text-[11px] flex items-center gap-1.5">
                                  <span>📄</span>
                                  <span>{d.path || 'file'}</span>
                                  <span className="text-[10px] text-slate-500 font-normal">({d.tool})</span>
                                </div>
                                <pre className="text-slate-300 text-[10px] whitespace-pre-wrap bg-slate-900/60 p-2 rounded-lg overflow-x-auto">
                                  {d.diff}
                                </pre>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Pending Plan Approval */}
                  {activeSession.status === 'pending_plan' && (
                    <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-5 space-y-3">
                      <div className="flex items-center gap-2 text-amber-300 font-semibold text-xs">
                        <Icon name="shield" className="h-4 w-4" />
                        Plan Approval Required
                      </div>
                      <p className="text-xs text-slate-300">
                        The agent generated the following execution plan. Approve to allow file mutations:
                      </p>
                      <div className="max-h-48 overflow-y-auto space-y-1 rounded-xl bg-slate-950/70 p-3 font-mono text-[11px] text-slate-200">
                        {activeSession.plan?.map((step, idx) => (
                          <div key={idx} className="flex gap-2">
                            <span className="text-brand-300 font-bold">{idx + 1}.</span>
                            <span className="text-emerald-300">{step.tool}</span>
                            <span className="text-slate-400 truncate">
                              {JSON.stringify(step.args)}
                            </span>
                          </div>
                        ))}
                      </div>
                      <div className="flex gap-3 justify-end pt-2">
                        <button
                          onClick={() => handleRespond(false)}
                          className="rounded-xl bg-slate-800 px-4 py-2 text-xs font-medium text-red-300 hover:bg-slate-700"
                        >
                          Reject Plan
                        </button>
                        <button
                          onClick={() => handleRespond(true)}
                          className="rounded-xl bg-emerald-500 px-4 py-2 text-xs font-semibold text-slate-950 hover:bg-emerald-400"
                        >
                          Approve & Execute Plan
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Pending Confirmation (Diff / High Risk Action) */}
                  {activeSession.status === 'pending_confirmation' && (
                    <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-5 space-y-3">
                      <div className="flex items-center gap-2 text-amber-300 font-semibold text-xs">
                        <Icon name="shield" className="h-4 w-4" />
                        Confirmation Required for Action
                      </div>
                      <p className="text-xs text-slate-300">
                        {activeSession.proposal?.summary || activeSession.proposal?.prompt}
                      </p>
                      {activeSession.proposal?.diff && (
                        <div className="max-h-60 overflow-y-auto rounded-xl bg-slate-950/90 p-3 font-mono text-[11px]">
                          <pre className="text-slate-300 whitespace-pre-wrap">
                            {activeSession.proposal.diff}
                          </pre>
                        </div>
                      )}
                      <div className="flex gap-3 justify-end pt-2">
                        <button
                          onClick={() => handleRespond(false)}
                          className="rounded-xl bg-slate-800 px-4 py-2 text-xs font-medium text-red-300 hover:bg-slate-700"
                        >
                          Deny Action
                        </button>
                        <button
                          onClick={() => handleRespond(true)}
                          className="rounded-xl bg-emerald-500 px-4 py-2 text-xs font-semibold text-slate-950 hover:bg-emerald-400"
                        >
                          Approve Action
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Build Completed */}
                  {activeSession.status === 'done' && activeSession.result && (
                    <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-5 space-y-3">
                      <div className="flex items-center gap-2 text-emerald-300 font-semibold text-xs">
                        <Icon name="sparkles" className="h-4 w-4" />
                        Build Complete: {activeSession.result.stopped}
                      </div>
                      <p className="text-xs text-slate-200">
                        {activeSession.result.summary}
                      </p>
                      {activeSession.result.executed?.length > 0 && (
                        <div className="space-y-1">
                          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                            Files Created/Modified:
                          </p>
                          <div className="flex flex-wrap gap-1.5 font-mono text-[11px]">
                            {activeSession.result.executed.map((f, i) => (
                              <span
                                key={i}
                                onClick={() => handleReadFile(f.path)}
                                className="rounded bg-slate-800 px-2 py-0.5 text-brand-300 cursor-pointer hover:bg-slate-700"
                              >
                                {f.path}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      <div className="flex justify-end pt-2">
                        <button
                          onClick={() => {
                            setActiveSession(null);
                            setBuildTask('');
                          }}
                          className="rounded-xl bg-white/10 px-3.5 py-1.5 text-xs text-slate-200 hover:bg-white/20"
                        >
                          Dismiss & New Task
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Error State */}
                  {activeSession.status === 'error' && (
                    <div className="rounded-2xl border border-red-500/30 bg-red-500/10 p-5 space-y-2">
                      <p className="text-xs font-semibold text-red-300">
                        Build Error: {activeSession.message || 'Unknown error'}
                      </p>
                      <button
                        onClick={() => setActiveSession(null)}
                        className="rounded-xl bg-white/10 px-3 py-1 text-xs text-slate-200 hover:bg-white/20"
                      >
                        Dismiss
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* File Viewer Panel (When a file is selected) */}
            {selectedFile && (
              <div className="rounded-3xl border border-white/[0.08] bg-slate-900/60 p-6 backdrop-blur">
                <div className="mb-3 flex items-center justify-between border-b border-white/5 pb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400">📄</span>
                    <span className="font-mono text-xs text-brand-200">{selectedFile}</span>
                  </div>
                  <button
                    onClick={() => setSelectedFile(null)}
                    className="text-xs text-slate-400 hover:text-white"
                  >
                    Close
                  </button>
                </div>

                {loadingFile ? (
                  <p className="py-6 text-center text-xs text-slate-400">Loading file...</p>
                ) : (
                  <div className="max-h-[420px] overflow-y-auto">
                    <CodeBlock code={fileContent} />
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
