import React from 'react';
import {
  View, Text, TouchableOpacity, TextInput,
  StyleSheet, ActivityIndicator, Switch,
} from 'react-native';
import { C, R, S } from '../utils/theme';

/* ── Card ──────────────────────────────────────────── */
export function Card({ children, style, accent }) {
  return (
    <View style={[st.card, accent && { borderColor: accent + '55' }, style]}>
      {children}
    </View>
  );
}

/* ── Row ───────────────────────────────────────────── */
export function Row({ children, style }) {
  return <View style={[st.row, style]}>{children}</View>;
}

/* ── Label ─────────────────────────────────────────── */
export function Label({ children, size = 12, color = C.t3, style, caps }) {
  return (
    <Text style={[{ fontSize:size, color, letterSpacing: caps ? 1.1 : 0,
      textTransform: caps ? 'uppercase' : 'none', fontWeight: caps ? '700' : '400' }, style]}>
      {children}
    </Text>
  );
}

/* ── Divider ───────────────────────────────────────── */
export function Div({ my = S.sm }) {
  return <View style={{ height: 0.5, backgroundColor: C.border, marginVertical: my }} />;
}

/* ── Chip ──────────────────────────────────────────── */
export function Chip({ label, active, onPress, color = C.accent }) {
  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.7}
      style={[st.chip, active && { backgroundColor: color, borderColor: color }]}>
      <Text style={[st.chipTxt, active && { color: '#0A0A0A', fontWeight:'700' }]}>
        {label}
      </Text>
    </TouchableOpacity>
  );
}

/* ── Button ────────────────────────────────────────── */
export function Btn({ label, onPress, variant='primary', disabled, loading, small, icon, color }) {
  const bg = variant === 'primary'
    ? (color || C.accent)
    : variant === 'danger' ? C.redDim : 'transparent';
  const tc = variant === 'primary' ? '#0A0A0A'
    : variant === 'danger' ? C.red : C.t2;
  const bc = variant === 'primary'
    ? (color || C.accent)
    : variant === 'danger' ? C.red + '44' : C.border;

  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={disabled || loading}
      activeOpacity={0.75}
      style={[st.btn, { backgroundColor:bg, borderColor:bc },
        small && st.btnSm, (disabled||loading) && { opacity:0.4 }]}>
      {loading
        ? <ActivityIndicator size="small" color={tc} />
        : <Text style={[st.btnTxt, { color:tc }, small && { fontSize:12 }]}>
            {icon}{icon ? '  ' : ''}{label}
          </Text>}
    </TouchableOpacity>
  );
}

/* ── FieldRow ──────────────────────────────────────── */
export function FieldRow({ label, value, onChange, placeholder, keyboardType, last, multiline, secureTextEntry }) {
  return (
    <View style={[st.fieldRow, last && { borderBottomWidth:0 }]}>
      <Text style={st.fieldLabel}>{label}</Text>
      <TextInput
        style={[st.fieldInput, multiline && { height:56, textAlignVertical:'top', paddingTop:4 }]}
        value={value}
        onChangeText={onChange}
        placeholder={placeholder}
        placeholderTextColor={C.t3}
        keyboardType={keyboardType || 'default'}
        autoCapitalize="none"
        multiline={multiline}
        secureTextEntry={secureTextEntry}
      />
    </View>
  );
}

/* ── SectionTitle ──────────────────────────────────── */
export function SectionTitle({ title }) {
  return (
    <Text style={st.sectionTitle}>{title.toUpperCase()}</Text>
  );
}

/* ── Toggle Row ─────────────────────────────────────── */
export function ToggleRow({ label, sub, value, onChange }) {
  return (
    <View style={st.toggleRow}>
      <View style={{ flex:1 }}>
        <Text style={{ fontSize:14, color:C.t1 }}>{label}</Text>
        {sub && <Text style={{ fontSize:12, color:C.t3, marginTop:2 }}>{sub}</Text>}
      </View>
      <Switch
        value={value}
        onValueChange={onChange}
        trackColor={{ false:C.elevated, true:'rgba(232,167,74,0.35)' }}
        thumbColor={value ? C.accent : C.t3}
        ios_backgroundColor={C.elevated}
      />
    </View>
  );
}

const st = StyleSheet.create({
  card: {
    backgroundColor: C.card,
    borderRadius: R.lg,
    borderWidth: 0.5,
    borderColor: C.border,
    padding: S.md,
    marginBottom: S.sm,
  },
  row: { flexDirection:'row', alignItems:'center' },
  chip: {
    paddingHorizontal: 14, paddingVertical: 7,
    borderRadius: R.full, borderWidth: 0.5,
    borderColor: C.border,
    marginRight: S.xs, marginBottom: S.xs,
  },
  chipTxt: { fontSize:13, color:C.t2, fontWeight:'500' },
  btn: {
    borderRadius: R.md, paddingVertical: 13, paddingHorizontal: 20,
    alignItems:'center', justifyContent:'center', borderWidth: 0.5,
  },
  btnSm: { paddingVertical:9, paddingHorizontal:14 },
  btnTxt: { fontSize:14, fontWeight:'700', letterSpacing:0.2 },
  fieldRow: {
    paddingVertical: 12,
    borderBottomWidth: 0.5, borderBottomColor: C.border,
  },
  fieldLabel: { fontSize:11, color:C.t3, marginBottom:6, letterSpacing:0.5 },
  fieldInput: { fontSize:14, color:C.t1 },
  sectionTitle: {
    fontSize:11, fontWeight:'700', color:C.t3,
    letterSpacing:1.2, marginTop:S.md, marginBottom:S.sm,
  },
  toggleRow: {
    flexDirection:'row', alignItems:'center',
    paddingVertical:12,
    borderBottomWidth:0.5, borderBottomColor:C.border,
  },
});
