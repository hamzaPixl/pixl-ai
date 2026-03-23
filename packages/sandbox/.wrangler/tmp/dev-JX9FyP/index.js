var __defProp = Object.defineProperty;
var __name = (target, value) => __defProp(target, "name", { value, configurable: true });

// node_modules/unenv/dist/runtime/_internal/utils.mjs
// @__NO_SIDE_EFFECTS__
function createNotImplementedError(name) {
  return new Error(`[unenv] ${name} is not implemented yet!`);
}
__name(createNotImplementedError, "createNotImplementedError");
// @__NO_SIDE_EFFECTS__
function notImplemented(name) {
  const fn = /* @__PURE__ */ __name(() => {
    throw /* @__PURE__ */ createNotImplementedError(name);
  }, "fn");
  return Object.assign(fn, { __unenv__: true });
}
__name(notImplemented, "notImplemented");
// @__NO_SIDE_EFFECTS__
function notImplementedClass(name) {
  return class {
    __unenv__ = true;
    constructor() {
      throw new Error(`[unenv] ${name} is not implemented yet!`);
    }
  };
}
__name(notImplementedClass, "notImplementedClass");

// node_modules/unenv/dist/runtime/node/internal/perf_hooks/performance.mjs
var _timeOrigin = globalThis.performance?.timeOrigin ?? Date.now();
var _performanceNow = globalThis.performance?.now ? globalThis.performance.now.bind(globalThis.performance) : () => Date.now() - _timeOrigin;
var nodeTiming = {
  name: "node",
  entryType: "node",
  startTime: 0,
  duration: 0,
  nodeStart: 0,
  v8Start: 0,
  bootstrapComplete: 0,
  environment: 0,
  loopStart: 0,
  loopExit: 0,
  idleTime: 0,
  uvMetricsInfo: {
    loopCount: 0,
    events: 0,
    eventsWaiting: 0
  },
  detail: void 0,
  toJSON() {
    return this;
  }
};
var PerformanceEntry = class {
  static {
    __name(this, "PerformanceEntry");
  }
  __unenv__ = true;
  detail;
  entryType = "event";
  name;
  startTime;
  constructor(name, options) {
    this.name = name;
    this.startTime = options?.startTime || _performanceNow();
    this.detail = options?.detail;
  }
  get duration() {
    return _performanceNow() - this.startTime;
  }
  toJSON() {
    return {
      name: this.name,
      entryType: this.entryType,
      startTime: this.startTime,
      duration: this.duration,
      detail: this.detail
    };
  }
};
var PerformanceMark = class PerformanceMark2 extends PerformanceEntry {
  static {
    __name(this, "PerformanceMark");
  }
  entryType = "mark";
  constructor() {
    super(...arguments);
  }
  get duration() {
    return 0;
  }
};
var PerformanceMeasure = class extends PerformanceEntry {
  static {
    __name(this, "PerformanceMeasure");
  }
  entryType = "measure";
};
var PerformanceResourceTiming = class extends PerformanceEntry {
  static {
    __name(this, "PerformanceResourceTiming");
  }
  entryType = "resource";
  serverTiming = [];
  connectEnd = 0;
  connectStart = 0;
  decodedBodySize = 0;
  domainLookupEnd = 0;
  domainLookupStart = 0;
  encodedBodySize = 0;
  fetchStart = 0;
  initiatorType = "";
  name = "";
  nextHopProtocol = "";
  redirectEnd = 0;
  redirectStart = 0;
  requestStart = 0;
  responseEnd = 0;
  responseStart = 0;
  secureConnectionStart = 0;
  startTime = 0;
  transferSize = 0;
  workerStart = 0;
  responseStatus = 0;
};
var PerformanceObserverEntryList = class {
  static {
    __name(this, "PerformanceObserverEntryList");
  }
  __unenv__ = true;
  getEntries() {
    return [];
  }
  getEntriesByName(_name, _type) {
    return [];
  }
  getEntriesByType(type) {
    return [];
  }
};
var Performance = class {
  static {
    __name(this, "Performance");
  }
  __unenv__ = true;
  timeOrigin = _timeOrigin;
  eventCounts = /* @__PURE__ */ new Map();
  _entries = [];
  _resourceTimingBufferSize = 0;
  navigation = void 0;
  timing = void 0;
  timerify(_fn, _options) {
    throw createNotImplementedError("Performance.timerify");
  }
  get nodeTiming() {
    return nodeTiming;
  }
  eventLoopUtilization() {
    return {};
  }
  markResourceTiming() {
    return new PerformanceResourceTiming("");
  }
  onresourcetimingbufferfull = null;
  now() {
    if (this.timeOrigin === _timeOrigin) {
      return _performanceNow();
    }
    return Date.now() - this.timeOrigin;
  }
  clearMarks(markName) {
    this._entries = markName ? this._entries.filter((e) => e.name !== markName) : this._entries.filter((e) => e.entryType !== "mark");
  }
  clearMeasures(measureName) {
    this._entries = measureName ? this._entries.filter((e) => e.name !== measureName) : this._entries.filter((e) => e.entryType !== "measure");
  }
  clearResourceTimings() {
    this._entries = this._entries.filter((e) => e.entryType !== "resource" || e.entryType !== "navigation");
  }
  getEntries() {
    return this._entries;
  }
  getEntriesByName(name, type) {
    return this._entries.filter((e) => e.name === name && (!type || e.entryType === type));
  }
  getEntriesByType(type) {
    return this._entries.filter((e) => e.entryType === type);
  }
  mark(name, options) {
    const entry = new PerformanceMark(name, options);
    this._entries.push(entry);
    return entry;
  }
  measure(measureName, startOrMeasureOptions, endMark) {
    let start;
    let end;
    if (typeof startOrMeasureOptions === "string") {
      start = this.getEntriesByName(startOrMeasureOptions, "mark")[0]?.startTime;
      end = this.getEntriesByName(endMark, "mark")[0]?.startTime;
    } else {
      start = Number.parseFloat(startOrMeasureOptions?.start) || this.now();
      end = Number.parseFloat(startOrMeasureOptions?.end) || this.now();
    }
    const entry = new PerformanceMeasure(measureName, {
      startTime: start,
      detail: {
        start,
        end
      }
    });
    this._entries.push(entry);
    return entry;
  }
  setResourceTimingBufferSize(maxSize) {
    this._resourceTimingBufferSize = maxSize;
  }
  addEventListener(type, listener, options) {
    throw createNotImplementedError("Performance.addEventListener");
  }
  removeEventListener(type, listener, options) {
    throw createNotImplementedError("Performance.removeEventListener");
  }
  dispatchEvent(event) {
    throw createNotImplementedError("Performance.dispatchEvent");
  }
  toJSON() {
    return this;
  }
};
var PerformanceObserver = class {
  static {
    __name(this, "PerformanceObserver");
  }
  __unenv__ = true;
  static supportedEntryTypes = [];
  _callback = null;
  constructor(callback) {
    this._callback = callback;
  }
  takeRecords() {
    return [];
  }
  disconnect() {
    throw createNotImplementedError("PerformanceObserver.disconnect");
  }
  observe(options) {
    throw createNotImplementedError("PerformanceObserver.observe");
  }
  bind(fn) {
    return fn;
  }
  runInAsyncScope(fn, thisArg, ...args) {
    return fn.call(thisArg, ...args);
  }
  asyncId() {
    return 0;
  }
  triggerAsyncId() {
    return 0;
  }
  emitDestroy() {
    return this;
  }
};
var performance = globalThis.performance && "addEventListener" in globalThis.performance ? globalThis.performance : new Performance();

// node_modules/@cloudflare/unenv-preset/dist/runtime/polyfill/performance.mjs
globalThis.performance = performance;
globalThis.Performance = Performance;
globalThis.PerformanceEntry = PerformanceEntry;
globalThis.PerformanceMark = PerformanceMark;
globalThis.PerformanceMeasure = PerformanceMeasure;
globalThis.PerformanceObserver = PerformanceObserver;
globalThis.PerformanceObserverEntryList = PerformanceObserverEntryList;
globalThis.PerformanceResourceTiming = PerformanceResourceTiming;

// node_modules/unenv/dist/runtime/node/console.mjs
import { Writable } from "node:stream";

// node_modules/unenv/dist/runtime/mock/noop.mjs
var noop_default = Object.assign(() => {
}, { __unenv__: true });

// node_modules/unenv/dist/runtime/node/console.mjs
var _console = globalThis.console;
var _ignoreErrors = true;
var _stderr = new Writable();
var _stdout = new Writable();
var log = _console?.log ?? noop_default;
var info = _console?.info ?? log;
var trace = _console?.trace ?? info;
var debug = _console?.debug ?? log;
var table = _console?.table ?? log;
var error = _console?.error ?? log;
var warn = _console?.warn ?? error;
var createTask = _console?.createTask ?? /* @__PURE__ */ notImplemented("console.createTask");
var clear = _console?.clear ?? noop_default;
var count = _console?.count ?? noop_default;
var countReset = _console?.countReset ?? noop_default;
var dir = _console?.dir ?? noop_default;
var dirxml = _console?.dirxml ?? noop_default;
var group = _console?.group ?? noop_default;
var groupEnd = _console?.groupEnd ?? noop_default;
var groupCollapsed = _console?.groupCollapsed ?? noop_default;
var profile = _console?.profile ?? noop_default;
var profileEnd = _console?.profileEnd ?? noop_default;
var time = _console?.time ?? noop_default;
var timeEnd = _console?.timeEnd ?? noop_default;
var timeLog = _console?.timeLog ?? noop_default;
var timeStamp = _console?.timeStamp ?? noop_default;
var Console = _console?.Console ?? /* @__PURE__ */ notImplementedClass("console.Console");
var _times = /* @__PURE__ */ new Map();
var _stdoutErrorHandler = noop_default;
var _stderrErrorHandler = noop_default;

// node_modules/@cloudflare/unenv-preset/dist/runtime/node/console.mjs
var workerdConsole = globalThis["console"];
var {
  assert,
  clear: clear2,
  // @ts-expect-error undocumented public API
  context,
  count: count2,
  countReset: countReset2,
  // @ts-expect-error undocumented public API
  createTask: createTask2,
  debug: debug2,
  dir: dir2,
  dirxml: dirxml2,
  error: error2,
  group: group2,
  groupCollapsed: groupCollapsed2,
  groupEnd: groupEnd2,
  info: info2,
  log: log2,
  profile: profile2,
  profileEnd: profileEnd2,
  table: table2,
  time: time2,
  timeEnd: timeEnd2,
  timeLog: timeLog2,
  timeStamp: timeStamp2,
  trace: trace2,
  warn: warn2
} = workerdConsole;
Object.assign(workerdConsole, {
  Console,
  _ignoreErrors,
  _stderr,
  _stderrErrorHandler,
  _stdout,
  _stdoutErrorHandler,
  _times
});
var console_default = workerdConsole;

// node_modules/wrangler/_virtual_unenv_global_polyfill-@cloudflare-unenv-preset-node-console
globalThis.console = console_default;

// node_modules/unenv/dist/runtime/node/internal/process/hrtime.mjs
var hrtime = /* @__PURE__ */ Object.assign(/* @__PURE__ */ __name(function hrtime2(startTime) {
  const now = Date.now();
  const seconds = Math.trunc(now / 1e3);
  const nanos = now % 1e3 * 1e6;
  if (startTime) {
    let diffSeconds = seconds - startTime[0];
    let diffNanos = nanos - startTime[0];
    if (diffNanos < 0) {
      diffSeconds = diffSeconds - 1;
      diffNanos = 1e9 + diffNanos;
    }
    return [diffSeconds, diffNanos];
  }
  return [seconds, nanos];
}, "hrtime"), { bigint: /* @__PURE__ */ __name(function bigint() {
  return BigInt(Date.now() * 1e6);
}, "bigint") });

// node_modules/unenv/dist/runtime/node/internal/process/process.mjs
import { EventEmitter } from "node:events";

// node_modules/unenv/dist/runtime/node/internal/tty/read-stream.mjs
var ReadStream = class {
  static {
    __name(this, "ReadStream");
  }
  fd;
  isRaw = false;
  isTTY = false;
  constructor(fd) {
    this.fd = fd;
  }
  setRawMode(mode) {
    this.isRaw = mode;
    return this;
  }
};

// node_modules/unenv/dist/runtime/node/internal/tty/write-stream.mjs
var WriteStream = class {
  static {
    __name(this, "WriteStream");
  }
  fd;
  columns = 80;
  rows = 24;
  isTTY = false;
  constructor(fd) {
    this.fd = fd;
  }
  clearLine(dir3, callback) {
    callback && callback();
    return false;
  }
  clearScreenDown(callback) {
    callback && callback();
    return false;
  }
  cursorTo(x, y, callback) {
    callback && typeof callback === "function" && callback();
    return false;
  }
  moveCursor(dx, dy, callback) {
    callback && callback();
    return false;
  }
  getColorDepth(env2) {
    return 1;
  }
  hasColors(count3, env2) {
    return false;
  }
  getWindowSize() {
    return [this.columns, this.rows];
  }
  write(str, encoding, cb) {
    if (str instanceof Uint8Array) {
      str = new TextDecoder().decode(str);
    }
    try {
      console.log(str);
    } catch {
    }
    cb && typeof cb === "function" && cb();
    return false;
  }
};

// node_modules/unenv/dist/runtime/node/internal/process/node-version.mjs
var NODE_VERSION = "22.14.0";

// node_modules/unenv/dist/runtime/node/internal/process/process.mjs
var Process = class _Process extends EventEmitter {
  static {
    __name(this, "Process");
  }
  env;
  hrtime;
  nextTick;
  constructor(impl) {
    super();
    this.env = impl.env;
    this.hrtime = impl.hrtime;
    this.nextTick = impl.nextTick;
    for (const prop of [...Object.getOwnPropertyNames(_Process.prototype), ...Object.getOwnPropertyNames(EventEmitter.prototype)]) {
      const value = this[prop];
      if (typeof value === "function") {
        this[prop] = value.bind(this);
      }
    }
  }
  // --- event emitter ---
  emitWarning(warning, type, code) {
    console.warn(`${code ? `[${code}] ` : ""}${type ? `${type}: ` : ""}${warning}`);
  }
  emit(...args) {
    return super.emit(...args);
  }
  listeners(eventName) {
    return super.listeners(eventName);
  }
  // --- stdio (lazy initializers) ---
  #stdin;
  #stdout;
  #stderr;
  get stdin() {
    return this.#stdin ??= new ReadStream(0);
  }
  get stdout() {
    return this.#stdout ??= new WriteStream(1);
  }
  get stderr() {
    return this.#stderr ??= new WriteStream(2);
  }
  // --- cwd ---
  #cwd = "/";
  chdir(cwd2) {
    this.#cwd = cwd2;
  }
  cwd() {
    return this.#cwd;
  }
  // --- dummy props and getters ---
  arch = "";
  platform = "";
  argv = [];
  argv0 = "";
  execArgv = [];
  execPath = "";
  title = "";
  pid = 200;
  ppid = 100;
  get version() {
    return `v${NODE_VERSION}`;
  }
  get versions() {
    return { node: NODE_VERSION };
  }
  get allowedNodeEnvironmentFlags() {
    return /* @__PURE__ */ new Set();
  }
  get sourceMapsEnabled() {
    return false;
  }
  get debugPort() {
    return 0;
  }
  get throwDeprecation() {
    return false;
  }
  get traceDeprecation() {
    return false;
  }
  get features() {
    return {};
  }
  get release() {
    return {};
  }
  get connected() {
    return false;
  }
  get config() {
    return {};
  }
  get moduleLoadList() {
    return [];
  }
  constrainedMemory() {
    return 0;
  }
  availableMemory() {
    return 0;
  }
  uptime() {
    return 0;
  }
  resourceUsage() {
    return {};
  }
  // --- noop methods ---
  ref() {
  }
  unref() {
  }
  // --- unimplemented methods ---
  umask() {
    throw createNotImplementedError("process.umask");
  }
  getBuiltinModule() {
    return void 0;
  }
  getActiveResourcesInfo() {
    throw createNotImplementedError("process.getActiveResourcesInfo");
  }
  exit() {
    throw createNotImplementedError("process.exit");
  }
  reallyExit() {
    throw createNotImplementedError("process.reallyExit");
  }
  kill() {
    throw createNotImplementedError("process.kill");
  }
  abort() {
    throw createNotImplementedError("process.abort");
  }
  dlopen() {
    throw createNotImplementedError("process.dlopen");
  }
  setSourceMapsEnabled() {
    throw createNotImplementedError("process.setSourceMapsEnabled");
  }
  loadEnvFile() {
    throw createNotImplementedError("process.loadEnvFile");
  }
  disconnect() {
    throw createNotImplementedError("process.disconnect");
  }
  cpuUsage() {
    throw createNotImplementedError("process.cpuUsage");
  }
  setUncaughtExceptionCaptureCallback() {
    throw createNotImplementedError("process.setUncaughtExceptionCaptureCallback");
  }
  hasUncaughtExceptionCaptureCallback() {
    throw createNotImplementedError("process.hasUncaughtExceptionCaptureCallback");
  }
  initgroups() {
    throw createNotImplementedError("process.initgroups");
  }
  openStdin() {
    throw createNotImplementedError("process.openStdin");
  }
  assert() {
    throw createNotImplementedError("process.assert");
  }
  binding() {
    throw createNotImplementedError("process.binding");
  }
  // --- attached interfaces ---
  permission = { has: /* @__PURE__ */ notImplemented("process.permission.has") };
  report = {
    directory: "",
    filename: "",
    signal: "SIGUSR2",
    compact: false,
    reportOnFatalError: false,
    reportOnSignal: false,
    reportOnUncaughtException: false,
    getReport: /* @__PURE__ */ notImplemented("process.report.getReport"),
    writeReport: /* @__PURE__ */ notImplemented("process.report.writeReport")
  };
  finalization = {
    register: /* @__PURE__ */ notImplemented("process.finalization.register"),
    unregister: /* @__PURE__ */ notImplemented("process.finalization.unregister"),
    registerBeforeExit: /* @__PURE__ */ notImplemented("process.finalization.registerBeforeExit")
  };
  memoryUsage = Object.assign(() => ({
    arrayBuffers: 0,
    rss: 0,
    external: 0,
    heapTotal: 0,
    heapUsed: 0
  }), { rss: /* @__PURE__ */ __name(() => 0, "rss") });
  // --- undefined props ---
  mainModule = void 0;
  domain = void 0;
  // optional
  send = void 0;
  exitCode = void 0;
  channel = void 0;
  getegid = void 0;
  geteuid = void 0;
  getgid = void 0;
  getgroups = void 0;
  getuid = void 0;
  setegid = void 0;
  seteuid = void 0;
  setgid = void 0;
  setgroups = void 0;
  setuid = void 0;
  // internals
  _events = void 0;
  _eventsCount = void 0;
  _exiting = void 0;
  _maxListeners = void 0;
  _debugEnd = void 0;
  _debugProcess = void 0;
  _fatalException = void 0;
  _getActiveHandles = void 0;
  _getActiveRequests = void 0;
  _kill = void 0;
  _preload_modules = void 0;
  _rawDebug = void 0;
  _startProfilerIdleNotifier = void 0;
  _stopProfilerIdleNotifier = void 0;
  _tickCallback = void 0;
  _disconnect = void 0;
  _handleQueue = void 0;
  _pendingMessage = void 0;
  _channel = void 0;
  _send = void 0;
  _linkedBinding = void 0;
};

// node_modules/@cloudflare/unenv-preset/dist/runtime/node/process.mjs
var globalProcess = globalThis["process"];
var getBuiltinModule = globalProcess.getBuiltinModule;
var workerdProcess = getBuiltinModule("node:process");
var unenvProcess = new Process({
  env: globalProcess.env,
  hrtime,
  // `nextTick` is available from workerd process v1
  nextTick: workerdProcess.nextTick
});
var { exit, features, platform } = workerdProcess;
var {
  _channel,
  _debugEnd,
  _debugProcess,
  _disconnect,
  _events,
  _eventsCount,
  _exiting,
  _fatalException,
  _getActiveHandles,
  _getActiveRequests,
  _handleQueue,
  _kill,
  _linkedBinding,
  _maxListeners,
  _pendingMessage,
  _preload_modules,
  _rawDebug,
  _send,
  _startProfilerIdleNotifier,
  _stopProfilerIdleNotifier,
  _tickCallback,
  abort,
  addListener,
  allowedNodeEnvironmentFlags,
  arch,
  argv,
  argv0,
  assert: assert2,
  availableMemory,
  binding,
  channel,
  chdir,
  config,
  connected,
  constrainedMemory,
  cpuUsage,
  cwd,
  debugPort,
  disconnect,
  dlopen,
  domain,
  emit,
  emitWarning,
  env,
  eventNames,
  execArgv,
  execPath,
  exitCode,
  finalization,
  getActiveResourcesInfo,
  getegid,
  geteuid,
  getgid,
  getgroups,
  getMaxListeners,
  getuid,
  hasUncaughtExceptionCaptureCallback,
  hrtime: hrtime3,
  initgroups,
  kill,
  listenerCount,
  listeners,
  loadEnvFile,
  mainModule,
  memoryUsage,
  moduleLoadList,
  nextTick,
  off,
  on,
  once,
  openStdin,
  permission,
  pid,
  ppid,
  prependListener,
  prependOnceListener,
  rawListeners,
  reallyExit,
  ref,
  release,
  removeAllListeners,
  removeListener,
  report,
  resourceUsage,
  send,
  setegid,
  seteuid,
  setgid,
  setgroups,
  setMaxListeners,
  setSourceMapsEnabled,
  setuid,
  setUncaughtExceptionCaptureCallback,
  sourceMapsEnabled,
  stderr,
  stdin,
  stdout,
  throwDeprecation,
  title,
  traceDeprecation,
  umask,
  unref,
  uptime,
  version,
  versions
} = unenvProcess;
var _process = {
  abort,
  addListener,
  allowedNodeEnvironmentFlags,
  hasUncaughtExceptionCaptureCallback,
  setUncaughtExceptionCaptureCallback,
  loadEnvFile,
  sourceMapsEnabled,
  arch,
  argv,
  argv0,
  chdir,
  config,
  connected,
  constrainedMemory,
  availableMemory,
  cpuUsage,
  cwd,
  debugPort,
  dlopen,
  disconnect,
  emit,
  emitWarning,
  env,
  eventNames,
  execArgv,
  execPath,
  exit,
  finalization,
  features,
  getBuiltinModule,
  getActiveResourcesInfo,
  getMaxListeners,
  hrtime: hrtime3,
  kill,
  listeners,
  listenerCount,
  memoryUsage,
  nextTick,
  on,
  off,
  once,
  pid,
  platform,
  ppid,
  prependListener,
  prependOnceListener,
  rawListeners,
  release,
  removeAllListeners,
  removeListener,
  report,
  resourceUsage,
  setMaxListeners,
  setSourceMapsEnabled,
  stderr,
  stdin,
  stdout,
  title,
  throwDeprecation,
  traceDeprecation,
  umask,
  uptime,
  version,
  versions,
  // @ts-expect-error old API
  domain,
  initgroups,
  moduleLoadList,
  reallyExit,
  openStdin,
  assert: assert2,
  binding,
  send,
  exitCode,
  channel,
  getegid,
  geteuid,
  getgid,
  getgroups,
  getuid,
  setegid,
  seteuid,
  setgid,
  setgroups,
  setuid,
  permission,
  mainModule,
  _events,
  _eventsCount,
  _exiting,
  _maxListeners,
  _debugEnd,
  _debugProcess,
  _fatalException,
  _getActiveHandles,
  _getActiveRequests,
  _kill,
  _preload_modules,
  _rawDebug,
  _startProfilerIdleNotifier,
  _stopProfilerIdleNotifier,
  _tickCallback,
  _disconnect,
  _handleQueue,
  _pendingMessage,
  _channel,
  _send,
  _linkedBinding
};
var process_default = _process;

// node_modules/wrangler/_virtual_unenv_global_polyfill-@cloudflare-unenv-preset-node-process
globalThis.process = process_default;

// node_modules/hono/dist/compose.js
var compose = /* @__PURE__ */ __name((middleware, onError, onNotFound) => {
  return (context2, next) => {
    let index = -1;
    return dispatch(0);
    async function dispatch(i) {
      if (i <= index) {
        throw new Error("next() called multiple times");
      }
      index = i;
      let res;
      let isError = false;
      let handler;
      if (middleware[i]) {
        handler = middleware[i][0][0];
        context2.req.routeIndex = i;
      } else {
        handler = i === middleware.length && next || void 0;
      }
      if (handler) {
        try {
          res = await handler(context2, () => dispatch(i + 1));
        } catch (err) {
          if (err instanceof Error && onError) {
            context2.error = err;
            res = await onError(err, context2);
            isError = true;
          } else {
            throw err;
          }
        }
      } else {
        if (context2.finalized === false && onNotFound) {
          res = await onNotFound(context2);
        }
      }
      if (res && (context2.finalized === false || isError)) {
        context2.res = res;
      }
      return context2;
    }
    __name(dispatch, "dispatch");
  };
}, "compose");

// node_modules/hono/dist/http-exception.js
var HTTPException = class extends Error {
  static {
    __name(this, "HTTPException");
  }
  res;
  status;
  /**
   * Creates an instance of `HTTPException`.
   * @param status - HTTP status code for the exception. Defaults to 500.
   * @param options - Additional options for the exception.
   */
  constructor(status = 500, options) {
    super(options?.message, { cause: options?.cause });
    this.res = options?.res;
    this.status = status;
  }
  /**
   * Returns the response object associated with the exception.
   * If a response object is not provided, a new response is created with the error message and status code.
   * @returns The response object.
   */
  getResponse() {
    if (this.res) {
      const newResponse = new Response(this.res.body, {
        status: this.status,
        headers: this.res.headers
      });
      return newResponse;
    }
    return new Response(this.message, {
      status: this.status
    });
  }
};

// node_modules/hono/dist/request/constants.js
var GET_MATCH_RESULT = /* @__PURE__ */ Symbol();

// node_modules/hono/dist/utils/body.js
var parseBody = /* @__PURE__ */ __name(async (request, options = /* @__PURE__ */ Object.create(null)) => {
  const { all = false, dot = false } = options;
  const headers = request instanceof HonoRequest ? request.raw.headers : request.headers;
  const contentType = headers.get("Content-Type");
  if (contentType?.startsWith("multipart/form-data") || contentType?.startsWith("application/x-www-form-urlencoded")) {
    return parseFormData(request, { all, dot });
  }
  return {};
}, "parseBody");
async function parseFormData(request, options) {
  const formData = await request.formData();
  if (formData) {
    return convertFormDataToBodyData(formData, options);
  }
  return {};
}
__name(parseFormData, "parseFormData");
function convertFormDataToBodyData(formData, options) {
  const form = /* @__PURE__ */ Object.create(null);
  formData.forEach((value, key) => {
    const shouldParseAllValues = options.all || key.endsWith("[]");
    if (!shouldParseAllValues) {
      form[key] = value;
    } else {
      handleParsingAllValues(form, key, value);
    }
  });
  if (options.dot) {
    Object.entries(form).forEach(([key, value]) => {
      const shouldParseDotValues = key.includes(".");
      if (shouldParseDotValues) {
        handleParsingNestedValues(form, key, value);
        delete form[key];
      }
    });
  }
  return form;
}
__name(convertFormDataToBodyData, "convertFormDataToBodyData");
var handleParsingAllValues = /* @__PURE__ */ __name((form, key, value) => {
  if (form[key] !== void 0) {
    if (Array.isArray(form[key])) {
      ;
      form[key].push(value);
    } else {
      form[key] = [form[key], value];
    }
  } else {
    if (!key.endsWith("[]")) {
      form[key] = value;
    } else {
      form[key] = [value];
    }
  }
}, "handleParsingAllValues");
var handleParsingNestedValues = /* @__PURE__ */ __name((form, key, value) => {
  if (/(?:^|\.)__proto__\./.test(key)) {
    return;
  }
  let nestedForm = form;
  const keys = key.split(".");
  keys.forEach((key2, index) => {
    if (index === keys.length - 1) {
      nestedForm[key2] = value;
    } else {
      if (!nestedForm[key2] || typeof nestedForm[key2] !== "object" || Array.isArray(nestedForm[key2]) || nestedForm[key2] instanceof File) {
        nestedForm[key2] = /* @__PURE__ */ Object.create(null);
      }
      nestedForm = nestedForm[key2];
    }
  });
}, "handleParsingNestedValues");

// node_modules/hono/dist/utils/url.js
var splitPath = /* @__PURE__ */ __name((path) => {
  const paths = path.split("/");
  if (paths[0] === "") {
    paths.shift();
  }
  return paths;
}, "splitPath");
var splitRoutingPath = /* @__PURE__ */ __name((routePath) => {
  const { groups, path } = extractGroupsFromPath(routePath);
  const paths = splitPath(path);
  return replaceGroupMarks(paths, groups);
}, "splitRoutingPath");
var extractGroupsFromPath = /* @__PURE__ */ __name((path) => {
  const groups = [];
  path = path.replace(/\{[^}]+\}/g, (match2, index) => {
    const mark = `@${index}`;
    groups.push([mark, match2]);
    return mark;
  });
  return { groups, path };
}, "extractGroupsFromPath");
var replaceGroupMarks = /* @__PURE__ */ __name((paths, groups) => {
  for (let i = groups.length - 1; i >= 0; i--) {
    const [mark] = groups[i];
    for (let j = paths.length - 1; j >= 0; j--) {
      if (paths[j].includes(mark)) {
        paths[j] = paths[j].replace(mark, groups[i][1]);
        break;
      }
    }
  }
  return paths;
}, "replaceGroupMarks");
var patternCache = {};
var getPattern = /* @__PURE__ */ __name((label, next) => {
  if (label === "*") {
    return "*";
  }
  const match2 = label.match(/^\:([^\{\}]+)(?:\{(.+)\})?$/);
  if (match2) {
    const cacheKey = `${label}#${next}`;
    if (!patternCache[cacheKey]) {
      if (match2[2]) {
        patternCache[cacheKey] = next && next[0] !== ":" && next[0] !== "*" ? [cacheKey, match2[1], new RegExp(`^${match2[2]}(?=/${next})`)] : [label, match2[1], new RegExp(`^${match2[2]}$`)];
      } else {
        patternCache[cacheKey] = [label, match2[1], true];
      }
    }
    return patternCache[cacheKey];
  }
  return null;
}, "getPattern");
var tryDecode = /* @__PURE__ */ __name((str, decoder2) => {
  try {
    return decoder2(str);
  } catch {
    return str.replace(/(?:%[0-9A-Fa-f]{2})+/g, (match2) => {
      try {
        return decoder2(match2);
      } catch {
        return match2;
      }
    });
  }
}, "tryDecode");
var tryDecodeURI = /* @__PURE__ */ __name((str) => tryDecode(str, decodeURI), "tryDecodeURI");
var getPath = /* @__PURE__ */ __name((request) => {
  const url = request.url;
  const start = url.indexOf("/", url.indexOf(":") + 4);
  let i = start;
  for (; i < url.length; i++) {
    const charCode = url.charCodeAt(i);
    if (charCode === 37) {
      const queryIndex = url.indexOf("?", i);
      const hashIndex = url.indexOf("#", i);
      const end = queryIndex === -1 ? hashIndex === -1 ? void 0 : hashIndex : hashIndex === -1 ? queryIndex : Math.min(queryIndex, hashIndex);
      const path = url.slice(start, end);
      return tryDecodeURI(path.includes("%25") ? path.replace(/%25/g, "%2525") : path);
    } else if (charCode === 63 || charCode === 35) {
      break;
    }
  }
  return url.slice(start, i);
}, "getPath");
var getPathNoStrict = /* @__PURE__ */ __name((request) => {
  const result = getPath(request);
  return result.length > 1 && result.at(-1) === "/" ? result.slice(0, -1) : result;
}, "getPathNoStrict");
var mergePath = /* @__PURE__ */ __name((base, sub, ...rest) => {
  if (rest.length) {
    sub = mergePath(sub, ...rest);
  }
  return `${base?.[0] === "/" ? "" : "/"}${base}${sub === "/" ? "" : `${base?.at(-1) === "/" ? "" : "/"}${sub?.[0] === "/" ? sub.slice(1) : sub}`}`;
}, "mergePath");
var checkOptionalParameter = /* @__PURE__ */ __name((path) => {
  if (path.charCodeAt(path.length - 1) !== 63 || !path.includes(":")) {
    return null;
  }
  const segments = path.split("/");
  const results = [];
  let basePath = "";
  segments.forEach((segment) => {
    if (segment !== "" && !/\:/.test(segment)) {
      basePath += "/" + segment;
    } else if (/\:/.test(segment)) {
      if (/\?/.test(segment)) {
        if (results.length === 0 && basePath === "") {
          results.push("/");
        } else {
          results.push(basePath);
        }
        const optionalSegment = segment.replace("?", "");
        basePath += "/" + optionalSegment;
        results.push(basePath);
      } else {
        basePath += "/" + segment;
      }
    }
  });
  return results.filter((v, i, a) => a.indexOf(v) === i);
}, "checkOptionalParameter");
var _decodeURI = /* @__PURE__ */ __name((value) => {
  if (!/[%+]/.test(value)) {
    return value;
  }
  if (value.indexOf("+") !== -1) {
    value = value.replace(/\+/g, " ");
  }
  return value.indexOf("%") !== -1 ? tryDecode(value, decodeURIComponent_) : value;
}, "_decodeURI");
var _getQueryParam = /* @__PURE__ */ __name((url, key, multiple) => {
  let encoded;
  if (!multiple && key && !/[%+]/.test(key)) {
    let keyIndex2 = url.indexOf("?", 8);
    if (keyIndex2 === -1) {
      return void 0;
    }
    if (!url.startsWith(key, keyIndex2 + 1)) {
      keyIndex2 = url.indexOf(`&${key}`, keyIndex2 + 1);
    }
    while (keyIndex2 !== -1) {
      const trailingKeyCode = url.charCodeAt(keyIndex2 + key.length + 1);
      if (trailingKeyCode === 61) {
        const valueIndex = keyIndex2 + key.length + 2;
        const endIndex = url.indexOf("&", valueIndex);
        return _decodeURI(url.slice(valueIndex, endIndex === -1 ? void 0 : endIndex));
      } else if (trailingKeyCode == 38 || isNaN(trailingKeyCode)) {
        return "";
      }
      keyIndex2 = url.indexOf(`&${key}`, keyIndex2 + 1);
    }
    encoded = /[%+]/.test(url);
    if (!encoded) {
      return void 0;
    }
  }
  const results = {};
  encoded ??= /[%+]/.test(url);
  let keyIndex = url.indexOf("?", 8);
  while (keyIndex !== -1) {
    const nextKeyIndex = url.indexOf("&", keyIndex + 1);
    let valueIndex = url.indexOf("=", keyIndex);
    if (valueIndex > nextKeyIndex && nextKeyIndex !== -1) {
      valueIndex = -1;
    }
    let name = url.slice(
      keyIndex + 1,
      valueIndex === -1 ? nextKeyIndex === -1 ? void 0 : nextKeyIndex : valueIndex
    );
    if (encoded) {
      name = _decodeURI(name);
    }
    keyIndex = nextKeyIndex;
    if (name === "") {
      continue;
    }
    let value;
    if (valueIndex === -1) {
      value = "";
    } else {
      value = url.slice(valueIndex + 1, nextKeyIndex === -1 ? void 0 : nextKeyIndex);
      if (encoded) {
        value = _decodeURI(value);
      }
    }
    if (multiple) {
      if (!(results[name] && Array.isArray(results[name]))) {
        results[name] = [];
      }
      ;
      results[name].push(value);
    } else {
      results[name] ??= value;
    }
  }
  return key ? results[key] : results;
}, "_getQueryParam");
var getQueryParam = _getQueryParam;
var getQueryParams = /* @__PURE__ */ __name((url, key) => {
  return _getQueryParam(url, key, true);
}, "getQueryParams");
var decodeURIComponent_ = decodeURIComponent;

