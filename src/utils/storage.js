import AsyncStorage from '@react-native-async-storage/async-storage';

const KEY = 'reservebot_v2';

export const DEFAULT_AGENTS = [
  {
    id: 'naru',
    name: 'Naru Noodle Bar',
    cuisine: 'Ramen · Shanti Nagar',
    emoji: '🍜',
    color: '#E8A74A',
    bookingUrl: 'https://bookings.airmenus.in/eatnaru/order',
    enabled: true,
    schedule: {
      type: 'weekly',        // 'weekly' | 'daily'
      weekday: 1,            // 0=Sun … 6=Sat  (1=Mon)
      hour: 20, minute: 0,
      tz: 'Asia/Kolkata',
      label: 'Every Monday at 8:00 PM IST',
    },
    prefs: {
      partySize: 1,
      slots: ['12:30 PM', '2:30 PM'],
      days: ['Tue','Wed','Thu','Fri','Sat','Sun'],
      specialRequest: '',
    },
    guest: {
      name:  'Your Name',
      phone: '0000000000',
      email: 'you@example.com',
    },
    github: 'maxthecat2024/naru-booking',
    history: [{ ts: new Date().toISOString(), status: 'success', note: 'Sample booking for testing' }],
  },
  {
    id: 'pizza4ps',
    name: "Pizza 4P's",
    cuisine: 'Italian · Indiranagar',
    emoji: '🍕',
    color: '#F87171',
    bookingUrl: 'https://www.tablecheck.com/en/pizza-4ps-in-indiranagar/reserve/message',
    enabled: false,
    schedule: {
      type: 'daily',
      weekday: null,
      hour: 10, minute: 0,
      tz: 'Asia/Kolkata',
      label: 'Every day at 10:00 AM IST',
    },
    prefs: {
      partySize: 2,
      slots: ['12:00 PM','1:00 PM','7:00 PM','8:00 PM'],
      days: ['Fri','Sat','Sun'],
      specialRequest: '',
    },
    guest: {
      name:  'Your Name',
      phone: '0000000000',
      email: 'you@example.com',
    },
    github: '',
    history: [],
  },
];

export async function loadAgents() {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    if (raw) return JSON.parse(raw);
    await AsyncStorage.setItem(KEY, JSON.stringify(DEFAULT_AGENTS));
    return DEFAULT_AGENTS;
  } catch { return DEFAULT_AGENTS; }
}

export async function saveAgents(agents) {
  await AsyncStorage.setItem(KEY, JSON.stringify(agents));
}

export async function patchAgent(id, patch) {
  const list = await loadAgents();
  const next = list.map(a => a.id === id ? deepMerge(a, patch) : a);
  await saveAgents(next);
  return next;
}

function deepMerge(base, patch) {
  const out = { ...base };
  for (const k of Object.keys(patch)) {
    if (patch[k] && typeof patch[k] === 'object' && !Array.isArray(patch[k])) {
      out[k] = deepMerge(base[k] || {}, patch[k]);
    } else {
      out[k] = patch[k];
    }
  }
  return out;
}
