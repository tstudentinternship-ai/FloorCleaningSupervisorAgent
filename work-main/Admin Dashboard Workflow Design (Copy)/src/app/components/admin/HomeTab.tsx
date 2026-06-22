import { useEffect, useRef, useState } from 'react';
import { Plus, Trash2, Send, Bot, User, ChevronRight, X, FileText } from 'lucide-react';
import { useT } from '../../ThemeContext';
import { createStore, deleteStore, getGlobalDashboard, getStores, type StoreSummary } from '../../api';
import { ReportModal } from '../shared/ReportModal';

interface StoreEntry extends StoreSummary {}

interface ChatMessage {
  id: string;
  role: 'user' | 'bot';
  text: string;
  time: string;
}

function buildReply(message: string, stores: StoreEntry[]): string {
  const lower = message.toLowerCase();
  const avgCompliance = stores.length ? Math.round(stores.reduce((s, st) => s + st.compliance, 0) / stores.length) : 0;
  const topStore = [...stores].sort((a, b) => b.compliance - a.compliance)[0];
  const alertCount = stores.reduce((s, st) => s + st.activeAlerts, 0);

  if (lower.includes('compliance') || lower.includes('percent')) {
    return `Overall compliance across ${stores.length} stores is averaging ${avgCompliance}%. ${topStore ? `${topStore.name} ${topStore.storeNumber} is leading at ${topStore.compliance}%.` : ''}`;
  }
  if (lower.includes('alert') || lower.includes('warning') || lower.includes('critical')) {
    return `There are ${alertCount} active alerts across ${stores.length} stores right now. The backend alert list is live, so reviewing the Alerts tab will show the current status.`;
  }
  if (lower.includes('nfc') || lower.includes('tag')) {
    const totalTags = stores.reduce((s, st) => s + st.nfcCount, 0);
    return `Total NFC tags deployed: ${totalTags} across ${stores.length} stores. Use the Store Dashboard or NFC Tag Registry to review live tags.`;
  }
  if (lower.includes('round') || lower.includes('scan')) {
    return `Rounds are now loaded from the backend per store. Open a store dashboard to see the live round list and scan history.`;
  }
  return 'I can help summarize live stores, NFC tags, alerts, rounds, and compliance. Ask about a store or a metric and I will use the current backend data.';
}

function AddStoreModal({ onClose, onAdd }: { onClose: () => void; onAdd: (s: StoreEntry) => void }) {
  const t = useT();
  const [name, setName] = useState('');
  const [num, setNum] = useState('');
  const [location, setLocation] = useState('');
  const [manager, setManager] = useState('');

  const submit = async () => {
    if (!name || !num) return;
    const payload = {
      id: `store-${Date.now()}`,
      name,
      storeNumber: `#${num}`,
      location,
      manager,
    };
    const created = await createStore(payload);
    onAdd({
      id: created.id,
      name: created.name,
      storeNumber: created.storeNumber,
      location: created.location,
      manager: created.manager,
      compliance: created.compliance ?? 0,
      nfcCount: created.nfcCount ?? 0,
      activeAlerts: created.activeAlerts ?? 0,
      lastSync: created.lastSync ?? '—',
    });
    onClose();
  };

  return (
    <div className="absolute inset-0 bg-black/40 z-50 flex items-end">
      <div className={`w-full rounded-t-2xl p-5 pb-8 ${t.cardFlat}`}>
        <div className="flex items-center justify-between mb-4">
          <h3 className={`font-semibold ${t.text}`}>Add New Store</h3>
          <button onClick={onClose} className={`p-1.5 rounded-full ${t.hoverRow}`}><X className={`w-4 h-4 ${t.textMuted}`} /></button>
        </div>
        <div className="space-y-3">
          {[
            { label: 'Store Name *', val: name, set: setName, ph: 'e.g. CityMart Express' },
            { label: 'Store Number *', val: num, set: setNum, ph: 'e.g. 042' },
            { label: 'Location', val: location, set: setLocation, ph: 'e.g. Ground Floor, Mall' },
            { label: 'Manager Name', val: manager, set: setManager, ph: 'e.g. John Smith' },
          ].map(f => (
            <div key={f.label}>
              <label className={`block text-xs mb-1 ${t.textXs}`}>{f.label}</label>
              <input value={f.val} onChange={e => f.set(e.target.value)} placeholder={f.ph} className={`w-full px-3 py-2.5 border rounded-xl text-sm focus:outline-none focus:border-orange-400 focus:ring-2 focus:ring-orange-100 ${t.input}`} />
            </div>
          ))}
          <button onClick={submit} disabled={!name || !num} className="w-full py-3 bg-orange-500 text-white rounded-xl font-semibold disabled:opacity-50 hover:bg-orange-600 mt-2">
            Add Store
          </button>
        </div>
      </div>
    </div>
  );
}

