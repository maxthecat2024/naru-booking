import React, { useState, useEffect, useRef } from 'react';
import { View, Text, Animated, StyleSheet } from 'react-native';
import { secsUntilNext, fmtCountdown } from '../utils/countdown';
import { C, R, S } from '../utils/theme';

export function Countdown({ schedule, compact, accentColor }) {
  const [secs, setSecs] = useState(() => secsUntilNext(schedule));
  const pulse = useRef(new Animated.Value(1)).current;
  const color = accentColor || C.accent;

  useEffect(() => {
    const t = setInterval(() => setSecs(secsUntilNext(schedule)), 1000);
    return () => clearInterval(t);
  }, [schedule]);

  const { text, live, urgent } = fmtCountdown(secs);

  useEffect(() => {
    if (live) {
      Animated.loop(Animated.sequence([
        Animated.timing(pulse, { toValue:1.04, duration:700, useNativeDriver:true }),
        Animated.timing(pulse, { toValue:1,    duration:700, useNativeDriver:true }),
      ])).start();
    } else {
      pulse.setValue(1);
    }
  }, [live]);

  if (compact) {
    const dotColor = live ? C.green : urgent ? color : C.t3;
    const pillBg   = live ? C.greenDim : urgent ? (color+'18') : C.elevated;
    return (
      <View style={[st.pill, { backgroundColor:pillBg }]}>
        <Animated.View style={[st.dot, { backgroundColor:dotColor },
          live && { transform:[{scale:pulse}] }]} />
        <Text style={[st.pillTxt, { color: live ? C.green : urgent ? color : C.t2 }]}>
          {live ? 'OPEN NOW' : text}
        </Text>
      </View>
    );
  }

  return (
    <Animated.View style={[st.big, live && { borderColor:C.green+'44', backgroundColor:C.greenDim },
      { transform:[{scale: live ? pulse : 1}] }]}>
      <Text style={st.bigLabel}>
        {live ? '🟢 BOOKING WINDOW IS OPEN' : 'next window opens in'}
      </Text>
      <Text style={[st.bigTime,
        live  && { color:C.green,  fontSize:26, letterSpacing:3 },
        urgent && !live && { color },
      ]}>
        {text}
      </Text>
      <Text style={st.bigSub}>{schedule.label}</Text>
    </Animated.View>
  );
}

const st = StyleSheet.create({
  pill: {
    flexDirection:'row', alignItems:'center',
    paddingHorizontal:10, paddingVertical:5,
    borderRadius:R.full, gap:6,
  },
  dot:    { width:6, height:6, borderRadius:3 },
  pillTxt:{ fontSize:12, fontWeight:'600' },
  big: {
    backgroundColor: C.card,
    borderRadius: R.lg, borderWidth:0.5, borderColor:C.border,
    padding:S.lg, alignItems:'center', marginBottom:S.sm,
  },
  bigLabel:{ fontSize:11, fontWeight:'700', color:C.t3, letterSpacing:1, textTransform:'uppercase' },
  bigTime: { fontSize:42, fontWeight:'200', color:C.t1, letterSpacing:-1, marginVertical:6 },
  bigSub:  { fontSize:12, color:C.t3 },
});
