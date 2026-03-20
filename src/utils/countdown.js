import { dayjs } from 'dayjs';

export function secsUntilNext(schedule) {
  // schedule: { type, weekday, hour, minute, tz }
  // This is a simplified version. For a real app, use dayjs-timezone.
  const now = new Date();
  
  if (schedule.type === 'daily') {
    let next = new Date(now);
    next.setHours(schedule.hour, schedule.minute, 0, 0);
    if (next <= now) next.setDate(next.getDate() + 1);
    return Math.floor((next - now) / 1000);
  } else if (schedule.type === 'weekly') {
    let next = new Date(now);
    next.setHours(schedule.hour, schedule.minute, 0, 0);
    let days = (schedule.weekday - next.getDay() + 7) % 7;
    if (days === 0 && next <= now) days = 7;
    next.setDate(next.getDate() + days);
    return Math.floor((next - now) / 1000);
  }
  return 0;
}

export function fmtCountdown(secs) {
  if (secs <= 0) return { text: '00:00:00', live: true, urgent: true };
  
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = secs % 60;
  
  const text = [h, m, s].map(v => String(v).padStart(2, '0')).join(':');
  const urgent = secs < 300; // 5 minutes
  const live = secs <= 0;
  
  return { text, live, urgent };
}

const DAYS_FULL = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];

export function nextRunLabel(schedule) {
  const day = DAYS_FULL[schedule.weekday];
  const hh = schedule.hour % 12 || 12;
  const ampm = schedule.hour >= 12 ? 'PM' : 'AM';
  const mm = String(schedule.minute).padStart(2, '0');
  
  if (schedule.type === 'daily') {
    return `Every day at ${hh}:${mm} ${ampm} IST`;
  } else {
    return `Every ${day} at ${hh}:${mm} ${ampm} IST`;
  }
}