// node_modules/hono/dist/request.js
var tryDecodeURIComponent = /* @__PURE__ */ __name((str) => tryDecode(str, decodeURIComponent_), "tryDecodeURIComponent");
var HonoRequest = class {
  static {
    __name(this, "HonoRequest");
  }
  /**
   * `.raw` can get the raw Request object.
   *
   * @see {@link https://hono.dev/docs/api/request#raw}
   *
   * @example
   * ```ts
   * // For Cloudflare Workers
   * app.post('/', async (c) => {
   *   const metadata = c.req.raw.cf?.hostMetadata?
   *   ...
   * })
   * ```
   */
  raw;
  #validatedData;
  // Short name of validatedData
  #matchResult;
  routeIndex = 0;
  /**
   * `.path` can get the pathname of the request.
   *
   * @see {@link https://hono.dev/docs/api/request#path}
   *
   * @example
   * ```ts
   * app.get('/about/me', (c) => {
   *   const pathname = c.req.path // `/about/me`
   * })
   * ```
   */
  path;
  bodyCache = {};
  constructor(request, path = "/", matchResult = [[]]) {
    this.raw = request;
    this.path = path;
    this.#matchResult = matchResult;
    this.#validatedData = {};
  }
  param(key) {
    return key ? this.#getDecodedParam(key) : this.#getAllDecodedParams();
  }
  #getDecodedParam(key) {
    const paramKey = this.#matchResult[0][this.routeIndex][1][key];
    const param = this.#getParamValue(paramKey);
    return param && /\%/.test(param) ? tryDecodeURIComponent(param) : param;
  }
  #getAllDecodedParams() {
    const decoded = {};
    const keys = Object.keys(this.#matchResult[0][this.routeIndex][1]);
    for (const key of keys) {
      const value = this.#getParamValue(this.#matchResult[0][this.routeIndex][1][key]);
      if (value !== void 0) {
        decoded[key] = /\%/.test(value) ? tryDecodeURIComponent(value) : value;
      }
    }
    return decoded;
  }
  #getParamValue(paramKey) {
    return this.#matchResult[1] ? this.#matchResult[1][paramKey] : paramKey;
  }
  query(key) {
    return getQueryParam(this.url, key);
  }
  queries(key) {
    return getQueryParams(this.url, key);
  }
  header(name) {
    if (name) {
      return this.raw.headers.get(name) ?? void 0;
    }
    const headerData = {};
    this.raw.headers.forEach((value, key) => {
      headerData[key] = value;
    });
    return headerData;
  }
  async parseBody(options) {
    return this.bodyCache.parsedBody ??= await parseBody(this, options);
  }
  #cachedBody = /* @__PURE__ */ __name((key) => {
    const { bodyCache, raw: raw2 } = this;
    const cachedBody = bodyCache[key];
    if (cachedBody) {
      return cachedBody;
    }
    const anyCachedKey = Object.keys(bodyCache)[0];
    if (anyCachedKey) {
      return bodyCache[anyCachedKey].then((body) => {
        if (anyCachedKey === "json") {
          body = JSON.stringify(body);
        }
        return new Response(body)[key]();
      });
    }
    return bodyCache[key] = raw2[key]();
  }, "#cachedBody");
  /**
   * `.json()` can parse Request body of type `application/json`
   *
   * @see {@link https://hono.dev/docs/api/request#json}
   *
   * @example
   * ```ts
   * app.post('/entry', async (c) => {
   *   const body = await c.req.json()
   * })
   * ```
   */
  json() {
    return this.#cachedBody("text").then((text) => JSON.parse(text));
  }
  /**
   * `.text()` can parse Request body of type `text/plain`
   *
   * @see {@link https://hono.dev/docs/api/request#text}
   *
   * @example
   * ```ts
   * app.post('/entry', async (c) => {
   *   const body = await c.req.text()
   * })
   * ```
   */
  text() {
    return this.#cachedBody("text");
  }
  /**
   * `.arrayBuffer()` parse Request body as an `ArrayBuffer`
   *
   * @see {@link https://hono.dev/docs/api/request#arraybuffer}
   *
   * @example
   * ```ts
   * app.post('/entry', async (c) => {
   *   const body = await c.req.arrayBuffer()
   * })
   * ```
   */
  arrayBuffer() {
    return this.#cachedBody("arrayBuffer");
  }
  /**
   * Parses the request body as a `Blob`.
   * @example
   * ```ts
   * app.post('/entry', async (c) => {
   *   const body = await c.req.blob();
   * });
   * ```
   * @see https://hono.dev/docs/api/request#blob
   */
  blob() {
    return this.#cachedBody("blob");
  }
  /**
   * Parses the request body as `FormData`.
   * @example
   * ```ts
   * app.post('/entry', async (c) => {
   *   const body = await c.req.formData();
   * });
   * ```
   * @see https://hono.dev/docs/api/request#formdata
   */
  formData() {
    return this.#cachedBody("formData");
  }
  /**
   * Adds validated data to the request.
   *
   * @param target - The target of the validation.
   * @param data - The validated data to add.
   */
  addValidatedData(target, data) {
    this.#validatedData[target] = data;
  }
  valid(target) {
    return this.#validatedData[target];
  }
  /**
   * `.url()` can get the request url strings.
   *
   * @see {@link https://hono.dev/docs/api/request#url}
   *
   * @example
   * ```ts
   * app.get('/about/me', (c) => {
   *   const url = c.req.url // `http://localhost:8787/about/me`
   *   ...
   * })
   * ```
   */
  get url() {
    return this.raw.url;
  }
  /**
   * `.method()` can get the method name of the request.
   *
   * @see {@link https://hono.dev/docs/api/request#method}
   *
   * @example
   * ```ts
   * app.get('/about/me', (c) => {
   *   const method = c.req.method // `GET`
   * })
   * ```
   */
  get method() {
    return this.raw.method;
  }
  get [GET_MATCH_RESULT]() {
    return this.#matchResult;
  }
  /**
   * `.matchedRoutes()` can return a matched route in the handler
   *
   * @deprecated
   *
   * Use matchedRoutes helper defined in "hono/route" instead.
   *
   * @see {@link https://hono.dev/docs/api/request#matchedroutes}
   *
   * @example
   * ```ts
   * app.use('*', async function logger(c, next) {
   *   await next()
   *   c.req.matchedRoutes.forEach(({ handler, method, path }, i) => {
   *     const name = handler.name || (handler.length < 2 ? '[handler]' : '[middleware]')
   *     console.log(
   *       method,
   *       ' ',
   *       path,
   *       ' '.repeat(Math.max(10 - path.length, 0)),
   *       name,
   *       i === c.req.routeIndex ? '<- respond from here' : ''
   *     )
   *   })
   * })
   * ```
   */
  get matchedRoutes() {
    return this.#matchResult[0].map(([[, route]]) => route);
  }
  /**
   * `routePath()` can retrieve the path registered within the handler
   *
   * @deprecated
   *
   * Use routePath helper defined in "hono/route" instead.
   *
   * @see {@link https://hono.dev/docs/api/request#routepath}
   *
   * @example
   * ```ts
   * app.get('/posts/:id', (c) => {
   *   return c.json({ path: c.req.routePath })
   * })
   * ```
   */
  get routePath() {
    return this.#matchResult[0].map(([[, route]]) => route)[this.routeIndex].path;
  }
};

// node_modules/hono/dist/utils/html.js
var HtmlEscapedCallbackPhase = {
  Stringify: 1,
  BeforeStream: 2,
  Stream: 3
};
var raw = /* @__PURE__ */ __name((value, callbacks) => {
  const escapedString = new String(value);
  escapedString.isEscaped = true;
  escapedString.callbacks = callbacks;
  return escapedString;
}, "raw");
var resolveCallback = /* @__PURE__ */ __name(async (str, phase, preserveCallbacks, context2, buffer) => {
  if (typeof str === "object" && !(str instanceof String)) {
    if (!(str instanceof Promise)) {
      str = str.toString();
    }
    if (str instanceof Promise) {
      str = await str;
    }
  }
  const callbacks = str.callbacks;
  if (!callbacks?.length) {
    return Promise.resolve(str);
  }
  if (buffer) {
    buffer[0] += str;
  } else {
    buffer = [str];
  }
  const resStr = Promise.all(callbacks.map((c) => c({ phase, buffer, context: context2 }))).then(
    (res) => Promise.all(
      res.filter(Boolean).map((str2) => resolveCallback(str2, phase, false, context2, buffer))
    ).then(() => buffer[0])
  );
  if (preserveCallbacks) {
    return raw(await resStr, callbacks);
  } else {
    return resStr;
  }
}, "resolveCallback");

