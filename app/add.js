import React, { useState } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity,
  StyleSheet, Alert, TextInput,
} from 'react-native';
import { useRouter } from 'expo-router';
import { C, R, S } from '../src/utils/theme';
import { loadAgents, saveAgents } from '../src/utils/storage';
import { Btn, SectionTitle, Chip, Card, Div } from '../src/components/UI';

const EMOJIS  = ['🍜','🍕','🍣','🍔','🥘','🍱','🥗','🍷','☕','🍰','🌮','🍛'];
const COLORS  = ['#E8A74A','#F87171','#60A5FA','#4ADE80','#A78BFA','#F472B6','#34D399','#FB923C'];
const SIZES   = ['1','2','3','4','5','6'];
const FREQ    = [
  { label:'Every Monday',    type:'weekly', weekday:1, hour:20, minute:0,  schedLabel:'Every Monday at 8:00 PM IST' },
  { label:'Every Tuesday',   type:'weekly', weekday:2, hour:10, minute:0,  schedLabel:'Every Tuesday at 10:00 AM IST' },
  { label:'Every day 10 AM', type:'daily',  weekday:null, hour:10, minute:0, schedLabel:'Every day at 10:00 AM IST' },
  { label:'Every day 8 PM',  type:'daily',  weekday:null, hour:20, minute:0, schedLabel:'Every day at 8:00 PM IST' },
];

export default function AddScreen() {
  const router = useRouter();
  const [name,    setName]    = useState('');
  const [cuisine, setCuisine] = useState('');
  const [url,     setUrl]     = useState('');
  const [emoji,   setEmoji]   = useState('🍜');
  const [color,   setColor]   = useState('#E8A74A');
  const [size,    setSize]    = useState('2');
  const [freq,    setFreq]    = useState(0);
  const [gName,   setGName]   = useState('');
  const [gPhone,  setGPhone]  = useState('');
  const [gEmail,  setGEmail]  = useState('');
  const [github,  setGithub]  = useState('');
  const [saving,  setSaving]  = useState(false);

  const valid = name.trim() && url.trim() && gEmail.trim();

  async function add() {
    if (!valid) { Alert.alert('Required', 'Please fill in name, booking URL, and email.'); return; }
    setSaving(true);
    const sched = FREQ[freq];
    const agents = await loadAgents();
    const id = name.toLowerCase().replace(/[^a-z0-9]/g,'-') + '-' + Date.now();
    await saveAgents([...agents, {
      id, name:name.trim(), cuisine:cuisine.trim(), emoji, color,
      bookingUrl: url.trim(),
      enabled: false,
      schedule: { type:sched.type, weekday:sched.weekday, hour:sched.hour, minute:sched.minute,
                  tz:'Asia/Kolkata', label:sched.schedLabel },
      prefs: { partySize:Number(size), slots:[], days:['Fri','Sat','Sun'], specialRequest:'' },
      guest: { name:gName.trim(), phone:gPhone.trim(), email:gEmail.trim() },
      github: github.trim(),
      history: [],
    }]);
    setSaving(false);
    router.back();
  }

  return (
    <ScrollView style={{ flex:1, backgroundColor:C.bg }}
      contentContainerStyle={{ padding:S.md, paddingBottom:S.xl }}>

      <SectionTitle title="Restaurant" />
      <Card>
        <Field label="Name" value={name} set={setName} placeholder="e.g. Pizza 4P's" />
        <Field label="Cuisine / location" value={cuisine} set={setCuisine} placeholder="e.g. Italian · Indiranagar" />
        <Field label="Booking URL" value={url} set={setUrl}
          placeholder="https://..." keyboardType="url" last />
      </Card>

      <SectionTitle title="Look" />
      <Card>
        <Text style={st.lbl}>Emoji</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom:S.sm }}>
          <View style={{ flexDirection:'row', gap:S.sm, paddingVertical:4 }}>
            {EMOJIS.map(e => (
              <TouchableOpacity key={e} onPress={()=>setEmoji(e)}
                style={[st.emojiBtn, emoji===e && { borderColor:color, borderWidth:2 }]}>
                <Text style={{ fontSize:24 }}>{e}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </ScrollView>
        <Div />
        <Text style={[st.lbl, { marginTop:S.sm }]}>Accent colour</Text>
        <View style={{ flexDirection:'row', flexWrap:'wrap', gap:S.sm }}>
          {COLORS.map(c => (
            <TouchableOpacity key={c} onPress={()=>setColor(c)}
              style={[st.colorBtn, { backgroundColor:c }, color===c && st.colorBtnActive]} />
          ))}
        </View>
      </Card>

      <SectionTitle title="Schedule" />
      <Card>
        <Text style={st.lbl}>Booking window opens</Text>
        <View style={st.chipRow}>
          {FREQ.map((f,i) => (
            <Chip key={i} label={f.label} active={freq===i} onPress={()=>setFreq(i)} color={color} />
          ))}
        </View>
      </Card>

      <SectionTitle title="Guest details" />
      <Card>
        <Field label="Full name" value={gName} set={setGName} placeholder="Your name" />
        <Field label="Phone"     value={gPhone} set={setGPhone} placeholder="+91…" keyboardType="phone-pad" />
        <Field label="Email"     value={gEmail} set={setGEmail} placeholder="you@email.com"
          keyboardType="email-address" last />
      </Card>

      <SectionTitle title="Party size" />
      <Card>
        <View style={st.chipRow}>
          {SIZES.map(sz => (
            <Chip key={sz} label={sz} active={size===sz} onPress={()=>setSize(sz)} color={color} />
          ))}
        </View>
      </Card>

      <SectionTitle title="GitHub Actions (optional)" />
      <Card>
        <Field label="Repo (username/repo-name)" value={github} set={setGithub}
          placeholder="e.g. maxthecat2024/naru-booking" last />
      </Card>

      <View style={{ marginTop:S.md }}>
        <Btn label="Add agent" onPress={add} loading={saving} disabled={!valid} color={color} />
      </View>
      <Text style={st.hint}>Enable the agent and configure slots on the detail screen after adding.</Text>
    </ScrollView>
  );
}

function Field({ label, value, set, placeholder, keyboardType, last }) {
  return (
    <View style={[st.fieldRow, last && { borderBottomWidth:0 }]}>
      <Text style={st.lbl}>{label}</Text>
      <TextInput style={st.input} value={value} onChangeText={set}
        placeholder={placeholder} placeholderTextColor={C.t3}
        keyboardType={keyboardType||'default'} autoCapitalize="none" />
    </View>
  );
}

const st = StyleSheet.create({
  lbl: { fontSize:11, color:C.t3, letterSpacing:0.5, marginBottom:6 },
  fieldRow: { paddingVertical:10, borderBottomWidth:0.5, borderBottomColor:C.border },
  input: { fontSize:14, color:C.t1 },
  chipRow: { flexDirection:'row', flexWrap:'wrap' },
  emojiBtn: {
    width:48, height:48, borderRadius:R.md, backgroundColor:C.elevated,
    alignItems:'center', justifyContent:'center', borderWidth:1, borderColor:'transparent',
  },
  colorBtn: {
    width:32, height:32, borderRadius:R.full, borderWidth:2, borderColor:'transparent',
  },
  colorBtnActive: { borderColor:C.t1 },
  hint: { fontSize:12, color:C.t3, textAlign:'center', marginTop:S.md, lineHeight:18 },
});
