import React, { useState, useEffect, useLayoutEffect } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity,
  StyleSheet, Alert, Linking, Share,
} from 'react-native';
import { useLocalSearchParams, useRouter, useNavigation } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { C, R, S } from '../../src/utils/theme';
import { loadAgents, saveAgents } from '../../src/utils/storage';
import { Countdown } from '../../src/components/Countdown';
import { nextRunLabel } from '../../src/utils/countdown';
import {
  Card, Row, Label, Div, Chip, Btn,
  FieldRow, SectionTitle, ToggleRow,
} from '../../src/components/UI';
import QRCode from 'react-native-qrcode-svg';

const PARTY_SIZES = ['1','2','3','4','5','6'];
const SLOTS = [
  '12:00 PM','12:30 PM','1:00 PM','1:30 PM','2:00 PM','2:30 PM',
  '4:30 PM','6:00 PM','6:30 PM','7:00 PM','7:30 PM','8:00 PM','8:30 PM','9:00 PM',
];
const DAYS = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];

export default function AgentDetail() {
  const { id } = useLocalSearchParams();
  const router = useRouter();
  const nav    = useNavigation();
  const [agent, setAgent] = useState(null);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [triggering, setTriggering] = useState(false);

  async function triggerRun() {
    if (!agent.github || !agent.githubToken) {
      Alert.alert('Setup Required', 'Please set your GitHub repo and Personal Access Token below.');
      return;
    }
    setTriggering(true);
    try {
      const [owner, repo] = agent.github.split('/');
      const workflow = agent.id === 'naru' ? 'naru-booking.yml' : 'pizza4ps-booking.yml';
      const res = await fetch(
        `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflow}/dispatches`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${agent.githubToken}`,
            Accept: 'application/vnd.github+json',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ ref: 'main' }),
        }
      );
      if (!res.ok) throw new Error(`GitHub API error: ${res.status}`);
      Alert.alert('Triggered', 'Booking agent started! Check back in 2–3 minutes for results.');
    } catch (e) {
      Alert.alert('Error', e.message);
    }
    setTriggering(false);
  }

  useEffect(() => {
    loadAgents().then(list => {
      const found = list.find(a => a.id === id);
      if (found) setAgent(JSON.parse(JSON.stringify(found)));
    });
  }, [id]);

  useLayoutEffect(() => {
    nav.setOptions({
      headerRight: dirty ? () => (
        <TouchableOpacity onPress={save} style={{ marginRight:4 }}>
          <Text style={{ color:C.accent, fontWeight:'700', fontSize:15 }}>Save</Text>
        </TouchableOpacity>
      ) : undefined,
    });
  }, [dirty, agent]);

  function set(path, val) {
    setAgent(prev => {
      const next = JSON.parse(JSON.stringify(prev));
      const keys = path.split('.');
      let cur = next;
      for (let i = 0; i < keys.length - 1; i++) cur = cur[keys[i]];
      cur[keys[keys.length - 1]] = val;
      return next;
    });
    setDirty(true);
  }

  function toggleArr(path, item) {
    const keys = path.split('.');
    let cur = agent;
    for (const k of keys) cur = cur[k];
    const arr = cur || [];
    set(path, arr.includes(item) ? arr.filter(x => x !== item) : [...arr, item]);
  }

  async function save() {
    setSaving(true);
    const list = await loadAgents();
    await saveAgents(list.map(a => a.id === agent.id ? agent : a));
    setSaving(false);
    setDirty(false);
    Alert.alert('Saved', 'Agent updated successfully.');
  }

  async function syncToGitHub() {
    if (!agent.githubToken || !agent.github) {
      Alert.alert('Missing Setup', 'Please set your GitHub PAT and repo first.');
      return;
    }
    setSaving(true);
    try {
      const [owner, repo] = agent.github.split('/');
      const workflowPath = `.github/workflows/${agent.id}-booking.yml`;
      const headers = {
        Authorization: `Bearer ${agent.githubToken}`,
        Accept: 'application/vnd.github+json',
        'Content-Type': 'application/json',
      };

      // Get current file content
      const getRes = await fetch(
        `https://api.github.com/repos/${owner}/${repo}/contents/${workflowPath}`,
        { headers }
      );
      if (!getRes.ok) throw new Error(`Could not fetch workflow: ${getRes.status}`);
      const fileData = await getRes.json();
      let content = atob(fileData.content.replace(/\n/g, ''));
      
      // IST to UTC
      let totalMins = agent.schedule.hour * 60 + agent.schedule.minute;
      let utcMins = (totalMins - 330 + 1440) % 1440;
      let h = Math.floor(utcMins / 60);
      let m = utcMins % 60;
      let d = agent.schedule.type === 'weekly' ? agent.schedule.weekday : '*';
      const cron = `${m} ${h} * * ${d}`;
      
      const regex = /cron:\s*['"][^'"]*['"]/;
      if (!regex.test(content)) throw new Error('Could not find cron schedule in workflow file.');
      content = content.replace(regex, `cron: '${cron}'`);
      
      // Update file
      const putRes = await fetch(
        `https://api.github.com/repos/${owner}/${repo}/contents/${workflowPath}`,
        {
          method: 'PUT',
          headers,
          body: JSON.stringify({
            message: `chore: update booking schedule to ${nextRunLabel(agent.schedule)}`,
            content: btoa(content),
            sha: fileData.sha,
          }),
        }
      );
      if (!putRes.ok) throw new Error(`Could not update workflow: ${putRes.status}`);
      
      Alert.alert('Synced!', 'GitHub automation schedule updated. The bot will now run at the new time!');
    } catch (e) {
      Alert.alert('Sync Error', e.message);
    }
    setSaving(false);
  }

  async function deleteAgent() {
    Alert.alert('Delete', `Remove ${agent.name}?`, [
      { text:'Cancel', style:'cancel' },
      { text:'Delete', style:'destructive', onPress: async () => {
        const list = await loadAgents();
        await saveAgents(list.filter(a => a.id !== id));
        router.back();
      }},
    ]);
  }

  if (!agent) return <View style={{ flex:1, backgroundColor:C.bg }} />;

  const lastEntry = (agent.history || []).slice(-1)[0];

  return (
    <ScrollView style={{ flex:1, backgroundColor:C.bg }}
      contentContainerStyle={{ padding:S.md, paddingBottom:S.xl }}>

      {/* ── Hero ── */}
      <Card accent={agent.color}>
        <Row style={{ gap:S.sm, marginBottom:S.md }}>
          <View style={[st.heroEmoji, { backgroundColor:agent.color+'18', borderColor:agent.color+'33' }]}>
            <Text style={{ fontSize:30 }}>{agent.emoji}</Text>
          </View>
          <View style={{ flex:1 }}>
            <Text style={st.heroName}>{agent.name}</Text>
            <Text style={{ fontSize:12, color:C.t3 }}>{agent.cuisine}</Text>
          </View>
        </Row>

        <ToggleRow
          label="Agent enabled"
          sub={agent.enabled ? 'Runs automatically on schedule' : 'Paused — will not run'}
          value={agent.enabled}
          onChange={v => set('enabled', v)}
        />

        {agent.enabled && (
          <>
            <Div my={S.sm} />
            <Countdown schedule={agent.schedule} accentColor={agent.color} />
            <Text style={st.nextRun}>Next run: {nextRunLabel(agent.schedule)}</Text>
          </>
        )}
      </Card>

      {/* ── Action buttons ── */}
      <Row style={{ gap:S.sm, marginBottom:S.sm }}>
        <View style={{ flex:1 }}>
          <Btn
            label="Open booking page"
            icon="🔗"
            variant="ghost"
            small
            onPress={() => Linking.openURL(agent.bookingUrl)}
          />
        </View>
        <View style={{ flex:1 }}>
          <Btn
            label="Run Now"
            icon="⚡"
            variant="primary"
            small
            loading={triggering}
            onPress={triggerRun}
            color={agent.color}
          />
        </View>
        <View style={{ flex:1 }}>
          <Btn
            label="GitHub Actions"
            icon="⚙️"
            variant="ghost"
            small
            onPress={() => {
              if (!agent.github) {
                Alert.alert('No repo set', 'Add your GitHub repo below first.');
                return;
              }
              Linking.openURL(`https://github.com/${agent.github}/actions`);
            }}
          />
        </View>
      </Row>

      {/* ── Last result ── */}
      {lastEntry && (
        <Card style={[
          lastEntry.status==='success'
            ? { borderColor:C.green+'44', backgroundColor:C.greenDim }
            : { borderColor:C.red+'44',   backgroundColor:C.redDim },
        ]}>
          <Label caps style={{ marginBottom:4 }}>Last run</Label>
          <Text style={{ fontSize:16, fontWeight:'600',
            color: lastEntry.status==='success' ? C.green : C.red }}>
            {lastEntry.status==='success' ? '🎉 Booking confirmed!' : '❌ No slots available'}
          </Text>
          <Text style={{ fontSize:11, color:C.t3, marginTop:4 }}>
            {new Date(lastEntry.ts).toLocaleString('en-IN')}
          </Text>
          {lastEntry.note && (
            <Text style={{ fontSize:12, color:C.t2, marginTop:6 }}>{lastEntry.note}</Text>
          )}

          {lastEntry.status === 'success' && (
            <>
              <View style={{ alignItems: 'center', marginTop: S.md, padding: S.sm, backgroundColor: '#fff', borderRadius: R.md }}>
                <QRCode
                  value={JSON.stringify({
                    restaurant: agent.name,
                    name: agent.guest.name,
                    phone: agent.guest.phone,
                    partySize: agent.prefs.partySize,
                    date: new Date(lastEntry.ts).toLocaleDateString(),
                  })}
                  size={140}
                  color="#000"
                  backgroundColor="#fff"
                />
                <Text style={{ fontSize: 10, color: '#000', marginTop: 8, fontWeight: '600' }}>
                  SHOW THIS AT THE ENTRANCE
                </Text>
              </View>
              <TouchableOpacity 
                onPress={() => {
                  const msg = `Booking for ${agent.name}\nName: ${agent.guest.name}\nDate: ${new Date(lastEntry.ts).toLocaleDateString()}\nParty: ${agent.prefs.partySize}\n\nShow this message at the entrance.`;
                  Share.share({ message: msg });
                }}
                style={{ marginTop: S.md, padding: S.sm, backgroundColor: agent.color + '22', borderRadius: R.md, alignItems: 'center', borderWidth: 1, borderColor: agent.color + '44' }}>
                <Text style={{ color: agent.color, fontWeight: '700', fontSize: 13 }}>📤 Share Booking Details</Text>
              </TouchableOpacity>
            </>
          )}
        </Card>
      )}

      {/* ─────────── GUEST DETAILS ─────────── */}
      <SectionTitle title="Guest details" />
      <Card>
        <FieldRow label="Full name"   value={agent.guest.name}
          onChange={v=>set('guest.name',v)}  placeholder="Your name" />
        <FieldRow label="Phone"       value={agent.guest.phone}
          onChange={v=>set('guest.phone',v)} placeholder="+91 XXXXX XXXXX"
          keyboardType="phone-pad" />
        <FieldRow label="Email"       value={agent.guest.email}
          onChange={v=>set('guest.email',v)} placeholder="you@email.com"
          keyboardType="email-address" last />
      </Card>

      {/* ─────────── BOOKING PREFS ─────────── */}
      <SectionTitle title="Booking preferences" />
      <Card>
        <Label size={13} color={C.t2} style={{ marginBottom:S.sm }}>Party size</Label>
        <View style={st.chipRow}>
          {PARTY_SIZES.map(sz => (
            <Chip key={sz} label={sz}
              active={String(agent.prefs.partySize)===sz}
              onPress={()=>set('prefs.partySize', Number(sz))}
              color={agent.color}
            />
          ))}
        </View>

        <Div />

        <Label size={13} color={C.t2} style={{ marginBottom:S.sm }}>Preferred days</Label>
        <View style={st.chipRow}>
          {DAYS.map(d => (
            <Chip key={d} label={d}
              active={(agent.prefs.days||[]).includes(d)}
              onPress={()=>toggleArr('prefs.days', d)}
              color={agent.color}
            />
          ))}
        </View>

        <Div />

        <Label size={13} color={C.t2} style={{ marginBottom:S.sm }}>Preferred time slots</Label>
        <View style={st.chipRow}>
          {SLOTS.map(sl => (
            <Chip key={sl} label={sl}
              active={(agent.prefs.slots||[]).includes(sl)}
              onPress={()=>toggleArr('prefs.slots', sl)}
              color={agent.color}
            />
          ))}
        </View>

        <Div />
        <FieldRow label="Special requests"
          value={agent.prefs.specialRequest||''}
          onChange={v=>set('prefs.specialRequest',v)}
          placeholder="e.g. birthday, window seat…"
          last multiline />
      </Card>

      {/* ─────────── SCHEDULE ─────────── */}
      <SectionTitle title="Schedule (Live on Phone)" />
      <Card>
        <Label size={13} color={C.t2} style={{ marginBottom:S.sm }}>Booking frequency</Label>
        <View style={st.chipRow}>
          {['daily','weekly'].map(t => (
            <Chip key={t} label={t.toUpperCase()}
              active={agent.schedule.type===t}
              onPress={()=>set('schedule.type', t)}
              color={agent.color}
            />
          ))}
        </View>

        <Div />

        {agent.schedule.type === 'weekly' && (
          <>
            <Label size={13} color={C.t2} style={{ marginBottom:S.sm }}>Run on day</Label>
            <View style={st.chipRow}>
              {DAYS.map((d, i) => (
                <Chip key={d} label={d}
                  active={agent.schedule.weekday===i}
                  onPress={()=>set('schedule.weekday', i)}
                  color={agent.color}
                />
              ))}
            </View>
            <Div />
          </>
        )}

        <Row style={{ gap:S.md }}>
          <View style={{ flex:1 }}>
            <FieldRow label="Hour (24h)"
              value={String(agent.schedule.hour)}
              onChange={v => set('schedule.hour', Number(v) || 0)}
              keyboardType="number-pad" />
          </View>
          <View style={{ flex:1 }}>
            <FieldRow label="Minute"
              value={String(agent.schedule.minute)}
              onChange={v => set('schedule.minute', Number(v) || 0)}
              keyboardType="number-pad" last />
          </View>
        </Row>

        <View style={st.infoRow}>
          <Text style={st.infoLabel}>Timezone</Text>
          <Text style={st.infoVal}>{agent.schedule.tz}</Text>
        </View>

        <TouchableOpacity 
          style={{ 
            marginTop: S.md, 
            padding: S.sm, 
            backgroundColor: agent.color + '11', 
            borderRadius: R.sm,
            borderWidth: 1,
            borderColor: agent.color + '33',
            flexDirection: 'row',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          onPress={syncToGitHub}>
          <Ionicons name="cloud-upload-outline" size={16} color={agent.color} />
          <Text style={{ color: agent.color, fontWeight: '700', fontSize: 13, marginLeft: 8 }}>
            Sync Schedule to GitHub
          </Text>
        </TouchableOpacity>
        
        <Text style={{ fontSize:10, color:C.t3, marginTop:8, textAlign:'center' }}>
          * Sycing updates the `.yml` file in your repo so the robot runs at the new time.
        </Text>
      </Card>

      {/* ─────────── GITHUB SETUP ─────────── */}
      <SectionTitle title="GitHub Actions" />
      <Card>
        <FieldRow label="GitHub repo (username/repo-name)"
          value={agent.github||''}
          onChange={v=>set('github',v)}
          placeholder="e.g. maxthecat2024/naru-booking" />
        <FieldRow label="GitHub PAT (Personal Access Token)"
          value={agent.githubToken||''}
          onChange={v=>set('githubToken',v)}
          placeholder="ghp_xxxxxxxxxxxx"
          secureTextEntry // This won't work on FieldRow unless we pass it down
          last />
        {agent.github ? (
          <TouchableOpacity
            style={st.ghLink}
            onPress={()=>Linking.openURL(`https://github.com/${agent.github}/actions`)}>
            <Ionicons name="logo-github" size={13} color={C.t3} />
            <Text style={{ fontSize:12, color:C.t3, marginLeft:5 }}>
              github.com/{agent.github}/actions
            </Text>
          </TouchableOpacity>
        ) : (
          <Text style={{ fontSize:12, color:C.t3, marginTop:S.sm, lineHeight:18 }}>
            Set your repo above to get a direct link to the Actions tab where you can manually trigger runs.
          </Text>
        )}
      </Card>

      {/* ─────────── HISTORY ─────────── */}
      {(agent.history||[]).length > 0 && (
        <>
          <SectionTitle title="Run history" />
          <Card>
            {[...(agent.history||[])].reverse().slice(0,10).map((h, i) => (
              <View key={i} style={[st.histRow, i===0 && { paddingTop:0 }]}>
                <Text style={{ fontSize:14 }}>
                  {h.status==='success' ? '✅' : '❌'}
                </Text>
                <View style={{ flex:1, marginLeft:S.sm }}>
                  <Text style={{ fontSize:12, color:C.t2 }}>
                    {new Date(h.ts).toLocaleDateString('en-IN',{weekday:'short',month:'short',day:'numeric'})}
                  </Text>
                  {h.note && <Text style={{ fontSize:11, color:C.t3 }}>{h.note}</Text>}
                </View>
              </View>
            ))}
          </Card>
        </>
      )}

      {/* ─────────── SAVE BANNER ─────────── */}
      {dirty && (
        <View style={{ marginTop:S.sm, marginBottom:S.sm }}>
          <Btn label="Save changes" onPress={save} loading={saving} color={agent.color} />
        </View>
      )}

      {/* ─────────── DANGER ─────────── */}
      <SectionTitle title="Danger zone" />
      <Row style={{ gap:S.sm }}>
        <View style={{ flex:1 }}>
          <Btn label="Share config" variant="ghost" icon="📤"
            onPress={()=>Share.share({ message:`ReserveBot config:\n${JSON.stringify(agent,null,2)}` })} />
        </View>
        <View style={{ flex:1 }}>
          <Btn label="Delete agent" variant="danger" onPress={deleteAgent} />
        </View>
      </Row>

    </ScrollView>
  );
}

const st = StyleSheet.create({
  heroEmoji: {
    width:56, height:56, borderRadius:R.md, borderWidth:0.5,
    alignItems:'center', justifyContent:'center',
  },
  heroName: { fontSize:17, fontWeight:'700', color:C.t1 },
  nextRun: { fontSize:11, color:C.t3, textAlign:'center', marginTop:-4 },
  chipRow: { flexDirection:'row', flexWrap:'wrap' },
  infoRow: {
    flexDirection:'row', justifyContent:'space-between', alignItems:'center',
    paddingVertical:10, borderBottomWidth:0.5, borderBottomColor:C.border,
  },
  infoLabel: { fontSize:13, color:C.t2 },
  infoVal:   { fontSize:13, color:C.t1, fontWeight:'500' },
  ghLink: { flexDirection:'row', alignItems:'center', marginTop:S.sm },
  histRow: {
    flexDirection:'row', alignItems:'flex-start',
    paddingVertical:8, borderBottomWidth:0.5, borderBottomColor:C.border,
  },
});