// node_modules/hono/dist/context.js
var TEXT_PLAIN = "text/plain; charset=UTF-8";
var setDefaultContentType = /* @__PURE__ */ __name((contentType, headers) => {
  return {
    "Content-Type": contentType,
    ...headers
  };
}, "setDefaultContentType");
var createResponseInstance = /* @__PURE__ */ __name((body, init) => new Response(body, init), "createResponseInstance");
var Context = class {
  static {
    __name(this, "Context");
  }
  #rawRequest;
  #req;
  /**
   * `.env` can get bindings (environment variables, secrets, KV namespaces, D1 database, R2 bucket etc.) in Cloudflare Workers.
   *
   * @see {@link https://hono.dev/docs/api/context#env}
   *
   * @example
   * ```ts
   * // Environment object for Cloudflare Workers
   * app.get('*', async c => {
   *   const counter = c.env.COUNTER
   * })
   * ```
   */
  env = {};
  #var;
  finalized = false;
  /**
   * `.error` can get the error object from the middleware if the Handler throws an error.
   *
   * @see {@link https://hono.dev/docs/api/context#error}
   *
   * @example
   * ```ts
   * app.use('*', async (c, next) => {
   *   await next()
   *   if (c.error) {
   *     // do something...
   *   }
   * })
   * ```
   */
  error;
  #status;
  #executionCtx;
  #res;
  #layout;
  #renderer;
  #notFoundHandler;
  #preparedHeaders;
  #matchResult;
  #path;
  /**
   * Creates an instance of the Context class.
   *
   * @param req - The Request object.
   * @param options - Optional configuration options for the context.
   */
  constructor(req, options) {
    this.#rawRequest = req;
    if (options) {
      this.#executionCtx = options.executionCtx;
      this.env = options.env;
      this.#notFoundHandler = options.notFoundHandler;
      this.#path = options.path;
      this.#matchResult = options.matchResult;
    }
  }
  /**
   * `.req` is the instance of {@link HonoRequest}.
   */
  get req() {
    this.#req ??= new HonoRequest(this.#rawRequest, this.#path, this.#matchResult);
    return this.#req;
  }
  /**
   * @see {@link https://hono.dev/docs/api/context#event}
   * The FetchEvent associated with the current request.
   *
   * @throws Will throw an error if the context does not have a FetchEvent.
   */
  get event() {
    if (this.#executionCtx && "respondWith" in this.#executionCtx) {
      return this.#executionCtx;
    } else {
      throw Error("This context has no FetchEvent");
    }
  }
  /**
   * @see {@link https://hono.dev/docs/api/context#executionctx}
   * The ExecutionContext associated with the current request.
   *
   * @throws Will throw an error if the context does not have an ExecutionContext.
   */
  get executionCtx() {
    if (this.#executionCtx) {
      return this.#executionCtx;
    } else {
      throw Error("This context has no ExecutionContext");
    }
  }
  /**
   * @see {@link https://hono.dev/docs/api/context#res}
   * The Response object for the current request.
   */
  get res() {
    return this.#res ||= createResponseInstance(null, {
      headers: this.#preparedHeaders ??= new Headers()
    });
  }
  /**
   * Sets the Response object for the current request.
   *
   * @param _res - The Response object to set.
   */
  set res(_res) {
    if (this.#res && _res) {
      _res = createResponseInstance(_res.body, _res);
      for (const [k, v] of this.#res.headers.entries()) {
        if (k === "content-type") {
          continue;
        }
        if (k === "set-cookie") {
          const cookies = this.#res.headers.getSetCookie();
          _res.headers.delete("set-cookie");
          for (const cookie of cookies) {
            _res.headers.append("set-cookie", cookie);
          }
        } else {
          _res.headers.set(k, v);
        }
      }
    }
    this.#res = _res;
    this.finalized = true;
  }
  /**
   * `.render()` can create a response within a layout.
   *
   * @see {@link https://hono.dev/docs/api/context#render-setrenderer}
   *
   * @example
   * ```ts
   * app.get('/', (c) => {
   *   return c.render('Hello!')
   * })
   * ```
   */
  render = /* @__PURE__ */ __name((...args) => {
    this.#renderer ??= (content) => this.html(content);
    return this.#renderer(...args);
  }, "render");
  /**
   * Sets the layout for the response.
   *
   * @param layout - The layout to set.
   * @returns The layout function.
   */
  setLayout = /* @__PURE__ */ __name((layout) => this.#layout = layout, "setLayout");
  /**
   * Gets the current layout for the response.
   *
   * @returns The current layout function.
   */
  getLayout = /* @__PURE__ */ __name(() => this.#layout, "getLayout");
  /**
   * `.setRenderer()` can set the layout in the custom middleware.
   *
   * @see {@link https://hono.dev/docs/api/context#render-setrenderer}
   *
   * @example
   * ```tsx
   * app.use('*', async (c, next) => {
   *   c.setRenderer((content) => {
   *     return c.html(
   *       <html>
   *         <body>
   *           <p>{content}</p>
   *         </body>
   *       </html>
   *     )
   *   })
   *   await next()
   * })
   * ```
   */
  setRenderer = /* @__PURE__ */ __name((renderer) => {
    this.#renderer = renderer;
  }, "setRenderer");
  /**
   * `.header()` can set headers.
   *
   * @see {@link https://hono.dev/docs/api/context#header}
   *
   * @example
   * ```ts
   * app.get('/welcome', (c) => {
   *   // Set headers
   *   c.header('X-Message', 'Hello!')
   *   c.header('Content-Type', 'text/plain')
   *
   *   return c.body('Thank you for coming')
   * })
   * ```
   */
  header = /* @__PURE__ */ __name((name, value, options) => {
    if (this.finalized) {
      this.#res = createResponseInstance(this.#res.body, this.#res);
    }
    const headers = this.#res ? this.#res.headers : this.#preparedHeaders ??= new Headers();
    if (value === void 0) {
      headers.delete(name);
    } else if (options?.append) {
      headers.append(name, value);
    } else {
      headers.set(name, value);
    }
  }, "header");
  status = /* @__PURE__ */ __name((status) => {
    this.#status = status;
  }, "status");
  /**
   * `.set()` can set the value specified by the key.
   *
   * @see {@link https://hono.dev/docs/api/context#set-get}
   *
   * @example
   * ```ts
   * app.use('*', async (c, next) => {
   *   c.set('message', 'Hono is hot!!')
   *   await next()
   * })
   * ```
   */
  set = /* @__PURE__ */ __name((key, value) => {
    this.#var ??= /* @__PURE__ */ new Map();
    this.#var.set(key, value);
  }, "set");
  /**
   * `.get()` can use the value specified by the key.
   *
   * @see {@link https://hono.dev/docs/api/context#set-get}
   *
   * @example
   * ```ts
   * app.get('/', (c) => {
   *   const message = c.get('message')
   *   return c.text(`The message is "${message}"`)
   * })
   * ```
   */
  get = /* @__PURE__ */ __name((key) => {
    return this.#var ? this.#var.get(key) : void 0;
  }, "get");
  /**
   * `.var` can access the value of a variable.
   *
   * @see {@link https://hono.dev/docs/api/context#var}
   *
   * @example
   * ```ts
   * const result = c.var.client.oneMethod()
   * ```
   */
  // c.var.propName is a read-only
  get var() {
    if (!this.#var) {
      return {};
    }
    return Object.fromEntries(this.#var);
  }
  #newResponse(data, arg, headers) {
    const responseHeaders = this.#res ? new Headers(this.#res.headers) : this.#preparedHeaders ?? new Headers();
    if (typeof arg === "object" && "headers" in arg) {
      const argHeaders = arg.headers instanceof Headers ? arg.headers : new Headers(arg.headers);
      for (const [key, value] of argHeaders) {
        if (key.toLowerCase() === "set-cookie") {
          responseHeaders.append(key, value);
        } else {
          responseHeaders.set(key, value);
        }
      }
    }
    if (headers) {
      for (const [k, v] of Object.entries(headers)) {
        if (typeof v === "string") {
          responseHeaders.set(k, v);
        } else {
          responseHeaders.delete(k);
          for (const v2 of v) {
            responseHeaders.append(k, v2);
          }
        }
      }
    }
    const status = typeof arg === "number" ? arg : arg?.status ?? this.#status;
    return createResponseInstance(data, { status, headers: responseHeaders });
  }
  newResponse = /* @__PURE__ */ __name((...args) => this.#newResponse(...args), "newResponse");
  /**
   * `.body()` can return the HTTP response.
   * You can set headers with `.header()` and set HTTP status code with `.status`.
   * This can also be set in `.text()`, `.json()` and so on.
   *
   * @see {@link https://hono.dev/docs/api/context#body}
   *
   * @example
   * ```ts
   * app.get('/welcome', (c) => {
   *   // Set headers
   *   c.header('X-Message', 'Hello!')
   *   c.header('Content-Type', 'text/plain')
   *   // Set HTTP status code
   *   c.status(201)
   *
   *   // Return the response body
   *   return c.body('Thank you for coming')
   * })
   * ```
   */
  body = /* @__PURE__ */ __name((data, arg, headers) => this.#newResponse(data, arg, headers), "body");
  /**
   * `.text()` can render text as `Content-Type:text/plain`.
   *
   * @see {@link https://hono.dev/docs/api/context#text}
   *
   * @example
   * ```ts
   * app.get('/say', (c) => {
   *   return c.text('Hello!')
   * })
   * ```
   */
  text = /* @__PURE__ */ __name((text, arg, headers) => {
    return !this.#preparedHeaders && !this.#status && !arg && !headers && !this.finalized ? new Response(text) : this.#newResponse(
      text,
      arg,
      setDefaultContentType(TEXT_PLAIN, headers)
    );
  }, "text");
  /**
   * `.json()` can render JSON as `Content-Type:application/json`.
   *
   * @see {@link https://hono.dev/docs/api/context#json}
   *
   * @example
   * ```ts
   * app.get('/api', (c) => {
   *   return c.json({ message: 'Hello!' })
   * })
   * ```
   */
  json = /* @__PURE__ */ __name((object, arg, headers) => {
    return this.#newResponse(
      JSON.stringify(object),
      arg,
      setDefaultContentType("application/json", headers)
    );
  }, "json");
  html = /* @__PURE__ */ __name((html, arg, headers) => {
    const res = /* @__PURE__ */ __name((html2) => this.#newResponse(html2, arg, setDefaultContentType("text/html; charset=UTF-8", headers)), "res");
    return typeof html === "object" ? resolveCallback(html, HtmlEscapedCallbackPhase.Stringify, false, {}).then(res) : res(html);
  }, "html");
  /**
   * `.redirect()` can Redirect, default status code is 302.
   *
   * @see {@link https://hono.dev/docs/api/context#redirect}
   *
   * @example
   * ```ts
   * app.get('/redirect', (c) => {
   *   return c.redirect('/')
   * })
   * app.get('/redirect-permanently', (c) => {
   *   return c.redirect('/', 301)
   * })
   * ```
   */
  redirect = /* @__PURE__ */ __name((location, status) => {
    const locationString = String(location);
    this.header(
      "Location",
      // Multibyes should be encoded
      // eslint-disable-next-line no-control-regex
      !/[^\x00-\xFF]/.test(locationString) ? locationString : encodeURI(locationString)
    );
    return this.newResponse(null, status ?? 302);
  }, "redirect");
  /**
   * `.notFound()` can return the Not Found Response.
   *
   * @see {@link https://hono.dev/docs/api/context#notfound}
   *
   * @example
   * ```ts
   * app.get('/notfound', (c) => {
   *   return c.notFound()
   * })
   * ```
   */
  notFound = /* @__PURE__ */ __name(() => {
    this.#notFoundHandler ??= () => createResponseInstance();
    return this.#notFoundHandler(this);
  }, "notFound");
};

// node_modules/hono/dist/router.js
var METHOD_NAME_ALL = "ALL";
var METHOD_NAME_ALL_LOWERCASE = "all";
var METHODS = ["get", "post", "put", "delete", "options", "patch"];
var MESSAGE_MATCHER_IS_ALREADY_BUILT = "Can not add a route since the matcher is already built.";
var UnsupportedPathError = class extends Error {
  static {
    __name(this, "UnsupportedPathError");
  }
};

// node_modules/hono/dist/utils/constants.js
var COMPOSED_HANDLER = "__COMPOSED_HANDLER";

// node_modules/hono/dist/hono-base.js
var notFoundHandler = /* @__PURE__ */ __name((c) => {
  return c.text("404 Not Found", 404);
}, "notFoundHandler");
var errorHandler = /* @__PURE__ */ __name((err, c) => {
  if ("getResponse" in err) {
    const res = err.getResponse();
    return c.newResponse(res.body, res);
  }
  console.error(err);
  return c.text("Internal Server Error", 500);
}, "errorHandler");
var Hono = class _Hono {
  static {
    __name(this, "_Hono");
  }
  get;
  post;
  put;
  delete;
  options;
  patch;
  all;
  on;
  use;
  /*
    This class is like an abstract class and does not have a router.
    To use it, inherit the class and implement router in the constructor.
  */
  router;
  getPath;
  // Cannot use `#` because it requires visibility at JavaScript runtime.
  _basePath = "/";
  #path = "/";
  routes = [];
  constructor(options = {}) {
    const allMethods = [...METHODS, METHOD_NAME_ALL_LOWERCASE];
    allMethods.forEach((method) => {
      this[method] = (args1, ...args) => {
        if (typeof args1 === "string") {
          this.#path = args1;
        } else {
          this.#addRoute(method, this.#path, args1);
        }
        args.forEach((handler) => {
          this.#addRoute(method, this.#path, handler);
        });
        return this;
      };
    });
    this.on = (method, path, ...handlers) => {
      for (const p of [path].flat()) {
        this.#path = p;
        for (const m of [method].flat()) {
          handlers.map((handler) => {
            this.#addRoute(m.toUpperCase(), this.#path, handler);
          });
        }
      }
      return this;
    };
    this.use = (arg1, ...handlers) => {
      if (typeof arg1 === "string") {
        this.#path = arg1;
      } else {
        this.#path = "*";
        handlers.unshift(arg1);
      }
      handlers.forEach((handler) => {
        this.#addRoute(METHOD_NAME_ALL, this.#path, handler);
      });
      return this;
    };
    const { strict, ...optionsWithoutStrict } = options;
    Object.assign(this, optionsWithoutStrict);
    this.getPath = strict ?? true ? options.getPath ?? getPath : getPathNoStrict;
  }
  #clone() {
    const clone = new _Hono({
      router: this.router,
      getPath: this.getPath
    });
    clone.errorHandler = this.errorHandler;
    clone.#notFoundHandler = this.#notFoundHandler;
    clone.routes = this.routes;
    return clone;
  }
  #notFoundHandler = notFoundHandler;
  // Cannot use `#` because it requires visibility at JavaScript runtime.
  errorHandler = errorHandler;
  /**
   * `.route()` allows grouping other Hono instance in routes.
   *
   * @see {@link https://hono.dev/docs/api/routing#grouping}
   *
   * @param {string} path - base Path
   * @param {Hono} app - other Hono instance
   * @returns {Hono} routed Hono instance
   *
   * @example
   * ```ts
   * const app = new Hono()
   * const app2 = new Hono()
   *
   * app2.get("/user", (c) => c.text("user"))
   * app.route("/api", app2) // GET /api/user
   * ```
   */
  route(path, app2) {
    const subApp = this.basePath(path);
    app2.routes.map((r) => {
      let handler;
      if (app2.errorHandler === errorHandler) {
        handler = r.handler;
      } else {
        handler = /* @__PURE__ */ __name(async (c, next) => (await compose([], app2.errorHandler)(c, () => r.handler(c, next))).res, "handler");
        handler[COMPOSED_HANDLER] = r.handler;
      }
      subApp.#addRoute(r.method, r.path, handler);
    });
    return this;
  }
  /**
   * `.basePath()` allows base paths to be specified.
   *
   * @see {@link https://hono.dev/docs/api/routing#base-path}
   *
   * @param {string} path - base Path
   * @returns {Hono} changed Hono instance
   *
   * @example
   * ```ts
   * const api = new Hono().basePath('/api')
   * ```
   */
  basePath(path) {
    const subApp = this.#clone();
    subApp._basePath = mergePath(this._basePath, path);
    return subApp;
  }
  /**
   * `.onError()` handles an error and returns a customized Response.
   *
   * @see {@link https://hono.dev/docs/api/hono#error-handling}
   *
   * @param {ErrorHandler} handler - request Handler for error
   * @returns {Hono} changed Hono instance
   *
   * @example
   * ```ts
   * app.onError((err, c) => {
   *   console.error(`${err}`)
   *   return c.text('Custom Error Message', 500)
   * })
   * ```
   */
  onError = /* @__PURE__ */ __name((handler) => {
    this.errorHandler = handler;
    return this;
  }, "onError");
  /**
   * `.notFound()` allows you to customize a Not Found Response.
   *
   * @see {@link https://hono.dev/docs/api/hono#not-found}
   *
   * @param {NotFoundHandler} handler - request handler for not-found
   * @returns {Hono} changed Hono instance
   *
   * @example
   * ```ts
   * app.notFound((c) => {
   *   return c.text('Custom 404 Message', 404)
   * })
   * ```
   */
  notFound = /* @__PURE__ */ __name((handler) => {
    this.#notFoundHandler = handler;
    return this;
  }, "notFound");
  /**
   * `.mount()` allows you to mount applications built with other frameworks into your Hono application.
   *
   * @see {@link https://hono.dev/docs/api/hono#mount}
   *
   * @param {string} path - base Path
   * @param {Function} applicationHandler - other Request Handler
   * @param {MountOptions} [options] - options of `.mount()`
   * @returns {Hono} mounted Hono instance
   *
   * @example
   * ```ts
   * import { Router as IttyRouter } from 'itty-router'
   * import { Hono } from 'hono'
   * // Create itty-router application
   * const ittyRouter = IttyRouter()
   * // GET /itty-router/hello
   * ittyRouter.get('/hello', () => new Response('Hello from itty-router'))
   *
   * const app = new Hono()
   * app.mount('/itty-router', ittyRouter.handle)
   * ```
   *
   * @example
   * ```ts
   * const app = new Hono()
   * // Send the request to another application without modification.
   * app.mount('/app', anotherApp, {
   *   replaceRequest: (req) => req,
   * })
   * ```
   */
  mount(path, applicationHandler, options) {
    let replaceRequest;
    let optionHandler;
    if (options) {
      if (typeof options === "function") {
        optionHandler = options;
      } else {
        optionHandler = options.optionHandler;
        if (options.replaceRequest === false) {
          replaceRequest = /* @__PURE__ */ __name((request) => request, "replaceRequest");
        } else {
          replaceRequest = options.replaceRequest;
        }
      }
    }
    const getOptions = optionHandler ? (c) => {
      const options2 = optionHandler(c);
      return Array.isArray(options2) ? options2 : [options2];
    } : (c) => {
      let executionContext = void 0;
      try {
        executionContext = c.executionCtx;
      } catch {
      }
      return [c.env, executionContext];
    };
    replaceRequest ||= (() => {
      const mergedPath = mergePath(this._basePath, path);
      const pathPrefixLength = mergedPath === "/" ? 0 : mergedPath.length;
      return (request) => {
        const url = new URL(request.url);
        url.pathname = url.pathname.slice(pathPrefixLength) || "/";
        return new Request(url, request);
      };
    })();
    const handler = /* @__PURE__ */ __name(async (c, next) => {
      const res = await applicationHandler(replaceRequest(c.req.raw), ...getOptions(c));
      if (res) {
        return res;
      }
      await next();
    }, "handler");
    this.#addRoute(METHOD_NAME_ALL, mergePath(path, "*"), handler);
    return this;
  }
  #addRoute(method, path, handler) {
    method = method.toUpperCase();
    path = mergePath(this._basePath, path);
    const r = { basePath: this._basePath, path, method, handler };
    this.router.add(method, path, [handler, r]);
    this.routes.push(r);
  }
  #handleError(err, c) {
    if (err instanceof Error) {
      return this.errorHandler(err, c);
    }
    throw err;
  }
  #dispatch(request, executionCtx, env2, method) {
    if (method === "HEAD") {
      return (async () => new Response(null, await this.#dispatch(request, executionCtx, env2, "GET")))();
    }
    const path = this.getPath(request, { env: env2 });
    const matchResult = this.router.match(method, path);
    const c = new Context(request, {
      path,
      matchResult,
      env: env2,
      executionCtx,
      notFoundHandler: this.#notFoundHandler
    });
    if (matchResult[0].length === 1) {
      let res;
      try {
        res = matchResult[0][0][0][0](c, async () => {
          c.res = await this.#notFoundHandler(c);
        });
      } catch (err) {
        return this.#handleError(err, c);
      }
      return res instanceof Promise ? res.then(
        (resolved) => resolved || (c.finalized ? c.res : this.#notFoundHandler(c))
      ).catch((err) => this.#handleError(err, c)) : res ?? this.#notFoundHandler(c);
    }
    const composed = compose(matchResult[0], this.errorHandler, this.#notFoundHandler);
    return (async () => {
      try {
        const context2 = await composed(c);
        if (!context2.finalized) {
          throw new Error(
            "Context is not finalized. Did you forget to return a Response object or `await next()`?"
          );
        }
        return context2.res;
      } catch (err) {
        return this.#handleError(err, c);
      }
    })();
  }
  /**
   * `.fetch()` will be entry point of your app.
   *
   * @see {@link https://hono.dev/docs/api/hono#fetch}
   *
   * @param {Request} request - request Object of request
   * @param {Env} Env - env Object
   * @param {ExecutionContext} - context of execution
   * @returns {Response | Promise<Response>} response of request
   *
   */
  fetch = /* @__PURE__ */ __name((request, ...rest) => {
    return this.#dispatch(request, rest[1], rest[0], request.method);
  }, "fetch");
  /**
   * `.request()` is a useful method for testing.
   * You can pass a URL or pathname to send a GET request.
   * app will return a Response object.
   * ```ts
   * test('GET /hello is ok', async () => {
   *   const res = await app.request('/hello')
   *   expect(res.status).toBe(200)
   * })
   * ```
   * @see https://hono.dev/docs/api/hono#request
   */
  request = /* @__PURE__ */ __name((input, requestInit, Env, executionCtx) => {
    if (input instanceof Request) {
      return this.fetch(requestInit ? new Request(input, requestInit) : input, Env, executionCtx);
    }
    input = input.toString();
    return this.fetch(
      new Request(
        /^https?:\/\//.test(input) ? input : `http://localhost${mergePath("/", input)}`,
        requestInit
      ),
      Env,
      executionCtx
    );
  }, "request");
  /**
   * `.fire()` automatically adds a global fetch event listener.
   * This can be useful for environments that adhere to the Service Worker API, such as non-ES module Cloudflare Workers.
   * @deprecated
   * Use `fire` from `hono/service-worker` instead.
   * ```ts
   * import { Hono } from 'hono'
   * import { fire } from 'hono/service-worker'
   *
   * const app = new Hono()
   * // ...
   * fire(app)
   * ```
   * @see https://hono.dev/docs/api/hono#fire
   * @see https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API
   * @see https://developers.cloudflare.com/workers/reference/migrate-to-module-workers/
   */
  fire = /* @__PURE__ */ __name(() => {
    addEventListener("fetch", (event) => {
      event.respondWith(this.#dispatch(event.request, event, void 0, event.request.method));
    });
  }, "fire");
};

// node_modules/hono/dist/router/reg-exp-router/matcher.js
var emptyParam = [];
function match(method, path) {
  const matchers = this.buildAllMatchers();
  const match2 = /* @__PURE__ */ __name(((method2, path2) => {
    const matcher = matchers[method2] || matchers[METHOD_NAME_ALL];
    const staticMatch = matcher[2][path2];
    if (staticMatch) {
      return staticMatch;
    }
    const match3 = path2.match(matcher[0]);
    if (!match3) {
      return [[], emptyParam];
    }
    const index = match3.indexOf("", 1);
    return [matcher[1][index], match3];
  }), "match2");
  this.match = match2;
  return match2(method, path);
}
__name(match, "match");

// node_modules/hono/dist/router/reg-exp-router/node.js
var LABEL_REG_EXP_STR = "[^/]+";
var ONLY_WILDCARD_REG_EXP_STR = ".*";
var TAIL_WILDCARD_REG_EXP_STR = "(?:|/.*)";
var PATH_ERROR = /* @__PURE__ */ Symbol();
var regExpMetaChars = new Set(".\\+*[^]$()");
function compareKey(a, b) {
  if (a.length === 1) {
    return b.length === 1 ? a < b ? -1 : 1 : -1;
  }
  if (b.length === 1) {
    return 1;
  }
  if (a === ONLY_WILDCARD_REG_EXP_STR || a === TAIL_WILDCARD_REG_EXP_STR) {
    return 1;
  } else if (b === ONLY_WILDCARD_REG_EXP_STR || b === TAIL_WILDCARD_REG_EXP_STR) {
    return -1;
  }
  if (a === LABEL_REG_EXP_STR) {
    return 1;
  } else if (b === LABEL_REG_EXP_STR) {
    return -1;
  }
  return a.length === b.length ? a < b ? -1 : 1 : b.length - a.length;
}
__name(compareKey, "compareKey");
var Node = class _Node {
  static {
    __name(this, "_Node");
  }
  #index;
  #varIndex;
  #children = /* @__PURE__ */ Object.create(null);
  insert(tokens, index, paramMap, context2, pathErrorCheckOnly) {
    if (tokens.length === 0) {
      if (this.#index !== void 0) {
        throw PATH_ERROR;
      }
      if (pathErrorCheckOnly) {
        return;
      }
      this.#index = index;
      return;
    }
    const [token, ...restTokens] = tokens;
    const pattern = token === "*" ? restTokens.length === 0 ? ["", "", ONLY_WILDCARD_REG_EXP_STR] : ["", "", LABEL_REG_EXP_STR] : token === "/*" ? ["", "", TAIL_WILDCARD_REG_EXP_STR] : token.match(/^\:([^\{\}]+)(?:\{(.+)\})?$/);
    let node;
    if (pattern) {
      const name = pattern[1];
      let regexpStr = pattern[2] || LABEL_REG_EXP_STR;
      if (name && pattern[2]) {
        if (regexpStr === ".*") {
          throw PATH_ERROR;
        }
        regexpStr = regexpStr.replace(/^\((?!\?:)(?=[^)]+\)$)/, "(?:");
        if (/\((?!\?:)/.test(regexpStr)) {
          throw PATH_ERROR;
        }
      }
      node = this.#children[regexpStr];
      if (!node) {
        if (Object.keys(this.#children).some(
          (k) => k !== ONLY_WILDCARD_REG_EXP_STR && k !== TAIL_WILDCARD_REG_EXP_STR
        )) {
          throw PATH_ERROR;
        }
        if (pathErrorCheckOnly) {
          return;
        }
        node = this.#children[regexpStr] = new _Node();
        if (name !== "") {
          node.#varIndex = context2.varIndex++;
        }
      }
      if (!pathErrorCheckOnly && name !== "") {
        paramMap.push([name, node.#varIndex]);
      }
    } else {
      node = this.#children[token];
      if (!node) {
        if (Object.keys(this.#children).some(
          (k) => k.length > 1 && k !== ONLY_WILDCARD_REG_EXP_STR && k !== TAIL_WILDCARD_REG_EXP_STR
        )) {
          throw PATH_ERROR;
        }
        if (pathErrorCheckOnly) {
          return;
        }
        node = this.#children[token] = new _Node();
      }
    }
    node.insert(restTokens, index, paramMap, context2, pathErrorCheckOnly);
  }
  buildRegExpStr() {
    const childKeys = Object.keys(this.#children).sort(compareKey);
    const strList = childKeys.map((k) => {
      const c = this.#children[k];
      return (typeof c.#varIndex === "number" ? `(${k})@${c.#varIndex}` : regExpMetaChars.has(k) ? `\\${k}` : k) + c.buildRegExpStr();
    });
    if (typeof this.#index === "number") {
      strList.unshift(`#${this.#index}`);
    }
    if (strList.length === 0) {
      return "";
    }
    if (strList.length === 1) {
      return strList[0];
    }
    return "(?:" + strList.join("|") + ")";
  }
};

// node_modules/hono/dist/router/reg-exp-router/trie.js
var Trie = class {
  static {
    __name(this, "Trie");
  }
  #context = { varIndex: 0 };
  #root = new Node();
  insert(path, index, pathErrorCheckOnly) {
    const paramAssoc = [];
    const groups = [];
    for (let i = 0; ; ) {
      let replaced = false;
      path = path.replace(/\{[^}]+\}/g, (m) => {
        const mark = `@\\${i}`;
        groups[i] = [mark, m];
        i++;
        replaced = true;
        return mark;
      });
      if (!replaced) {
        break;
      }
    }
    const tokens = path.match(/(?::[^\/]+)|(?:\/\*$)|./g) || [];
    for (let i = groups.length - 1; i >= 0; i--) {
      const [mark] = groups[i];
      for (let j = tokens.length - 1; j >= 0; j--) {
        if (tokens[j].indexOf(mark) !== -1) {
          tokens[j] = tokens[j].replace(mark, groups[i][1]);
          break;
        }
      }
    }
    this.#root.insert(tokens, index, paramAssoc, this.#context, pathErrorCheckOnly);
    return paramAssoc;
  }
  buildRegExp() {
    let regexp = this.#root.buildRegExpStr();
    if (regexp === "") {
      return [/^$/, [], []];
    }
    let captureIndex = 0;
    const indexReplacementMap = [];
    const paramReplacementMap = [];
    regexp = regexp.replace(/#(\d+)|@(\d+)|\.\*\$/g, (_, handlerIndex, paramIndex) => {
      if (handlerIndex !== void 0) {
        indexReplacementMap[++captureIndex] = Number(handlerIndex);
        return "$()";
      }
      if (paramIndex !== void 0) {
        paramReplacementMap[Number(paramIndex)] = ++captureIndex;
        return "";
      }
      return "";
    });
    return [new RegExp(`^${regexp}`), indexReplacementMap, paramReplacementMap];
  }
};

// node_modules/hono/dist/router/reg-exp-router/router.js
var nullMatcher = [/^$/, [], /* @__PURE__ */ Object.create(null)];
var wildcardRegExpCache = /* @__PURE__ */ Object.create(null);
function buildWildcardRegExp(path) {
  return wildcardRegExpCache[path] ??= new RegExp(
    path === "*" ? "" : `^${path.replace(
      /\/\*$|([.\\+*[^\]$()])/g,
      (_, metaChar) => metaChar ? `\\${metaChar}` : "(?:|/.*)"
    )}$`
  );
}
__name(buildWildcardRegExp, "buildWildcardRegExp");
function clearWildcardRegExpCache() {
  wildcardRegExpCache = /* @__PURE__ */ Object.create(null);
}
__name(clearWildcardRegExpCache, "clearWildcardRegExpCache");
function buildMatcherFromPreprocessedRoutes(routes) {
  const trie = new Trie();
  const handlerData = [];
  if (routes.length === 0) {
    return nullMatcher;
  }
  const routesWithStaticPathFlag = routes.map(
    (route) => [!/\*|\/:/.test(route[0]), ...route]
  ).sort(
    ([isStaticA, pathA], [isStaticB, pathB]) => isStaticA ? 1 : isStaticB ? -1 : pathA.length - pathB.length
  );
  const staticMap = /* @__PURE__ */ Object.create(null);
  for (let i = 0, j = -1, len = routesWithStaticPathFlag.length; i < len; i++) {
    const [pathErrorCheckOnly, path, handlers] = routesWithStaticPathFlag[i];
    if (pathErrorCheckOnly) {
      staticMap[path] = [handlers.map(([h]) => [h, /* @__PURE__ */ Object.create(null)]), emptyParam];
    } else {
      j++;
    }
    let paramAssoc;
    try {
      paramAssoc = trie.insert(path, j, pathErrorCheckOnly);
    } catch (e) {
      throw e === PATH_ERROR ? new UnsupportedPathError(path) : e;
    }
    if (pathErrorCheckOnly) {
      continue;
    }
    handlerData[j] = handlers.map(([h, paramCount]) => {
      const paramIndexMap = /* @__PURE__ */ Object.create(null);
      paramCount -= 1;
      for (; paramCount >= 0; paramCount--) {
        const [key, value] = paramAssoc[paramCount];
        paramIndexMap[key] = value;
      }
      return [h, paramIndexMap];
    });
  }
  const [regexp, indexReplacementMap, paramReplacementMap] = trie.buildRegExp();
  for (let i = 0, len = handlerData.length; i < len; i++) {
    for (let j = 0, len2 = handlerData[i].length; j < len2; j++) {
      const map = handlerData[i][j]?.[1];
      if (!map) {
        continue;
      }
      const keys = Object.keys(map);
      for (let k = 0, len3 = keys.length; k < len3; k++) {
        map[keys[k]] = paramReplacementMap[map[keys[k]]];
      }
    }
  }
  const handlerMap = [];
  for (const i in indexReplacementMap) {
    handlerMap[i] = handlerData[indexReplacementMap[i]];
  }
  return [regexp, handlerMap, staticMap];
}
__name(buildMatcherFromPreprocessedRoutes, "buildMatcherFromPreprocessedRoutes");
function findMiddleware(middleware, path) {
  if (!middleware) {
    return void 0;
  }
  for (const k of Object.keys(middleware).sort((a, b) => b.length - a.length)) {
    if (buildWildcardRegExp(k).test(path)) {
      return [...middleware[k]];
    }
  }
  return void 0;
}
__name(findMiddleware, "findMiddleware");
var RegExpRouter = class {
  static {
    __name(this, "RegExpRouter");
  }
  name = "RegExpRouter";
  #middleware;
  #routes;
  constructor() {
    this.#middleware = { [METHOD_NAME_ALL]: /* @__PURE__ */ Object.create(null) };
    this.#routes = { [METHOD_NAME_ALL]: /* @__PURE__ */ Object.create(null) };
  }
  add(method, path, handler) {
    const middleware = this.#middleware;
    const routes = this.#routes;
    if (!middleware || !routes) {
      throw new Error(MESSAGE_MATCHER_IS_ALREADY_BUILT);
    }
    if (!middleware[method]) {
      ;
      [middleware, routes].forEach((handlerMap) => {
        handlerMap[method] = /* @__PURE__ */ Object.create(null);
        Object.keys(handlerMap[METHOD_NAME_ALL]).forEach((p) => {
          handlerMap[method][p] = [...handlerMap[METHOD_NAME_ALL][p]];
        });
      });
    }
    if (path === "/*") {
      path = "*";
    }
    const paramCount = (path.match(/\/:/g) || []).length;
    if (/\*$/.test(path)) {
      const re = buildWildcardRegExp(path);
      if (method === METHOD_NAME_ALL) {
        Object.keys(middleware).forEach((m) => {
          middleware[m][path] ||= findMiddleware(middleware[m], path) || findMiddleware(middleware[METHOD_NAME_ALL], path) || [];
        });
      } else {
        middleware[method][path] ||= findMiddleware(middleware[method], path) || findMiddleware(middleware[METHOD_NAME_ALL], path) || [];
      }
      Object.keys(middleware).forEach((m) => {
        if (method === METHOD_NAME_ALL || method === m) {
          Object.keys(middleware[m]).forEach((p) => {
            re.test(p) && middleware[m][p].push([handler, paramCount]);
          });
        }
      });
      Object.keys(routes).forEach((m) => {
        if (method === METHOD_NAME_ALL || method === m) {
          Object.keys(routes[m]).forEach(
            (p) => re.test(p) && routes[m][p].push([handler, paramCount])
          );
        }
      });
      return;
    }
    const paths = checkOptionalParameter(path) || [path];
    for (let i = 0, len = paths.length; i < len; i++) {
      const path2 = paths[i];
      Object.keys(routes).forEach((m) => {
        if (method === METHOD_NAME_ALL || method === m) {
          routes[m][path2] ||= [
            ...findMiddleware(middleware[m], path2) || findMiddleware(middleware[METHOD_NAME_ALL], path2) || []
          ];
          routes[m][path2].push([handler, paramCount - len + i + 1]);
        }
      });
    }
  }
  match = match;
  buildAllMatchers() {
    const matchers = /* @__PURE__ */ Object.create(null);
    Object.keys(this.#routes).concat(Object.keys(this.#middleware)).forEach((method) => {
      matchers[method] ||= this.#buildMatcher(method);
    });
    this.#middleware = this.#routes = void 0;
    clearWildcardRegExpCache();
    return matchers;
  }
  #buildMatcher(method) {
    const routes = [];
    let hasOwnRoute = method === METHOD_NAME_ALL;
    [this.#middleware, this.#routes].forEach((r) => {
      const ownRoute = r[method] ? Object.keys(r[method]).map((path) => [path, r[method][path]]) : [];
      if (ownRoute.length !== 0) {
        hasOwnRoute ||= true;
        routes.push(...ownRoute);
      } else if (method !== METHOD_NAME_ALL) {
        routes.push(
          ...Object.keys(r[METHOD_NAME_ALL]).map((path) => [path, r[METHOD_NAME_ALL][path]])
        );
      }
    });
    if (!hasOwnRoute) {
      return null;
    } else {
      return buildMatcherFromPreprocessedRoutes(routes);
    }
  }
};

// node_modules/hono/dist/router/smart-router/router.js
var SmartRouter = class {
  static {
    __name(this, "SmartRouter");
  }
  name = "SmartRouter";
  #routers = [];
  #routes = [];
  constructor(init) {
    this.#routers = init.routers;
  }
  add(method, path, handler) {
    if (!this.#routes) {
      throw new Error(MESSAGE_MATCHER_IS_ALREADY_BUILT);
    }
    this.#routes.push([method, path, handler]);
  }
  match(method, path) {
    if (!this.#routes) {
      throw new Error("Fatal error");
    }
    const routers = this.#routers;
    const routes = this.#routes;
    const len = routers.length;
    let i = 0;
    let res;
    for (; i < len; i++) {
      const router = routers[i];
      try {
        for (let i2 = 0, len2 = routes.length; i2 < len2; i2++) {
          router.add(...routes[i2]);
        }
        res = router.match(method, path);
      } catch (e) {
        if (e instanceof UnsupportedPathError) {
          continue;
        }
        throw e;
      }
      this.match = router.match.bind(router);
      this.#routers = [router];
      this.#routes = void 0;
      break;
    }
    if (i === len) {
      throw new Error("Fatal error");
    }
    this.name = `SmartRouter + ${this.activeRouter.name}`;
    return res;
  }
  get activeRouter() {
    if (this.#routes || this.#routers.length !== 1) {
      throw new Error("No active router has been determined yet.");
    }
    return this.#routers[0];
  }
};

// node_modules/hono/dist/router/trie-router/node.js
var emptyParams = /* @__PURE__ */ Object.create(null);
var hasChildren = /* @__PURE__ */ __name((children) => {
  for (const _ in children) {
    return true;
  }
  return false;
}, "hasChildren");
var Node2 = class _Node2 {
  static {
    __name(this, "_Node");
  }
  #methods;
  #children;
  #patterns;
  #order = 0;
  #params = emptyParams;
  constructor(method, handler, children) {
    this.#children = children || /* @__PURE__ */ Object.create(null);
    this.#methods = [];
    if (method && handler) {
      const m = /* @__PURE__ */ Object.create(null);
      m[method] = { handler, possibleKeys: [], score: 0 };
      this.#methods = [m];
    }
    this.#patterns = [];
  }
  insert(method, path, handler) {
    this.#order = ++this.#order;
    let curNode = this;
    const parts = splitRoutingPath(path);
    const possibleKeys = [];
    for (let i = 0, len = parts.length; i < len; i++) {
      const p = parts[i];
      const nextP = parts[i + 1];
      const pattern = getPattern(p, nextP);
      const key = Array.isArray(pattern) ? pattern[0] : p;
      if (key in curNode.#children) {
        curNode = curNode.#children[key];
        if (pattern) {
          possibleKeys.push(pattern[1]);
        }
        continue;
      }
      curNode.#children[key] = new _Node2();
      if (pattern) {
        curNode.#patterns.push(pattern);
        possibleKeys.push(pattern[1]);
      }
      curNode = curNode.#children[key];
    }
    curNode.#methods.push({
      [method]: {
        handler,
        possibleKeys: possibleKeys.filter((v, i, a) => a.indexOf(v) === i),
        score: this.#order
      }
    });
    return curNode;
  }
  #pushHandlerSets(handlerSets, node, method, nodeParams, params) {
    for (let i = 0, len = node.#methods.length; i < len; i++) {
      const m = node.#methods[i];
      const handlerSet = m[method] || m[METHOD_NAME_ALL];
      const processedSet = {};
      if (handlerSet !== void 0) {
        handlerSet.params = /* @__PURE__ */ Object.create(null);
        handlerSets.push(handlerSet);
        if (nodeParams !== emptyParams || params && params !== emptyParams) {
          for (let i2 = 0, len2 = handlerSet.possibleKeys.length; i2 < len2; i2++) {
            const key = handlerSet.possibleKeys[i2];
            const processed = processedSet[handlerSet.score];
            handlerSet.params[key] = params?.[key] && !processed ? params[key] : nodeParams[key] ?? params?.[key];
            processedSet[handlerSet.score] = true;
          }
        }
      }
    }
  }
  search(method, path) {
    const handlerSets = [];
    this.#params = emptyParams;
    const curNode = this;
    let curNodes = [curNode];
    const parts = splitPath(path);
    const curNodesQueue = [];
    const len = parts.length;
    let partOffsets = null;
    for (let i = 0; i < len; i++) {
      const part = parts[i];
      const isLast = i === len - 1;
      const tempNodes = [];
      for (let j = 0, len2 = curNodes.length; j < len2; j++) {
        const node = curNodes[j];
        const nextNode = node.#children[part];
        if (nextNode) {
          nextNode.#params = node.#params;
          if (isLast) {
            if (nextNode.#children["*"]) {
              this.#pushHandlerSets(handlerSets, nextNode.#children["*"], method, node.#params);
            }
            this.#pushHandlerSets(handlerSets, nextNode, method, node.#params);
          } else {
            tempNodes.push(nextNode);
          }
        }
        for (let k = 0, len3 = node.#patterns.length; k < len3; k++) {
          const pattern = node.#patterns[k];
          const params = node.#params === emptyParams ? {} : { ...node.#params };
          if (pattern === "*") {
            const astNode = node.#children["*"];
            if (astNode) {
              this.#pushHandlerSets(handlerSets, astNode, method, node.#params);
              astNode.#params = params;
              tempNodes.push(astNode);
            }
            continue;
          }
          const [key, name, matcher] = pattern;
          if (!part && !(matcher instanceof RegExp)) {
            continue;
          }
          const child = node.#children[key];
          if (matcher instanceof RegExp) {
            if (partOffsets === null) {
              partOffsets = new Array(len);
              let offset = path[0] === "/" ? 1 : 0;
              for (let p = 0; p < len; p++) {
                partOffsets[p] = offset;
                offset += parts[p].length + 1;
              }
            }
            const restPathString = path.substring(partOffsets[i]);
            const m = matcher.exec(restPathString);
            if (m) {
              params[name] = m[0];
              this.#pushHandlerSets(handlerSets, child, method, node.#params, params);
              if (hasChildren(child.#children)) {
                child.#params = params;
                const componentCount = m[0].match(/\//)?.length ?? 0;
                const targetCurNodes = curNodesQueue[componentCount] ||= [];
                targetCurNodes.push(child);
              }
              continue;
            }
          }
          if (matcher === true || matcher.test(part)) {
            params[name] = part;
            if (isLast) {
              this.#pushHandlerSets(handlerSets, child, method, params, node.#params);
              if (child.#children["*"]) {
                this.#pushHandlerSets(
                  handlerSets,
                  child.#children["*"],
                  method,
                  params,
                  node.#params
                );
              }
            } else {
              child.#params = params;
              tempNodes.push(child);
            }
          }
        }
      }
      const shifted = curNodesQueue.shift();
      curNodes = shifted ? tempNodes.concat(shifted) : tempNodes;
    }
    if (handlerSets.length > 1) {
      handlerSets.sort((a, b) => {
        return a.score - b.score;
      });
    }
    return [handlerSets.map(({ handler, params }) => [handler, params])];
  }
};

// node_modules/hono/dist/router/trie-router/router.js
var TrieRouter = class {
  static {
    __name(this, "TrieRouter");
  }
  name = "TrieRouter";
  #node;
  constructor() {
    this.#node = new Node2();
  }
  add(method, path, handler) {
    const results = checkOptionalParameter(path);
    if (results) {
      for (let i = 0, len = results.length; i < len; i++) {
        this.#node.insert(method, results[i], handler);
      }
      return;
    }
    this.#node.insert(method, path, handler);
  }
  match(method, path) {
    return this.#node.search(method, path);
  }
};

// node_modules/hono/dist/hono.js
var Hono2 = class extends Hono {
  static {
    __name(this, "Hono");
  }
  /**
   * Creates an instance of the Hono class.
   *
   * @param options - Optional configuration options for the Hono instance.
   */
  constructor(options = {}) {
    super(options);
    this.router = options.router ?? new SmartRouter({
      routers: [new RegExpRouter(), new TrieRouter()]
    });
  }
};

// node_modules/hono/dist/middleware/cors/index.js
var cors = /* @__PURE__ */ __name((options) => {
  const defaults = {
    origin: "*",
    allowMethods: ["GET", "HEAD", "PUT", "POST", "DELETE", "PATCH"],
    allowHeaders: [],
    exposeHeaders: []
  };
  const opts = {
    ...defaults,
    ...options
  };
  const findAllowOrigin = ((optsOrigin) => {
    if (typeof optsOrigin === "string") {
      if (optsOrigin === "*") {
        return () => optsOrigin;
      } else {
        return (origin) => optsOrigin === origin ? origin : null;
      }
    } else if (typeof optsOrigin === "function") {
      return optsOrigin;
    } else {
      return (origin) => optsOrigin.includes(origin) ? origin : null;
    }
  })(opts.origin);
  const findAllowMethods = ((optsAllowMethods) => {
    if (typeof optsAllowMethods === "function") {
      return optsAllowMethods;
    } else if (Array.isArray(optsAllowMethods)) {
      return () => optsAllowMethods;
    } else {
      return () => [];
    }
  })(opts.allowMethods);
  return /* @__PURE__ */ __name(async function cors2(c, next) {
    function set(key, value) {
      c.res.headers.set(key, value);
    }
    __name(set, "set");
    const allowOrigin = await findAllowOrigin(c.req.header("origin") || "", c);
    if (allowOrigin) {
      set("Access-Control-Allow-Origin", allowOrigin);
    }
    if (opts.credentials) {
      set("Access-Control-Allow-Credentials", "true");
    }
    if (opts.exposeHeaders?.length) {
      set("Access-Control-Expose-Headers", opts.exposeHeaders.join(","));
    }
    if (c.req.method === "OPTIONS") {
      if (opts.origin !== "*") {
        set("Vary", "Origin");
      }
      if (opts.maxAge != null) {
        set("Access-Control-Max-Age", opts.maxAge.toString());
      }
      const allowMethods = await findAllowMethods(c.req.header("origin") || "", c);
      if (allowMethods.length) {
        set("Access-Control-Allow-Methods", allowMethods.join(","));
      }
      let headers = opts.allowHeaders;
      if (!headers?.length) {
        const requestHeaders = c.req.header("Access-Control-Request-Headers");
        if (requestHeaders) {
          headers = requestHeaders.split(/\s*,\s*/);
        }
      }
      if (headers?.length) {
        set("Access-Control-Allow-Headers", headers.join(","));
        c.res.headers.append("Vary", "Access-Control-Request-Headers");
      }
      c.res.headers.delete("Content-Length");
      c.res.headers.delete("Content-Type");
      return new Response(null, {
        headers: c.res.headers,
        status: 204,
        statusText: "No Content"
      });
    }
    await next();
    if (opts.origin !== "*") {
      c.header("Vary", "Origin", { append: true });
    }
  }, "cors2");
}, "cors");

// node_modules/hono/dist/middleware/body-limit/index.js
var ERROR_MESSAGE = "Payload Too Large";
var BodyLimitError = class extends Error {
  static {
    __name(this, "BodyLimitError");
  }
  constructor(message2) {
    super(message2);
    this.name = "BodyLimitError";
  }
};
var bodyLimit = /* @__PURE__ */ __name((options) => {
  const onError = options.onError || (() => {
    const res = new Response(ERROR_MESSAGE, {
      status: 413
    });
    throw new HTTPException(413, { res });
  });
  const maxSize = options.maxSize;
  return /* @__PURE__ */ __name(async function bodyLimit2(c, next) {
    if (!c.req.raw.body) {
      return next();
    }
    const hasTransferEncoding = c.req.raw.headers.has("transfer-encoding");
    const hasContentLength = c.req.raw.headers.has("content-length");
    if (hasTransferEncoding && hasContentLength) {
    }
    if (hasContentLength && !hasTransferEncoding) {
      const contentLength = parseInt(c.req.raw.headers.get("content-length") || "0", 10);
      return contentLength > maxSize ? onError(c) : next();
    }
    let size = 0;
    const rawReader = c.req.raw.body.getReader();
    const reader = new ReadableStream({
      async start(controller) {
        try {
          for (; ; ) {
            const { done, value } = await rawReader.read();
            if (done) {
              break;
            }
            size += value.length;
            if (size > maxSize) {
              controller.error(new BodyLimitError(ERROR_MESSAGE));
              break;
            }
            controller.enqueue(value);
          }
        } finally {
          controller.close();
        }
      }
    });
    const requestInit = { body: reader, duplex: "half" };
    c.req.raw = new Request(c.req.raw, requestInit);
    await next();
    if (c.error instanceof BodyLimitError) {
      c.res = await onError(c);
    }
  }, "bodyLimit2");
}, "bodyLimit");

// node_modules/@cloudflare/sandbox/dist/index.js
import { AsyncLocalStorage } from "node:async_hooks";

// node_modules/@cloudflare/containers/dist/lib/helpers.js
function generateId(length = 9) {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  const bytes = new Uint8Array(length);
  crypto.getRandomValues(bytes);
  let result = "";
  for (let i = 0; i < length; i++) {
    result += alphabet[bytes[i] % alphabet.length];
  }
  return result;
}
__name(generateId, "generateId");
function parseTimeExpression(timeExpression) {
  if (typeof timeExpression === "number") {
    return timeExpression;
  }
  if (typeof timeExpression === "string") {
    const match2 = timeExpression.match(/^(\d+)([smh])$/);
    if (!match2) {
      throw new Error(`invalid time expression ${timeExpression}`);
    }
    const value = parseInt(match2[1]);
    const unit = match2[2];
    switch (unit) {
      case "s":
        return value;
      case "m":
        return value * 60;
      case "h":
        return value * 60 * 60;
      default:
        throw new Error(`unknown time unit ${unit}`);
    }
  }
  throw new Error(`invalid type for a time expression: ${typeof timeExpression}`);
}
__name(parseTimeExpression, "parseTimeExpression");

// node_modules/@cloudflare/containers/dist/lib/container.js
import { DurableObject } from "cloudflare:workers";
var NO_CONTAINER_INSTANCE_ERROR = "there is no container instance that can be provided to this durable object";
var RUNTIME_SIGNALLED_ERROR = "runtime signalled the container to exit:";
var UNEXPECTED_EXIT_ERROR = "container exited with unexpected exit code:";
var NOT_LISTENING_ERROR = "the container is not listening";
var CONTAINER_STATE_KEY = "__CF_CONTAINER_STATE";
var MAX_ALARM_RETRIES = 3;
var PING_TIMEOUT_MS = 5e3;
var DEFAULT_SLEEP_AFTER = "10m";
var INSTANCE_POLL_INTERVAL_MS = 300;
var TIMEOUT_TO_GET_CONTAINER_MS = 8e3;
var TIMEOUT_TO_GET_PORTS_MS = 2e4;
var FALLBACK_PORT_TO_CHECK = 33;
var signalToNumbers = {
  SIGINT: 2,
  SIGTERM: 15,
  SIGKILL: 9
};
function isErrorOfType(e, matchingString) {
  const errorString = e instanceof Error ? e.message : String(e);
  return errorString.toLowerCase().includes(matchingString);
}
__name(isErrorOfType, "isErrorOfType");
var isNoInstanceError = /* @__PURE__ */ __name((error3) => isErrorOfType(error3, NO_CONTAINER_INSTANCE_ERROR), "isNoInstanceError");
var isRuntimeSignalledError = /* @__PURE__ */ __name((error3) => isErrorOfType(error3, RUNTIME_SIGNALLED_ERROR), "isRuntimeSignalledError");
var isNotListeningError = /* @__PURE__ */ __name((error3) => isErrorOfType(error3, NOT_LISTENING_ERROR), "isNotListeningError");
var isContainerExitNonZeroError = /* @__PURE__ */ __name((error3) => isErrorOfType(error3, UNEXPECTED_EXIT_ERROR), "isContainerExitNonZeroError");
function getExitCodeFromError(error3) {
  if (!(error3 instanceof Error)) {
    return null;
  }
  if (isRuntimeSignalledError(error3)) {
    return +error3.message.toLowerCase().slice(error3.message.toLowerCase().indexOf(RUNTIME_SIGNALLED_ERROR) + RUNTIME_SIGNALLED_ERROR.length + 1);
  }
  if (isContainerExitNonZeroError(error3)) {
    return +error3.message.toLowerCase().slice(error3.message.toLowerCase().indexOf(UNEXPECTED_EXIT_ERROR) + UNEXPECTED_EXIT_ERROR.length + 1);
  }
  return null;
}
__name(getExitCodeFromError, "getExitCodeFromError");
function addTimeoutSignal(existingSignal, timeoutMs) {
  const controller = new AbortController();
  if (existingSignal?.aborted) {
    controller.abort();
    return controller.signal;
  }
  existingSignal?.addEventListener("abort", () => controller.abort());
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  controller.signal.addEventListener("abort", () => clearTimeout(timeoutId));
  return controller.signal;
}
__name(addTimeoutSignal, "addTimeoutSignal");
var ContainerState = class {
  static {
    __name(this, "ContainerState");
  }
  storage;
  status;
  constructor(storage) {
    this.storage = storage;
  }
  async setRunning() {
    await this.setStatusAndupdate("running");
  }
  async setHealthy() {
    await this.setStatusAndupdate("healthy");
  }
  async setStopping() {
    await this.setStatusAndupdate("stopping");
  }
  async setStopped() {
    await this.setStatusAndupdate("stopped");
  }
  async setStoppedWithCode(exitCode2) {
    this.status = { status: "stopped_with_code", lastChange: Date.now(), exitCode: exitCode2 };
    await this.update();
  }
  async getState() {
    if (!this.status) {
      const state = await this.storage.get(CONTAINER_STATE_KEY);
      if (!state) {
        this.status = {
          status: "stopped",
          lastChange: Date.now()
        };
        await this.update();
      } else {
        this.status = state;
      }
    }
    return this.status;
  }
  async setStatusAndupdate(status) {
    this.status = { status, lastChange: Date.now() };
    await this.update();
  }
  async update() {
    if (!this.status)
      throw new Error("status should be init");
    await this.storage.put(CONTAINER_STATE_KEY, this.status);
  }
};
var Container = class extends DurableObject {
  static {
    __name(this, "Container");
  }
  // =========================
  //     Public Attributes
  // =========================
  // Default port for the container (undefined means no default port)
  defaultPort;
  // Required ports that should be checked for availability during container startup
  // Override this in your subclass to specify ports that must be ready
  requiredPorts;
  // Timeout after which the container will sleep if no activity
  // The signal sent to the container by default is a SIGTERM.
  // The container won't get a SIGKILL if this threshold is triggered.
  sleepAfter = DEFAULT_SLEEP_AFTER;
  // Container configuration properties
  // Set these properties directly in your container instance
  envVars = {};
  entrypoint;
  enableInternet = true;
  // =========================
  //     PUBLIC INTERFACE
  // =========================
  constructor(ctx, env2, options) {
    super(ctx, env2);
    if (ctx.container === void 0) {
      throw new Error("Containers have not been enabled for this Durable Object class. Have you correctly setup your Wrangler config? More info: https://developers.cloudflare.com/containers/get-started/#configuration");
    }
    this.state = new ContainerState(this.ctx.storage);
    this.ctx.blockConcurrencyWhile(async () => {
      this.renewActivityTimeout();
      await this.scheduleNextAlarm();
    });
    this.container = ctx.container;
    if (options) {
      if (options.defaultPort !== void 0)
        this.defaultPort = options.defaultPort;
      if (options.sleepAfter !== void 0)
        this.sleepAfter = options.sleepAfter;
    }
    this.sql`
      CREATE TABLE IF NOT EXISTS container_schedules (
        id TEXT PRIMARY KEY NOT NULL DEFAULT (randomblob(9)),
        callback TEXT NOT NULL,
        payload TEXT,
        type TEXT NOT NULL CHECK(type IN ('scheduled', 'delayed')),
        time INTEGER NOT NULL,
        delayInSeconds INTEGER,
        created_at INTEGER DEFAULT (unixepoch())
      )
    `;
    if (this.container.running) {
      this.monitor = this.container.monitor();
      this.setupMonitorCallbacks();
    }
  }
  /**
   * Gets the current state of the container
   * @returns Promise<State>
   */
  async getState() {
    return { ...await this.state.getState() };
  }
  // ==========================
  //     CONTAINER STARTING
  // ==========================
  /**
   * Start the container if it's not running and set up monitoring and lifecycle hooks,
   * without waiting for ports to be ready.
   *
   * It will automatically retry if the container fails to start, using the specified waitOptions
   *
   *
   * @example
   * await this.start({
   *   envVars: { DEBUG: 'true', NODE_ENV: 'development' },
   *   entrypoint: ['npm', 'run', 'dev'],
   *   enableInternet: false
   * });
   *
   * @param startOptions - Override `envVars`, `entrypoint` and `enableInternet` on a per-instance basis
   * @param waitOptions - Optional wait configuration with abort signal for cancellation. Default ~8s timeout.
   * @returns A promise that resolves when the container start command has been issued
   * @throws Error if no container context is available or if all start attempts fail
   */
  async start(startOptions, waitOptions) {
    const portToCheck = waitOptions?.portToCheck ?? this.defaultPort ?? (this.requiredPorts ? this.requiredPorts[0] : FALLBACK_PORT_TO_CHECK);
    const pollInterval = waitOptions?.waitInterval ?? INSTANCE_POLL_INTERVAL_MS;
    await this.startContainerIfNotRunning({
      signal: waitOptions?.signal,
      waitInterval: pollInterval,
      retries: waitOptions?.retries ?? Math.ceil(TIMEOUT_TO_GET_CONTAINER_MS / pollInterval),
      portToCheck
    }, startOptions);
    this.setupMonitorCallbacks();
    await this.ctx.blockConcurrencyWhile(async () => {
      await this.onStart();
    });
  }
  async startAndWaitForPorts(portsOrArgs, cancellationOptions, startOptions) {
    let ports;
    let resolvedCancellationOptions = {};
    let resolvedStartOptions = {};
    if (typeof portsOrArgs === "object" && portsOrArgs !== null && !Array.isArray(portsOrArgs)) {
      ports = portsOrArgs.ports;
      resolvedCancellationOptions = portsOrArgs.cancellationOptions;
      resolvedStartOptions = portsOrArgs.startOptions;
    } else {
      ports = portsOrArgs;
      resolvedCancellationOptions = cancellationOptions;
      resolvedStartOptions = startOptions;
    }
    const portsToCheck = await this.getPortsToCheck(ports);
    await this.syncPendingStoppedEvents();
    resolvedCancellationOptions ??= {};
    const containerGetTimeout = resolvedCancellationOptions.instanceGetTimeoutMS ?? TIMEOUT_TO_GET_CONTAINER_MS;
    const pollInterval = resolvedCancellationOptions.waitInterval ?? INSTANCE_POLL_INTERVAL_MS;
    let containerGetRetries = Math.ceil(containerGetTimeout / pollInterval);
    const waitOptions = {
      signal: resolvedCancellationOptions.abort,
      retries: containerGetRetries,
      waitInterval: pollInterval,
      portToCheck: portsToCheck[0]
    };
    const triesUsed = await this.startContainerIfNotRunning(waitOptions, resolvedStartOptions);
    const totalPortReadyTries = Math.ceil(resolvedCancellationOptions.portReadyTimeoutMS ?? TIMEOUT_TO_GET_PORTS_MS / pollInterval);
    let triesLeft = totalPortReadyTries - triesUsed;
    for (const port of portsToCheck) {
      triesLeft = await this.waitForPort({
        signal: resolvedCancellationOptions.abort,
        waitInterval: pollInterval,
        retries: triesLeft,
        portToCheck: port
      });
    }
    this.setupMonitorCallbacks();
    await this.ctx.blockConcurrencyWhile(async () => {
      await this.state.setHealthy();
      await this.onStart();
    });
  }
  /**
   *
   * Waits for a specified port to be ready
   *
   * Returns the number of tries used to get the port, or throws if it couldn't get the port within the specified retry limits.
   *
   * @param waitOptions -
   * - `portToCheck`: The port number to check
   * - `abort`: Optional AbortSignal to cancel waiting
   * - `retries`: Number of retries before giving up (default: TRIES_TO_GET_PORTS)
   * - `waitInterval`: Interval between retries in milliseconds (default: INSTANCE_POLL_INTERVAL_MS)
   */
  async waitForPort(waitOptions) {
    const port = waitOptions.portToCheck;
    const tcpPort = this.container.getTcpPort(port);
    const abortedSignal = new Promise((res) => {
      waitOptions.signal?.addEventListener("abort", () => {
        res(true);
      });
    });
    const pollInterval = waitOptions.waitInterval ?? INSTANCE_POLL_INTERVAL_MS;
    let tries = waitOptions.retries ?? Math.ceil(TIMEOUT_TO_GET_PORTS_MS / pollInterval);
    for (let i = 0; i < tries; i++) {
      try {
        const combinedSignal = addTimeoutSignal(waitOptions.signal, PING_TIMEOUT_MS);
        await tcpPort.fetch("http://ping", { signal: combinedSignal });
        console.log(`Port ${port} is ready`);
        break;
      } catch (e) {
        const errorMessage = e instanceof Error ? e.message : String(e);
        console.debug(`Error checking ${port}: ${errorMessage}`);
        if (!this.container.running) {
          try {
            await this.onError(new Error(`Container crashed while checking for ports, did you start the container and setup the entrypoint correctly?`));
          } catch {
          }
          throw e;
        }
        if (i === tries - 1) {
          try {
            await this.onError(`Failed to verify port ${port} is available after ${(i + 1) * pollInterval}ms, last error: ${errorMessage}`);
          } catch {
          }
          throw e;
        }
        await Promise.any([
          new Promise((resolve) => setTimeout(resolve, waitOptions.waitInterval)),
          abortedSignal
        ]);
        if (waitOptions.signal?.aborted) {
          throw new Error("Container request aborted.");
        }
      }
    }
    return tries;
  }
  // =======================
  //     LIFECYCLE HOOKS
  // =======================
  /**
   * Send a signal to the container.
   * @param signal - The signal to send to the container (default: 15 for SIGTERM)
   */
  async stop(signal = "SIGTERM") {
    if (!this.container.running) {
      return;
    }
    this.container.signal(typeof signal === "string" ? signalToNumbers[signal] : signal);
  }
  /**
   * Destroys the container with a SIGKILL. Triggers onStop.
   */
  async destroy() {
    await this.container.destroy();
  }
  /**
   * Lifecycle method called when container starts successfully
   * Override this method in subclasses to handle container start events
   */
  onStart() {
  }
  /**
   * Lifecycle method called when container shuts down
   * Override this method in subclasses to handle Container stopped events
   * @param params - Object containing exitCode and reason for the stop
   */
  onStop(_) {
  }
  /**
   * Lifecycle method called when the container is running, and the activity timeout
   * expiration (set by `sleepAfter`) has been reached.
   *
   * If you want to shutdown the container, you should call this.stop() here
   *
   * By default, this method calls `this.stop()`
   */
  async onActivityExpired() {
    if (!this.container.running) {
      return;
    }
    await this.stop();
  }
  /**
   * Error handler for container errors
   * Override this method in subclasses to handle container errors
   * @param error - The error that occurred
   * @returns Can return any value or throw the error
   */
  onError(error3) {
    console.error("Container error:", error3);
    throw error3;
  }
  /**
   * Renew the container's activity timeout
   *
   * Call this method whenever there is activity on the container
   */
  renewActivityTimeout() {
    const timeoutInMs = parseTimeExpression(this.sleepAfter) * 1e3;
    this.sleepAfterMs = Date.now() + timeoutInMs;
  }
  // ==================
  //     SCHEDULING
  // ==================
  /**
   * Schedule a task to be executed in the future.
   *
   * We strongly recommend using this instead of the `alarm` handler.
   *
   * @template T Type of the payload data
   * @param when When to execute the task (Date object or number of seconds delay)
   * @param callback Name of the method to call
   * @param payload Data to pass to the callback
   * @returns Schedule object representing the scheduled task
   */
  async schedule(when, callback, payload) {
    const id = generateId(9);
    if (typeof callback !== "string") {
      throw new Error("Callback must be a string (method name)");
    }
    if (typeof this[callback] !== "function") {
      throw new Error(`this.${callback} is not a function`);
    }
    if (when instanceof Date) {
      const timestamp = Math.floor(when.getTime() / 1e3);
      this.sql`
        INSERT OR REPLACE INTO container_schedules (id, callback, payload, type, time)
        VALUES (${id}, ${callback}, ${JSON.stringify(payload)}, 'scheduled', ${timestamp})
      `;
      await this.scheduleNextAlarm();
      return {
        taskId: id,
        callback,
        payload,
        time: timestamp,
        type: "scheduled"
      };
    }
    if (typeof when === "number") {
      const time3 = Math.floor(Date.now() / 1e3 + when);
      this.sql`
        INSERT OR REPLACE INTO container_schedules (id, callback, payload, type, delayInSeconds, time)
        VALUES (${id}, ${callback}, ${JSON.stringify(payload)}, 'delayed', ${when}, ${time3})
      `;
      await this.scheduleNextAlarm();
      return {
        taskId: id,
        callback,
        payload,
        delayInSeconds: when,
        time: time3,
        type: "delayed"
      };
    }
    throw new Error("Invalid schedule type. 'when' must be a Date or number of seconds");
  }
  // ============
  //     HTTP
  // ============
  /**
   * Send a request to the container (HTTP or WebSocket) using standard fetch API signature
   *
   * This method handles HTTP requests to the container.
   *
   * WebSocket requests done outside the DO won't work until https://github.com/cloudflare/workerd/issues/2319 is addressed.
   * Until then, please use `switchPort` + `fetch()`.
   *
   * Method supports multiple signatures to match standard fetch API:
   * - containerFetch(request: Request, port?: number)
   * - containerFetch(url: string | URL, init?: RequestInit, port?: number)
   *
   * Starts the container if not already running, and waits for the target port to be ready.
   *
   * @returns A Response from the container
   */
  async containerFetch(requestOrUrl, portOrInit, portParam) {
    let { request, port } = this.requestAndPortFromContainerFetchArgs(requestOrUrl, portOrInit, portParam);
    const state = await this.state.getState();
    if (!this.container.running || state.status !== "healthy") {
      try {
        await this.startAndWaitForPorts(port, { abort: request.signal });
      } catch (e) {
        if (isNoInstanceError(e)) {
          return new Response("There is no Container instance available at this time.\nThis is likely because you have reached your max concurrent instance count (set in wrangler config) or are you currently provisioning the Container.\nIf you are deploying your Container for the first time, check your dashboard to see provisioning status, this may take a few minutes.", { status: 503 });
        } else {
          return new Response(`Failed to start container: ${e instanceof Error ? e.message : String(e)}`, { status: 500 });
        }
      }
    }
    const tcpPort = this.container.getTcpPort(port);
    const containerUrl = request.url.replace("https:", "http:");
    try {
      this.renewActivityTimeout();
      const res = await tcpPort.fetch(containerUrl, request);
      return res;
    } catch (e) {
      if (!(e instanceof Error)) {
        throw e;
      }
      if (e.message.includes("Network connection lost.")) {
        return new Response("Container suddenly disconnected, try again", { status: 500 });
      }
      console.error(`Error proxying request to container ${this.ctx.id}:`, e);
      return new Response(`Error proxying request to container: ${e instanceof Error ? e.message : String(e)}`, { status: 500 });
    }
  }
  /**
   *
   * Fetch handler on the Container class.
   * By default this forwards all requests to the container by calling `containerFetch`.
   * Use `switchPort` to specify which port on the container to target, or this will use `defaultPort`.
   * @param request The request to handle
   */
  async fetch(request) {
    if (this.defaultPort === void 0 && !request.headers.has("cf-container-target-port")) {
      throw new Error("No port configured for this container. Set the `defaultPort` in your Container subclass, or specify a port with `container.fetch(switchPort(request, port))`.");
    }
    let portValue = this.defaultPort;
    if (request.headers.has("cf-container-target-port")) {
      const portFromHeaders = parseInt(request.headers.get("cf-container-target-port") ?? "");
      if (isNaN(portFromHeaders)) {
        throw new Error("port value from switchPort is not a number");
      } else {
        portValue = portFromHeaders;
      }
    }
    return await this.containerFetch(request, portValue);
  }
  // ===============================
  // ===============================
  //     PRIVATE METHODS & ATTRS
  // ===============================
  // ===============================
  // ==========================
  //     PRIVATE ATTRIBUTES
  // ==========================
  container;
  // onStopCalled will be true when we are in the middle of an onStop call
  onStopCalled = false;
  state;
  monitor;
  monitorSetup = false;
  sleepAfterMs = 0;
  // ==========================
  //     GENERAL HELPERS
  // ==========================
  /**
   * Execute SQL queries against the Container's database
   */
  sql(strings, ...values) {
    let query = "";
    query = strings.reduce((acc, str, i) => acc + str + (i < values.length ? "?" : ""), "");
    return [...this.ctx.storage.sql.exec(query, ...values)];
  }
  requestAndPortFromContainerFetchArgs(requestOrUrl, portOrInit, portParam) {
    let request;
    let port;
    if (requestOrUrl instanceof Request) {
      request = requestOrUrl;
      port = typeof portOrInit === "number" ? portOrInit : void 0;
    } else {
      const url = typeof requestOrUrl === "string" ? requestOrUrl : requestOrUrl.toString();
      const init = typeof portOrInit === "number" ? {} : portOrInit || {};
      port = typeof portOrInit === "number" ? portOrInit : typeof portParam === "number" ? portParam : void 0;
      request = new Request(url, init);
    }
    port ??= this.defaultPort;
    if (port === void 0) {
      throw new Error("No port specified for container fetch. Set defaultPort or specify a port parameter.");
    }
    return { request, port };
  }
  /**
   *
   * The method prioritizes port sources in this order:
   * 1. Ports specified directly in the method call
   * 2. `requiredPorts` class property (if set)
   * 3. `defaultPort` (if neither of the above is specified)
   * 4. Falls back to port 33 if none of the above are set
   */
  async getPortsToCheck(overridePorts) {
    let portsToCheck = [];
    if (overridePorts !== void 0) {
      portsToCheck = Array.isArray(overridePorts) ? overridePorts : [overridePorts];
    } else if (this.requiredPorts && this.requiredPorts.length > 0) {
      portsToCheck = [...this.requiredPorts];
    } else {
      portsToCheck = [this.defaultPort ?? FALLBACK_PORT_TO_CHECK];
    }
    return portsToCheck;
  }
  // ===========================================
  //     CONTAINER INTERACTION & MONITORING
  // ===========================================
  /**
   * Tries to start a container if it's not already running
   * Returns the number of tries used
   */
  async startContainerIfNotRunning(waitOptions, options) {
    if (this.container.running) {
      if (!this.monitor) {
        this.monitor = this.container.monitor();
      }
      return 0;
    }
    const abortedSignal = new Promise((res) => {
      waitOptions.signal?.addEventListener("abort", () => {
        res(true);
      });
    });
    const pollInterval = waitOptions.waitInterval ?? INSTANCE_POLL_INTERVAL_MS;
    const totalTries = waitOptions.retries ?? Math.ceil(TIMEOUT_TO_GET_CONTAINER_MS / pollInterval);
    await this.state.setRunning();
    for (let tries = 0; tries < totalTries; tries++) {
      const envVars = options?.envVars ?? this.envVars;
      const entrypoint = options?.entrypoint ?? this.entrypoint;
      const enableInternet = options?.enableInternet ?? this.enableInternet;
      const startConfig = {
        enableInternet
      };
      if (envVars && Object.keys(envVars).length > 0)
        startConfig.env = envVars;
      if (entrypoint)
        startConfig.entrypoint = entrypoint;
      this.renewActivityTimeout();
      const handleError = /* @__PURE__ */ __name(async () => {
        const err = await this.monitor?.catch((err2) => err2);
        if (typeof err === "number") {
          const toThrow = new Error(`Container exited before we could determine the container health, exit code: ${err}`);
          try {
            await this.onError(toThrow);
          } catch {
          }
          throw toThrow;
        } else if (!isNoInstanceError(err)) {
          try {
            await this.onError(err);
          } catch {
          }
          throw err;
        }
      }, "handleError");
      if (tries > 0 && !this.container.running) {
        await handleError();
      }
      await this.scheduleNextAlarm();
      if (!this.container.running) {
        this.container.start(startConfig);
        this.monitor = this.container.monitor();
      } else {
        await this.scheduleNextAlarm();
      }
      this.renewActivityTimeout();
      const port = this.container.getTcpPort(waitOptions.portToCheck);
      try {
        const combinedSignal = addTimeoutSignal(waitOptions.signal, PING_TIMEOUT_MS);
        await port.fetch("http://containerstarthealthcheck", { signal: combinedSignal });
        return tries;
      } catch (error3) {
        if (isNotListeningError(error3) && this.container.running) {
          return tries;
        }
        if (!this.container.running && isNotListeningError(error3)) {
          await handleError();
        }
        console.debug("Error checking if container is ready:", error3 instanceof Error ? error3.message : String(error3));
        await Promise.any([
          new Promise((res) => setTimeout(res, waitOptions.waitInterval)),
          abortedSignal
        ]);
        if (waitOptions.signal?.aborted) {
          throw new Error("Aborted waiting for container to start as we received a cancellation signal");
        }
        if (totalTries === tries + 1) {
          if (error3 instanceof Error && error3.message.includes("Network connection lost")) {
            this.ctx.abort();
          }
          throw new Error(NO_CONTAINER_INSTANCE_ERROR);
        }
        continue;
      }
    }
    throw new Error(`Container did not start after ${totalTries * pollInterval}ms`);
  }
  setupMonitorCallbacks() {
    if (this.monitorSetup) {
      return;
    }
    this.monitorSetup = true;
    this.monitor?.then(async () => {
      await this.ctx.blockConcurrencyWhile(async () => {
        await this.state.setStoppedWithCode(0);
      });
    }).catch(async (error3) => {
      if (isNoInstanceError(error3)) {
        return;
      }
      const exitCode2 = getExitCodeFromError(error3);
      if (exitCode2 !== null) {
        await this.state.setStoppedWithCode(exitCode2);
        this.monitorSetup = false;
        this.monitor = void 0;
        return;
      }
      try {
        await this.onError(error3);
      } catch {
      }
    }).finally(() => {
      this.monitorSetup = false;
      if (this.timeout) {
        if (this.resolve)
          this.resolve();
        clearTimeout(this.timeout);
      }
    });
  }
  deleteSchedules(name) {
    this.sql`DELETE FROM container_schedules WHERE callback = ${name}`;
  }
  // ============================
  //     ALARMS AND SCHEDULES
  // ============================
  /**
   * Method called when an alarm fires
   * Executes any scheduled tasks that are due
   */
  async alarm(alarmProps) {
    if (alarmProps.isRetry && alarmProps.retryCount > MAX_ALARM_RETRIES) {
      const scheduleCount = Number(this.sql`SELECT COUNT(*) as count FROM container_schedules`[0]?.count) || 0;
      const hasScheduledTasks = scheduleCount > 0;
      if (hasScheduledTasks || this.container.running) {
        await this.scheduleNextAlarm();
      }
      return;
    }
    const prevAlarm = Date.now();
    await this.ctx.storage.setAlarm(prevAlarm);
    await this.ctx.storage.sync();
    const result = this.sql`
         SELECT * FROM container_schedules;
       `;
    let minTime = Date.now() + 3 * 60 * 1e3;
    const now = Date.now() / 1e3;
    for (const row of result) {
      if (row.time > now) {
        continue;
      }
      const callback = this[row.callback];
      if (!callback || typeof callback !== "function") {
        console.error(`Callback ${row.callback} not found or is not a function`);
        continue;
      }
      const schedule = this.getSchedule(row.id);
      try {
        const payload = row.payload ? JSON.parse(row.payload) : void 0;
        await callback.call(this, payload, await schedule);
      } catch (e) {
        console.error(`Error executing scheduled callback "${row.callback}":`, e);
      }
      this.sql`DELETE FROM container_schedules WHERE id = ${row.id}`;
    }
    const resultForMinTime = this.sql`
         SELECT * FROM container_schedules;
       `;
    const minTimeFromSchedules = Math.min(...resultForMinTime.map((r) => r.time * 1e3));
    if (!this.container.running) {
      await this.syncPendingStoppedEvents();
      if (resultForMinTime.length == 0) {
        await this.ctx.storage.deleteAlarm();
      } else {
        await this.ctx.storage.setAlarm(minTimeFromSchedules);
      }
      return;
    }
    if (this.isActivityExpired()) {
      await this.onActivityExpired();
      this.renewActivityTimeout();
      return;
    }
    minTime = Math.min(minTimeFromSchedules, minTime, this.sleepAfterMs);
    const timeout = Math.max(0, minTime - Date.now());
    await new Promise((resolve) => {
      this.resolve = resolve;
      if (!this.container.running) {
        resolve();
        return;
      }
      this.timeout = setTimeout(() => {
        resolve();
      }, timeout);
    });
    await this.ctx.storage.setAlarm(Date.now());
  }
  timeout;
  resolve;
  // synchronises container state with the container source of truth to process events
  async syncPendingStoppedEvents() {
    const state = await this.state.getState();
    if (!this.container.running && state.status === "healthy") {
      await this.callOnStop({ exitCode: 0, reason: "exit" });
      return;
    }
    if (!this.container.running && state.status === "stopped_with_code") {
      await this.callOnStop({ exitCode: state.exitCode ?? 0, reason: "exit" });
      return;
    }
  }
  async callOnStop(onStopParams) {
    if (this.onStopCalled) {
      return;
    }
    this.onStopCalled = true;
    const promise = this.onStop(onStopParams);
    if (promise instanceof Promise) {
      await promise.finally(() => {
        this.onStopCalled = false;
      });
    } else {
      this.onStopCalled = false;
    }
    await this.state.setStopped();
  }
  /**
   * Schedule the next alarm based on upcoming tasks
   */
  async scheduleNextAlarm(ms = 1e3) {
    const nextTime = ms + Date.now();
    if (this.timeout) {
      if (this.resolve)
        this.resolve();
      clearTimeout(this.timeout);
    }
    await this.ctx.storage.setAlarm(nextTime);
    await this.ctx.storage.sync();
  }
  async listSchedules(name) {
    const result = this.sql`
      SELECT * FROM container_schedules WHERE callback = ${name} LIMIT 1
    `;
    if (!result || result.length === 0) {
      return [];
    }
    return result.map(this.toSchedule);
  }
  toSchedule(schedule) {
    let payload;
    try {
      payload = JSON.parse(schedule.payload);
    } catch (e) {
      console.error(`Error parsing payload for schedule ${schedule.id}:`, e);
      payload = void 0;
    }
    if (schedule.type === "delayed") {
      return {
        taskId: schedule.id,
        callback: schedule.callback,
        payload,
        type: "delayed",
        time: schedule.time,
        delayInSeconds: schedule.delayInSeconds
      };
    }
    return {
      taskId: schedule.id,
      callback: schedule.callback,
      payload,
      type: "scheduled",
      time: schedule.time
    };
  }
  /**
   * Get a scheduled task by ID
   * @template T Type of the payload data
   * @param id ID of the scheduled task
   * @returns The Schedule object or undefined if not found
   */
  async getSchedule(id) {
    const result = this.sql`
      SELECT * FROM container_schedules WHERE id = ${id} LIMIT 1
    `;
    if (!result || result.length === 0) {
      return void 0;
    }
    const schedule = result[0];
    return this.toSchedule(schedule);
  }
  isActivityExpired() {
    return this.sleepAfterMs <= Date.now();
  }
};

// node_modules/@cloudflare/containers/dist/lib/utils.js
var singletonContainerId = "cf-singleton-container";
function getContainer(binding2, name = singletonContainerId) {
  const objectId = binding2.idFromName(name);
  return binding2.get(objectId);
}
__name(getContainer, "getContainer");
function switchPort(request, port) {
  const headers = new Headers(request.headers);
  headers.set("cf-container-target-port", port.toString());
  return new Request(request, { headers });
}
__name(switchPort, "switchPort");

// node_modules/@cloudflare/sandbox/dist/index.js
function redactCredentials(text) {
  let result = text;
  let pos = 0;
  while (pos < result.length) {
    const httpPos = result.indexOf("http://", pos);
    const httpsPos = result.indexOf("https://", pos);
    let protocolPos = -1;
    let protocolLen = 0;
    if (httpPos === -1 && httpsPos === -1) break;
    if (httpPos !== -1 && (httpsPos === -1 || httpPos < httpsPos)) {
      protocolPos = httpPos;
      protocolLen = 7;
    } else {
      protocolPos = httpsPos;
      protocolLen = 8;
    }
    const searchStart = protocolPos + protocolLen;
    const atPos = result.indexOf("@", searchStart);
    let urlEnd = searchStart;
    while (urlEnd < result.length) {
      const char = result[urlEnd];
      if (/[\s"'`<>,;{}[\]]/.test(char)) break;
      urlEnd++;
    }
    if (atPos !== -1 && atPos < urlEnd) {
      result = `${result.substring(0, searchStart)}******${result.substring(atPos)}`;
      pos = searchStart + 6;
    } else pos = protocolPos + protocolLen;
  }
  return result;
}
__name(redactCredentials, "redactCredentials");
function sanitizeGitData(data) {
  if (typeof data === "string") return redactCredentials(data);
  if (data === null || data === void 0) return data;
  if (Array.isArray(data)) return data.map((item) => sanitizeGitData(item));
  if (typeof data === "object") {
    const result = {};
    for (const [key, value] of Object.entries(data)) result[key] = sanitizeGitData(value);
    return result;
  }
  return data;
}
__name(sanitizeGitData, "sanitizeGitData");
var GitLogger = class GitLogger2 {
  static {
    __name(this, "GitLogger");
  }
  baseLogger;
  constructor(baseLogger) {
    this.baseLogger = baseLogger;
  }
  sanitizeContext(context2) {
    return context2 ? sanitizeGitData(context2) : context2;
  }
  sanitizeError(error3) {
    if (!error3) return error3;
    const sanitized = new Error(redactCredentials(error3.message));
    sanitized.name = error3.name;
    if (error3.stack) sanitized.stack = redactCredentials(error3.stack);
    const sanitizedRecord = sanitized;
    const errorRecord = error3;
    for (const key of Object.keys(error3)) if (key !== "message" && key !== "stack" && key !== "name") sanitizedRecord[key] = sanitizeGitData(errorRecord[key]);
    return sanitized;
  }
  debug(message2, context2) {
    this.baseLogger.debug(message2, this.sanitizeContext(context2));
  }
  info(message2, context2) {
    this.baseLogger.info(message2, this.sanitizeContext(context2));
  }
  warn(message2, context2) {
    this.baseLogger.warn(message2, this.sanitizeContext(context2));
  }
  error(message2, error3, context2) {
    this.baseLogger.error(message2, this.sanitizeError(error3), this.sanitizeContext(context2));
  }
  child(context2) {
    const sanitized = sanitizeGitData(context2);
    return new GitLogger2(this.baseLogger.child(sanitized));
  }
};
var Execution = class {
  static {
    __name(this, "Execution");
  }
  code;
  context;
  /**
  * All results from the execution
  */
  results = [];
  /**
  * Accumulated stdout and stderr
  */
  logs = {
    stdout: [],
    stderr: []
  };
  /**
  * Execution error if any
  */
  error;
  /**
  * Execution count (for interpreter)
  */
  executionCount;
  constructor(code, context2) {
    this.code = code;
    this.context = context2;
  }
  /**
  * Convert to a plain object for serialization
  */
  toJSON() {
    return {
      code: this.code,
      logs: this.logs,
      error: this.error,
      executionCount: this.executionCount,
      results: this.results.map((result) => ({
        text: result.text,
        html: result.html,
        png: result.png,
        jpeg: result.jpeg,
        svg: result.svg,
        latex: result.latex,
        markdown: result.markdown,
        javascript: result.javascript,
        json: result.json,
        chart: result.chart,
        data: result.data
      }))
    };
  }
};
var ResultImpl = class {
  static {
    __name(this, "ResultImpl");
  }
  raw;
  constructor(raw2) {
    this.raw = raw2;
  }
  get text() {
    return this.raw.text || this.raw.data?.["text/plain"];
  }
  get html() {
    return this.raw.html || this.raw.data?.["text/html"];
  }
  get png() {
    return this.raw.png || this.raw.data?.["image/png"];
  }
  get jpeg() {
    return this.raw.jpeg || this.raw.data?.["image/jpeg"];
  }
  get svg() {
    return this.raw.svg || this.raw.data?.["image/svg+xml"];
  }
  get latex() {
    return this.raw.latex || this.raw.data?.["text/latex"];
  }
  get markdown() {
    return this.raw.markdown || this.raw.data?.["text/markdown"];
  }
  get javascript() {
    return this.raw.javascript || this.raw.data?.["application/javascript"];
  }
  get json() {
    return this.raw.json || this.raw.data?.["application/json"];
  }
  get chart() {
    return this.raw.chart;
  }
  get data() {
    return this.raw.data;
  }
  formats() {
    const formats = [];
    if (this.text) formats.push("text");
    if (this.html) formats.push("html");
    if (this.png) formats.push("png");
    if (this.jpeg) formats.push("jpeg");
    if (this.svg) formats.push("svg");
    if (this.latex) formats.push("latex");
    if (this.markdown) formats.push("markdown");
    if (this.javascript) formats.push("javascript");
    if (this.json) formats.push("json");
    if (this.chart) formats.push("chart");
    return formats;
  }
};
var LogLevel;
(function(LogLevel$1) {
  LogLevel$1[LogLevel$1["DEBUG"] = 0] = "DEBUG";
  LogLevel$1[LogLevel$1["INFO"] = 1] = "INFO";
  LogLevel$1[LogLevel$1["WARN"] = 2] = "WARN";
  LogLevel$1[LogLevel$1["ERROR"] = 3] = "ERROR";
})(LogLevel || (LogLevel = {}));
var COLORS = {
  reset: "\x1B[0m",
  debug: "\x1B[36m",
  info: "\x1B[32m",
  warn: "\x1B[33m",
  error: "\x1B[31m",
  dim: "\x1B[2m"
};
var CloudflareLogger = class CloudflareLogger2 {
  static {
    __name(this, "CloudflareLogger");
  }
  baseContext;
  minLevel;
  pretty;
  /**
  * Create a new CloudflareLogger
  *
  * @param baseContext Base context included in all log entries
  * @param minLevel Minimum log level to output (default: INFO)
  * @param pretty Enable pretty printing for human-readable output (default: false)
  */
  constructor(baseContext, minLevel = LogLevel.INFO, pretty = false) {
    this.baseContext = baseContext;
    this.minLevel = minLevel;
    this.pretty = pretty;
  }
  /**
  * Log debug-level message
  */
  debug(message2, context2) {
    if (this.shouldLog(LogLevel.DEBUG)) {
      const logData = this.buildLogData("debug", message2, context2);
      this.output(console.log, logData);
    }
  }
  /**
  * Log info-level message
  */
  info(message2, context2) {
    if (this.shouldLog(LogLevel.INFO)) {
      const logData = this.buildLogData("info", message2, context2);
      this.output(console.log, logData);
    }
  }
  /**
  * Log warning-level message
  */
  warn(message2, context2) {
    if (this.shouldLog(LogLevel.WARN)) {
      const logData = this.buildLogData("warn", message2, context2);
      this.output(console.warn, logData);
    }
  }
  /**
  * Log error-level message
  */
  error(message2, error3, context2) {
    if (this.shouldLog(LogLevel.ERROR)) {
      const logData = this.buildLogData("error", message2, context2, error3);
      this.output(console.error, logData);
    }
  }
  /**
  * Create a child logger with additional context
  */
  child(context2) {
    return new CloudflareLogger2({
      ...this.baseContext,
      ...context2
    }, this.minLevel, this.pretty);
  }
  /**
  * Check if a log level should be output
  */
  shouldLog(level) {
    return level >= this.minLevel;
  }
  /**
  * Build log data object
  */
  buildLogData(level, message2, context2, error3) {
    const logData = {
      level,
      msg: message2,
      ...this.baseContext,
      ...context2,
      timestamp: (/* @__PURE__ */ new Date()).toISOString()
    };
    if (error3) logData.error = {
      message: error3.message,
      stack: error3.stack,
      name: error3.name
    };
    return logData;
  }
  /**
  * Output log data to console (pretty or JSON)
  */
  output(consoleFn, data) {
    if (this.pretty) this.outputPretty(consoleFn, data);
    else this.outputJson(consoleFn, data);
  }
  /**
  * Output as JSON (production)
  */
  outputJson(consoleFn, data) {
    consoleFn(JSON.stringify(data));
  }
  /**
  * Output as pretty-printed, colored text (development)
  *
  * Format: LEVEL [component] message (trace: tr_...) {context}
  * Example: INFO [sandbox-do] Command started (trace: tr_7f3a9b2c) {commandId: "cmd-123"}
  */
  outputPretty(consoleFn, data) {
    const { level, msg, timestamp, traceId, component, sandboxId, sessionId, processId, commandId, operation, duration, error: error3, ...rest } = data;
    const levelStr = String(level || "INFO").toUpperCase();
    const levelColor = this.getLevelColor(levelStr);
    const componentBadge = component ? `[${component}]` : "";
    const traceIdShort = traceId ? String(traceId).substring(0, 12) : "";
    let logLine = `${levelColor}${levelStr.padEnd(5)}${COLORS.reset} ${componentBadge} ${msg}`;
    if (traceIdShort) logLine += ` ${COLORS.dim}(trace: ${traceIdShort})${COLORS.reset}`;
    const contextFields = [];
    if (operation) contextFields.push(`operation: ${operation}`);
    if (commandId) contextFields.push(`commandId: ${String(commandId).substring(0, 12)}`);
    if (sandboxId) contextFields.push(`sandboxId: ${sandboxId}`);
    if (sessionId) contextFields.push(`sessionId: ${String(sessionId).substring(0, 12)}`);
    if (processId) contextFields.push(`processId: ${processId}`);
    if (duration !== void 0) contextFields.push(`duration: ${duration}ms`);
    if (contextFields.length > 0) logLine += ` ${COLORS.dim}{${contextFields.join(", ")}}${COLORS.reset}`;
    consoleFn(logLine);
    if (error3 && typeof error3 === "object") {
      const errorObj = error3;
      if (errorObj.message) consoleFn(`  ${COLORS.error}Error: ${errorObj.message}${COLORS.reset}`);
      if (errorObj.stack) consoleFn(`  ${COLORS.dim}${errorObj.stack}${COLORS.reset}`);
    }
    if (Object.keys(rest).length > 0) consoleFn(`  ${COLORS.dim}${JSON.stringify(rest, null, 2)}${COLORS.reset}`);
  }
  /**
  * Get ANSI color code for log level
  */
  getLevelColor(level) {
    switch (level.toLowerCase()) {
      case "debug":
        return COLORS.debug;
      case "info":
        return COLORS.info;
      case "warn":
        return COLORS.warn;
      case "error":
        return COLORS.error;
      default:
        return COLORS.reset;
    }
  }
};
var TraceContext = class TraceContext2 {
  static {
    __name(this, "TraceContext");
  }
  /**
  * HTTP header name for trace ID propagation
  */
  static TRACE_HEADER = "X-Trace-Id";
  /**
  * Generate a new trace ID
  *
  * Format: "tr_" + 16 random hex characters
  * Example: "tr_7f3a9b2c4e5d6f1a"
  *
  * @returns Newly generated trace ID
  */
  static generate() {
    return `tr_${crypto.randomUUID().replace(/-/g, "").substring(0, 16)}`;
  }
  /**
  * Extract trace ID from HTTP request headers
  *
  * @param headers Request headers
  * @returns Trace ID if present, null otherwise
  */
  static fromHeaders(headers) {
    return headers.get(TraceContext2.TRACE_HEADER);
  }
  /**
  * Create headers object with trace ID for outgoing requests
  *
  * @param traceId Trace ID to include
  * @returns Headers object with X-Trace-Id set
  */
  static toHeaders(traceId) {
    return { [TraceContext2.TRACE_HEADER]: traceId };
  }
  /**
  * Get the header name used for trace ID propagation
  *
  * @returns Header name ("X-Trace-Id")
  */
  static getHeaderName() {
    return TraceContext2.TRACE_HEADER;
  }
};
function createNoOpLogger() {
  return {
    debug: /* @__PURE__ */ __name(() => {
    }, "debug"),
    info: /* @__PURE__ */ __name(() => {
    }, "info"),
    warn: /* @__PURE__ */ __name(() => {
    }, "warn"),
    error: /* @__PURE__ */ __name(() => {
    }, "error"),
    child: /* @__PURE__ */ __name(() => createNoOpLogger(), "child")
  };
}
__name(createNoOpLogger, "createNoOpLogger");
var loggerStorage = new AsyncLocalStorage();
function runWithLogger(logger, fn) {
  return loggerStorage.run(logger, fn);
}
__name(runWithLogger, "runWithLogger");
function createLogger(context2) {
  const minLevel = getLogLevelFromEnv();
  const pretty = isPrettyPrintEnabled();
  return new CloudflareLogger({
    ...context2,
    traceId: context2.traceId || TraceContext.generate(),
    component: context2.component
  }, minLevel, pretty);
}
__name(createLogger, "createLogger");
function getLogLevelFromEnv() {
  switch ((getEnvVar("SANDBOX_LOG_LEVEL") || "info").toLowerCase()) {
    case "debug":
      return LogLevel.DEBUG;
    case "info":
      return LogLevel.INFO;
    case "warn":
      return LogLevel.WARN;
    case "error":
      return LogLevel.ERROR;
    default:
      return LogLevel.INFO;
  }
}
__name(getLogLevelFromEnv, "getLogLevelFromEnv");
function isPrettyPrintEnabled() {
  const format = getEnvVar("SANDBOX_LOG_FORMAT");
  if (format) return format.toLowerCase() === "pretty";
  return false;
}
__name(isPrettyPrintEnabled, "isPrettyPrintEnabled");
function getEnvVar(name) {
  if (typeof process !== "undefined" && process.env) return process.env[name];
  if (typeof Bun !== "undefined") {
    const bunEnv = Bun.env;
    if (bunEnv) return bunEnv[name];
  }
}
__name(getEnvVar, "getEnvVar");
var ErrorCode = {
  FILE_NOT_FOUND: "FILE_NOT_FOUND",
  PERMISSION_DENIED: "PERMISSION_DENIED",
  FILE_EXISTS: "FILE_EXISTS",
  IS_DIRECTORY: "IS_DIRECTORY",
  NOT_DIRECTORY: "NOT_DIRECTORY",
  NO_SPACE: "NO_SPACE",
  TOO_MANY_FILES: "TOO_MANY_FILES",
  RESOURCE_BUSY: "RESOURCE_BUSY",
  READ_ONLY: "READ_ONLY",
  NAME_TOO_LONG: "NAME_TOO_LONG",
  TOO_MANY_LINKS: "TOO_MANY_LINKS",
  FILESYSTEM_ERROR: "FILESYSTEM_ERROR",
  COMMAND_NOT_FOUND: "COMMAND_NOT_FOUND",
  COMMAND_PERMISSION_DENIED: "COMMAND_PERMISSION_DENIED",
  INVALID_COMMAND: "INVALID_COMMAND",
  COMMAND_EXECUTION_ERROR: "COMMAND_EXECUTION_ERROR",
  STREAM_START_ERROR: "STREAM_START_ERROR",
  PROCESS_NOT_FOUND: "PROCESS_NOT_FOUND",
  PROCESS_PERMISSION_DENIED: "PROCESS_PERMISSION_DENIED",
  PROCESS_ERROR: "PROCESS_ERROR",
  PORT_ALREADY_EXPOSED: "PORT_ALREADY_EXPOSED",
  PORT_IN_USE: "PORT_IN_USE",
  PORT_NOT_EXPOSED: "PORT_NOT_EXPOSED",
  INVALID_PORT_NUMBER: "INVALID_PORT_NUMBER",
  INVALID_PORT: "INVALID_PORT",
  SERVICE_NOT_RESPONDING: "SERVICE_NOT_RESPONDING",
  PORT_OPERATION_ERROR: "PORT_OPERATION_ERROR",
  CUSTOM_DOMAIN_REQUIRED: "CUSTOM_DOMAIN_REQUIRED",
  GIT_REPOSITORY_NOT_FOUND: "GIT_REPOSITORY_NOT_FOUND",
  GIT_BRANCH_NOT_FOUND: "GIT_BRANCH_NOT_FOUND",
  GIT_AUTH_FAILED: "GIT_AUTH_FAILED",
  GIT_NETWORK_ERROR: "GIT_NETWORK_ERROR",
  INVALID_GIT_URL: "INVALID_GIT_URL",
  GIT_CLONE_FAILED: "GIT_CLONE_FAILED",
  GIT_CHECKOUT_FAILED: "GIT_CHECKOUT_FAILED",
  GIT_OPERATION_FAILED: "GIT_OPERATION_FAILED",
  INTERPRETER_NOT_READY: "INTERPRETER_NOT_READY",
  CONTEXT_NOT_FOUND: "CONTEXT_NOT_FOUND",
  CODE_EXECUTION_ERROR: "CODE_EXECUTION_ERROR",
  VALIDATION_FAILED: "VALIDATION_FAILED",
  INVALID_JSON_RESPONSE: "INVALID_JSON_RESPONSE",
  UNKNOWN_ERROR: "UNKNOWN_ERROR",
  INTERNAL_ERROR: "INTERNAL_ERROR"
};
var ERROR_STATUS_MAP = {
  [ErrorCode.FILE_NOT_FOUND]: 404,
  [ErrorCode.COMMAND_NOT_FOUND]: 404,
  [ErrorCode.PROCESS_NOT_FOUND]: 404,
  [ErrorCode.PORT_NOT_EXPOSED]: 404,
  [ErrorCode.GIT_REPOSITORY_NOT_FOUND]: 404,
  [ErrorCode.GIT_BRANCH_NOT_FOUND]: 404,
  [ErrorCode.CONTEXT_NOT_FOUND]: 404,
  [ErrorCode.IS_DIRECTORY]: 400,
  [ErrorCode.NOT_DIRECTORY]: 400,
  [ErrorCode.INVALID_COMMAND]: 400,
  [ErrorCode.INVALID_PORT_NUMBER]: 400,
  [ErrorCode.INVALID_PORT]: 400,
  [ErrorCode.INVALID_GIT_URL]: 400,
  [ErrorCode.CUSTOM_DOMAIN_REQUIRED]: 400,
  [ErrorCode.INVALID_JSON_RESPONSE]: 400,
  [ErrorCode.NAME_TOO_LONG]: 400,
  [ErrorCode.VALIDATION_FAILED]: 400,
  [ErrorCode.GIT_AUTH_FAILED]: 401,
  [ErrorCode.PERMISSION_DENIED]: 403,
  [ErrorCode.COMMAND_PERMISSION_DENIED]: 403,
  [ErrorCode.PROCESS_PERMISSION_DENIED]: 403,
  [ErrorCode.READ_ONLY]: 403,
  [ErrorCode.FILE_EXISTS]: 409,
  [ErrorCode.PORT_ALREADY_EXPOSED]: 409,
  [ErrorCode.PORT_IN_USE]: 409,
  [ErrorCode.RESOURCE_BUSY]: 409,
  [ErrorCode.SERVICE_NOT_RESPONDING]: 502,
  [ErrorCode.GIT_NETWORK_ERROR]: 502,
  [ErrorCode.INTERPRETER_NOT_READY]: 503,
  [ErrorCode.NO_SPACE]: 500,
  [ErrorCode.TOO_MANY_FILES]: 500,
  [ErrorCode.TOO_MANY_LINKS]: 500,
  [ErrorCode.FILESYSTEM_ERROR]: 500,
  [ErrorCode.COMMAND_EXECUTION_ERROR]: 500,
  [ErrorCode.STREAM_START_ERROR]: 500,
  [ErrorCode.PROCESS_ERROR]: 500,
  [ErrorCode.PORT_OPERATION_ERROR]: 500,
  [ErrorCode.GIT_CLONE_FAILED]: 500,
  [ErrorCode.GIT_CHECKOUT_FAILED]: 500,
  [ErrorCode.GIT_OPERATION_FAILED]: 500,
  [ErrorCode.CODE_EXECUTION_ERROR]: 500,
  [ErrorCode.UNKNOWN_ERROR]: 500,
  [ErrorCode.INTERNAL_ERROR]: 500
};
var SandboxError = class extends Error {
  static {
    __name(this, "SandboxError");
  }
  constructor(errorResponse) {
    super(errorResponse.message);
    this.errorResponse = errorResponse;
    this.name = "SandboxError";
  }
  get code() {
    return this.errorResponse.code;
  }
  get context() {
    return this.errorResponse.context;
  }
  get httpStatus() {
    return this.errorResponse.httpStatus;
  }
  get operation() {
    return this.errorResponse.operation;
  }
  get suggestion() {
    return this.errorResponse.suggestion;
  }
  get timestamp() {
    return this.errorResponse.timestamp;
  }
  get documentation() {
    return this.errorResponse.documentation;
  }
  toJSON() {
    return {
      name: this.name,
      message: this.message,
      code: this.code,
      context: this.context,
      httpStatus: this.httpStatus,
      operation: this.operation,
      suggestion: this.suggestion,
      timestamp: this.timestamp,
      documentation: this.documentation,
      stack: this.stack
    };
  }
};
var FileNotFoundError = class extends SandboxError {
  static {
    __name(this, "FileNotFoundError");
  }
  constructor(errorResponse) {
    super(errorResponse);
    this.name = "FileNotFoundError";
  }
  get path() {
    return this.context.path;
  }
};
var FileExistsError = class extends SandboxError {
  static {
    __name(this, "FileExistsError");
  }
  constructor(errorResponse) {
    super(errorResponse);
    this.name = "FileExistsError";
  }
  get path() {
    return this.context.path;
  }
};
var FileSystemError = class extends SandboxError {
  static {
    __name(this, "FileSystemError");
  }
  constructor(errorResponse) {
    super(errorResponse);
    this.name = "FileSystemError";
  }
  get path() {
    return this.context.path;
  }
  get stderr() {
    return this.context.stderr;
  }
  get exitCode() {
    return this.context.exitCode;
  }
};
var PermissionDeniedError = class extends SandboxError {
  static {
    __name(this, "PermissionDeniedError");
  }
  constructor(errorResponse) {
    super(errorResponse);
    this.name = "PermissionDeniedError";
  }
  get path() {
    return this.context.path;
  }
};
var CommandNotFoundError = class extends SandboxError {
  static {
    __name(this, "CommandNotFoundError");
  }
  constructor(errorResponse) {
    super(errorResponse);
    this.name = "CommandNotFoundError";
  }
  get command() {
    return this.context.command;
  }
};
var CommandError = class extends SandboxError {
  static {
    __name(this, "CommandError");
  }
  constructor(errorResponse) {
    super(errorResponse);
    this.name = "CommandError";
  }
  get command() {
    return this.context.command;
  }
  get exitCode() {
    return this.context.exitCode;
  }
  get stdout() {
    return this.context.stdout;
  }
  get stderr() {
    return this.context.stderr;
  }
};
var ProcessNotFoundError = class extends SandboxError {
  static {
    __name(this, "ProcessNotFoundError");
  }
  constructor(errorResponse) {
    super(errorResponse);
    this.name = "ProcessNotFoundError";
  }
  get processId() {
    return this.context.processId;
  }
};
var ProcessError = class extends SandboxError {
  static {
    __name(this, "ProcessError");
  }
  constructor(errorResponse) {
    super(errorResponse);
    this.name = "ProcessError";
  }
  get processId() {
    return this.context.processId;
  }
  get pid() {
    return this.context.pid;
  }
  get exitCode() {
    return this.context.exitCode;
  }
  get stderr() {
    return this.context.stderr;
  }
};
var PortAlreadyExposedError = class extends SandboxError {
  static {
    __name(this, "PortAlreadyExposedError");
  }
  constructor(errorResponse) {
    super(errorResponse);
    this.name = "PortAlreadyExposedError";
  }
  get port() {
    return this.context.port;
  }
  get portName() {
    return this.context.portName;
  }
};
var PortNotExposedError = class extends SandboxError {
  static {
    __name(this, "PortNotExposedError");
  }
  constructor(errorResponse) {
    super(errorResponse);
    this.name = "PortNotExposedError";
  }
  get port() {
    return this.context.port;
  }
};
var InvalidPortError = class extends SandboxError {
  static {
    __name(this, "InvalidPortError");
  }
  constructor(errorResponse) {
    super(errorResponse);
    this.name = "InvalidPortError";
  }
  get port() {
    return this.context.port;
  }
  get reason() {
    return this.context.reason;
  }
};
var ServiceNotRespondingError = class extends SandboxError {
  static {
    __name(this, "ServiceNotRespondingError");
  }
  constructor(errorResponse) {
    super(errorResponse);
    this.name = "ServiceNotRespondingError";
  }
  get port() {
    return this.context.port;
  }
  get portName() {
    return this.context.portName;
  }
};
var PortInUseError = class extends SandboxError {
  static {
    __name(this, "PortInUseError");
  }
  constructor(errorResponse) {
    super(errorResponse);
    this.name = "PortInUseError";
  }
  get port() {
    return this.context.port;
  }
};
var PortError = class extends SandboxError {
  static {
    __name(this, "PortError");
  }
  constructor(errorResponse) {
    super(errorResponse);
    this.name = "PortError";
  }
  get port() {
    return this.context.port;
  }
  get portName() {
    return this.context.portName;
  }
  get stderr() {
    return this.context.stderr;
  }
};
var CustomDomainRequiredError = class extends SandboxError {
  static {
    __name(this, "CustomDomainRequiredError");
  }
  constructor(errorResponse) {
    super(errorResponse);
    this.name = "CustomDomainRequiredError";
  }
};
var GitRepositoryNotFoundError = class extends SandboxError {
  static {
    __name(this, "GitRepositoryNotFoundError");
  }
  constructor(errorResponse) {
    super(errorResponse);
    this.name = "GitRepositoryNotFoundError";
  }
  get repository() {
    return this.context.repository;
  }
};
var GitAuthenticationError = class extends SandboxError {
  static {
    __name(this, "GitAuthenticationError");
  }
  constructor(errorResponse) {
    super(errorResponse);
    this.name = "GitAuthenticationError";
  }
  get repository() {
    return this.context.repository;
  }
};
var GitBranchNotFoundError = class extends SandboxError {
  static {
    __name(this, "GitBranchNotFoundError");
  }
  constructor(errorResponse) {
    super(errorResponse);
    this.name = "GitBranchNotFoundError";
  }
  get branch() {
    return this.context.branch;
  }
  get repository() {
    return this.context.repository;
  }
};
var GitNetworkError = class extends SandboxError {
  static {
    __name(this, "GitNetworkError");
  }
  constructor(errorResponse) {
    super(errorResponse);
    this.name = "GitNetworkError";
  }
  get repository() {
    return this.context.repository;
  }
  get branch() {
    return this.context.branch;
  }
  get targetDir() {
    return this.context.targetDir;
  }
};
var GitCloneError = class extends SandboxError {
  static {
    __name(this, "GitCloneError");
  }
  constructor(errorResponse) {
    super(errorResponse);
    this.name = "GitCloneError";
  }
  get repository() {
    return this.context.repository;
  }
  get targetDir() {
    return this.context.targetDir;
  }
  get stderr() {
    return this.context.stderr;
  }
  get exitCode() {
    return this.context.exitCode;
  }
};
var GitCheckoutError = class extends SandboxError {
  static {
    __name(this, "GitCheckoutError");
  }
  constructor(errorResponse) {
    super(errorResponse);
    this.name = "GitCheckoutError";
  }
  get branch() {
    return this.context.branch;
  }
  get repository() {
    return this.context.repository;
  }
  get stderr() {
    return this.context.stderr;
  }
};
var InvalidGitUrlError = class extends SandboxError {
  static {
    __name(this, "InvalidGitUrlError");
  }
  constructor(errorResponse) {
    super(errorResponse);
    this.name = "InvalidGitUrlError";
  }
  get validationErrors() {
    return this.context.validationErrors;
  }
};
var GitError = class extends SandboxError {
  static {
    __name(this, "GitError");
  }
  constructor(errorResponse) {
    super(errorResponse);
    this.name = "GitError";
  }
  get repository() {
    return this.context.repository;
  }
  get branch() {
    return this.context.branch;
  }
  get targetDir() {
    return this.context.targetDir;
  }
  get stderr() {
    return this.context.stderr;
  }
  get exitCode() {
    return this.context.exitCode;
  }
};
var InterpreterNotReadyError = class extends SandboxError {
  static {
    __name(this, "InterpreterNotReadyError");
  }
  constructor(errorResponse) {
    super(errorResponse);
    this.name = "InterpreterNotReadyError";
  }
  get retryAfter() {
    return this.context.retryAfter;
  }
  get progress() {
    return this.context.progress;
  }
};
var ContextNotFoundError = class extends SandboxError {
  static {
    __name(this, "ContextNotFoundError");
  }
  constructor(errorResponse) {
    super(errorResponse);
    this.name = "ContextNotFoundError";
  }
  get contextId() {
    return this.context.contextId;
  }
};
var CodeExecutionError = class extends SandboxError {
  static {
    __name(this, "CodeExecutionError");
  }
  constructor(errorResponse) {
    super(errorResponse);
    this.name = "CodeExecutionError";
  }
  get contextId() {
    return this.context.contextId;
  }
  get ename() {
    return this.context.ename;
  }
  get evalue() {
    return this.context.evalue;
  }
  get traceback() {
    return this.context.traceback;
  }
};
var ValidationFailedError = class extends SandboxError {
  static {
    __name(this, "ValidationFailedError");
  }
  constructor(errorResponse) {
    super(errorResponse);
    this.name = "ValidationFailedError";
  }
  get validationErrors() {
    return this.context.validationErrors;
  }
};
function createErrorFromResponse(errorResponse) {
  switch (errorResponse.code) {
    case ErrorCode.FILE_NOT_FOUND:
      return new FileNotFoundError(errorResponse);
    case ErrorCode.FILE_EXISTS:
      return new FileExistsError(errorResponse);
    case ErrorCode.PERMISSION_DENIED:
      return new PermissionDeniedError(errorResponse);
    case ErrorCode.IS_DIRECTORY:
    case ErrorCode.NOT_DIRECTORY:
    case ErrorCode.NO_SPACE:
    case ErrorCode.TOO_MANY_FILES:
    case ErrorCode.RESOURCE_BUSY:
    case ErrorCode.READ_ONLY:
    case ErrorCode.NAME_TOO_LONG:
    case ErrorCode.TOO_MANY_LINKS:
    case ErrorCode.FILESYSTEM_ERROR:
      return new FileSystemError(errorResponse);
    case ErrorCode.COMMAND_NOT_FOUND:
      return new CommandNotFoundError(errorResponse);
    case ErrorCode.COMMAND_PERMISSION_DENIED:
    case ErrorCode.COMMAND_EXECUTION_ERROR:
    case ErrorCode.INVALID_COMMAND:
    case ErrorCode.STREAM_START_ERROR:
      return new CommandError(errorResponse);
    case ErrorCode.PROCESS_NOT_FOUND:
      return new ProcessNotFoundError(errorResponse);
    case ErrorCode.PROCESS_PERMISSION_DENIED:
    case ErrorCode.PROCESS_ERROR:
      return new ProcessError(errorResponse);
    case ErrorCode.PORT_ALREADY_EXPOSED:
      return new PortAlreadyExposedError(errorResponse);
    case ErrorCode.PORT_NOT_EXPOSED:
      return new PortNotExposedError(errorResponse);
    case ErrorCode.INVALID_PORT_NUMBER:
    case ErrorCode.INVALID_PORT:
      return new InvalidPortError(errorResponse);
    case ErrorCode.SERVICE_NOT_RESPONDING:
      return new ServiceNotRespondingError(errorResponse);
    case ErrorCode.PORT_IN_USE:
      return new PortInUseError(errorResponse);
    case ErrorCode.PORT_OPERATION_ERROR:
      return new PortError(errorResponse);
    case ErrorCode.CUSTOM_DOMAIN_REQUIRED:
      return new CustomDomainRequiredError(errorResponse);
    case ErrorCode.GIT_REPOSITORY_NOT_FOUND:
      return new GitRepositoryNotFoundError(errorResponse);
    case ErrorCode.GIT_AUTH_FAILED:
      return new GitAuthenticationError(errorResponse);
    case ErrorCode.GIT_BRANCH_NOT_FOUND:
      return new GitBranchNotFoundError(errorResponse);
    case ErrorCode.GIT_NETWORK_ERROR:
      return new GitNetworkError(errorResponse);
    case ErrorCode.GIT_CLONE_FAILED:
      return new GitCloneError(errorResponse);
    case ErrorCode.GIT_CHECKOUT_FAILED:
      return new GitCheckoutError(errorResponse);
    case ErrorCode.INVALID_GIT_URL:
      return new InvalidGitUrlError(errorResponse);
    case ErrorCode.GIT_OPERATION_FAILED:
      return new GitError(errorResponse);
    case ErrorCode.INTERPRETER_NOT_READY:
      return new InterpreterNotReadyError(errorResponse);
    case ErrorCode.CONTEXT_NOT_FOUND:
      return new ContextNotFoundError(errorResponse);
    case ErrorCode.CODE_EXECUTION_ERROR:
      return new CodeExecutionError(errorResponse);
    case ErrorCode.VALIDATION_FAILED:
      return new ValidationFailedError(errorResponse);
    case ErrorCode.INVALID_JSON_RESPONSE:
    case ErrorCode.UNKNOWN_ERROR:
    case ErrorCode.INTERNAL_ERROR:
      return new SandboxError(errorResponse);
    default:
      return new SandboxError(errorResponse);
  }
}
__name(createErrorFromResponse, "createErrorFromResponse");
var TIMEOUT_MS = 6e4;
var MIN_TIME_FOR_RETRY_MS = 1e4;
var BaseHttpClient = class {
  static {
    __name(this, "BaseHttpClient");
  }
  baseUrl;
  options;
  logger;
  constructor(options = {}) {
    this.options = options;
    this.logger = options.logger ?? createNoOpLogger();
    this.baseUrl = this.options.baseUrl;
  }
  /**
  * Core HTTP request method with automatic retry for container provisioning delays
  */
  async doFetch(path, options) {
    const startTime = Date.now();
    let attempt = 0;
    while (true) {
      const response = await this.executeFetch(path, options);
      if (response.status === 503) {
        if (await this.isContainerProvisioningError(response)) {
          const remaining = TIMEOUT_MS - (Date.now() - startTime);
          if (remaining > MIN_TIME_FOR_RETRY_MS) {
            const delay = Math.min(2e3 * 2 ** attempt, 16e3);
            this.logger.info("Container provisioning in progress, retrying", {
              attempt: attempt + 1,
              delayMs: delay,
              remainingSec: Math.floor(remaining / 1e3)
            });
            await new Promise((resolve) => setTimeout(resolve, delay));
            attempt++;
            continue;
          } else {
            this.logger.error("Container failed to provision after multiple attempts", /* @__PURE__ */ new Error(`Failed after ${attempt + 1} attempts over 60s`));
            return response;
          }
        }
      }
      return response;
    }
  }
  /**
  * Make a POST request with JSON body
  */
  async post(endpoint, data, responseHandler) {
    const response = await this.doFetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });
    return this.handleResponse(response, responseHandler);
  }
  /**
  * Make a GET request
  */
  async get(endpoint, responseHandler) {
    const response = await this.doFetch(endpoint, { method: "GET" });
    return this.handleResponse(response, responseHandler);
  }
  /**
  * Make a DELETE request
  */
  async delete(endpoint, responseHandler) {
    const response = await this.doFetch(endpoint, { method: "DELETE" });
    return this.handleResponse(response, responseHandler);
  }
  /**
  * Handle HTTP response with error checking and parsing
  */
  async handleResponse(response, customHandler) {
    if (!response.ok) await this.handleErrorResponse(response);
    if (customHandler) return customHandler(response);
    try {
      return await response.json();
    } catch (error3) {
      throw createErrorFromResponse({
        code: ErrorCode.INVALID_JSON_RESPONSE,
        message: `Invalid JSON response: ${error3 instanceof Error ? error3.message : "Unknown parsing error"}`,
        context: {},
        httpStatus: response.status,
        timestamp: (/* @__PURE__ */ new Date()).toISOString()
      });
    }
  }
  /**
  * Handle error responses with consistent error throwing
  */
  async handleErrorResponse(response) {
    let errorData;
    try {
      errorData = await response.json();
    } catch {
      errorData = {
        code: ErrorCode.INTERNAL_ERROR,
        message: `HTTP error! status: ${response.status}`,
        context: { statusText: response.statusText },
        httpStatus: response.status,
        timestamp: (/* @__PURE__ */ new Date()).toISOString()
      };
    }
    const error3 = createErrorFromResponse(errorData);
    this.options.onError?.(errorData.message, void 0);
    throw error3;
  }
  /**
  * Create a streaming response handler for Server-Sent Events
  */
  async handleStreamResponse(response) {
    if (!response.ok) await this.handleErrorResponse(response);
    if (!response.body) throw new Error("No response body for streaming");
    return response.body;
  }
  /**
  * Utility method to log successful operations
  */
  logSuccess(operation, details) {
    this.logger.info(`${operation} completed successfully`, details ? { details } : void 0);
  }
  /**
  * Utility method to log errors intelligently
  * Only logs unexpected errors (5xx), not expected errors (4xx)
  *
  * - 4xx errors (validation, not found, conflicts): Don't log (expected client errors)
  * - 5xx errors (server failures, internal errors): DO log (unexpected server errors)
  */
  logError(operation, error3) {
    if (error3 && typeof error3 === "object" && "httpStatus" in error3) {
      const httpStatus = error3.httpStatus;
      if (httpStatus >= 500) this.logger.error(`Unexpected error in ${operation}`, error3 instanceof Error ? error3 : new Error(String(error3)), { httpStatus });
    } else this.logger.error(`Error in ${operation}`, error3 instanceof Error ? error3 : new Error(String(error3)));
  }
  /**
  * Check if 503 response is from container provisioning (retryable)
  * vs user application (not retryable)
  */
  async isContainerProvisioningError(response) {
    try {
      return (await response.clone().text()).includes("There is no Container instance available");
    } catch (error3) {
      this.logger.error("Error checking response body", error3 instanceof Error ? error3 : new Error(String(error3)));
      return false;
    }
  }
  async executeFetch(path, options) {
    const url = this.options.stub ? `http://localhost:${this.options.port}${path}` : `${this.baseUrl}${path}`;
    try {
      if (this.options.stub) return await this.options.stub.containerFetch(url, options || {}, this.options.port);
      else return await fetch(url, options);
    } catch (error3) {
      this.logger.error("HTTP request error", error3 instanceof Error ? error3 : new Error(String(error3)), {
        method: options?.method || "GET",
        url
      });
      throw error3;
    }
  }
};
var CommandClient = class extends BaseHttpClient {
  static {
    __name(this, "CommandClient");
  }
  /**
  * Execute a command and return the complete result
  * @param command - The command to execute
  * @param sessionId - The session ID for this command execution
  * @param timeoutMs - Optional timeout in milliseconds (unlimited by default)
  */
  async execute(command, sessionId, timeoutMs) {
    try {
      const data = {
        command,
        sessionId,
        ...timeoutMs !== void 0 && { timeoutMs }
      };
      const response = await this.post("/api/execute", data);
      this.logSuccess("Command executed", `${command}, Success: ${response.success}`);
      this.options.onCommandComplete?.(response.success, response.exitCode, response.stdout, response.stderr, response.command);
      return response;
    } catch (error3) {
      this.logError("execute", error3);
      this.options.onError?.(error3 instanceof Error ? error3.message : String(error3), command);
      throw error3;
    }
  }
  /**
  * Execute a command and return a stream of events
  * @param command - The command to execute
  * @param sessionId - The session ID for this command execution
  */
  async executeStream(command, sessionId) {
    try {
      const data = {
        command,
        sessionId
      };
      const response = await this.doFetch("/api/execute/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
      });
      const stream = await this.handleStreamResponse(response);
      this.logSuccess("Command stream started", command);
      return stream;
    } catch (error3) {
      this.logError("executeStream", error3);
      this.options.onError?.(error3 instanceof Error ? error3.message : String(error3), command);
      throw error3;
    }
  }
};
var FileClient = class extends BaseHttpClient {
  static {
    __name(this, "FileClient");
  }
  /**
  * Create a directory
  * @param path - Directory path to create
  * @param sessionId - The session ID for this operation
  * @param options - Optional settings (recursive)
  */
  async mkdir(path, sessionId, options) {
    try {
      const data = {
        path,
        sessionId,
        recursive: options?.recursive ?? false
      };
      const response = await this.post("/api/mkdir", data);
      this.logSuccess("Directory created", `${path} (recursive: ${data.recursive})`);
      return response;
    } catch (error3) {
      this.logError("mkdir", error3);
      throw error3;
    }
  }
  /**
  * Write content to a file
  * @param path - File path to write to
  * @param content - Content to write
  * @param sessionId - The session ID for this operation
  * @param options - Optional settings (encoding)
  */
  async writeFile(path, content, sessionId, options) {
    try {
      const data = {
        path,
        content,
        sessionId,
        encoding: options?.encoding
      };
      const response = await this.post("/api/write", data);
      this.logSuccess("File written", `${path} (${content.length} chars)`);
      return response;
    } catch (error3) {
      this.logError("writeFile", error3);
      throw error3;
    }
  }
  /**
  * Read content from a file
  * @param path - File path to read from
  * @param sessionId - The session ID for this operation
  * @param options - Optional settings (encoding)
  */
  async readFile(path, sessionId, options) {
    try {
      const data = {
        path,
        sessionId,
        encoding: options?.encoding
      };
      const response = await this.post("/api/read", data);
      this.logSuccess("File read", `${path} (${response.content.length} chars)`);
      return response;
    } catch (error3) {
      this.logError("readFile", error3);
      throw error3;
    }
  }
  /**
  * Stream a file using Server-Sent Events
  * Returns a ReadableStream of SSE events containing metadata, chunks, and completion
  * @param path - File path to stream
  * @param sessionId - The session ID for this operation
  */
  async readFileStream(path, sessionId) {
    try {
      const data = {
        path,
        sessionId
      };
      const response = await this.doFetch("/api/read/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
      });
      const stream = await this.handleStreamResponse(response);
      this.logSuccess("File stream started", path);
      return stream;
    } catch (error3) {
      this.logError("readFileStream", error3);
      throw error3;
    }
  }
  /**
  * Delete a file
  * @param path - File path to delete
  * @param sessionId - The session ID for this operation
  */
  async deleteFile(path, sessionId) {
    try {
      const data = {
        path,
        sessionId
      };
      const response = await this.post("/api/delete", data);
      this.logSuccess("File deleted", path);
      return response;
    } catch (error3) {
      this.logError("deleteFile", error3);
      throw error3;
    }
  }
  /**
  * Rename a file
  * @param path - Current file path
  * @param newPath - New file path
  * @param sessionId - The session ID for this operation
  */
  async renameFile(path, newPath, sessionId) {
    try {
      const data = {
        oldPath: path,
        newPath,
        sessionId
      };
      const response = await this.post("/api/rename", data);
      this.logSuccess("File renamed", `${path} -> ${newPath}`);
      return response;
    } catch (error3) {
      this.logError("renameFile", error3);
      throw error3;
    }
  }
  /**
  * Move a file
  * @param path - Current file path
  * @param newPath - Destination file path
  * @param sessionId - The session ID for this operation
  */
  async moveFile(path, newPath, sessionId) {
    try {
      const data = {
        sourcePath: path,
        destinationPath: newPath,
        sessionId
      };
      const response = await this.post("/api/move", data);
      this.logSuccess("File moved", `${path} -> ${newPath}`);
      return response;
    } catch (error3) {
      this.logError("moveFile", error3);
      throw error3;
    }
  }
  /**
  * List files in a directory
  * @param path - Directory path to list
  * @param sessionId - The session ID for this operation
  * @param options - Optional settings (recursive, includeHidden)
  */
  async listFiles(path, sessionId, options) {
    try {
      const data = {
        path,
        sessionId,
        options: options || {}
      };
      const response = await this.post("/api/list-files", data);
      this.logSuccess("Files listed", `${path} (${response.count} files)`);
      return response;
    } catch (error3) {
      this.logError("listFiles", error3);
      throw error3;
    }
  }
  /**
  * Check if a file or directory exists
  * @param path - Path to check
  * @param sessionId - The session ID for this operation
  */
  async exists(path, sessionId) {
    try {
      const data = {
        path,
        sessionId
      };
      const response = await this.post("/api/exists", data);
      this.logSuccess("Path existence checked", `${path} (exists: ${response.exists})`);
      return response;
    } catch (error3) {
      this.logError("exists", error3);
      throw error3;
    }
  }
};
var GitClient = class extends BaseHttpClient {
  static {
    __name(this, "GitClient");
  }
  constructor(options = {}) {
    super(options);
    this.logger = new GitLogger(this.logger);
  }
  /**
  * Clone a Git repository
  * @param repoUrl - URL of the Git repository to clone
  * @param sessionId - The session ID for this operation
  * @param options - Optional settings (branch, targetDir)
  */
  async checkout(repoUrl, sessionId, options) {
    try {
      let targetDir = options?.targetDir;
      if (!targetDir) targetDir = `/workspace/${this.extractRepoName(repoUrl)}`;
      const data = {
        repoUrl,
        sessionId,
        targetDir
      };
      if (options?.branch) data.branch = options.branch;
      const response = await this.post("/api/git/checkout", data);
      this.logSuccess("Repository cloned", `${repoUrl} (branch: ${response.branch}) -> ${response.targetDir}`);
      return response;
    } catch (error3) {
      this.logError("checkout", error3);
      throw error3;
    }
  }
  /**
  * Extract repository name from URL for default directory name
  */
  extractRepoName(repoUrl) {
    try {
      const pathParts = new URL(repoUrl).pathname.split("/");
      return pathParts[pathParts.length - 1].replace(/\.git$/, "");
    } catch {
      const parts = repoUrl.split("/");
      return parts[parts.length - 1].replace(/\.git$/, "") || "repo";
    }
  }
};
var InterpreterClient = class extends BaseHttpClient {
  static {
    __name(this, "InterpreterClient");
  }
  maxRetries = 3;
  retryDelayMs = 1e3;
  async createCodeContext(options = {}) {
    return this.executeWithRetry(async () => {
      const response = await this.doFetch("/api/contexts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          language: options.language || "python",
          cwd: options.cwd || "/workspace",
          env_vars: options.envVars
        })
      });
      if (!response.ok) throw await this.parseErrorResponse(response);
      const data = await response.json();
      if (!data.success) throw new Error(`Failed to create context: ${JSON.stringify(data)}`);
      return {
        id: data.contextId,
        language: data.language,
        cwd: data.cwd || "/workspace",
        createdAt: new Date(data.timestamp),
        lastUsed: new Date(data.timestamp)
      };
    });
  }
  async runCodeStream(contextId, code, language, callbacks, timeoutMs) {
    return this.executeWithRetry(async () => {
      const response = await this.doFetch("/api/execute/code", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream"
        },
        body: JSON.stringify({
          context_id: contextId,
          code,
          language,
          ...timeoutMs !== void 0 && { timeout_ms: timeoutMs }
        })
      });
      if (!response.ok) throw await this.parseErrorResponse(response);
      if (!response.body) throw new Error("No response body for streaming execution");
      for await (const chunk of this.readLines(response.body)) await this.parseExecutionResult(chunk, callbacks);
    });
  }
  async listCodeContexts() {
    return this.executeWithRetry(async () => {
      const response = await this.doFetch("/api/contexts", {
        method: "GET",
        headers: { "Content-Type": "application/json" }
      });
      if (!response.ok) throw await this.parseErrorResponse(response);
      const data = await response.json();
      if (!data.success) throw new Error(`Failed to list contexts: ${JSON.stringify(data)}`);
      return data.contexts.map((ctx) => ({
        id: ctx.id,
        language: ctx.language,
        cwd: ctx.cwd || "/workspace",
        createdAt: new Date(data.timestamp),
        lastUsed: new Date(data.timestamp)
      }));
    });
  }
  async deleteCodeContext(contextId) {
    return this.executeWithRetry(async () => {
      const response = await this.doFetch(`/api/contexts/${contextId}`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" }
      });
      if (!response.ok) throw await this.parseErrorResponse(response);
    });
  }
  /**
  * Execute an operation with automatic retry for transient errors
  */
  async executeWithRetry(operation) {
    let lastError;
    for (let attempt = 0; attempt < this.maxRetries; attempt++) try {
      return await operation();
    } catch (error3) {
      this.logError("executeWithRetry", error3);
      lastError = error3;
      if (this.isRetryableError(error3)) {
        if (attempt < this.maxRetries - 1) {
          const delay = this.retryDelayMs * 2 ** attempt + Math.random() * 1e3;
          await new Promise((resolve) => setTimeout(resolve, delay));
          continue;
        }
      }
      throw error3;
    }
    throw lastError || /* @__PURE__ */ new Error("Execution failed after retries");
  }
  isRetryableError(error3) {
    if (error3 instanceof InterpreterNotReadyError) return true;
    if (error3 instanceof Error) return error3.message.includes("not ready") || error3.message.includes("initializing");
    return false;
  }
  async parseErrorResponse(response) {
    try {
      return createErrorFromResponse(await response.json());
    } catch {
      return createErrorFromResponse({
        code: ErrorCode.INTERNAL_ERROR,
        message: `HTTP ${response.status}: ${response.statusText}`,
        context: {},
        httpStatus: response.status,
        timestamp: (/* @__PURE__ */ new Date()).toISOString()
      });
    }
  }
  async *readLines(stream) {
    const reader = stream.getReader();
    let buffer = "";
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (value) buffer += new TextDecoder().decode(value);
        if (done) break;
        let newlineIdx = buffer.indexOf("\n");
        while (newlineIdx !== -1) {
          yield buffer.slice(0, newlineIdx);
          buffer = buffer.slice(newlineIdx + 1);
          newlineIdx = buffer.indexOf("\n");
        }
      }
      if (buffer.length > 0) yield buffer;
    } finally {
      reader.releaseLock();
    }
  }
  async parseExecutionResult(line, callbacks) {
    if (!line.trim()) return;
    if (!line.startsWith("data: ")) return;
    try {
      const jsonData = line.substring(6);
      const data = JSON.parse(jsonData);
      switch (data.type) {
        case "stdout":
          if (callbacks.onStdout && data.text) await callbacks.onStdout({
            text: data.text,
            timestamp: data.timestamp || Date.now()
          });
          break;
        case "stderr":
          if (callbacks.onStderr && data.text) await callbacks.onStderr({
            text: data.text,
            timestamp: data.timestamp || Date.now()
          });
          break;
        case "result":
          if (callbacks.onResult) {
            const result = new ResultImpl(data);
            await callbacks.onResult(result);
          }
          break;
        case "error":
          if (callbacks.onError) await callbacks.onError({
            name: data.ename || "Error",
            message: data.evalue || "Unknown error",
            traceback: data.traceback || []
          });
          break;
        case "execution_complete":
          break;
      }
    } catch (error3) {
      this.logError("parseExecutionResult", error3);
    }
  }
};
var PortClient = class extends BaseHttpClient {
  static {
    __name(this, "PortClient");
  }
  /**
  * Expose a port and get a preview URL
  * @param port - Port number to expose
  * @param sessionId - The session ID for this operation
  * @param name - Optional name for the port
  */
  async exposePort(port, sessionId, name) {
    try {
      const data = {
        port,
        sessionId,
        name
      };
      const response = await this.post("/api/expose-port", data);
      this.logSuccess("Port exposed", `${port} exposed at ${response.url}${name ? ` (${name})` : ""}`);
      return response;
    } catch (error3) {
      this.logError("exposePort", error3);
      throw error3;
    }
  }
  /**
  * Unexpose a port and remove its preview URL
  * @param port - Port number to unexpose
  * @param sessionId - The session ID for this operation
  */
  async unexposePort(port, sessionId) {
    try {
      const url = `/api/exposed-ports/${port}?session=${encodeURIComponent(sessionId)}`;
      const response = await this.delete(url);
      this.logSuccess("Port unexposed", `${port}`);
      return response;
    } catch (error3) {
      this.logError("unexposePort", error3);
      throw error3;
    }
  }
  /**
  * Get all currently exposed ports
  * @param sessionId - The session ID for this operation
  */
  async getExposedPorts(sessionId) {
    try {
      const url = `/api/exposed-ports?session=${encodeURIComponent(sessionId)}`;
      const response = await this.get(url);
      this.logSuccess("Exposed ports retrieved", `${response.ports.length} ports exposed`);
      return response;
    } catch (error3) {
      this.logError("getExposedPorts", error3);
      throw error3;
    }
  }
};
var ProcessClient = class extends BaseHttpClient {
  static {
    __name(this, "ProcessClient");
  }
  /**
  * Start a background process
  * @param command - Command to execute as a background process
  * @param sessionId - The session ID for this operation
  * @param options - Optional settings (processId)
  */
  async startProcess(command, sessionId, options) {
    try {
      const data = {
        command,
        sessionId,
        processId: options?.processId
      };
      const response = await this.post("/api/process/start", data);
      this.logSuccess("Process started", `${command} (ID: ${response.processId})`);
      return response;
    } catch (error3) {
      this.logError("startProcess", error3);
      throw error3;
    }
  }
  /**
  * List all processes (sandbox-scoped, not session-scoped)
  */
  async listProcesses() {
    try {
      const response = await this.get(`/api/process/list`);
      this.logSuccess("Processes listed", `${response.processes.length} processes`);
      return response;
    } catch (error3) {
      this.logError("listProcesses", error3);
      throw error3;
    }
  }
  /**
  * Get information about a specific process (sandbox-scoped, not session-scoped)
  * @param processId - ID of the process to retrieve
  */
  async getProcess(processId) {
    try {
      const url = `/api/process/${processId}`;
      const response = await this.get(url);
      this.logSuccess("Process retrieved", `ID: ${processId}`);
      return response;
    } catch (error3) {
      this.logError("getProcess", error3);
      throw error3;
    }
  }
  /**
  * Kill a specific process (sandbox-scoped, not session-scoped)
  * @param processId - ID of the process to kill
  */
  async killProcess(processId) {
    try {
      const url = `/api/process/${processId}`;
      const response = await this.delete(url);
      this.logSuccess("Process killed", `ID: ${processId}`);
      return response;
    } catch (error3) {
      this.logError("killProcess", error3);
      throw error3;
    }
  }
  /**
  * Kill all running processes (sandbox-scoped, not session-scoped)
  */
  async killAllProcesses() {
    try {
      const response = await this.delete(`/api/process/kill-all`);
      this.logSuccess("All processes killed", `${response.cleanedCount} processes terminated`);
      return response;
    } catch (error3) {
      this.logError("killAllProcesses", error3);
      throw error3;
    }
  }
  /**
  * Get logs from a specific process (sandbox-scoped, not session-scoped)
  * @param processId - ID of the process to get logs from
  */
  async getProcessLogs(processId) {
    try {
      const url = `/api/process/${processId}/logs`;
      const response = await this.get(url);
      this.logSuccess("Process logs retrieved", `ID: ${processId}, stdout: ${response.stdout.length} chars, stderr: ${response.stderr.length} chars`);
      return response;
    } catch (error3) {
      this.logError("getProcessLogs", error3);
      throw error3;
    }
  }
  /**
  * Stream logs from a specific process (sandbox-scoped, not session-scoped)
  * @param processId - ID of the process to stream logs from
  */
  async streamProcessLogs(processId) {
    try {
      const url = `/api/process/${processId}/stream`;
      const response = await this.doFetch(url, { method: "GET" });
      const stream = await this.handleStreamResponse(response);
      this.logSuccess("Process log stream started", `ID: ${processId}`);
      return stream;
    } catch (error3) {
      this.logError("streamProcessLogs", error3);
      throw error3;
    }
  }
};
var UtilityClient = class extends BaseHttpClient {
  static {
    __name(this, "UtilityClient");
  }
  /**
  * Ping the sandbox to check if it's responsive
  */
  async ping() {
    try {
      const response = await this.get("/api/ping");
      this.logSuccess("Ping successful", response.message);
      return response.message;
    } catch (error3) {
      this.logError("ping", error3);
      throw error3;
    }
  }
  /**
  * Get list of available commands in the sandbox environment
  */
  async getCommands() {
    try {
      const response = await this.get("/api/commands");
      this.logSuccess("Commands retrieved", `${response.count} commands available`);
      return response.availableCommands;
    } catch (error3) {
      this.logError("getCommands", error3);
      throw error3;
    }
  }
  /**
  * Create a new execution session
  * @param options - Session configuration (id, env, cwd)
  */
  async createSession(options) {
    try {
      const response = await this.post("/api/session/create", options);
      this.logSuccess("Session created", `ID: ${options.id}`);
      return response;
    } catch (error3) {
      this.logError("createSession", error3);
      throw error3;
    }
  }
  /**
  * Delete an execution session
  * @param sessionId - Session ID to delete
  */
  async deleteSession(sessionId) {
    try {
      const response = await this.post("/api/session/delete", { sessionId });
      this.logSuccess("Session deleted", `ID: ${sessionId}`);
      return response;
    } catch (error3) {
      this.logError("deleteSession", error3);
      throw error3;
    }
  }
  /**
  * Get the container version
  * Returns the version embedded in the Docker image during build
  */
  async getVersion() {
    try {
      const response = await this.get("/api/version");
      this.logSuccess("Version retrieved", response.version);
      return response.version;
    } catch (error3) {
      this.logger.debug("Failed to get container version (may be old container)", { error: error3 });
      return "unknown";
    }
  }
};
var SandboxClient = class {
  static {
    __name(this, "SandboxClient");
  }
  commands;
  files;
  processes;
  ports;
  git;
  interpreter;
  utils;
  constructor(options) {
    const clientOptions = {
      baseUrl: "http://localhost:3000",
      ...options
    };
    this.commands = new CommandClient(clientOptions);
    this.files = new FileClient(clientOptions);
    this.processes = new ProcessClient(clientOptions);
    this.ports = new PortClient(clientOptions);
    this.git = new GitClient(clientOptions);
    this.interpreter = new InterpreterClient(clientOptions);
    this.utils = new UtilityClient(clientOptions);
  }
};
var SecurityError = class extends Error {
  static {
    __name(this, "SecurityError");
  }
  constructor(message2, code) {
    super(message2);
    this.code = code;
    this.name = "SecurityError";
  }
};
function validatePort(port) {
  if (!Number.isInteger(port)) return false;
  if (port < 1024 || port > 65535) return false;
  if ([3e3, 8787].includes(port)) return false;
  return true;
}
__name(validatePort, "validatePort");
function sanitizeSandboxId(id) {
  if (!id || id.length > 63) throw new SecurityError("Sandbox ID must be 1-63 characters long.", "INVALID_SANDBOX_ID_LENGTH");
  if (id.startsWith("-") || id.endsWith("-")) throw new SecurityError("Sandbox ID cannot start or end with hyphens (DNS requirement).", "INVALID_SANDBOX_ID_HYPHENS");
  const reservedNames = [
    "www",
    "api",
    "admin",
    "root",
    "system",
    "cloudflare",
    "workers"
  ];
  const lowerCaseId = id.toLowerCase();
  if (reservedNames.includes(lowerCaseId)) throw new SecurityError(`Reserved sandbox ID '${id}' is not allowed.`, "RESERVED_SANDBOX_ID");
  return id;
}
__name(sanitizeSandboxId, "sanitizeSandboxId");
function validateLanguage(language) {
  if (!language) return;
  const supportedLanguages = [
    "python",
    "python3",
    "javascript",
    "js",
    "node",
    "typescript",
    "ts"
  ];
  const normalized = language.toLowerCase();
  if (!supportedLanguages.includes(normalized)) throw new SecurityError(`Unsupported language '${language}'. Supported languages: python, javascript, typescript`, "INVALID_LANGUAGE");
}
__name(validateLanguage, "validateLanguage");
var CodeInterpreter = class {
  static {
    __name(this, "CodeInterpreter");
  }
  interpreterClient;
  contexts = /* @__PURE__ */ new Map();
  constructor(sandbox) {
    this.interpreterClient = sandbox.client.interpreter;
  }
  /**
  * Create a new code execution context
  */
  async createCodeContext(options = {}) {
    validateLanguage(options.language);
    const context2 = await this.interpreterClient.createCodeContext(options);
    this.contexts.set(context2.id, context2);
    return context2;
  }
  /**
  * Run code with optional context
  */
  async runCode(code, options = {}) {
    let context2 = options.context;
    if (!context2) {
      const language = options.language || "python";
      context2 = await this.getOrCreateDefaultContext(language);
    }
    const execution = new Execution(code, context2);
    await this.interpreterClient.runCodeStream(context2.id, code, options.language, {
      onStdout: /* @__PURE__ */ __name((output) => {
        execution.logs.stdout.push(output.text);
        if (options.onStdout) return options.onStdout(output);
      }, "onStdout"),
      onStderr: /* @__PURE__ */ __name((output) => {
        execution.logs.stderr.push(output.text);
        if (options.onStderr) return options.onStderr(output);
      }, "onStderr"),
      onResult: /* @__PURE__ */ __name(async (result) => {
        execution.results.push(new ResultImpl(result));
        if (options.onResult) return options.onResult(result);
      }, "onResult"),
      onError: /* @__PURE__ */ __name((error3) => {
        execution.error = error3;
        if (options.onError) return options.onError(error3);
      }, "onError")
    });
    return execution;
  }
  /**
  * Run code and return a streaming response
  */
  async runCodeStream(code, options = {}) {
    let context2 = options.context;
    if (!context2) {
      const language = options.language || "python";
      context2 = await this.getOrCreateDefaultContext(language);
    }
    const response = await this.interpreterClient.doFetch("/api/execute/code", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream"
      },
      body: JSON.stringify({
        context_id: context2.id,
        code,
        language: options.language
      })
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: "Unknown error" }));
      throw new Error(errorData.error || `Failed to execute code: ${response.status}`);
    }
    if (!response.body) throw new Error("No response body for streaming execution");
    return response.body;
  }
  /**
  * List all code contexts
  */
  async listCodeContexts() {
    const contexts = await this.interpreterClient.listCodeContexts();
    for (const context2 of contexts) this.contexts.set(context2.id, context2);
    return contexts;
  }
  /**
  * Delete a code context
  */
  async deleteCodeContext(contextId) {
    await this.interpreterClient.deleteCodeContext(contextId);
    this.contexts.delete(contextId);
  }
  async getOrCreateDefaultContext(language) {
    for (const context2 of this.contexts.values()) if (context2.language === language) return context2;
    return this.createCodeContext({ language });
  }
};
function isLocalhostPattern(hostname) {
  if (hostname.startsWith("[")) if (hostname.includes("]:")) return hostname.substring(0, hostname.indexOf("]:") + 1) === "[::1]";
  else return hostname === "[::1]";
  if (hostname === "::1") return true;
  const hostPart = hostname.split(":")[0];
  return hostPart === "localhost" || hostPart === "127.0.0.1" || hostPart === "0.0.0.0";
}
__name(isLocalhostPattern, "isLocalhostPattern");
async function* parseSSEStream(stream, signal) {
  const reader = stream.getReader();
  const decoder2 = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      if (signal?.aborted) throw new Error("Operation was aborted");
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder2.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (line.trim() === "") continue;
        if (line.startsWith("data: ")) {
          const data = line.substring(6);
          if (data === "[DONE]" || data.trim() === "") continue;
          try {
            yield JSON.parse(data);
          } catch {
          }
        }
      }
    }
    if (buffer.trim() && buffer.startsWith("data: ")) {
      const data = buffer.substring(6);
      if (data !== "[DONE]" && data.trim()) try {
        yield JSON.parse(data);
      } catch {
      }
    }
  } finally {
    reader.releaseLock();
  }
}
__name(parseSSEStream, "parseSSEStream");
var SDK_VERSION = "0.4.18";
function getSandbox(ns, id, options) {
  const stub = getContainer(ns, id);
  stub.setSandboxName?.(id);
  if (options?.baseUrl) stub.setBaseUrl(options.baseUrl);
  if (options?.sleepAfter !== void 0) stub.setSleepAfter(options.sleepAfter);
  if (options?.keepAlive !== void 0) stub.setKeepAlive(options.keepAlive);
  return Object.assign(stub, { wsConnect: connect(stub) });
}
__name(getSandbox, "getSandbox");
function connect(stub) {
  return async (request, port) => {
    if (!validatePort(port)) throw new SecurityError(`Invalid or restricted port: ${port}. Ports must be in range 1024-65535 and not reserved.`);
    const portSwitchedRequest = switchPort(request, port);
    return await stub.fetch(portSwitchedRequest);
  };
}
__name(connect, "connect");
var Sandbox = class extends Container {
  static {
    __name(this, "Sandbox");
  }
  defaultPort = 3e3;
  sleepAfter = "10m";
  client;
  codeInterpreter;
  sandboxName = null;
  baseUrl = null;
  portTokens = /* @__PURE__ */ new Map();
  defaultSession = null;
  envVars = {};
  logger;
  keepAliveEnabled = false;
  constructor(ctx, env2) {
    super(ctx, env2);
    const envObj = env2;
    ["SANDBOX_LOG_LEVEL", "SANDBOX_LOG_FORMAT"].forEach((key) => {
      if (envObj?.[key]) this.envVars[key] = envObj[key];
    });
    this.logger = createLogger({
      component: "sandbox-do",
      sandboxId: this.ctx.id.toString()
    });
    this.client = new SandboxClient({
      logger: this.logger,
      port: 3e3,
      stub: this
    });
    this.codeInterpreter = new CodeInterpreter(this);
    this.ctx.blockConcurrencyWhile(async () => {
      this.sandboxName = await this.ctx.storage.get("sandboxName") || null;
      this.defaultSession = await this.ctx.storage.get("defaultSession") || null;
      const storedTokens = await this.ctx.storage.get("portTokens") || {};
      this.portTokens = /* @__PURE__ */ new Map();
      for (const [portStr, token] of Object.entries(storedTokens)) this.portTokens.set(parseInt(portStr, 10), token);
    });
  }
  async setSandboxName(name) {
    if (!this.sandboxName) {
      this.sandboxName = name;
      await this.ctx.storage.put("sandboxName", name);
    }
  }
  async setBaseUrl(baseUrl) {
    if (!this.baseUrl) {
      this.baseUrl = baseUrl;
      await this.ctx.storage.put("baseUrl", baseUrl);
    } else if (this.baseUrl !== baseUrl) throw new Error("Base URL already set and different from one previously provided");
  }
  async setSleepAfter(sleepAfter) {
    this.sleepAfter = sleepAfter;
  }
  async setKeepAlive(keepAlive) {
    this.keepAliveEnabled = keepAlive;
    if (keepAlive) this.logger.info("KeepAlive mode enabled - container will stay alive until explicitly destroyed");
    else this.logger.info("KeepAlive mode disabled - container will timeout normally");
  }
  async setEnvVars(envVars) {
    this.envVars = {
      ...this.envVars,
      ...envVars
    };
    if (this.defaultSession) for (const [key, value] of Object.entries(envVars)) {
      const exportCommand = `export ${key}='${value.replace(/'/g, "'\\''")}'`;
      const result = await this.client.commands.execute(exportCommand, this.defaultSession);
      if (result.exitCode !== 0) throw new Error(`Failed to set ${key}: ${result.stderr || "Unknown error"}`);
    }
  }
  /**
  * Cleanup and destroy the sandbox container
  */
  async destroy() {
    this.logger.info("Destroying sandbox container");
    await super.destroy();
  }
  onStart() {
    this.logger.debug("Sandbox started");
    this.checkVersionCompatibility().catch((error3) => {
      this.logger.error("Version compatibility check failed", error3 instanceof Error ? error3 : new Error(String(error3)));
    });
  }
  /**
  * Check if the container version matches the SDK version
  * Logs a warning if there's a mismatch
  */
  async checkVersionCompatibility() {
    try {
      const sdkVersion = SDK_VERSION;
      const containerVersion = await this.client.utils.getVersion();
      if (containerVersion === "unknown") {
        this.logger.warn("Container version check: Container version could not be determined. This may indicate an outdated container image. Please update your container to match SDK version " + sdkVersion);
        return;
      }
      if (containerVersion !== sdkVersion) {
        const message2 = `Version mismatch detected! SDK version (${sdkVersion}) does not match container version (${containerVersion}). This may cause compatibility issues. Please update your container image to version ${sdkVersion}`;
        this.logger.warn(message2);
      } else this.logger.debug("Version check passed", {
        sdkVersion,
        containerVersion
      });
    } catch (error3) {
      this.logger.debug("Version compatibility check encountered an error", { error: error3 instanceof Error ? error3.message : String(error3) });
    }
  }
  onStop() {
    this.logger.debug("Sandbox stopped");
  }
  onError(error3) {
    this.logger.error("Sandbox error", error3 instanceof Error ? error3 : new Error(String(error3)));
  }
  /**
  * Override onActivityExpired to prevent automatic shutdown when keepAlive is enabled
  * When keepAlive is disabled, calls parent implementation which stops the container
  */
  async onActivityExpired() {
    if (this.keepAliveEnabled) this.logger.debug("Activity expired but keepAlive is enabled - container will stay alive");
    else {
      this.logger.debug("Activity expired - stopping container");
      await super.onActivityExpired();
    }
  }
  async fetch(request) {
    const traceId = TraceContext.fromHeaders(request.headers) || TraceContext.generate();
    const requestLogger = this.logger.child({
      traceId,
      operation: "fetch"
    });
    return await runWithLogger(requestLogger, async () => {
      const url = new URL(request.url);
      if (!this.sandboxName && request.headers.has("X-Sandbox-Name")) {
        const name = request.headers.get("X-Sandbox-Name");
        this.sandboxName = name;
        await this.ctx.storage.put("sandboxName", name);
      }
      const upgradeHeader = request.headers.get("Upgrade");
      const connectionHeader = request.headers.get("Connection");
      if (upgradeHeader?.toLowerCase() === "websocket" && connectionHeader?.toLowerCase().includes("upgrade")) try {
        requestLogger.debug("WebSocket upgrade requested", {
          path: url.pathname,
          port: this.determinePort(url)
        });
        return await super.fetch(request);
      } catch (error3) {
        requestLogger.error("WebSocket connection failed", error3 instanceof Error ? error3 : new Error(String(error3)), { path: url.pathname });
        throw error3;
      }
      const port = this.determinePort(url);
      return await this.containerFetch(request, port);
    });
  }
  wsConnect(request, port) {
    throw new Error("Not implemented here to avoid RPC serialization issues");
  }
  determinePort(url) {
    const proxyMatch = url.pathname.match(/^\/proxy\/(\d+)/);
    if (proxyMatch) return parseInt(proxyMatch[1], 10);
    return 3e3;
  }
  /**
  * Ensure default session exists - lazy initialization
  * This is called automatically by all public methods that need a session
  *
  * The session is persisted to Durable Object storage to survive hot reloads
  * during development. If a session already exists in the container after reload,
  * we reuse it instead of trying to create a new one.
  */
  async ensureDefaultSession() {
    if (!this.defaultSession) {
      const sessionId = `sandbox-${this.sandboxName || "default"}`;
      try {
        await this.client.utils.createSession({
          id: sessionId,
          env: this.envVars || {},
          cwd: "/workspace"
        });
        this.defaultSession = sessionId;
        await this.ctx.storage.put("defaultSession", sessionId);
        this.logger.debug("Default session initialized", { sessionId });
      } catch (error3) {
        if (error3?.message?.includes("already exists")) {
          this.logger.debug("Reusing existing session after reload", { sessionId });
          this.defaultSession = sessionId;
          await this.ctx.storage.put("defaultSession", sessionId);
        } else throw error3;
      }
    }
    return this.defaultSession;
  }
  async exec(command, options) {
    const session = await this.ensureDefaultSession();
    return this.execWithSession(command, session, options);
  }
  /**
  * Internal session-aware exec implementation
  * Used by both public exec() and session wrappers
  */
  async execWithSession(command, sessionId, options) {
    const startTime = Date.now();
    const timestamp = (/* @__PURE__ */ new Date()).toISOString();
    try {
      if (options?.signal?.aborted) throw new Error("Operation was aborted");
      let result;
      if (options?.stream && options?.onOutput) result = await this.executeWithStreaming(command, sessionId, options, startTime, timestamp);
      else {
        const response = await this.client.commands.execute(command, sessionId);
        const duration = Date.now() - startTime;
        result = this.mapExecuteResponseToExecResult(response, duration, sessionId);
      }
      if (options?.onComplete) options.onComplete(result);
      return result;
    } catch (error3) {
      if (options?.onError && error3 instanceof Error) options.onError(error3);
      throw error3;
    }
  }
  async executeWithStreaming(command, sessionId, options, startTime, timestamp) {
    let stdout2 = "";
    let stderr2 = "";
    try {
      const stream = await this.client.commands.executeStream(command, sessionId);
      for await (const event of parseSSEStream(stream)) {
        if (options.signal?.aborted) throw new Error("Operation was aborted");
        switch (event.type) {
          case "stdout":
          case "stderr":
            if (event.data) {
              if (event.type === "stdout") stdout2 += event.data;
              if (event.type === "stderr") stderr2 += event.data;
              if (options.onOutput) options.onOutput(event.type, event.data);
            }
            break;
          case "complete": {
            const duration = Date.now() - startTime;
            return {
              success: (event.exitCode ?? 0) === 0,
              exitCode: event.exitCode ?? 0,
              stdout: stdout2,
              stderr: stderr2,
              command,
              duration,
              timestamp,
              sessionId
            };
          }
          case "error":
            throw new Error(event.data || "Command execution failed");
        }
      }
      throw new Error("Stream ended without completion event");
    } catch (error3) {
      if (options.signal?.aborted) throw new Error("Operation was aborted");
      throw error3;
    }
  }
  mapExecuteResponseToExecResult(response, duration, sessionId) {
    return {
      success: response.success,
      exitCode: response.exitCode,
      stdout: response.stdout,
      stderr: response.stderr,
      command: response.command,
      duration,
      timestamp: response.timestamp,
      sessionId
    };
  }
  /**
  * Create a Process domain object from HTTP client DTO
  * Centralizes process object creation with bound methods
  * This eliminates duplication across startProcess, listProcesses, getProcess, and session wrappers
  */
  createProcessFromDTO(data, sessionId) {
    return {
      id: data.id,
      pid: data.pid,
      command: data.command,
      status: data.status,
      startTime: typeof data.startTime === "string" ? new Date(data.startTime) : data.startTime,
      endTime: data.endTime ? typeof data.endTime === "string" ? new Date(data.endTime) : data.endTime : void 0,
      exitCode: data.exitCode,
      sessionId,
      kill: /* @__PURE__ */ __name(async (signal) => {
        await this.killProcess(data.id, signal);
      }, "kill"),
      getStatus: /* @__PURE__ */ __name(async () => {
        return (await this.getProcess(data.id))?.status || "error";
      }, "getStatus"),
      getLogs: /* @__PURE__ */ __name(async () => {
        const logs = await this.getProcessLogs(data.id);
        return {
          stdout: logs.stdout,
          stderr: logs.stderr
        };
      }, "getLogs")
    };
  }
  async startProcess(command, options, sessionId) {
    try {
      const session = sessionId ?? await this.ensureDefaultSession();
      const response = await this.client.processes.startProcess(command, session, { processId: options?.processId });
      const processObj = this.createProcessFromDTO({
        id: response.processId,
        pid: response.pid,
        command: response.command,
        status: "running",
        startTime: /* @__PURE__ */ new Date(),
        endTime: void 0,
        exitCode: void 0
      }, session);
      if (options?.onStart) options.onStart(processObj);
      return processObj;
    } catch (error3) {
      if (options?.onError && error3 instanceof Error) options.onError(error3);
      throw error3;
    }
  }
  async listProcesses(sessionId) {
    const session = sessionId ?? await this.ensureDefaultSession();
    return (await this.client.processes.listProcesses()).processes.map((processData) => this.createProcessFromDTO({
      id: processData.id,
      pid: processData.pid,
      command: processData.command,
      status: processData.status,
      startTime: processData.startTime,
      endTime: processData.endTime,
      exitCode: processData.exitCode
    }, session));
  }
  async getProcess(id, sessionId) {
    const session = sessionId ?? await this.ensureDefaultSession();
    const response = await this.client.processes.getProcess(id);
    if (!response.process) return null;
    const processData = response.process;
    return this.createProcessFromDTO({
      id: processData.id,
      pid: processData.pid,
      command: processData.command,
      status: processData.status,
      startTime: processData.startTime,
      endTime: processData.endTime,
      exitCode: processData.exitCode
    }, session);
  }
  async killProcess(id, signal, sessionId) {
    await this.client.processes.killProcess(id);
  }
  async killAllProcesses(sessionId) {
    return (await this.client.processes.killAllProcesses()).cleanedCount;
  }
  async cleanupCompletedProcesses(sessionId) {
    return 0;
  }
  async getProcessLogs(id, sessionId) {
    const response = await this.client.processes.getProcessLogs(id);
    return {
      stdout: response.stdout,
      stderr: response.stderr,
      processId: response.processId
    };
  }
  async execStream(command, options) {
    if (options?.signal?.aborted) throw new Error("Operation was aborted");
    const session = await this.ensureDefaultSession();
    return this.client.commands.executeStream(command, session);
  }
  /**
  * Internal session-aware execStream implementation
  */
  async execStreamWithSession(command, sessionId, options) {
    if (options?.signal?.aborted) throw new Error("Operation was aborted");
    return this.client.commands.executeStream(command, sessionId);
  }
  /**
  * Stream logs from a background process as a ReadableStream.
  */
  async streamProcessLogs(processId, options) {
    if (options?.signal?.aborted) throw new Error("Operation was aborted");
    return this.client.processes.streamProcessLogs(processId);
  }
  async gitCheckout(repoUrl, options) {
    const session = options.sessionId ?? await this.ensureDefaultSession();
    return this.client.git.checkout(repoUrl, session, {
      branch: options.branch,
      targetDir: options.targetDir
    });
  }
  async mkdir(path, options = {}) {
    const session = options.sessionId ?? await this.ensureDefaultSession();
    return this.client.files.mkdir(path, session, { recursive: options.recursive });
  }
  async writeFile(path, content, options = {}) {
    const session = options.sessionId ?? await this.ensureDefaultSession();
    return this.client.files.writeFile(path, content, session, { encoding: options.encoding });
  }
  async deleteFile(path, sessionId) {
    const session = sessionId ?? await this.ensureDefaultSession();
    return this.client.files.deleteFile(path, session);
  }
  async renameFile(oldPath, newPath, sessionId) {
    const session = sessionId ?? await this.ensureDefaultSession();
    return this.client.files.renameFile(oldPath, newPath, session);
  }
  async moveFile(sourcePath, destinationPath, sessionId) {
    const session = sessionId ?? await this.ensureDefaultSession();
    return this.client.files.moveFile(sourcePath, destinationPath, session);
  }
  async readFile(path, options = {}) {
    const session = options.sessionId ?? await this.ensureDefaultSession();
    return this.client.files.readFile(path, session, { encoding: options.encoding });
  }
  /**
  * Stream a file from the sandbox using Server-Sent Events
  * Returns a ReadableStream that can be consumed with streamFile() or collectFile() utilities
  * @param path - Path to the file to stream
  * @param options - Optional session ID
  */
  async readFileStream(path, options = {}) {
    const session = options.sessionId ?? await this.ensureDefaultSession();
    return this.client.files.readFileStream(path, session);
  }
  async listFiles(path, options) {
    const session = await this.ensureDefaultSession();
    return this.client.files.listFiles(path, session, options);
  }
  async exists(path, sessionId) {
    const session = sessionId ?? await this.ensureDefaultSession();
    return this.client.files.exists(path, session);
  }
  async exposePort(port, options) {
    if (options.hostname.endsWith(".workers.dev")) throw new CustomDomainRequiredError({
      code: ErrorCode.CUSTOM_DOMAIN_REQUIRED,
      message: `Port exposure requires a custom domain. .workers.dev domains do not support wildcard subdomains required for port proxying.`,
      context: { originalError: options.hostname },
      httpStatus: 400,
      timestamp: (/* @__PURE__ */ new Date()).toISOString()
    });
    const sessionId = await this.ensureDefaultSession();
    await this.client.ports.exposePort(port, sessionId, options?.name);
    if (!this.sandboxName) throw new Error("Sandbox name not available. Ensure sandbox is accessed through getSandbox()");
    const token = this.generatePortToken();
    this.portTokens.set(port, token);
    await this.persistPortTokens();
    return {
      url: this.constructPreviewUrl(port, this.sandboxName, options.hostname, token),
      port,
      name: options?.name
    };
  }
  async unexposePort(port) {
    if (!validatePort(port)) throw new SecurityError(`Invalid port number: ${port}. Must be between 1024-65535 and not reserved.`);
    const sessionId = await this.ensureDefaultSession();
    await this.client.ports.unexposePort(port, sessionId);
    if (this.portTokens.has(port)) {
      this.portTokens.delete(port);
      await this.persistPortTokens();
    }
  }
  async getExposedPorts(hostname) {
    const sessionId = await this.ensureDefaultSession();
    const response = await this.client.ports.getExposedPorts(sessionId);
    if (!this.sandboxName) throw new Error("Sandbox name not available. Ensure sandbox is accessed through getSandbox()");
    return response.ports.map((port) => {
      const token = this.portTokens.get(port.port);
      if (!token) throw new Error(`Port ${port.port} is exposed but has no token. This should not happen.`);
      return {
        url: this.constructPreviewUrl(port.port, this.sandboxName, hostname, token),
        port: port.port,
        status: port.status
      };
    });
  }
  async isPortExposed(port) {
    try {
      const sessionId = await this.ensureDefaultSession();
      return (await this.client.ports.getExposedPorts(sessionId)).ports.some((exposedPort) => exposedPort.port === port);
    } catch (error3) {
      this.logger.error("Error checking if port is exposed", error3 instanceof Error ? error3 : new Error(String(error3)), { port });
      return false;
    }
  }
  async validatePortToken(port, token) {
    if (!await this.isPortExposed(port)) return false;
    const storedToken = this.portTokens.get(port);
    if (!storedToken) {
      this.logger.error("Port is exposed but has no token - bug detected", void 0, { port });
      return false;
    }
    return storedToken === token;
  }
  generatePortToken() {
    const array = new Uint8Array(12);
    crypto.getRandomValues(array);
    return btoa(String.fromCharCode(...array)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "").toLowerCase();
  }
  async persistPortTokens() {
    const tokensObj = {};
    for (const [port, token] of this.portTokens.entries()) tokensObj[port.toString()] = token;
    await this.ctx.storage.put("portTokens", tokensObj);
  }
  constructPreviewUrl(port, sandboxId, hostname, token) {
    if (!validatePort(port)) throw new SecurityError(`Invalid port number: ${port}. Must be between 1024-65535 and not reserved.`);
    const sanitizedSandboxId = sanitizeSandboxId(sandboxId);
    if (isLocalhostPattern(hostname)) {
      const [host, portStr] = hostname.split(":");
      const mainPort = portStr || "80";
      try {
        const baseUrl = new URL(`http://${host}:${mainPort}`);
        baseUrl.hostname = `${port}-${sanitizedSandboxId}-${token}.${host}`;
        return baseUrl.toString();
      } catch (error3) {
        throw new SecurityError(`Failed to construct preview URL: ${error3 instanceof Error ? error3.message : "Unknown error"}`);
      }
    }
    try {
      const baseUrl = new URL(`https://${hostname}`);
      baseUrl.hostname = `${port}-${sanitizedSandboxId}-${token}.${hostname}`;
      return baseUrl.toString();
    } catch (error3) {
      throw new SecurityError(`Failed to construct preview URL: ${error3 instanceof Error ? error3.message : "Unknown error"}`);
    }
  }
  /**
  * Create isolated execution session for advanced use cases
  * Returns ExecutionSession with full sandbox API bound to specific session
  */
  async createSession(options) {
    const sessionId = options?.id || `session-${Date.now()}`;
    await this.client.utils.createSession({
      id: sessionId,
      env: options?.env,
      cwd: options?.cwd
    });
    return this.getSessionWrapper(sessionId);
  }
  /**
  * Get an existing session by ID
  * Returns ExecutionSession wrapper bound to the specified session
  *
  * This is useful for retrieving sessions across different requests/contexts
  * without storing the ExecutionSession object (which has RPC lifecycle limitations)
  *
  * @param sessionId - The ID of an existing session
  * @returns ExecutionSession wrapper bound to the session
  */
  async getSession(sessionId) {
    return this.getSessionWrapper(sessionId);
  }
  /**
  * Delete an execution session
  * Cleans up session resources and removes it from the container
  * Note: Cannot delete the default session. To reset the default session,
  * use sandbox.destroy() to terminate the entire sandbox.
  *
  * @param sessionId - The ID of the session to delete
  * @returns Result with success status, sessionId, and timestamp
  * @throws Error if attempting to delete the default session
  */
  async deleteSession(sessionId) {
    if (this.defaultSession && sessionId === this.defaultSession) throw new Error(`Cannot delete default session '${sessionId}'. Use sandbox.destroy() to terminate the sandbox.`);
    const response = await this.client.utils.deleteSession(sessionId);
    return {
      success: response.success,
      sessionId: response.sessionId,
      timestamp: response.timestamp
    };
  }
  /**
  * Internal helper to create ExecutionSession wrapper for a given sessionId
  * Used by both createSession and getSession
  */
  getSessionWrapper(sessionId) {
    return {
      id: sessionId,
      exec: /* @__PURE__ */ __name((command, options) => this.execWithSession(command, sessionId, options), "exec"),
      execStream: /* @__PURE__ */ __name((command, options) => this.execStreamWithSession(command, sessionId, options), "execStream"),
      startProcess: /* @__PURE__ */ __name((command, options) => this.startProcess(command, options, sessionId), "startProcess"),
      listProcesses: /* @__PURE__ */ __name(() => this.listProcesses(sessionId), "listProcesses"),
      getProcess: /* @__PURE__ */ __name((id) => this.getProcess(id, sessionId), "getProcess"),
      killProcess: /* @__PURE__ */ __name((id, signal) => this.killProcess(id, signal), "killProcess"),
      killAllProcesses: /* @__PURE__ */ __name(() => this.killAllProcesses(), "killAllProcesses"),
      cleanupCompletedProcesses: /* @__PURE__ */ __name(() => this.cleanupCompletedProcesses(), "cleanupCompletedProcesses"),
      getProcessLogs: /* @__PURE__ */ __name((id) => this.getProcessLogs(id), "getProcessLogs"),
      streamProcessLogs: /* @__PURE__ */ __name((processId, options) => this.streamProcessLogs(processId, options), "streamProcessLogs"),
      writeFile: /* @__PURE__ */ __name((path, content, options) => this.writeFile(path, content, {
        ...options,
        sessionId
      }), "writeFile"),
      readFile: /* @__PURE__ */ __name((path, options) => this.readFile(path, {
        ...options,
        sessionId
      }), "readFile"),
      readFileStream: /* @__PURE__ */ __name((path) => this.readFileStream(path, { sessionId }), "readFileStream"),
      mkdir: /* @__PURE__ */ __name((path, options) => this.mkdir(path, {
        ...options,
        sessionId
      }), "mkdir"),
      deleteFile: /* @__PURE__ */ __name((path) => this.deleteFile(path, sessionId), "deleteFile"),
      renameFile: /* @__PURE__ */ __name((oldPath, newPath) => this.renameFile(oldPath, newPath, sessionId), "renameFile"),
      moveFile: /* @__PURE__ */ __name((sourcePath, destPath) => this.moveFile(sourcePath, destPath, sessionId), "moveFile"),
      listFiles: /* @__PURE__ */ __name((path, options) => this.client.files.listFiles(path, sessionId, options), "listFiles"),
      exists: /* @__PURE__ */ __name((path) => this.exists(path, sessionId), "exists"),
      gitCheckout: /* @__PURE__ */ __name((repoUrl, options) => this.gitCheckout(repoUrl, {
        ...options,
        sessionId
      }), "gitCheckout"),
      setEnvVars: /* @__PURE__ */ __name(async (envVars) => {
        try {
          for (const [key, value] of Object.entries(envVars)) {
            const exportCommand = `export ${key}='${value.replace(/'/g, "'\\''")}'`;
            const result = await this.client.commands.execute(exportCommand, sessionId);
            if (result.exitCode !== 0) throw new Error(`Failed to set ${key}: ${result.stderr || "Unknown error"}`);
          }
        } catch (error3) {
          this.logger.error("Failed to set environment variables", error3 instanceof Error ? error3 : new Error(String(error3)), { sessionId });
          throw error3;
        }
      }, "setEnvVars"),
      createCodeContext: /* @__PURE__ */ __name((options) => this.codeInterpreter.createCodeContext(options), "createCodeContext"),
      runCode: /* @__PURE__ */ __name(async (code, options) => {
        return (await this.codeInterpreter.runCode(code, options)).toJSON();
      }, "runCode"),
      runCodeStream: /* @__PURE__ */ __name((code, options) => this.codeInterpreter.runCodeStream(code, options), "runCodeStream"),
      listCodeContexts: /* @__PURE__ */ __name(() => this.codeInterpreter.listCodeContexts(), "listCodeContexts"),
      deleteCodeContext: /* @__PURE__ */ __name((contextId) => this.codeInterpreter.deleteCodeContext(contextId), "deleteCodeContext")
    };
  }
  async createCodeContext(options) {
    return this.codeInterpreter.createCodeContext(options);
  }
  async runCode(code, options) {
    return (await this.codeInterpreter.runCode(code, options)).toJSON();
  }
  async runCodeStream(code, options) {
    return this.codeInterpreter.runCodeStream(code, options);
  }
  async listCodeContexts() {
    return this.codeInterpreter.listCodeContexts();
  }
  async deleteCodeContext(contextId) {
    return this.codeInterpreter.deleteCodeContext(contextId);
  }
};