export function HomeTab() {
  const [storeList, setStoreList] = useState<StoreEntry[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { id: '1', role: 'bot', text: 'Hi! I\'m the CleanCheck assistant. Ask me anything about your stores, alerts, compliance, or NFC tags.', time: 'Now' }
  ]);
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);
  const [showReport, setShowReport] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const t = useT();

  useEffect(() => {
    getStores().then(setStoreList).catch(() => setStoreList([]));
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, typing]);

  const sendMessage = () => {
    if (!input.trim()) return;
    const userMsg: ChatMessage = { id: Date.now().toString(), role: 'user', text: input, time: 'Now' };
    setMessages(prev => [...prev, userMsg]);
    const q = input;
    setInput('');
    setTyping(true);
    setTimeout(() => {
      setTyping(false);
      setMessages(prev => [...prev, { id: (Date.now() + 1).toString(), role: 'bot', text: buildReply(q, storeList), time: 'Now' }]);
    }, 500);
  };

  const confirmDelete = async (id: string) => {
    await deleteStore(id);
    setStoreList(prev => prev.filter(s => s.id !== id));
    setDeleteId(null);
  };

  return (
    <div className={`flex-1 overflow-y-auto pb-6 ${t.page}`}>
      <div className={`px-4 py-3 border-b flex items-center justify-between ${t.header}`}>
        <div>
          <h2 className={`font-semibold text-sm ${t.text}`}>Store Management</h2>
          <p className={`text-xs ${t.textXs}`}>{storeList.length} stores under administration</p>
        </div>
        <button onClick={() => setShowReport(true)} className="flex items-center gap-1.5 text-xs text-red-600 bg-red-50 dark:bg-red-900/30 px-3 py-1.5 rounded-full">
          <FileText className="w-3.5 h-3.5" /> Report
        </button>
      </div>

      <div className="px-4 pt-4 space-y-4">
        <div className="grid grid-cols-3 gap-3">
          <div className={`rounded-2xl p-3 border shadow-sm text-center ${t.card}`}>
            <div className="text-2xl font-bold text-red-600">{storeList.length}</div>
            <div className={`text-xs ${t.textXs}`}>Total Stores</div>
          </div>
          <div className={`rounded-2xl p-3 border shadow-sm text-center ${t.card}`}>
            <div className={`text-2xl font-bold ${t.text}`}>{storeList.reduce((s, st) => s + (st.nfcCount || 0), 0)}</div>
            <div className={`text-xs ${t.textXs}`}>Total NFCs</div>
          </div>
          <div className={`rounded-2xl p-3 border shadow-sm text-center ${t.card}`}>
            <div className="text-2xl font-bold text-amber-500">{storeList.reduce((s, st) => s + (st.activeAlerts || 0), 0)}</div>
            <div className={`text-xs ${t.textXs}`}>Total Alerts</div>
          </div>
        </div>

        <div className={`rounded-2xl border shadow-sm overflow-hidden ${t.card}`}>
          <div className={`px-4 py-3 border-b ${t.border} flex items-center justify-between`}>
            <h3 className={`font-semibold text-sm ${t.text}`}>Stores</h3>
            <button onClick={() => setShowAdd(true)} className="flex items-center gap-1 text-xs text-orange-500 bg-orange-50 dark:bg-orange-900/30 px-3 py-1.5 rounded-full hover:bg-orange-100 dark:hover:bg-orange-900/40">
              <Plus className="w-3.5 h-3.5" /> Add Store
            </button>
          </div>
          {storeList.map((s, i) => (
            <div key={s.id} className={`px-4 py-3.5 flex items-center gap-3 ${i > 0 ? `border-t ${t.borderGray}` : ''}`}>
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-xs font-bold text-white shrink-0 ${(s.compliance || 0) >= 85 ? 'bg-green-500' : (s.compliance || 0) >= 70 ? 'bg-amber-500' : 'bg-gray-400'}`}>
                {s.compliance ? `${s.compliance}%` : '—'}
              </div>
              <div className="flex-1 min-w-0">
                <div className={`text-sm font-medium truncate ${t.text}`}>{s.name} {s.storeNumber}</div>
                <div className={`text-xs truncate ${t.textMuted}`}>{s.location || 'Location not set'}</div>
                {s.manager && <div className={`text-xs ${t.textMuted}`}>{s.manager}</div>}
              </div>
              <button onClick={() => setDeleteId(s.id)} className={`p-2 rounded-lg ${t.hoverRow} ${t.textMuted} hover:text-red-500 transition-colors shrink-0`}>
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
          {storeList.length === 0 && <div className={`px-4 py-8 text-center text-sm ${t.textMuted}`}>No stores yet. Add your first store.</div>}
        </div>

        <div className={`rounded-2xl border shadow-sm overflow-hidden ${t.card}`}>
          <button onClick={() => setChatOpen(!chatOpen)} className={`w-full px-4 py-3.5 flex items-center justify-between ${t.hoverRow} transition-colors`}>
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 bg-orange-500 rounded-xl flex items-center justify-center">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div className="text-left">
                <div className={`text-sm font-semibold ${t.text}`}>Live Store Assistant</div>
                <div className={`text-xs ${t.textXs}`}>Ask anything about your stores</div>
              </div>
            </div>
            <ChevronRight className={`w-4 h-4 ${t.textMuted} transition-transform ${chatOpen ? 'rotate-90' : ''}`} />
          </button>

          {chatOpen && (
            <div className={`border-t ${t.border}`}>
              <div className={`h-64 overflow-y-auto px-4 py-3 space-y-3 ${t.surface}`}>
                {messages.map(m => (
                  <div key={m.id} className={`flex gap-2 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${m.role === 'bot' ? 'bg-orange-500' : 'bg-gray-600 dark:bg-gray-500'}`}>
                      {m.role === 'bot' ? <Bot className="w-4 h-4 text-white" /> : <User className="w-3.5 h-3.5 text-white" />}
                    </div>
                    <div className={`max-w-[75%] px-3 py-2 rounded-2xl text-xs leading-relaxed ${m.role === 'bot' ? `${t.card} ${t.text} rounded-tl-sm` : 'bg-orange-500 text-white rounded-tr-sm'}`}>
                      {m.text}
                    </div>
                  </div>
                ))}
                {typing && (
                  <div className="flex gap-2">
                    <div className="w-7 h-7 rounded-full bg-orange-500 flex items-center justify-center"><Bot className="w-4 h-4 text-white" /></div>
                    <div className={`${t.card} px-3 py-2 rounded-2xl rounded-tl-sm`}>
                      <div className="flex gap-1 items-center h-4">
                        <span className="w-1.5 h-1.5 bg-orange-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                        <span className="w-1.5 h-1.5 bg-orange-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                        <span className="w-1.5 h-1.5 bg-orange-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>
              <div className={`px-4 py-3 border-t ${t.border} flex gap-2`}>
                <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && sendMessage()} placeholder="Ask about any store..." className={`flex-1 px-3 py-2 border rounded-xl text-sm focus:outline-none focus:border-orange-400 focus:ring-2 focus:ring-orange-100 ${t.input}`} />
                <button onClick={sendMessage} disabled={!input.trim()} className="w-9 h-9 bg-orange-500 rounded-xl flex items-center justify-center disabled:opacity-50 hover:bg-orange-600 transition-colors shrink-0">
                  <Send className="w-4 h-4 text-white" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {showAdd && <AddStoreModal onClose={() => setShowAdd(false)} onAdd={s => setStoreList(prev => [...prev, s])} />}
      {deleteId && (
        <div className="absolute inset-0 bg-black/40 z-50 flex items-center justify-center px-6">
          <div className={`rounded-2xl p-5 w-full max-w-sm ${t.cardFlat}`}>
            <h3 className={`font-semibold mb-2 ${t.text}`}>Delete Store?</h3>
            <p className={`text-sm mb-4 ${t.textSm}`}>This will remove the store and all its data from your dashboard. This action cannot be undone.</p>
            <div className="flex gap-2">
              <button onClick={() => setDeleteId(null)} className={`flex-1 py-2.5 border rounded-xl text-sm ${t.borderGray} ${t.textSm}`}>Cancel</button>
              <button onClick={() => confirmDelete(deleteId)} className="flex-1 py-2.5 bg-red-600 text-white rounded-xl text-sm font-semibold hover:bg-red-700">Delete</button>
            </div>
          </div>
        </div>
      )}
      {showReport && <ReportModal title="Store Management Report" context={`${storeList.length} stores`} onClose={() => setShowReport(false)} />}
    </div>
  );
}
