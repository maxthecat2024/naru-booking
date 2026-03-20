import React, { useState, useCallback } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity,
  StyleSheet, RefreshControl, Linking, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { C, R, S } from '../src/utils/theme';
import { loadAgents, saveAgents } from '../src/utils/storage';
import { Countdown } from '../src/components/Countdown';
import { nextRunLabel } from '../src/utils/countdown';

export default function Home() {
  const [agents, setAgents] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const router = useRouter();

  const load = async () => {
    setAgents(await loadAgents());
  };

  useFocusEffect(useCallback(() => { load(); }, []));

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  const toggle = async (id, val) => {
    const next = agents.map(a => a.id === id ? { ...a, enabled: val } : a);
    setAgents(next);
    await saveAgents(next);
  };

  const active = agents.filter(a => a.enabled).length;
  const booked = agents.reduce((n, a) =>
    n + (a.history || []).filter(h => h.status === 'success').length, 0);

  return (
    <SafeAreaView style={{ flex:1, backgroundColor:C.bg }} edges={['top']}>
      {/* ── Header ── */}
      <View style={st.header}>
        <View>
          <Text style={st.appName}>ReserveBot</Text>
          <Text style={st.appSub}>Automatic restaurant booking</Text>
        </View>
        <TouchableOpacity
          onPress={() => router.push('/add')}
          style={st.addBtn}>
          <Ionicons name="add" size={22} color={C.accent} />
        </TouchableOpacity>
      </View>

      <ScrollView
        style={{ flex:1 }}
        contentContainerStyle={{ padding:S.md, paddingBottom:S.xl }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={C.accent} />}>

        {/* ── Stats ── */}
        <View style={st.statsRow}>
          {[
            { n: agents.length, lbl: 'restaurants' },
            { n: active,        lbl: 'active',  color: active > 0 ? C.green : C.t3 },
            { n: booked,        lbl: 'booked',  color: C.accent },
          ].map(({ n, lbl, color }) => (
            <View key={lbl} style={st.stat}>
              <Text style={[st.statN, color && { color }]}>{n}</Text>
              <Text style={st.statL}>{lbl}</Text>
            </View>
          ))}
        </View>

        {/* ── Notice ── */}
        <View style={st.notice}>
          <Ionicons name="information-circle-outline" size={14} color={C.accent} />
          <Text style={st.noticeTxt}>
            Agents run on GitHub Actions. Tap any agent to configure or trigger manually.
          </Text>
        </View>

        {/* ── Agent cards ── */}
        <Text style={st.sectionHdr}>YOUR AGENTS</Text>
        {agents.map(agent => (
          <AgentCard key={agent.id} agent={agent} onToggle={toggle} onPress={() =>
            router.push(`/agent/${agent.id}`)} />
        ))}

        {/* ── GitHub shortcut ── */}
        <TouchableOpacity
          style={st.ghRow}
          onPress={() => Linking.openURL('https://github.com')}>
          <Ionicons name="logo-github" size={15} color={C.t3} />
          <Text style={{ fontSize:13, color:C.t3, marginLeft:6 }}>Open GitHub Actions</Text>
          <Ionicons name="open-outline" size={13} color={C.t3} style={{ marginLeft:4 }} />
        </TouchableOpacity>

      </ScrollView>
    </SafeAreaView>
  );
}