// node_modules/jose/dist/webapi/lib/buffer_utils.js
var encoder = new TextEncoder();
var decoder = new TextDecoder();
var MAX_INT32 = 2 ** 32;
function concat(...buffers) {
  const size = buffers.reduce((acc, { length }) => acc + length, 0);
  const buf = new Uint8Array(size);
  let i = 0;
  for (const buffer of buffers) {
    buf.set(buffer, i);
    i += buffer.length;
  }
  return buf;
}
__name(concat, "concat");
function encode(string) {
  const bytes = new Uint8Array(string.length);
  for (let i = 0; i < string.length; i++) {
    const code = string.charCodeAt(i);
    if (code > 127) {
      throw new TypeError("non-ASCII string encountered in encode()");
    }
    bytes[i] = code;
  }
  return bytes;
}
__name(encode, "encode");

// node_modules/jose/dist/webapi/lib/base64.js
function decodeBase64(encoded) {
  if (Uint8Array.fromBase64) {
    return Uint8Array.fromBase64(encoded);
  }
  const binary = atob(encoded);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}
__name(decodeBase64, "decodeBase64");

// node_modules/jose/dist/webapi/util/base64url.js
function decode(input) {
  if (Uint8Array.fromBase64) {
    return Uint8Array.fromBase64(typeof input === "string" ? input : decoder.decode(input), {
      alphabet: "base64url"
    });
  }
  let encoded = input;
  if (encoded instanceof Uint8Array) {
    encoded = decoder.decode(encoded);
  }
  encoded = encoded.replace(/-/g, "+").replace(/_/g, "/");
  try {
    return decodeBase64(encoded);
  } catch {
    throw new TypeError("The input to be decoded is not correctly encoded.");
  }
}
__name(decode, "decode");

