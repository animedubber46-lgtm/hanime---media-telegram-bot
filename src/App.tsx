import React, { useState, useEffect } from "react";
import {
  Bot,
  Terminal,
  Activity,
  Database,
  Tv,
  Link as LinkIcon,
  Sparkles,
  Coins,
  UserPlus,
  KeyRound,
  CheckCircle2,
  AlertTriangle,
  Shield,
  Copy,
  Play,
  RotateCw
} from "lucide-react";

interface StatusMetrics {
  configLoaded: {
    bot_token: boolean;
    tmdb_api: boolean;
    db_prefix: string;
    base_url: string;
  };
  isDbCreated: boolean;
  dbSize: string;
  bot_status: string;
}

interface ScrapedResult {
  title: string;
  slug: string;
  description: string;
  rating: number;
  genres: string;
  thumbnail_url: string;
  master_url: string;
  warning?: string;
}

export default function App() {
  // Stats states
  const [stats, setStats] = useState<StatusMetrics | null>(null);
  const [loadingStats, setLoadingStats] = useState(true);

  // Scraper Sandbox states
  const [testUrl, setTestUrl] = useState("https://hanime.tv/videos/hentai/fault-milestone-one-1");
  const [scrapingLogs, setScrapingLogs] = useState<string[]>([]);
  const [scrapingInProgress, setScrapingInProgress] = useState(false);
  const [scrapedData, setScrapedData] = useState<ScrapedResult | null>(null);
  const [scrapeError, setScrapeError] = useState<string | null>(null);
  const [copiedLink, setCopiedLink] = useState(false);

  // Load telemetry metrics
  const fetchStats = async () => {
    try {
      setLoadingStats(true);
      const res = await fetch("/api/stats");
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (e) {
      console.error("Telemetry query failed: ", e);
    } finally {
      setLoadingStats(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  // Run scraper execution simulation in the visual preview!
  const handleScrapeSimulation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!testUrl) return;

    setScrapingInProgress(true);
    setScrapeError(null);
    setScrapedData(null);
    setScrapingLogs([
      "📡 Handshaking local Express proxy channel...",
      "🛠 Reading request parameters and validating URL schema...",
    ]);

    try {
      // Simulate stepwise log feeds for user visual immersion
      await new Promise((r) => setTimeout(r, 600));
      setScrapingLogs((prev) => [...prev, "⚡ Initiating sub-second HTTP stream parser..."]);
      
      await new Promise((r) => setTimeout(r, 700));
      setScrapingLogs((prev) => [...prev, "🧩 Compiling regular expression parsing lookups..."]);

      const response = await fetch(`/api/scrape?url=${encodeURIComponent(testUrl)}`);
      
      await new Promise((r) => setTimeout(r, 500));
      
      if (!response.ok) {
        const errJson = await response.json();
        throw new Error(errJson.error || "Failed to parse target HTML elements.");
      }

      const data = await response.json();
      
      setScrapingLogs((prev) => [
        ...prev,
        "🎬 State block isolated & content metadata serialized!",
        "✅ Query complete: Synopses, rating coefficients and stream URLs mapped."
      ]);
      setScrapedData(data);
      // Re-trigger stats update to reflect new entries that could populate
      fetchStats();
    } catch (err: any) {
      setScrapingLogs((prev) => [...prev, `❌ Compilation aborted: ${err.message}`]);
      setScrapeError(err.message || "An error occurred during target resolution.");
    } finally {
      setScrapingInProgress(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
  };

  return (
    <div className="flex min-h-screen bg-[#050608] text-slate-200 overflow-x-hidden select-none font-sans antialiased">
      
      {/* Left Sidebar Navigation - Desktop only */}
      <aside className="w-64 border-r border-white/5 bg-[#0a0c10] shrink-0 hidden md:flex flex-col z-20">
        <div className="p-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center shadow-lg shadow-blue-500/10">
              <Bot className="w-5 h-5 text-white animate-pulse" />
            </div>
            <span className="font-bold tracking-tight text-lg text-white">
              H-Bot <span className="text-blue-500">PRO</span>
            </span>
          </div>
        </div>
        
        <nav className="flex-1 px-4 py-2 space-y-1">
          <div className="bg-white/5 text-white px-4 py-3 rounded-xl flex items-center gap-3 cursor-pointer border border-white/10 text-xs font-semibold">
            <span className="w-1.5 h-1.5 bg-blue-500 rounded-full"></span>
            Control Dashboard
          </div>
          <div className="text-slate-400 px-4 py-3 rounded-xl hover:bg-white/5 flex items-center gap-3 transition-colors text-xs cursor-text">
            <Database className="w-4 h-4 text-slate-500" />
            User Directory
          </div>
          <div className="text-slate-400 px-4 py-3 rounded-xl hover:bg-white/5 flex items-center gap-3 transition-colors text-xs cursor-text">
            <Terminal className="w-4 h-4 text-slate-500" />
            Live Scrape Logs
          </div>
          <div className="text-slate-400 px-4 py-3 rounded-xl hover:bg-white/5 flex items-center gap-3 transition-colors text-xs cursor-text">
            <LinkIcon className="w-4 h-4 text-slate-500" />
            Link Shortener
          </div>
        </nav>

        {/* Dynamic Star Widget */}
        <div className="p-4 mt-auto">
          <div className="bg-gradient-to-br from-blue-600/20 to-purple-600/20 border border-blue-500/30 rounded-2xl p-4">
            <p className="text-[10px] font-semibold text-blue-400 uppercase tracking-widest mb-1">Telegram Stars</p>
            <p className="text-xl font-bold text-white flex items-center gap-1.5">
              14,250 <span className="text-amber-400 text-sm">⭐</span>
            </p>
            <p className="text-[9px] text-slate-500 mt-2">30-day projected velocity: +8,400</p>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col bg-slate-950 overflow-hidden relative min-w-0">
        
        {/* Abstract Background Accent Blur */}
        <div className="absolute -top-24 -right-24 w-96 h-96 bg-blue-600/10 rounded-full blur-[120px] pointer-events-none"></div>

        {/* Header Bar */}
        <header className="h-16 border-b border-white/5 px-6 md:px-8 flex items-center justify-between z-10 shrink-0">
          <div className="flex items-center gap-4">
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider hidden sm:block">System Engine:</h2>
            <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-[10px] font-bold border ${
              stats?.configLoaded.bot_token 
                ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" 
                : "bg-amber-500/10 text-amber-500 border-amber-500/20"
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${stats?.configLoaded.bot_token ? "bg-emerald-500 animate-pulse" : "bg-amber-500"}`}></span>
              {stats?.configLoaded.bot_token ? "OPERATIONAL" : "PENDING SECRETS"}
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={fetchStats}
              className="px-3.5 py-1.5 bg-white/5 hover:bg-white/10 active:bg-white/15 text-slate-200 hover:text-white rounded-lg border border-white/10 transition duration-150 text-xs font-semibold flex items-center gap-2"
              title="Refresh Stats"
              id="btn_refresh_telemetry"
            >
              <RotateCw className={`w-3.5 h-3.5 ${loadingStats ? "animate-spin" : ""}`} />
              Sync Telemetry
            </button>
            <a
              href="https://t.me"
              target="_blank"
              rel="noreferrer"
              className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold rounded-lg transition shadow-lg shadow-blue-500/15 duration-150 flex items-center gap-2"
              id="lnk_launch_tg"
            >
              <Bot className="w-3.5 h-3.5" />
              Launch Bot
            </a>
          </div>
        </header>

        {/* Grid and Content area */}
        <div className="flex-1 p-6 md:p-8 space-y-6 overflow-y-auto">
          
          {/* Header Mobile Brand */}
          <div className="md:hidden flex items-center justify-between border-b border-white/5 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <Bot className="w-4.5 h-4.5 text-white animate-pulse" />
              </div>
              <span className="font-bold text-base text-white">H-Bot <span className="text-blue-500">PRO</span></span>
            </div>
            <span className="px-2.5 py-0.5 text-[10px] font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/20 rounded-full">
              v20.7 Applet
            </span>
          </div>

          {/* Immersive Stats Row matching design HTML exact styles */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            
            {/* Stat Card 1 */}
            <div className="bg-[#11141b] p-5 rounded-2xl border border-white/5 shadow-2xl relative overflow-hidden group">
              <div className="absolute top-0 left-0 w-1 h-full bg-blue-500 opacity-60"></div>
              <p className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">SQLite Storage</p>
              <p className="text-2xl font-light mt-1.5 text-white font-mono break-all leading-tight">
                {stats?.dbSize || "Scanning..."}
              </p>
              <div className="flex items-center gap-1.5 text-slate-400 text-[10px] mt-2.5 font-sans">
                <Database className="w-3.5 h-3.5 text-blue-500" />
                <span>Path: {stats?.configLoaded.db_prefix || "tgbot.db"}</span>
              </div>
            </div>

            {/* Stat Card 2 */}
            <div className="bg-[#11141b] p-5 rounded-2xl border border-white/5 shadow-2xl relative overflow-hidden group">
              <div className="absolute top-0 left-0 w-1 h-full bg-purple-500 opacity-60"></div>
              <p className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">Execution Status</p>
              <p className={`text-2xl font-light mt-1.5 ${stats?.configLoaded.bot_token ? "text-emerald-400" : "text-amber-400"} uppercase`}>
                {stats?.configLoaded.bot_token ? "Active" : "Pending"}
              </p>
              <div className="flex items-center gap-1.5 text-slate-400 text-[10px] mt-2.5 font-sans">
                <Shield className="w-3.5 h-3.5 text-purple-400" />
                <span>Type: Python PTB v20</span>
              </div>
            </div>

            {/* Stat Card 3 */}
            <div className="bg-[#11141b] p-5 rounded-2xl border border-white/5 shadow-2xl relative overflow-hidden group">
              <div className="absolute top-0 left-0 w-1 h-full bg-pink-500 opacity-60"></div>
              <p className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">Premium Shortener</p>
              <p className="text-2xl font-light mt-1.5 text-pink-400 uppercase">
                Active
              </p>
              <div className="flex items-center gap-1.5 text-slate-400 text-[10px] mt-2.5 font-sans">
                <LinkIcon className="w-3.5 h-3.5 text-pink-500" />
                <span>Features: Limit & Expiry</span>
              </div>
            </div>

            {/* Stat Card 4 */}
            <div className="bg-[#11141b] p-5 rounded-2xl border border-white/5 shadow-2xl relative overflow-hidden group">
              <div className="absolute top-0 left-0 w-1 h-full bg-amber-500 opacity-60"></div>
              <p className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">Allocation Bonus</p>
              <p className="text-2xl font-light mt-1.5 text-amber-500">
                50 Credits
              </p>
              <div className="flex items-center gap-1.5 text-slate-400 text-[10px] mt-2.5 font-sans">
                <Coins className="w-3.5 h-3.5 text-amber-500" />
                <span>On-Registration auto grant</span>
              </div>
            </div>

          </div>

          {/* Central Workspace Structure */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            
            {/* Interactive Sandbox Panel (Cols: 8) */}
            <div className="lg:col-span-8 bg-[#0d1016] rounded-3xl border border-white/5 flex flex-col overflow-hidden shadow-2xl min-h-[500px]" id="card_sandbox">
              
              <div className="p-6 border-b border-white/5 flex justify-between items-center">
                <h3 className="font-bold flex items-center gap-2 text-white text-sm">
                  <span className="w-2 h-4 bg-blue-500 rounded-sm"></span>
                  Live Activity Monitor
                </h3>
                <span className="text-[10px] bg-white/5 px-2.5 py-1 rounded-md border border-white/10 uppercase font-mono text-slate-400">
                  SANDBOX CONSOLE
                </span>
              </div>

              <div className="p-6 flex-1 flex flex-col">
                <p className="text-xs text-slate-440 mb-4 leading-relaxed">
                  Test-drive the actual scraper parser engine from the dashboard! Input a valid <code className="text-blue-400 font-mono">hanime.tv</code> URL below to query real-time metadata.
                </p>

                {/* Scraper input component */}
                <form onSubmit={handleScrapeSimulation} className="flex flex-col sm:flex-row gap-3 mb-6" id="form_scraper_sim">
                  <div className="relative flex-1">
                    <Tv className="absolute left-3.5 top-3 w-4 h-4 text-slate-500" />
                    <input
                      type="url"
                      value={testUrl}
                      onChange={(e) => setTestUrl(e.target.value)}
                      placeholder="https://hanime.tv/videos/hentai/slug-name..."
                      className="w-full bg-[#050608] hover:bg-[#050608]/80 focus:bg-[#050608] border border-white/5 focus:border-blue-500/80 rounded-xl py-2.5 pl-11 pr-4 text-xs font-mono text-slate-200 placeholder-slate-700 focus:outline-none transition duration-150"
                      required
                      id="input_sim_url"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={scrapingInProgress}
                    className={`px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs rounded-xl shadow-lg transition duration-200 flex items-center justify-center gap-2 shrink-0 ${
                      scrapingInProgress ? "opacity-60 cursor-not-allowed" : ""
                    }`}
                    id="btn_sim_submit"
                  >
                    {scrapingInProgress ? (
                      <>
                        <RotateCw className="w-3.5 h-3.5 animate-spin" />
                        Scraping State...
                      </>
                    ) : (
                      <>
                        <Play className="w-3.5 h-3.5 fill-current" />
                        Run Scrape
                      </>
                    )}
                  </button>
                </form>

                {/* Log outputs */}
                <div className="bg-[#050608] border border-white/5 rounded-xl p-4 font-mono text-xs overflow-hidden flex-1 flex flex-col min-h-[220px]" id="sandbox_logs_container">
                  {/* Scraping Progress Logs */}
                  {scrapingLogs.length > 0 && (
                    <div className="mb-4">
                      <p className="text-slate-500 text-[10px] font-sans border-b border-white/5 pb-1 mb-2 tracking-widest uppercase">Console Diagnostics</p>
                      <div className="space-y-1.5 text-[11px]">
                        {scrapingLogs.map((log, idx) => (
                          <div key={idx} className="flex gap-2">
                            <span className="text-blue-500/60 flex-shrink-0">›</span>
                            <span className={log.startsWith("❌") ? "text-rose-400" : log.startsWith("✅") ? "text-emerald-400" : "text-slate-300"}>
                              {log}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Empty state */}
                  {!scrapingInProgress && !scrapedData && !scrapeError && (
                    <div className="flex flex-col items-center justify-center text-center my-auto py-10">
                      <Terminal className="w-8 h-8 text-slate-700 mb-2" />
                      <p className="text-xs text-slate-500">Wait-state. Paste a Hanime link and run the scraper simulation.</p>
                    </div>
                  )}

                  {/* Error state */}
                  {scrapeError && (
                    <div className="p-3 bg-rose-500/5 rounded-xl border border-rose-500/10 text-xs text-rose-300 leading-relaxed my-auto">
                      <p className="font-bold flex items-center gap-1 text-rose-400 mb-1">
                        <AlertTriangle className="w-4 h-4" /> Resolution error occurred!
                      </p>
                      <p>{scrapeError}</p>
                    </div>
                  )}
                </div>

              </div>

              {/* Dynamic Metadata Media Drawer in the footer match the aesthetic exact */}
              <div className="mt-auto p-6 bg-gradient-to-t from-[#050608] to-transparent border-t border-white/5">
                <div className="flex flex-col sm:flex-row items-center sm:items-stretch gap-6">
                  <div className="w-20 h-28 bg-slate-800 rounded-lg shadow-xl overflow-hidden flex-shrink-0 border border-white/10 relative">
                    <img
                      src={scrapedData?.thumbnail_url || "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?auto=format&fit=crop&w=600&q=80"}
                      alt="Poster cover animate-pulse"
                      className="w-full h-full object-cover"
                      referrerPolicy="no-referrer"
                    />
                    <div className="absolute top-1.5 right-1.5 px-1 py-0.2 bg-black/85 rounded text-[9px] font-bold text-amber-400 border border-amber-500/20">
                      ⭐ {scrapedData?.rating || 8.4}
                    </div>
                  </div>
                  
                  <div className="flex-1 text-center sm:text-left flex flex-col justify-between">
                    <div>
                      <p className="text-[10px] font-bold text-blue-400 uppercase tracking-wider mb-0.5">
                        {scrapedData ? "Live Resolved Content" : "Latest Resolved Content"}
                      </p>
                      <h4 className="text-base font-bold text-white tracking-tight">
                        {scrapedData?.title || "High School DxD Hero - Ep 12"}
                      </h4>
                      <div className="flex flex-wrap justify-center sm:justify-start gap-1.5 my-1.5">
                        {(scrapedData?.genres || "Fantasy, Ecchi, Action").split(",").map((genre, idx) => (
                          <span key={idx} className="px-1.5 py-0.2 text-[9px] bg-white/5 border border-white/10 rounded font-semibold text-slate-400">
                            {genre.trim()}
                          </span>
                        ))}
                      </div>
                    </div>
                    <p className="text-xs text-slate-400 line-clamp-2 mt-1">
                      {scrapedData?.description || "The struggle between devils continues as Issei reaches his final form is indexed into catalogs with active stream buffers."}
                    </p>
                  </div>

                  <div className="flex flex-col justify-between items-center sm:items-end text-center sm:text-right shrink-0">
                    <span className="text-[9px] bg-white/5 px-2 py-1 rounded border border-white/10 uppercase tracking-tight font-mono text-slate-400">
                      ID: {scrapedData ? "64b_124" : "64b_88291"}
                    </span>

                    {scrapedData ? (
                      <div className="flex items-center gap-2 mt-4 sm:mt-0">
                        <button
                          type="button"
                          onClick={() => copyToClipboard(scrapedData.master_url)}
                          className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-sans transition-all flex items-center gap-1.5 text-xs font-bold cursor-pointer shadow-md"
                          id="btn_copy_m3u8"
                        >
                          <Copy className="w-3 h-3" />
                          {copiedLink ? "Copied" : "Copy Playlist"}
                        </button>
                      </div>
                    ) : (
                      <div className="mt-4 flex gap-2">
                        <div className="w-8 h-8 rounded bg-white/5 border border-white/10 flex items-center justify-center text-slate-400 hover:text-white transition-colors cursor-pointer" title="Clipboard Copy">
                          <Copy className="w-3.5 h-3.5" />
                        </div>
                        <div className="w-8 h-8 rounded bg-white/5 border border-white/10 flex items-center justify-center text-slate-400 hover:text-white transition-colors cursor-pointer" title="Direct Play">
                          <Play className="w-3.5 h-3.5" />
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>

            </div>

            {/* Side Panel Widgets (Cols: 4) */}
            <div className="lg:col-span-4 flex flex-col gap-6">

              {/* Bot Telegram UI Mock Balloon Card matching exact Design HTML preview scheme */}
              <div className="bg-[#11141b] rounded-3xl p-6 border border-white/5 shadow-2xl relative" id="card_telegram_preview">
                <p className="text-[10px] font-black text-slate-500 mb-4 tracking-widest uppercase">Telegram Client Bot Preview</p>
                <div className="space-y-3">
                  <div className="bg-[#242f3d] rounded-2xl rounded-tl-none p-3 max-w-[90%] border border-white/5 text-slate-200">
                    <p className="text-xs leading-relaxed">
                      <b>🎬 Scrape Success!</b><br/>
                      <b>Title:</b> {scrapedData?.title || "H-Video Sample"}<br/>
                      <b>Rating:</b> {scrapedData?.rating || "8.4"}/10 ⭐<br/>
                      🆔 Content ID: <code className="text-blue-300">124-{scrapedData ? "992" : "012"}</code>
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-white text-xs">
                    <div className="bg-[#2b5278] hover:bg-[#2b5278]/90 py-2 rounded-lg text-center font-bold cursor-pointer select-none transition">
                      📋 Copy URL
                    </div>
                    <div className="bg-[#2b5278] hover:bg-[#2b5278]/90 py-2 rounded-lg text-center font-bold cursor-pointer select-none transition">
                      🔗 Shorten
                    </div>
                    <div className="bg-[#242f3d] hover:bg-[#242f3d]/80 py-2 rounded-lg text-center col-span-2 border border-white/10 cursor-pointer transition">
                      🏠 Main Menu
                    </div>
                  </div>
                </div>
                <div className="absolute bottom-4 right-6">
                  <div className="w-2.5 h-2.5 bg-blue-500 rounded-full shadow-[0_0_10px_#3b82f6]"></div>
                </div>
              </div>

              {/* Tier Threshold Limits Block */}
              <div className="bg-gradient-to-br from-[#1c1c1c] to-[#0a0a0a] rounded-3xl p-6 border border-white/5" id="card_premium_compare">
                <p className="text-[10px] font-black text-slate-500 mb-4 tracking-widest uppercase">Tier Thresholds & Parameters</p>
                <div className="space-y-4">
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-400">Free Daily Scrapes</span>
                    <span className="font-mono text-white">20 / day</span>
                  </div>
                  <div className="w-full bg-white/5 h-[1px]"></div>
                  <div className="flex justify-between items-center text-xs text-blue-400 font-bold">
                    <span>Premium Daily Scrapes</span>
                    <span className="font-mono text-blue-400">500 / day</span>
                  </div>
                  <div className="w-full bg-white/5 h-[1px]"></div>
                  <div className="flex justify-between items-center text-xs">
                    <span>TTL Cache window</span>
                    <span className="font-mono text-white">86400s</span>
                  </div>
                  <div className="w-full bg-white/5 h-[1px]"></div>
                  <div className="flex justify-between items-center text-xs">
                    <span>Referral Limit Multiplier</span>
                    <span className="font-mono text-white">5 Invites</span>
                  </div>
                </div>
              </div>

              {/* System Flow Guidelines info */}
              <div className="bg-[#11141b] rounded-2xl border border-white/5 p-6">
                <h3 className="font-semibold text-xs text-slate-200 mb-3 flex items-center gap-2 uppercase tracking-wide">
                  <Coins className="w-4 h-4 text-blue-400" />
                  Dual-tier Settlement
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Earn premium upgrades for free via our multi-tiered invite milestones, or make instant Star settlements with active PreCheckout and SuccessfulPayment sequences linked directly within python-telegram-bot.
                </p>
              </div>

            </div>

          </div>

        </div>

        {/* Footer */}
        <footer className="mt-auto py-6 border-t border-white/5 text-center text-[10px] text-slate-600">
          <p>© 2026 Hanime Curation Bot Command Center. Powered by python-telegram-bot v20 handlers.</p>
        </footer>

      </main>

    </div>
  );
}