function AgentCard({ agent, onToggle, onPress }) {
  const lastEntry = (agent.history || []).slice(-1)[0];
  const statusColor =
    !agent.enabled     ? C.t3 :
    !lastEntry         ? C.accent :
    lastEntry.status === 'success' ? C.green : C.red;
  const statusLabel =
    !agent.enabled     ? 'Paused' :
    !lastEntry         ? 'Active' :
    lastEntry.status === 'success' ? '✓ Booked' : '✗ No slot';

  return (
    <TouchableOpacity onPress={onPress} activeOpacity={0.82} style={st.card}>
      {/* top row */}
      <View style={st.cardTop}>
        <View style={[st.emojiBox, { backgroundColor: agent.color + '18', borderColor: agent.color + '33' }]}>
          <Text style={{ fontSize:24 }}>{agent.emoji}</Text>
        </View>
        <View style={{ flex:1 }}>
          <Text style={st.cardName}>{agent.name}</Text>
          <Text style={st.cardCuisine}>{agent.cuisine}</Text>
        </View>
        {/* status badge */}
        <View style={[st.badge, { backgroundColor: statusColor + '18' }]}>
          <Text style={[st.badgeTxt, { color: statusColor }]}>{statusLabel}</Text>
        </View>
      </View>

      {/* countdown pill */}
      {agent.enabled && (
        <View style={{ marginBottom:S.sm }}>
          <Countdown schedule={agent.schedule} compact accentColor={agent.color} />
        </View>
      )}

      {/* bottom row */}
      <View style={[st.cardBot]}>
        <Text style={st.cardInfo}>
          👤 {agent.prefs.partySize} · {agent.schedule.label}
        </Text>
        <TouchableOpacity
          onPress={() => onToggle(agent.id, !agent.enabled)}
          style={[st.toggleBtn, agent.enabled && { backgroundColor: agent.color + '22', borderColor: agent.color + '55' }]}>
          <Text style={[st.toggleTxt, { color: agent.enabled ? agent.color : C.t3 }]}>
            {agent.enabled ? 'On' : 'Off'}
          </Text>
        </TouchableOpacity>
      </View>
    </TouchableOpacity>
  );
}

const st = StyleSheet.create({
  header: {
    flexDirection:'row', justifyContent:'space-between', alignItems:'center',
    paddingHorizontal:S.md, paddingVertical:S.md,
    borderBottomWidth:0.5, borderBottomColor:C.border,
  },
  appName: { fontSize:22, fontWeight:'700', color:C.t1 },
  appSub:  { fontSize:12, color:C.t3, marginTop:2 },
  addBtn: {
    width:38, height:38, borderRadius:R.full,
    borderWidth:1, borderColor:C.accentBorder,
    backgroundColor:C.accentDim,
    alignItems:'center', justifyContent:'center',
  },
  statsRow: {
    flexDirection:'row', justifyContent:'space-around',
    backgroundColor:C.card, borderRadius:R.lg, borderWidth:0.5, borderColor:C.border,
    padding:S.md, marginBottom:S.md,
  },
  stat:  { alignItems:'center' },
  statN: { fontSize:30, fontWeight:'200', color:C.t1 },
  statL: { fontSize:11, color:C.t3, marginTop:2 },
  notice: {
    flexDirection:'row', gap:8, alignItems:'flex-start',
    backgroundColor:C.accentDim, borderRadius:R.md, borderWidth:0.5,
    borderColor:C.accentBorder, padding:S.sm, marginBottom:S.md,
  },
  noticeTxt: { fontSize:12, color:C.accent, flex:1, lineHeight:18 },
  sectionHdr: { fontSize:11, fontWeight:'700', color:C.t3, letterSpacing:1.2, marginBottom:S.sm },
  card: {
    backgroundColor:C.card, borderRadius:R.lg, borderWidth:0.5,
    borderColor:C.border, padding:S.md, marginBottom:S.sm,
  },
  cardTop: { flexDirection:'row', alignItems:'center', gap:S.sm, marginBottom:S.sm },
  emojiBox: {
    width:48, height:48, borderRadius:R.md, borderWidth:0.5,
    alignItems:'center', justifyContent:'center',
  },
  cardName:    { fontSize:15, fontWeight:'600', color:C.t1 },
  cardCuisine: { fontSize:12, color:C.t3, marginTop:1 },
  badge: {
    paddingHorizontal:10, paddingVertical:4,
    borderRadius:R.full, alignSelf:'flex-start',
  },
  badgeTxt: { fontSize:11, fontWeight:'700' },
  cardBot: { flexDirection:'row', justifyContent:'space-between', alignItems:'center' },
  cardInfo: { fontSize:12, color:C.t3 },
  toggleBtn: {
    paddingHorizontal:14, paddingVertical:5,
    borderRadius:R.full, borderWidth:0.5, borderColor:C.border,
  },
  toggleTxt: { fontSize:12, fontWeight:'700' },
  ghRow: {
    flexDirection:'row', alignItems:'center', justifyContent:'center',
    marginTop:S.md,
  },
});