// node_modules/jose/dist/webapi/lib/crypto_key.js
var unusable = /* @__PURE__ */ __name((name, prop = "algorithm.name") => new TypeError(`CryptoKey does not support this operation, its ${prop} must be ${name}`), "unusable");
var isAlgorithm = /* @__PURE__ */ __name((algorithm, name) => algorithm.name === name, "isAlgorithm");
function getHashLength(hash) {
  return parseInt(hash.name.slice(4), 10);
}
__name(getHashLength, "getHashLength");
function checkHashLength(algorithm, expected) {
  const actual = getHashLength(algorithm.hash);
  if (actual !== expected)
    throw unusable(`SHA-${expected}`, "algorithm.hash");
}
__name(checkHashLength, "checkHashLength");
function getNamedCurve(alg) {
  switch (alg) {
    case "ES256":
      return "P-256";
    case "ES384":
      return "P-384";
    case "ES512":
      return "P-521";
    default:
      throw new Error("unreachable");
  }
}
__name(getNamedCurve, "getNamedCurve");
function checkUsage(key, usage) {
  if (usage && !key.usages.includes(usage)) {
    throw new TypeError(`CryptoKey does not support this operation, its usages must include ${usage}.`);
  }
}
__name(checkUsage, "checkUsage");
function checkSigCryptoKey(key, alg, usage) {
  switch (alg) {
    case "HS256":
    case "HS384":
    case "HS512": {
      if (!isAlgorithm(key.algorithm, "HMAC"))
        throw unusable("HMAC");
      checkHashLength(key.algorithm, parseInt(alg.slice(2), 10));
      break;
    }
    case "RS256":
    case "RS384":
    case "RS512": {
      if (!isAlgorithm(key.algorithm, "RSASSA-PKCS1-v1_5"))
        throw unusable("RSASSA-PKCS1-v1_5");
      checkHashLength(key.algorithm, parseInt(alg.slice(2), 10));
      break;
    }
    case "PS256":
    case "PS384":
    case "PS512": {
      if (!isAlgorithm(key.algorithm, "RSA-PSS"))
        throw unusable("RSA-PSS");
      checkHashLength(key.algorithm, parseInt(alg.slice(2), 10));
      break;
    }
    case "Ed25519":
    case "EdDSA": {
      if (!isAlgorithm(key.algorithm, "Ed25519"))
        throw unusable("Ed25519");
      break;
    }
    case "ML-DSA-44":
    case "ML-DSA-65":
    case "ML-DSA-87": {
      if (!isAlgorithm(key.algorithm, alg))
        throw unusable(alg);
      break;
    }
    case "ES256":
    case "ES384":
    case "ES512": {
      if (!isAlgorithm(key.algorithm, "ECDSA"))
        throw unusable("ECDSA");
      const expected = getNamedCurve(alg);
      const actual = key.algorithm.namedCurve;
      if (actual !== expected)
        throw unusable(expected, "algorithm.namedCurve");
      break;
    }
    default:
      throw new TypeError("CryptoKey does not support this operation");
  }
  checkUsage(key, usage);
}
__name(checkSigCryptoKey, "checkSigCryptoKey");

// node_modules/jose/dist/webapi/lib/invalid_key_input.js
function message(msg, actual, ...types) {
  types = types.filter(Boolean);
  if (types.length > 2) {
    const last = types.pop();
    msg += `one of type ${types.join(", ")}, or ${last}.`;
  } else if (types.length === 2) {
    msg += `one of type ${types[0]} or ${types[1]}.`;
  } else {
    msg += `of type ${types[0]}.`;
  }
  if (actual == null) {
    msg += ` Received ${actual}`;
  } else if (typeof actual === "function" && actual.name) {
    msg += ` Received function ${actual.name}`;
  } else if (typeof actual === "object" && actual != null) {
    if (actual.constructor?.name) {
      msg += ` Received an instance of ${actual.constructor.name}`;
    }
  }
  return msg;
}
__name(message, "message");
var invalidKeyInput = /* @__PURE__ */ __name((actual, ...types) => message("Key must be ", actual, ...types), "invalidKeyInput");
var withAlg = /* @__PURE__ */ __name((alg, actual, ...types) => message(`Key for the ${alg} algorithm must be `, actual, ...types), "withAlg");

// node_modules/jose/dist/webapi/util/errors.js
var JOSEError = class extends Error {
  static {
    __name(this, "JOSEError");
  }
  static code = "ERR_JOSE_GENERIC";
  code = "ERR_JOSE_GENERIC";
  constructor(message2, options) {
    super(message2, options);
    this.name = this.constructor.name;
    Error.captureStackTrace?.(this, this.constructor);
  }
};
var JWTClaimValidationFailed = class extends JOSEError {
  static {
    __name(this, "JWTClaimValidationFailed");
  }
  static code = "ERR_JWT_CLAIM_VALIDATION_FAILED";
  code = "ERR_JWT_CLAIM_VALIDATION_FAILED";
  claim;
  reason;
  payload;
  constructor(message2, payload, claim = "unspecified", reason = "unspecified") {
    super(message2, { cause: { claim, reason, payload } });
    this.claim = claim;
    this.reason = reason;
    this.payload = payload;
  }
};
var JWTExpired = class extends JOSEError {
  static {
    __name(this, "JWTExpired");
  }
  static code = "ERR_JWT_EXPIRED";
  code = "ERR_JWT_EXPIRED";
  claim;
  reason;
  payload;
  constructor(message2, payload, claim = "unspecified", reason = "unspecified") {
    super(message2, { cause: { claim, reason, payload } });
    this.claim = claim;
    this.reason = reason;
    this.payload = payload;
  }
};
var JOSEAlgNotAllowed = class extends JOSEError {
  static {
    __name(this, "JOSEAlgNotAllowed");
  }
  static code = "ERR_JOSE_ALG_NOT_ALLOWED";
  code = "ERR_JOSE_ALG_NOT_ALLOWED";
};
var JOSENotSupported = class extends JOSEError {
  static {
    __name(this, "JOSENotSupported");
  }
  static code = "ERR_JOSE_NOT_SUPPORTED";
  code = "ERR_JOSE_NOT_SUPPORTED";
};
var JWSInvalid = class extends JOSEError {
  static {
    __name(this, "JWSInvalid");
  }
  static code = "ERR_JWS_INVALID";
  code = "ERR_JWS_INVALID";
};
var JWTInvalid = class extends JOSEError {
  static {
    __name(this, "JWTInvalid");
  }
  static code = "ERR_JWT_INVALID";
  code = "ERR_JWT_INVALID";
};
var JWSSignatureVerificationFailed = class extends JOSEError {
  static {
    __name(this, "JWSSignatureVerificationFailed");
  }
  static code = "ERR_JWS_SIGNATURE_VERIFICATION_FAILED";
  code = "ERR_JWS_SIGNATURE_VERIFICATION_FAILED";
  constructor(message2 = "signature verification failed", options) {
    super(message2, options);
  }
};

// node_modules/jose/dist/webapi/lib/is_key_like.js
var isCryptoKey = /* @__PURE__ */ __name((key) => {
  if (key?.[Symbol.toStringTag] === "CryptoKey")
    return true;
  try {
    return key instanceof CryptoKey;
  } catch {
    return false;
  }
}, "isCryptoKey");
var isKeyObject = /* @__PURE__ */ __name((key) => key?.[Symbol.toStringTag] === "KeyObject", "isKeyObject");
var isKeyLike = /* @__PURE__ */ __name((key) => isCryptoKey(key) || isKeyObject(key), "isKeyLike");

// node_modules/jose/dist/webapi/lib/helpers.js
function decodeBase64url(value, label, ErrorClass) {
  try {
    return decode(value);
  } catch {
    throw new ErrorClass(`Failed to base64url decode the ${label}`);
  }
}
__name(decodeBase64url, "decodeBase64url");

// node_modules/jose/dist/webapi/lib/type_checks.js
var isObjectLike = /* @__PURE__ */ __name((value) => typeof value === "object" && value !== null, "isObjectLike");
function isObject(input) {
  if (!isObjectLike(input) || Object.prototype.toString.call(input) !== "[object Object]") {
    return false;
  }
  if (Object.getPrototypeOf(input) === null) {
    return true;
  }
  let proto = input;
  while (Object.getPrototypeOf(proto) !== null) {
    proto = Object.getPrototypeOf(proto);
  }
  return Object.getPrototypeOf(input) === proto;
}
__name(isObject, "isObject");
function isDisjoint(...headers) {
  const sources = headers.filter(Boolean);
  if (sources.length === 0 || sources.length === 1) {
    return true;
  }
  let acc;
  for (const header of sources) {
    const parameters = Object.keys(header);
    if (!acc || acc.size === 0) {
      acc = new Set(parameters);
      continue;
    }
    for (const parameter of parameters) {
      if (acc.has(parameter)) {
        return false;
      }
      acc.add(parameter);
    }
  }
  return true;
}
__name(isDisjoint, "isDisjoint");
var isJWK = /* @__PURE__ */ __name((key) => isObject(key) && typeof key.kty === "string", "isJWK");
var isPrivateJWK = /* @__PURE__ */ __name((key) => key.kty !== "oct" && (key.kty === "AKP" && typeof key.priv === "string" || typeof key.d === "string"), "isPrivateJWK");
var isPublicJWK = /* @__PURE__ */ __name((key) => key.kty !== "oct" && key.d === void 0 && key.priv === void 0, "isPublicJWK");
var isSecretJWK = /* @__PURE__ */ __name((key) => key.kty === "oct" && typeof key.k === "string", "isSecretJWK");

// node_modules/jose/dist/webapi/lib/signing.js
function checkKeyLength(alg, key) {
  if (alg.startsWith("RS") || alg.startsWith("PS")) {
    const { modulusLength } = key.algorithm;
    if (typeof modulusLength !== "number" || modulusLength < 2048) {
      throw new TypeError(`${alg} requires key modulusLength to be 2048 bits or larger`);
    }
  }
}
__name(checkKeyLength, "checkKeyLength");
function subtleAlgorithm(alg, algorithm) {
  const hash = `SHA-${alg.slice(-3)}`;
  switch (alg) {
    case "HS256":
    case "HS384":
    case "HS512":
      return { hash, name: "HMAC" };
    case "PS256":
    case "PS384":
    case "PS512":
      return { hash, name: "RSA-PSS", saltLength: parseInt(alg.slice(-3), 10) >> 3 };
    case "RS256":
    case "RS384":
    case "RS512":
      return { hash, name: "RSASSA-PKCS1-v1_5" };
    case "ES256":
    case "ES384":
    case "ES512":
      return { hash, name: "ECDSA", namedCurve: algorithm.namedCurve };
    case "Ed25519":
    case "EdDSA":
      return { name: "Ed25519" };
    case "ML-DSA-44":
    case "ML-DSA-65":
    case "ML-DSA-87":
      return { name: alg };
    default:
      throw new JOSENotSupported(`alg ${alg} is not supported either by JOSE or your javascript runtime`);
  }
}
__name(subtleAlgorithm, "subtleAlgorithm");
async function getSigKey(alg, key, usage) {
  if (key instanceof Uint8Array) {
    if (!alg.startsWith("HS")) {
      throw new TypeError(invalidKeyInput(key, "CryptoKey", "KeyObject", "JSON Web Key"));
    }
    return crypto.subtle.importKey("raw", key, { hash: `SHA-${alg.slice(-3)}`, name: "HMAC" }, false, [usage]);
  }
  checkSigCryptoKey(key, alg, usage);
  return key;
}
__name(getSigKey, "getSigKey");
async function verify(alg, key, signature, data) {
  const cryptoKey = await getSigKey(alg, key, "verify");
  checkKeyLength(alg, cryptoKey);
  const algorithm = subtleAlgorithm(alg, cryptoKey.algorithm);
  try {
    return await crypto.subtle.verify(algorithm, cryptoKey, signature, data);
  } catch {
    return false;
  }
}
__name(verify, "verify");

// node_modules/jose/dist/webapi/lib/jwk_to_key.js
var unsupportedAlg = 'Invalid or unsupported JWK "alg" (Algorithm) Parameter value';
function subtleMapping(jwk) {
  let algorithm;
  let keyUsages;
  switch (jwk.kty) {
    case "AKP": {
      switch (jwk.alg) {
        case "ML-DSA-44":
        case "ML-DSA-65":
        case "ML-DSA-87":
          algorithm = { name: jwk.alg };
          keyUsages = jwk.priv ? ["sign"] : ["verify"];
          break;
        default:
          throw new JOSENotSupported(unsupportedAlg);
      }
      break;
    }
    case "RSA": {
      switch (jwk.alg) {
        case "PS256":
        case "PS384":
        case "PS512":
          algorithm = { name: "RSA-PSS", hash: `SHA-${jwk.alg.slice(-3)}` };
          keyUsages = jwk.d ? ["sign"] : ["verify"];
          break;
        case "RS256":
        case "RS384":
        case "RS512":
          algorithm = { name: "RSASSA-PKCS1-v1_5", hash: `SHA-${jwk.alg.slice(-3)}` };
          keyUsages = jwk.d ? ["sign"] : ["verify"];
          break;
        case "RSA-OAEP":
        case "RSA-OAEP-256":
        case "RSA-OAEP-384":
        case "RSA-OAEP-512":
          algorithm = {
            name: "RSA-OAEP",
            hash: `SHA-${parseInt(jwk.alg.slice(-3), 10) || 1}`
          };
          keyUsages = jwk.d ? ["decrypt", "unwrapKey"] : ["encrypt", "wrapKey"];
          break;
        default:
          throw new JOSENotSupported(unsupportedAlg);
      }
      break;
    }
    case "EC": {
      switch (jwk.alg) {
        case "ES256":
        case "ES384":
        case "ES512":
          algorithm = {
            name: "ECDSA",
            namedCurve: { ES256: "P-256", ES384: "P-384", ES512: "P-521" }[jwk.alg]
          };
          keyUsages = jwk.d ? ["sign"] : ["verify"];
          break;
        case "ECDH-ES":
        case "ECDH-ES+A128KW":
        case "ECDH-ES+A192KW":
        case "ECDH-ES+A256KW":
          algorithm = { name: "ECDH", namedCurve: jwk.crv };
          keyUsages = jwk.d ? ["deriveBits"] : [];
          break;
        default:
          throw new JOSENotSupported(unsupportedAlg);
      }
      break;
    }
    case "OKP": {
      switch (jwk.alg) {
        case "Ed25519":
        case "EdDSA":
          algorithm = { name: "Ed25519" };
          keyUsages = jwk.d ? ["sign"] : ["verify"];
          break;
        case "ECDH-ES":
        case "ECDH-ES+A128KW":
        case "ECDH-ES+A192KW":
        case "ECDH-ES+A256KW":
          algorithm = { name: jwk.crv };
          keyUsages = jwk.d ? ["deriveBits"] : [];
          break;
        default:
          throw new JOSENotSupported(unsupportedAlg);
      }
      break;
    }
    default:
      throw new JOSENotSupported('Invalid or unsupported JWK "kty" (Key Type) Parameter value');
  }
  return { algorithm, keyUsages };
}
__name(subtleMapping, "subtleMapping");
async function jwkToKey(jwk) {
  if (!jwk.alg) {
    throw new TypeError('"alg" argument is required when "jwk.alg" is not present');
  }
  const { algorithm, keyUsages } = subtleMapping(jwk);
  const keyData = { ...jwk };
  if (keyData.kty !== "AKP") {
    delete keyData.alg;
  }
  delete keyData.use;
  return crypto.subtle.importKey("jwk", keyData, algorithm, jwk.ext ?? (jwk.d || jwk.priv ? false : true), jwk.key_ops ?? keyUsages);
}
__name(jwkToKey, "jwkToKey");

// node_modules/jose/dist/webapi/lib/normalize_key.js
var unusableForAlg = "given KeyObject instance cannot be used for this algorithm";
var cache;
var handleJWK = /* @__PURE__ */ __name(async (key, jwk, alg, freeze = false) => {
  cache ||= /* @__PURE__ */ new WeakMap();
  let cached = cache.get(key);
  if (cached?.[alg]) {
    return cached[alg];
  }
  const cryptoKey = await jwkToKey({ ...jwk, alg });
  if (freeze)
    Object.freeze(key);
  if (!cached) {
    cache.set(key, { [alg]: cryptoKey });
  } else {
    cached[alg] = cryptoKey;
  }
  return cryptoKey;
}, "handleJWK");
var handleKeyObject = /* @__PURE__ */ __name((keyObject, alg) => {
  cache ||= /* @__PURE__ */ new WeakMap();
  let cached = cache.get(keyObject);
  if (cached?.[alg]) {
    return cached[alg];
  }
  const isPublic = keyObject.type === "public";
  const extractable = isPublic ? true : false;
  let cryptoKey;
  if (keyObject.asymmetricKeyType === "x25519") {
    switch (alg) {
      case "ECDH-ES":
      case "ECDH-ES+A128KW":
      case "ECDH-ES+A192KW":
      case "ECDH-ES+A256KW":
        break;
      default:
        throw new TypeError(unusableForAlg);
    }
    cryptoKey = keyObject.toCryptoKey(keyObject.asymmetricKeyType, extractable, isPublic ? [] : ["deriveBits"]);
  }
  if (keyObject.asymmetricKeyType === "ed25519") {
    if (alg !== "EdDSA" && alg !== "Ed25519") {
      throw new TypeError(unusableForAlg);
    }
    cryptoKey = keyObject.toCryptoKey(keyObject.asymmetricKeyType, extractable, [
      isPublic ? "verify" : "sign"
    ]);
  }
  switch (keyObject.asymmetricKeyType) {
    case "ml-dsa-44":
    case "ml-dsa-65":
    case "ml-dsa-87": {
      if (alg !== keyObject.asymmetricKeyType.toUpperCase()) {
        throw new TypeError(unusableForAlg);
      }
      cryptoKey = keyObject.toCryptoKey(keyObject.asymmetricKeyType, extractable, [
        isPublic ? "verify" : "sign"
      ]);
    }
  }
  if (keyObject.asymmetricKeyType === "rsa") {
    let hash;
    switch (alg) {
      case "RSA-OAEP":
        hash = "SHA-1";
        break;
      case "RS256":
      case "PS256":
      case "RSA-OAEP-256":
        hash = "SHA-256";
        break;
      case "RS384":
      case "PS384":
      case "RSA-OAEP-384":
        hash = "SHA-384";
        break;
      case "RS512":
      case "PS512":
      case "RSA-OAEP-512":
        hash = "SHA-512";
        break;
      default:
        throw new TypeError(unusableForAlg);
    }
    if (alg.startsWith("RSA-OAEP")) {
      return keyObject.toCryptoKey({
        name: "RSA-OAEP",
        hash
      }, extractable, isPublic ? ["encrypt"] : ["decrypt"]);
    }
    cryptoKey = keyObject.toCryptoKey({
      name: alg.startsWith("PS") ? "RSA-PSS" : "RSASSA-PKCS1-v1_5",
      hash
    }, extractable, [isPublic ? "verify" : "sign"]);
  }
  if (keyObject.asymmetricKeyType === "ec") {
    const nist = /* @__PURE__ */ new Map([
      ["prime256v1", "P-256"],
      ["secp384r1", "P-384"],
      ["secp521r1", "P-521"]
    ]);
    const namedCurve = nist.get(keyObject.asymmetricKeyDetails?.namedCurve);
    if (!namedCurve) {
      throw new TypeError(unusableForAlg);
    }
    const expectedCurve = { ES256: "P-256", ES384: "P-384", ES512: "P-521" };
    if (expectedCurve[alg] && namedCurve === expectedCurve[alg]) {
      cryptoKey = keyObject.toCryptoKey({
        name: "ECDSA",
        namedCurve
      }, extractable, [isPublic ? "verify" : "sign"]);
    }
    if (alg.startsWith("ECDH-ES")) {
      cryptoKey = keyObject.toCryptoKey({
        name: "ECDH",
        namedCurve
      }, extractable, isPublic ? [] : ["deriveBits"]);
    }
  }
  if (!cryptoKey) {
    throw new TypeError(unusableForAlg);
  }
  if (!cached) {
    cache.set(keyObject, { [alg]: cryptoKey });
  } else {
    cached[alg] = cryptoKey;
  }
  return cryptoKey;
}, "handleKeyObject");
async function normalizeKey(key, alg) {
  if (key instanceof Uint8Array) {
    return key;
  }
  if (isCryptoKey(key)) {
    return key;
  }
  if (isKeyObject(key)) {
    if (key.type === "secret") {
      return key.export();
    }
    if ("toCryptoKey" in key && typeof key.toCryptoKey === "function") {
      try {
        return handleKeyObject(key, alg);
      } catch (err) {
        if (err instanceof TypeError) {
          throw err;
        }
      }
    }
    let jwk = key.export({ format: "jwk" });
    return handleJWK(key, jwk, alg);
  }
  if (isJWK(key)) {
    if (key.k) {
      return decode(key.k);
    }
    return handleJWK(key, key, alg, true);
  }
  throw new Error("unreachable");
}
__name(normalizeKey, "normalizeKey");

// node_modules/jose/dist/webapi/lib/validate_crit.js
function validateCrit(Err, recognizedDefault, recognizedOption, protectedHeader, joseHeader) {
  if (joseHeader.crit !== void 0 && protectedHeader?.crit === void 0) {
    throw new Err('"crit" (Critical) Header Parameter MUST be integrity protected');
  }
  if (!protectedHeader || protectedHeader.crit === void 0) {
    return /* @__PURE__ */ new Set();
  }
  if (!Array.isArray(protectedHeader.crit) || protectedHeader.crit.length === 0 || protectedHeader.crit.some((input) => typeof input !== "string" || input.length === 0)) {
    throw new Err('"crit" (Critical) Header Parameter MUST be an array of non-empty strings when present');
  }
  let recognized;
  if (recognizedOption !== void 0) {
    recognized = new Map([...Object.entries(recognizedOption), ...recognizedDefault.entries()]);
  } else {
    recognized = recognizedDefault;
  }
  for (const parameter of protectedHeader.crit) {
    if (!recognized.has(parameter)) {
      throw new JOSENotSupported(`Extension Header Parameter "${parameter}" is not recognized`);
    }
    if (joseHeader[parameter] === void 0) {
      throw new Err(`Extension Header Parameter "${parameter}" is missing`);
    }
    if (recognized.get(parameter) && protectedHeader[parameter] === void 0) {
      throw new Err(`Extension Header Parameter "${parameter}" MUST be integrity protected`);
    }
  }
  return new Set(protectedHeader.crit);
}
__name(validateCrit, "validateCrit");

// node_modules/jose/dist/webapi/lib/validate_algorithms.js
function validateAlgorithms(option, algorithms) {
  if (algorithms !== void 0 && (!Array.isArray(algorithms) || algorithms.some((s) => typeof s !== "string"))) {
    throw new TypeError(`"${option}" option must be an array of strings`);
  }
  if (!algorithms) {
    return void 0;
  }
  return new Set(algorithms);
}
__name(validateAlgorithms, "validateAlgorithms");

// node_modules/jose/dist/webapi/lib/check_key_type.js
var tag = /* @__PURE__ */ __name((key) => key?.[Symbol.toStringTag], "tag");
var jwkMatchesOp = /* @__PURE__ */ __name((alg, key, usage) => {
  if (key.use !== void 0) {
    let expected;
    switch (usage) {
      case "sign":
      case "verify":
        expected = "sig";
        break;
      case "encrypt":
      case "decrypt":
        expected = "enc";
        break;
    }
    if (key.use !== expected) {
      throw new TypeError(`Invalid key for this operation, its "use" must be "${expected}" when present`);
    }
  }
  if (key.alg !== void 0 && key.alg !== alg) {
    throw new TypeError(`Invalid key for this operation, its "alg" must be "${alg}" when present`);
  }
  if (Array.isArray(key.key_ops)) {
    let expectedKeyOp;
    switch (true) {
      case (usage === "sign" || usage === "verify"):
      case alg === "dir":
      case alg.includes("CBC-HS"):
        expectedKeyOp = usage;
        break;
      case alg.startsWith("PBES2"):
        expectedKeyOp = "deriveBits";
        break;
      case /^A\d{3}(?:GCM)?(?:KW)?$/.test(alg):
        if (!alg.includes("GCM") && alg.endsWith("KW")) {
          expectedKeyOp = usage === "encrypt" ? "wrapKey" : "unwrapKey";
        } else {
          expectedKeyOp = usage;
        }
        break;
      case (usage === "encrypt" && alg.startsWith("RSA")):
        expectedKeyOp = "wrapKey";
        break;
      case usage === "decrypt":
        expectedKeyOp = alg.startsWith("RSA") ? "unwrapKey" : "deriveBits";
        break;
    }
    if (expectedKeyOp && key.key_ops?.includes?.(expectedKeyOp) === false) {
      throw new TypeError(`Invalid key for this operation, its "key_ops" must include "${expectedKeyOp}" when present`);
    }
  }
  return true;
}, "jwkMatchesOp");
var symmetricTypeCheck = /* @__PURE__ */ __name((alg, key, usage) => {
  if (key instanceof Uint8Array)
    return;
  if (isJWK(key)) {
    if (isSecretJWK(key) && jwkMatchesOp(alg, key, usage))
      return;
    throw new TypeError(`JSON Web Key for symmetric algorithms must have JWK "kty" (Key Type) equal to "oct" and the JWK "k" (Key Value) present`);
  }
  if (!isKeyLike(key)) {
    throw new TypeError(withAlg(alg, key, "CryptoKey", "KeyObject", "JSON Web Key", "Uint8Array"));
  }
  if (key.type !== "secret") {
    throw new TypeError(`${tag(key)} instances for symmetric algorithms must be of type "secret"`);
  }
}, "symmetricTypeCheck");
var asymmetricTypeCheck = /* @__PURE__ */ __name((alg, key, usage) => {
  if (isJWK(key)) {
    switch (usage) {
      case "decrypt":
      case "sign":
        if (isPrivateJWK(key) && jwkMatchesOp(alg, key, usage))
          return;
        throw new TypeError(`JSON Web Key for this operation must be a private JWK`);
      case "encrypt":
      case "verify":
        if (isPublicJWK(key) && jwkMatchesOp(alg, key, usage))
          return;
        throw new TypeError(`JSON Web Key for this operation must be a public JWK`);
    }
  }
  if (!isKeyLike(key)) {
    throw new TypeError(withAlg(alg, key, "CryptoKey", "KeyObject", "JSON Web Key"));
  }
  if (key.type === "secret") {
    throw new TypeError(`${tag(key)} instances for asymmetric algorithms must not be of type "secret"`);
  }
  if (key.type === "public") {
    switch (usage) {
      case "sign":
        throw new TypeError(`${tag(key)} instances for asymmetric algorithm signing must be of type "private"`);
      case "decrypt":
        throw new TypeError(`${tag(key)} instances for asymmetric algorithm decryption must be of type "private"`);
    }
  }
  if (key.type === "private") {
    switch (usage) {
      case "verify":
        throw new TypeError(`${tag(key)} instances for asymmetric algorithm verifying must be of type "public"`);
      case "encrypt":
        throw new TypeError(`${tag(key)} instances for asymmetric algorithm encryption must be of type "public"`);
    }
  }
}, "asymmetricTypeCheck");
function checkKeyType(alg, key, usage) {
  switch (alg.substring(0, 2)) {
    case "A1":
    case "A2":
    case "di":
    case "HS":
    case "PB":
      symmetricTypeCheck(alg, key, usage);
      break;
    default:
      asymmetricTypeCheck(alg, key, usage);
  }
}
__name(checkKeyType, "checkKeyType");

// node_modules/jose/dist/webapi/jws/flattened/verify.js
async function flattenedVerify(jws, key, options) {
  if (!isObject(jws)) {
    throw new JWSInvalid("Flattened JWS must be an object");
  }
  if (jws.protected === void 0 && jws.header === void 0) {
    throw new JWSInvalid('Flattened JWS must have either of the "protected" or "header" members');
  }
  if (jws.protected !== void 0 && typeof jws.protected !== "string") {
    throw new JWSInvalid("JWS Protected Header incorrect type");
  }
  if (jws.payload === void 0) {
    throw new JWSInvalid("JWS Payload missing");
  }
  if (typeof jws.signature !== "string") {
    throw new JWSInvalid("JWS Signature missing or incorrect type");
  }
  if (jws.header !== void 0 && !isObject(jws.header)) {
    throw new JWSInvalid("JWS Unprotected Header incorrect type");
  }
  let parsedProt = {};
  if (jws.protected) {
    try {
      const protectedHeader = decode(jws.protected);
      parsedProt = JSON.parse(decoder.decode(protectedHeader));
    } catch {
      throw new JWSInvalid("JWS Protected Header is invalid");
    }
  }
  if (!isDisjoint(parsedProt, jws.header)) {
    throw new JWSInvalid("JWS Protected and JWS Unprotected Header Parameter names must be disjoint");
  }
  const joseHeader = {
    ...parsedProt,
    ...jws.header
  };
  const extensions = validateCrit(JWSInvalid, /* @__PURE__ */ new Map([["b64", true]]), options?.crit, parsedProt, joseHeader);
  let b64 = true;
  if (extensions.has("b64")) {
    b64 = parsedProt.b64;
    if (typeof b64 !== "boolean") {
      throw new JWSInvalid('The "b64" (base64url-encode payload) Header Parameter must be a boolean');
    }
  }
  const { alg } = joseHeader;
  if (typeof alg !== "string" || !alg) {
    throw new JWSInvalid('JWS "alg" (Algorithm) Header Parameter missing or invalid');
  }
  const algorithms = options && validateAlgorithms("algorithms", options.algorithms);
  if (algorithms && !algorithms.has(alg)) {
    throw new JOSEAlgNotAllowed('"alg" (Algorithm) Header Parameter value not allowed');
  }
  if (b64) {
    if (typeof jws.payload !== "string") {
      throw new JWSInvalid("JWS Payload must be a string");
    }
  } else if (typeof jws.payload !== "string" && !(jws.payload instanceof Uint8Array)) {
    throw new JWSInvalid("JWS Payload must be a string or an Uint8Array instance");
  }
  let resolvedKey = false;
  if (typeof key === "function") {
    key = await key(parsedProt, jws);
    resolvedKey = true;
  }
  checkKeyType(alg, key, "verify");
  const data = concat(jws.protected !== void 0 ? encode(jws.protected) : new Uint8Array(), encode("."), typeof jws.payload === "string" ? b64 ? encode(jws.payload) : encoder.encode(jws.payload) : jws.payload);
  const signature = decodeBase64url(jws.signature, "signature", JWSInvalid);
  const k = await normalizeKey(key, alg);
  const verified = await verify(alg, k, signature, data);
  if (!verified) {
    throw new JWSSignatureVerificationFailed();
  }
  let payload;
  if (b64) {
    payload = decodeBase64url(jws.payload, "payload", JWSInvalid);
  } else if (typeof jws.payload === "string") {
    payload = encoder.encode(jws.payload);
  } else {
    payload = jws.payload;
  }
  const result = { payload };
  if (jws.protected !== void 0) {
    result.protectedHeader = parsedProt;
  }
  if (jws.header !== void 0) {
    result.unprotectedHeader = jws.header;
  }
  if (resolvedKey) {
    return { ...result, key: k };
  }
  return result;
}
__name(flattenedVerify, "flattenedVerify");

// node_modules/jose/dist/webapi/jws/compact/verify.js
async function compactVerify(jws, key, options) {
  if (jws instanceof Uint8Array) {
    jws = decoder.decode(jws);
  }
  if (typeof jws !== "string") {
    throw new JWSInvalid("Compact JWS must be a string or Uint8Array");
  }
  const { 0: protectedHeader, 1: payload, 2: signature, length } = jws.split(".");
  if (length !== 3) {
    throw new JWSInvalid("Invalid Compact JWS");
  }
  const verified = await flattenedVerify({ payload, protected: protectedHeader, signature }, key, options);
  const result = { payload: verified.payload, protectedHeader: verified.protectedHeader };
  if (typeof key === "function") {
    return { ...result, key: verified.key };
  }
  return result;
}
__name(compactVerify, "compactVerify");

// node_modules/jose/dist/webapi/lib/jwt_claims_set.js
var epoch = /* @__PURE__ */ __name((date) => Math.floor(date.getTime() / 1e3), "epoch");
var minute = 60;
var hour = minute * 60;
var day = hour * 24;
var week = day * 7;
var year = day * 365.25;
var REGEX = /^(\+|\-)? ?(\d+|\d+\.\d+) ?(seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h|days?|d|weeks?|w|years?|yrs?|y)(?: (ago|from now))?$/i;
function secs(str) {
  const matched = REGEX.exec(str);
  if (!matched || matched[4] && matched[1]) {
    throw new TypeError("Invalid time period format");
  }
  const value = parseFloat(matched[2]);
  const unit = matched[3].toLowerCase();
  let numericDate;
  switch (unit) {
    case "sec":
    case "secs":
    case "second":
    case "seconds":
    case "s":
      numericDate = Math.round(value);
      break;
    case "minute":
    case "minutes":
    case "min":
    case "mins":
    case "m":
      numericDate = Math.round(value * minute);
      break;
    case "hour":
    case "hours":
    case "hr":
    case "hrs":
    case "h":
      numericDate = Math.round(value * hour);
      break;
    case "day":
    case "days":
    case "d":
      numericDate = Math.round(value * day);
      break;
    case "week":
    case "weeks":
    case "w":
      numericDate = Math.round(value * week);
      break;
    default:
      numericDate = Math.round(value * year);
      break;
  }
  if (matched[1] === "-" || matched[4] === "ago") {
    return -numericDate;
  }
  return numericDate;
}
__name(secs, "secs");
var normalizeTyp = /* @__PURE__ */ __name((value) => {
  if (value.includes("/")) {
    return value.toLowerCase();
  }
  return `application/${value.toLowerCase()}`;
}, "normalizeTyp");
var checkAudiencePresence = /* @__PURE__ */ __name((audPayload, audOption) => {
  if (typeof audPayload === "string") {
    return audOption.includes(audPayload);
  }
  if (Array.isArray(audPayload)) {
    return audOption.some(Set.prototype.has.bind(new Set(audPayload)));
  }
  return false;
}, "checkAudiencePresence");
function validateClaimsSet(protectedHeader, encodedPayload, options = {}) {
  let payload;
  try {
    payload = JSON.parse(decoder.decode(encodedPayload));
  } catch {
  }
  if (!isObject(payload)) {
    throw new JWTInvalid("JWT Claims Set must be a top-level JSON object");
  }
  const { typ } = options;
  if (typ && (typeof protectedHeader.typ !== "string" || normalizeTyp(protectedHeader.typ) !== normalizeTyp(typ))) {
    throw new JWTClaimValidationFailed('unexpected "typ" JWT header value', payload, "typ", "check_failed");
  }
  const { requiredClaims = [], issuer, subject, audience, maxTokenAge } = options;
  const presenceCheck = [...requiredClaims];
  if (maxTokenAge !== void 0)
    presenceCheck.push("iat");
  if (audience !== void 0)
    presenceCheck.push("aud");
  if (subject !== void 0)
    presenceCheck.push("sub");
  if (issuer !== void 0)
    presenceCheck.push("iss");
  for (const claim of new Set(presenceCheck.reverse())) {
    if (!(claim in payload)) {
      throw new JWTClaimValidationFailed(`missing required "${claim}" claim`, payload, claim, "missing");
    }
  }
  if (issuer && !(Array.isArray(issuer) ? issuer : [issuer]).includes(payload.iss)) {
    throw new JWTClaimValidationFailed('unexpected "iss" claim value', payload, "iss", "check_failed");
  }
  if (subject && payload.sub !== subject) {
    throw new JWTClaimValidationFailed('unexpected "sub" claim value', payload, "sub", "check_failed");
  }
  if (audience && !checkAudiencePresence(payload.aud, typeof audience === "string" ? [audience] : audience)) {
    throw new JWTClaimValidationFailed('unexpected "aud" claim value', payload, "aud", "check_failed");
  }
  let tolerance;
  switch (typeof options.clockTolerance) {
    case "string":
      tolerance = secs(options.clockTolerance);
      break;
    case "number":
      tolerance = options.clockTolerance;
      break;
    case "undefined":
      tolerance = 0;
      break;
    default:
      throw new TypeError("Invalid clockTolerance option type");
  }
  const { currentDate } = options;
  const now = epoch(currentDate || /* @__PURE__ */ new Date());
  if ((payload.iat !== void 0 || maxTokenAge) && typeof payload.iat !== "number") {
    throw new JWTClaimValidationFailed('"iat" claim must be a number', payload, "iat", "invalid");
  }
  if (payload.nbf !== void 0) {
    if (typeof payload.nbf !== "number") {
      throw new JWTClaimValidationFailed('"nbf" claim must be a number', payload, "nbf", "invalid");
    }
    if (payload.nbf > now + tolerance) {
      throw new JWTClaimValidationFailed('"nbf" claim timestamp check failed', payload, "nbf", "check_failed");
    }
  }
  if (payload.exp !== void 0) {
    if (typeof payload.exp !== "number") {
      throw new JWTClaimValidationFailed('"exp" claim must be a number', payload, "exp", "invalid");
    }
    if (payload.exp <= now - tolerance) {
      throw new JWTExpired('"exp" claim timestamp check failed', payload, "exp", "check_failed");
    }
  }
  if (maxTokenAge) {
    const age = now - payload.iat;
    const max = typeof maxTokenAge === "number" ? maxTokenAge : secs(maxTokenAge);
    if (age - tolerance > max) {
      throw new JWTExpired('"iat" claim timestamp check failed (too far in the past)', payload, "iat", "check_failed");
    }
    if (age < 0 - tolerance) {
      throw new JWTClaimValidationFailed('"iat" claim timestamp check failed (it should be in the past)', payload, "iat", "check_failed");
    }
  }
  return payload;
}
__name(validateClaimsSet, "validateClaimsSet");

// node_modules/jose/dist/webapi/jwt/verify.js
async function jwtVerify(jwt, key, options) {
  const verified = await compactVerify(jwt, key, options);
  if (verified.protectedHeader.crit?.includes("b64") && verified.protectedHeader.b64 === false) {
    throw new JWTInvalid("JWTs MUST NOT use unencoded payload");
  }
  const payload = validateClaimsSet(verified.protectedHeader, verified.payload, options);
  const result = { payload, protectedHeader: verified.protectedHeader };
  if (typeof key === "function") {
    return { ...result, key: verified.key };
  }
  return result;
}
__name(jwtVerify, "jwtVerify");

// src/helpers.ts
function extractVersion(output, tool) {
  const match2 = output.match(new RegExp(`${tool}[\\s/v]+([\\d.]+)`));
  return match2?.[1] ?? "unknown";
}
__name(extractVersion, "extractVersion");
var SECRET_KEYS = Object.freeze([
  "ANTHROPIC_API_KEY",
  "OPENAI_API_KEY",
  "GITHUB_TOKEN"
]);
function buildEnvVars(anthropicKey, openaiKey, extra) {
  const vars = {};
  const secrets = {
    ANTHROPIC_API_KEY: anthropicKey
  };
  if (openaiKey) {
    secrets.OPENAI_API_KEY = openaiKey;
  }
  if (extra) {
    for (const [key, value] of Object.entries(extra)) {
      if (SECRET_KEYS.includes(key)) {
        secrets[key] = value;
      } else {
        vars[key] = value;
      }
    }
  }
  return { vars, secrets };
}
__name(buildEnvVars, "buildEnvVars");
function shellEscape(s) {
  return "'" + s.replace(/'/g, "'\\''") + "'";
}
__name(shellEscape, "shellEscape");
function validatePath(path) {
  if (!path.startsWith("/workspace")) return false;
  if (path.includes("..")) return false;
  if (!/^[\w./-]+$/.test(path)) return false;
  return true;
}
__name(validatePath, "validatePath");
async function getVersions(sb) {
  const [pixlResult, claudeResult, nodeResult, pythonResult] = await Promise.all([
    sb.exec("pixl --version"),
    sb.exec("claude --version"),
    sb.exec("node --version"),
    sb.exec("python3 --version")
  ]);
  return {
    pixl: extractVersion(pixlResult.stdout || pixlResult.stderr, "pixl"),
    claude: extractVersion(
      claudeResult.stdout || claudeResult.stderr,
      "claude"
    ),
    node: extractVersion(nodeResult.stdout || nodeResult.stderr, "node"),
    python: extractVersion(
      pythonResult.stdout || pythonResult.stderr,
      "Python"
    )
  };
}
__name(getVersions, "getVersions");
async function getGitInfo(sb) {
  const [branchResult, commitResult, statusResult, remoteResult] = await Promise.all([
    sb.exec("git -C /workspace branch --show-current 2>/dev/null || echo ''"),
    sb.exec(
      "git -C /workspace rev-parse --short HEAD 2>/dev/null || echo ''"
    ),
    sb.exec("git -C /workspace status --porcelain 2>/dev/null || echo ''"),
    sb.exec(
      "git -C /workspace remote get-url origin 2>/dev/null || echo ''"
    )
  ]);
  return {
    branch: branchResult.stdout.trim() || "main",
    commit: commitResult.stdout.trim() || "",
    dirty: statusResult.stdout.trim().length > 0,
    remoteUrl: remoteResult.stdout.trim() || null
  };
}
__name(getGitInfo, "getGitInfo");
async function getProjectInfo(sb) {
  const configResult = await sb.exec(
    "test -f /workspace/.pixl/config.json && echo yes || echo no"
  );
  const initialized = configResult.stdout.trim() === "yes";
  if (!initialized) {
    return { initialized, sessions: 0, workflows: 0 };
  }
  const [sessionsResult, workflowsResult] = await Promise.all([
    sb.exec(
      'pixl session list --json 2>/dev/null | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0'
    ),
    sb.exec("ls /workspace/.pixl/workflows/*.yaml 2>/dev/null | wc -l")
  ]);
  return {
    initialized,
    sessions: parseInt(sessionsResult.stdout.trim()) || 0,
    workflows: parseInt(workflowsResult.stdout.trim()) || 0
  };
}
__name(getProjectInfo, "getProjectInfo");

// src/usage.ts
var OPS_LOG = "/workspace/.pixl/sandbox-ops.jsonl";
async function logOperation(sb, entry) {
  try {
    const line = JSON.stringify(entry);
    await sb.exec(`mkdir -p /workspace/.pixl && echo '${line.replace(/'/g, "'\\''")}' >> ${OPS_LOG}`, {
      timeout: 5e3
    });
  } catch {
  }
}
__name(logOperation, "logOperation");
async function readUsage(sb) {
  const result = await sb.exec(`cat ${OPS_LOG} 2>/dev/null || echo ""`, {
    timeout: 5e3
  });
  const lines = result.stdout.trim().split("\n").filter(Boolean);
  const operations = [];
  for (const line of lines) {
    try {
      operations.push(JSON.parse(line));
    } catch {
    }
  }
  const byOp = {};
  let successful = 0;
  let failed = 0;
  for (const op of operations) {
    if (op.success) successful++;
    else failed++;
    if (!byOp[op.operation]) {
      byOp[op.operation] = { count: 0, total_ms: 0, errors: 0 };
    }
    byOp[op.operation].count++;
    byOp[op.operation].total_ms += op.duration_ms;
    if (!op.success) byOp[op.operation].errors++;
  }
  const by_operation = {};
  for (const [key, val] of Object.entries(byOp)) {
    by_operation[key] = {
      count: val.count,
      avg_ms: Math.round(val.total_ms / val.count),
      errors: val.errors
    };
  }
  return {
    total_operations: operations.length,
    successful,
    failed,
    operations,
    by_operation
  };
}
__name(readUsage, "readUsage");
async function timed(fn) {
  const start = Date.now();
  const result = await fn();
  return { result, duration_ms: Date.now() - start };
}
__name(timed, "timed");

// src/router.ts
var SCOPE_LEVEL = {
  read: 1,
  write: 2,
  admin: 3
};
function isValidScope(value) {
  return value === "read" || value === "write" || value === "admin";
}
__name(isValidScope, "isValidScope");
function requireScope(c, required) {
  const current = c.get("scope") ?? "admin";
  return SCOPE_LEVEL[current] >= SCOPE_LEVEL[required];
}
__name(requireScope, "requireScope");
var app = new Hono2();
app.use("*", async (c, next) => {
  const allowedOrigins = c.env.ALLOWED_ORIGINS;
  const origin = allowedOrigins ? allowedOrigins.split(",").map((o) => o.trim()) : "*";
  const middleware = cors({ origin });
  return middleware(c, next);
});
app.use("*", bodyLimit({ maxSize: 10 * 1024 * 1024 }));
app.use("*", async (c, next) => {
  if (c.req.path === "/health") return next();
  const authHeader = c.req.header("Authorization");
  if (!authHeader?.startsWith("Bearer ")) {
    return c.json({ error: "unauthorized" }, 401);
  }
  const token = authHeader.slice(7);
  if (c.env.JWT_SECRET) {
    try {
      const secret = new TextEncoder().encode(c.env.JWT_SECRET);
      const { payload } = await jwtVerify(token, secret, {
        algorithms: ["HS256"],
        issuer: "pixl-cli"
      });
      c.set("jwtPayload", payload);
      const scope = isValidScope(payload.scope) ? payload.scope : "admin";
      c.set("scope", scope);
      await next();
      return;
    } catch {
    }
  }
  if (c.env.SANDBOX_API_KEY && token === c.env.SANDBOX_API_KEY) {
    c.set("scope", "admin");
    await next();
    return;
  }
  return c.json({ error: "forbidden" }, 403);
});
app.get("/health", (c) => c.json({ status: "ok" }));
var rateLimitMap = /* @__PURE__ */ new Map();
var RATE_LIMIT = 60;
var RATE_WINDOW_MS = 6e4;
app.use("/sandboxes/*", async (c, next) => {
  const ip = c.req.header("cf-connecting-ip") || c.req.header("x-forwarded-for") || "unknown";
  const now = Date.now();
  const entry = rateLimitMap.get(ip);
  if (!entry || now > entry.resetAt) {
    rateLimitMap.set(ip, { count: 1, resetAt: now + RATE_WINDOW_MS });
  } else {
    entry.count++;
    if (entry.count > RATE_LIMIT) {
      return c.json({ error: "Rate limit exceeded" }, 429);
    }
  }
  await next();
});
app.use("/sandboxes/*", async (c, next) => {
  const method = c.req.method;
  if (method === "POST" || method === "DELETE") {
    const path = new URL(c.req.url).pathname;
    const ip = c.req.header("cf-connecting-ip") || c.req.header("x-forwarded-for") || "unknown";
    console.log(
      `[audit] ${method} ${path} from=${ip} at ${(/* @__PURE__ */ new Date()).toISOString()}`
    );
  }
  await next();
});
app.post("/sandboxes", async (c) => {
  if (!requireScope(c, "write")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const body = await c.req.json();
  if (!body.projectId) {
    return c.json({ error: "projectId is required" }, 400);
  }
  const sb = getSandbox(c.env.Sandbox, body.projectId, {
    keepAlive: body.keepAlive !== void 0 ? Boolean(body.keepAlive) : void 0
  });
  const { result, duration_ms } = await timed(async () => {
    const { vars, secrets } = buildEnvVars(
      c.env.ANTHROPIC_API_KEY,
      c.env.OPENAI_API_KEY,
      body.envVars
    );
    if (Object.keys(vars).length > 0) {
      await sb.setEnvVars(vars);
    }
    await sb.setEnvVars(secrets);
    if (body.repoUrl) {
      await sb.gitCheckout(body.repoUrl, {
        targetDir: "/workspace",
        branch: body.branch
      });
    } else {
      const branch = (body.branch || "main").replace(/[^a-zA-Z0-9_.\-/]/g, "");
      await sb.exec(
        `cd /workspace && git init -b '${branch}'`
      );
    }
    const initResult = await sb.exec(
      "bash /usr/local/bin/pixl-init.sh /workspace"
    );
    if (initResult.exitCode !== 0) {
      return {
        success: false,
        error: initResult.stderr || initResult.stdout
      };
    }
    const [versions2, gitInfo] = await Promise.all([
      getVersions(sb),
      getGitInfo(sb)
    ]);
    return { success: true, versions: versions2, git: gitInfo };
  });
  await logOperation(sb, {
    timestamp: (/* @__PURE__ */ new Date()).toISOString(),
    operation: "create",
    duration_ms,
    success: result.success,
    error: result.success ? void 0 : result.error
  });
  if (!result.success) {
    return c.json(
      { projectId: body.projectId, status: "error", error: result.error },
      500
    );
  }
  return c.json({
    projectId: body.projectId,
    status: "ready",
    versions: result.versions,
    git: result.git
  });
});
app.delete("/sandboxes/:id", async (c) => {
  if (!requireScope(c, "admin")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  await sb.destroy();
  return c.json({ success: true });
});
app.get("/sandboxes/:id/status", async (c) => {
  if (!requireScope(c, "read")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  const [versions2, gitInfo, projectInfo] = await Promise.all([
    getVersions(sb),
    getGitInfo(sb),
    getProjectInfo(sb)
  ]);
  const envResult = await sb.exec("env | cut -d= -f1 | sort");
  const envKeys = envResult.stdout.trim().split("\n").filter(Boolean);
  return c.json({
    projectId: c.req.param("id"),
    status: "running",
    versions: versions2,
    git: gitInfo,
    project: projectInfo,
    envKeys
  });
});
app.get("/sandboxes/:id/events", async (c) => {
  if (!requireScope(c, "read")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  const limit = c.req.query("limit") || "50";
  const result = await sb.exec(`pixl events list --json --limit ${limit}`);
  if (result.exitCode !== 0) {
    return c.json({
      success: false,
      error: result.stderr || "Failed to list events"
    }, 500);
  }
  try {
    const events = JSON.parse(result.stdout);
    return c.json({ success: true, events });
  } catch {
    return c.json({ success: true, raw: result.stdout });
  }
});
app.get("/sandboxes/:id/usage", async (c) => {
  if (!requireScope(c, "read")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  const usage = await readUsage(sb);
  return c.json(usage);
});
app.get("/sandboxes/:id/export", async (c) => {
  if (!requireScope(c, "read")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const id = c.req.param("id");
  const sb = getSandbox(c.env.Sandbox, id);
  const commandTimeout = 6e4;
  const { result, duration_ms } = await timed(async () => {
    const commands = [
      "pixl events list --json",
      "pixl session list --json",
      "pixl artifact list --json"
    ];
    const parseOutput = /* @__PURE__ */ __name((stdout2) => {
      try {
        const parsed = JSON.parse(stdout2);
        return Array.isArray(parsed) ? parsed : [];
      } catch {
        return [];
      }
    }, "parseOutput");
    const [eventsResult, sessionsResult, artifactsResult] = await Promise.all(
      commands.map((cmd) => sb.exec(cmd, { timeout: commandTimeout }))
    );
    return {
      sandbox_id: id,
      exported_at: (/* @__PURE__ */ new Date()).toISOString(),
      events: parseOutput(eventsResult.stdout),
      sessions: parseOutput(sessionsResult.stdout),
      artifacts: parseOutput(artifactsResult.stdout)
    };
  });
  await logOperation(sb, {
    timestamp: (/* @__PURE__ */ new Date()).toISOString(),
    operation: "export",
    duration_ms,
    success: true
  });
  return c.json(result);
});
app.post("/sandboxes/:id/env", async (c) => {
  if (!requireScope(c, "write")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const body = await c.req.json();
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  await sb.setEnvVars(body);
  return c.json({ success: true, keys: Object.keys(body) });
});
app.post("/sandboxes/:id/exec", async (c) => {
  if (!requireScope(c, "write")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const body = await c.req.json();
  if (!body.command) {
    return c.json({ error: "command is required" }, 400);
  }
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  const { result, duration_ms } = await timed(async () => {
    return sb.exec(body.command, {
      timeout: body.timeout,
      env: body.env,
      cwd: body.cwd
    });
  });
  await logOperation(sb, {
    timestamp: (/* @__PURE__ */ new Date()).toISOString(),
    operation: "exec",
    duration_ms,
    success: result.exitCode === 0,
    meta: { command: body.command.slice(0, 200) }
  });
  return c.json({
    stdout: result.stdout,
    stderr: result.stderr,
    exitCode: result.exitCode,
    success: result.exitCode === 0
  });
});
app.post("/sandboxes/:id/exec/stream", async (c) => {
  if (!requireScope(c, "write")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const body = await c.req.json();
  if (!body.command) {
    return c.json({ error: "command is required" }, 400);
  }
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  const stream = await sb.execStream(body.command, {
    timeout: body.timeout,
    env: body.env,
    cwd: body.cwd
  });
  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive"
    }
  });
});
app.post("/sandboxes/:id/workflow", async (c) => {
  if (!requireScope(c, "write")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const body = await c.req.json();
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  const { result, duration_ms } = await timed(async () => {
    const args = ["pixl", "workflow", "run"];
    if (body.prompt) args.push("--prompt", shellEscape(body.prompt));
    if (body.workflowId) args.push("--workflow", body.workflowId);
    if (body.autoApprove) args.push("--yes");
    args.push("--json");
    return sb.exec(args.join(" "));
  });
  await logOperation(sb, {
    timestamp: (/* @__PURE__ */ new Date()).toISOString(),
    operation: "workflow",
    duration_ms,
    success: result.exitCode === 0,
    meta: { workflowId: body.workflowId }
  });
  return c.json({
    stdout: result.stdout,
    stderr: result.stderr,
    exitCode: result.exitCode,
    success: result.exitCode === 0
  });
});
app.post("/sandboxes/:id/workflow/stream", async (c) => {
  if (!requireScope(c, "write")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const body = await c.req.json();
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  const args = ["pixl", "workflow", "run"];
  if (body.prompt) args.push("--prompt", shellEscape(body.prompt));
  if (body.workflowId) args.push("--workflow", body.workflowId);
  if (body.autoApprove) args.push("--yes");
  args.push("--json");
  const rawStream = await sb.execStream(args.join(" "));
  const encoder2 = new TextEncoder();
  const decoder2 = new TextDecoder();
  let lineBuffer = "";
  const structuredStream = new TransformStream({
    start(controller) {
      const startEvent = JSON.stringify({ type: "status", payload: { status: "started" } });
      controller.enqueue(encoder2.encode(`data: ${startEvent}

`));
    },
    transform(chunk, controller) {
      lineBuffer += decoder2.decode(chunk, { stream: true });
      const segments = lineBuffer.split("\n");
      lineBuffer = segments.pop();
      for (const line of segments) {
        if (!line.trim()) continue;
        const dataMatch = line.match(/^data:\s*(.+)/);
        const raw2 = dataMatch ? dataMatch[1] : line;
        try {
          const parsed = JSON.parse(raw2);
          const event = JSON.stringify({ type: "event", payload: parsed });
          controller.enqueue(encoder2.encode(`data: ${event}

`));
        } catch {
          const event = JSON.stringify({ type: "stdout", payload: { line: raw2 } });
          controller.enqueue(encoder2.encode(`data: ${event}

`));
        }
      }
    },
    flush(controller) {
      if (lineBuffer.trim()) {
        const event = JSON.stringify({ type: "stdout", payload: { line: lineBuffer } });
        controller.enqueue(encoder2.encode(`data: ${event}

`));
      }
      const endEvent = JSON.stringify({ type: "status", payload: { status: "complete" } });
      controller.enqueue(encoder2.encode(`data: ${endEvent}

`));
    }
  });
  return new Response(rawStream.pipeThrough(structuredStream), {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive"
    }
  });
});
app.post("/sandboxes/:id/workflow/cancel", async (c) => {
  if (!requireScope(c, "write")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  const { result, duration_ms } = await timed(async () => {
    return sb.exec("kill -SIGINT $(pgrep -f 'pixl workflow run')");
  });
  const success = result.exitCode === 0;
  await logOperation(sb, {
    timestamp: (/* @__PURE__ */ new Date()).toISOString(),
    operation: "workflow_cancel",
    duration_ms,
    success,
    error: success ? void 0 : result.stderr || void 0
  });
  return c.json({
    success,
    message: success ? "Workflow cancellation signal sent" : "No running workflow found or cancel failed"
  });
});
app.get("/sandboxes/:id/sessions", async (c) => {
  if (!requireScope(c, "read")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  const result = await sb.exec("pixl session list --json");
  if (result.exitCode !== 0) {
    return c.json({
      success: false,
      error: result.stderr || "Failed to list sessions"
    }, 500);
  }
  try {
    const sessions = JSON.parse(result.stdout);
    return c.json({ success: true, sessions });
  } catch {
    return c.json({ success: true, raw: result.stdout });
  }
});
app.get("/sandboxes/:id/sessions/:sessionId/export", async (c) => {
  if (!requireScope(c, "read")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const sandboxId = c.req.param("id");
  const sessionId = c.req.param("sessionId");
  const sb = getSandbox(c.env.Sandbox, sandboxId);
  const commandTimeout = 3e4;
  const { result, duration_ms } = await timed(async () => {
    const sessionResult = await sb.exec(
      `pixl session get ${sessionId} --json`,
      { timeout: commandTimeout }
    );
    if (sessionResult.exitCode !== 0) {
      return { success: false, error: sessionResult.stderr || "Session not found" };
    }
    let session;
    try {
      session = JSON.parse(sessionResult.stdout);
    } catch {
      return { success: false, error: "Failed to parse session data" };
    }
    const snapshotHash = session.snapshot_hash;
    const eventsResult = await sb.exec(
      `pixl events ${sessionId} --json --limit 1000`,
      { timeout: commandTimeout }
    );
    const parseArray = /* @__PURE__ */ __name((stdout2) => {
      try {
        const parsed = JSON.parse(stdout2);
        return Array.isArray(parsed) ? parsed : [];
      } catch {
        return [];
      }
    }, "parseArray");
    const nodeInstances = session.node_instances ?? {};
    const nodeList = Object.entries(nodeInstances).map(
      ([nodeId, data]) => ({ node_id: nodeId, ...data })
    );
    return {
      success: true,
      bundle: {
        session,
        node_instances: nodeList,
        events: parseArray(eventsResult.stdout),
        snapshot: snapshotHash ?? null,
        exported_at: (/* @__PURE__ */ new Date()).toISOString(),
        sandbox_id: sandboxId
      }
    };
  });
  await logOperation(sb, {
    timestamp: (/* @__PURE__ */ new Date()).toISOString(),
    operation: "session_export",
    duration_ms,
    success: result.success,
    meta: { sessionId }
  });
  if (!result.success) {
    return c.json({ success: false, error: result.error }, 404);
  }
  return c.json(result.bundle);
});
app.post("/sandboxes/:id/sessions/import", async (c) => {
  if (!requireScope(c, "write")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const sandboxId = c.req.param("id");
  const sb = getSandbox(c.env.Sandbox, sandboxId);
  const body = await c.req.json();
  if (!body.session || !body.session.id) {
    return c.json({ error: "session with id is required in bundle" }, 400);
  }
  const { result, duration_ms } = await timed(async () => {
    const bundlePath = `/tmp/session-import-${Date.now()}.json`;
    const bundleJson = JSON.stringify(body);
    await sb.writeFile(bundlePath, bundleJson);
    const importScript = `
import json, sqlite3, sys
with open('${bundlePath}') as f:
    bundle = json.load(f)
s = bundle['session']
sid = s['id']
db = sqlite3.connect('/workspace/.pixl/pixl.db')
db.execute('PRAGMA journal_mode=WAL')
db.execute(
    """INSERT OR REPLACE INTO workflow_sessions
       (id, feature_id, snapshot_hash, status, created_at,
        started_at, ended_at, last_updated_at, baseline_commit,
        workspace_root, sandbox_origin_id)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
    (sid, s.get('feature_id'), s.get('snapshot_hash', 'imported'),
     s.get('status', 'completed'), s.get('created_at'),
     s.get('started_at'), s.get('ended_at'), s.get('last_updated_at'),
     s.get('baseline_commit'), s.get('workspace_root'),
     s.get('sandbox_origin_id', bundle.get('sandbox_id'))))
for ni in bundle.get('node_instances', []):
    db.execute(
        """INSERT OR REPLACE INTO node_instances
           (session_id, node_id, state, attempt, ready_at,
            started_at, ended_at, blocked_reason, output_json,
            failure_kind, error_message, model_name, agent_name,
            input_tokens, output_tokens, total_tokens, cost_usd)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (sid, ni.get('node_id'), ni.get('state', 'task_pending'),
         ni.get('attempt', 0), ni.get('ready_at'), ni.get('started_at'),
         ni.get('ended_at'), ni.get('blocked_reason'),
         json.dumps(ni.get('output')) if ni.get('output') else None,
         ni.get('failure_kind'), ni.get('error_message'),
         ni.get('model_name'), ni.get('agent_name'),
         ni.get('input_tokens', 0), ni.get('output_tokens', 0),
         ni.get('total_tokens', 0), ni.get('cost_usd', 0.0)))
for ev in bundle.get('events', []):
    try:
        db.execute(
            """INSERT OR IGNORE INTO events
               (session_id, event_type, node_id, entity_type,
                entity_id, payload, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (ev.get('session_id', sid), ev.get('event_type', 'unknown'),
             ev.get('node_id'), ev.get('entity_type'),
             ev.get('entity_id'),
             json.dumps(ev.get('payload')) if ev.get('payload') else None,
             ev.get('created_at')))
    except Exception:
        pass
db.commit()
db.close()
print(json.dumps({"imported": sid}))
`;
    const importResult = await sb.exec(
      `python3 -c ${shellEscape(importScript)}`,
      { timeout: 3e4 }
    );
    await sb.exec(`rm -f ${bundlePath}`, { timeout: 5e3 });
    if (importResult.exitCode !== 0) {
      return {
        success: false,
        error: importResult.stderr || "Import script failed"
      };
    }
    try {
      const output = JSON.parse(importResult.stdout);
      return { success: true, imported_session_id: output.imported };
    } catch {
      return { success: true, imported_session_id: body.session.id };
    }
  });
  await logOperation(sb, {
    timestamp: (/* @__PURE__ */ new Date()).toISOString(),
    operation: "session_import",
    duration_ms,
    success: result.success,
    meta: { sessionId: String(body.session.id) }
  });
  if (!result.success) {
    return c.json({ success: false, error: result.error }, 500);
  }
  return c.json({
    success: true,
    imported_session_id: result.imported_session_id,
    sandbox_id: sandboxId
  });
});
app.post("/sandboxes/:id/files", async (c) => {
  const body = await c.req.json();
  if (!body.path || body.content === void 0) {
    return c.json({ error: "path and content are required" }, 400);
  }
  if (!validatePath(body.path)) {
    return c.json(
      {
        error: "invalid path \u2014 must start with /workspace and contain no '..' segments"
      },
      400
    );
  }
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  await sb.writeFile(body.path, body.content);
  return c.json({ success: true, path: body.path });
});
app.get("/sandboxes/:id/files/*", async (c) => {
  const filePath = "/" + (c.req.param("*") ?? c.req.path.split("/files/").pop() ?? "");
  if (!validatePath(filePath)) {
    return c.json(
      {
        error: "invalid path \u2014 must start with /workspace and contain no '..' segments"
      },
      400
    );
  }
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  const file = await sb.readFile(filePath);
  return c.json({
    success: true,
    path: filePath,
    content: file.content,
    encoding: file.encoding
  });
});
app.get("/sandboxes/:id/git", async (c) => {
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  const gitInfo = await getGitInfo(sb);
  const [statusResult, logResult] = await Promise.all([
    sb.exec("git -C /workspace status --porcelain"),
    sb.exec("git -C /workspace log --oneline -20 2>/dev/null || echo ''")
  ]);
  return c.json({
    ...gitInfo,
    status: statusResult.stdout.trim(),
    log: logResult.stdout.trim().split("\n").filter(Boolean)
  });
});
app.post("/sandboxes/:id/git/push", async (c) => {
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  const gitInfo = await getGitInfo(sb);
  const { result, duration_ms } = await timed(async () => {
    return sb.exec(
      `git -C /workspace push -u origin ${gitInfo.branch}`
    );
  });
  await logOperation(sb, {
    timestamp: (/* @__PURE__ */ new Date()).toISOString(),
    operation: "git_push",
    duration_ms,
    success: result.exitCode === 0,
    error: result.exitCode !== 0 ? result.stderr : void 0
  });
  return c.json({
    success: result.exitCode === 0,
    stdout: result.stdout,
    stderr: result.stderr
  });
});
app.post("/sandboxes/:id/git/config", async (c) => {
  const body = await c.req.json();
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  const commands = [];
  if (body.userName) {
    commands.push(
      `git -C /workspace config user.name ${shellEscape(body.userName)}`
    );
  }
  if (body.userEmail) {
    commands.push(
      `git -C /workspace config user.email ${shellEscape(body.userEmail)}`
    );
  }
  if (body.remoteUrl) {
    commands.push(
      `git -C /workspace remote set-url origin ${shellEscape(body.remoteUrl)} 2>/dev/null || git -C /workspace remote add origin ${shellEscape(body.remoteUrl)}`
    );
  }
  if (commands.length === 0) {
    return c.json({ error: "at least one config field required" }, 400);
  }
  const result = await sb.exec(commands.join(" && "));
  return c.json({
    success: result.exitCode === 0,
    stderr: result.stderr || void 0
  });
});
app.post("/sandboxes/:id/process/start", async (c) => {
  const body = await c.req.json();
  if (!body.command) {
    return c.json({ error: "command is required" }, 400);
  }
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  const proc = await sb.startProcess(body.command, {
    cwd: body.cwd,
    env: body.env
  });
  return c.json({ success: true, processId: proc.id });
});
app.delete("/sandboxes/:id/process/:pid", async (c) => {
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  await sb.killProcess(c.req.param("pid"));
  return c.json({ success: true });
});
var router_default = app;

// node_modules/wrangler/templates/middleware/middleware-ensure-req-body-drained.ts
var drainBody = /* @__PURE__ */ __name(async (request, env2, _ctx, middlewareCtx) => {
  try {
    return await middlewareCtx.next(request, env2);
  } finally {
    try {
      if (request.body !== null && !request.bodyUsed) {
        const reader = request.body.getReader();
        while (!(await reader.read()).done) {
        }
      }
    } catch (e) {
      console.error("Failed to drain the unused request body.", e);
    }
  }
}, "drainBody");
var middleware_ensure_req_body_drained_default = drainBody;

// node_modules/wrangler/templates/middleware/middleware-miniflare3-json-error.ts
function reduceError(e) {
  return {
    name: e?.name,
    message: e?.message ?? String(e),
    stack: e?.stack,
    cause: e?.cause === void 0 ? void 0 : reduceError(e.cause)
  };
}
__name(reduceError, "reduceError");
var jsonError = /* @__PURE__ */ __name(async (request, env2, _ctx, middlewareCtx) => {
  try {
    return await middlewareCtx.next(request, env2);
  } catch (e) {
    const error3 = reduceError(e);
    return Response.json(error3, {
      status: 500,
      headers: { "MF-Experimental-Error-Stack": "true" }
    });
  }
}, "jsonError");
var middleware_miniflare3_json_error_default = jsonError;

// .wrangler/tmp/bundle-uPuqxV/middleware-insertion-facade.js
var __INTERNAL_WRANGLER_MIDDLEWARE__ = [
  middleware_ensure_req_body_drained_default,
  middleware_miniflare3_json_error_default
];
var middleware_insertion_facade_default = router_default;

// node_modules/wrangler/templates/middleware/common.ts
var __facade_middleware__ = [];
function __facade_register__(...args) {
  __facade_middleware__.push(...args.flat());
}
__name(__facade_register__, "__facade_register__");
function __facade_invokeChain__(request, env2, ctx, dispatch, middlewareChain) {
  const [head, ...tail] = middlewareChain;
  const middlewareCtx = {
    dispatch,
    next(newRequest, newEnv) {
      return __facade_invokeChain__(newRequest, newEnv, ctx, dispatch, tail);
    }
  };
  return head(request, env2, ctx, middlewareCtx);
}
__name(__facade_invokeChain__, "__facade_invokeChain__");
function __facade_invoke__(request, env2, ctx, dispatch, finalMiddleware) {
  return __facade_invokeChain__(request, env2, ctx, dispatch, [
    ...__facade_middleware__,
    finalMiddleware
  ]);
}
__name(__facade_invoke__, "__facade_invoke__");

// .wrangler/tmp/bundle-uPuqxV/middleware-loader.entry.ts
var __Facade_ScheduledController__ = class ___Facade_ScheduledController__ {
  constructor(scheduledTime, cron, noRetry) {
    this.scheduledTime = scheduledTime;
    this.cron = cron;
    this.#noRetry = noRetry;
  }
  static {
    __name(this, "__Facade_ScheduledController__");
  }
  #noRetry;
  noRetry() {
    if (!(this instanceof ___Facade_ScheduledController__)) {
      throw new TypeError("Illegal invocation");
    }
    this.#noRetry();
  }
};
function wrapExportedHandler(worker) {
  if (__INTERNAL_WRANGLER_MIDDLEWARE__ === void 0 || __INTERNAL_WRANGLER_MIDDLEWARE__.length === 0) {
    return worker;
  }
  for (const middleware of __INTERNAL_WRANGLER_MIDDLEWARE__) {
    __facade_register__(middleware);
  }
  const fetchDispatcher = /* @__PURE__ */ __name(function(request, env2, ctx) {
    if (worker.fetch === void 0) {
      throw new Error("Handler does not export a fetch() function.");
    }
    return worker.fetch(request, env2, ctx);
  }, "fetchDispatcher");
  return {
    ...worker,
    fetch(request, env2, ctx) {
      const dispatcher = /* @__PURE__ */ __name(function(type, init) {
        if (type === "scheduled" && worker.scheduled !== void 0) {
          const controller = new __Facade_ScheduledController__(
            Date.now(),
            init.cron ?? "",
            () => {
            }
          );
          return worker.scheduled(controller, env2, ctx);
        }
      }, "dispatcher");
      return __facade_invoke__(request, env2, ctx, dispatcher, fetchDispatcher);
    }
  };
}
__name(wrapExportedHandler, "wrapExportedHandler");
function wrapWorkerEntrypoint(klass) {
  if (__INTERNAL_WRANGLER_MIDDLEWARE__ === void 0 || __INTERNAL_WRANGLER_MIDDLEWARE__.length === 0) {
    return klass;
  }
  for (const middleware of __INTERNAL_WRANGLER_MIDDLEWARE__) {
    __facade_register__(middleware);
  }
  return class extends klass {
    #fetchDispatcher = /* @__PURE__ */ __name((request, env2, ctx) => {
      this.env = env2;
      this.ctx = ctx;
      if (super.fetch === void 0) {
        throw new Error("Entrypoint class does not define a fetch() function.");
      }
      return super.fetch(request);
    }, "#fetchDispatcher");
    #dispatcher = /* @__PURE__ */ __name((type, init) => {
      if (type === "scheduled" && super.scheduled !== void 0) {
        const controller = new __Facade_ScheduledController__(
          Date.now(),
          init.cron ?? "",
          () => {
          }
        );
        return super.scheduled(controller);
      }
    }, "#dispatcher");
    fetch(request) {
      return __facade_invoke__(
        request,
        this.env,
        this.ctx,
        this.#dispatcher,
        this.#fetchDispatcher
      );
    }
  };
}
__name(wrapWorkerEntrypoint, "wrapWorkerEntrypoint");
var WRAPPED_ENTRY;
if (typeof middleware_insertion_facade_default === "object") {
  WRAPPED_ENTRY = wrapExportedHandler(middleware_insertion_facade_default);
} else if (typeof middleware_insertion_facade_default === "function") {
  WRAPPED_ENTRY = wrapWorkerEntrypoint(middleware_insertion_facade_default);
}
var middleware_loader_entry_default = WRAPPED_ENTRY;
export {
  Sandbox,
  __INTERNAL_WRANGLER_MIDDLEWARE__,
  middleware_loader_entry_default as default
};
//# sourceMappingURL=index.js.map
