import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { C } from '../src/utils/theme';

export default function RootLayout() {
  return (
    <>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerStyle:       { backgroundColor: C.bg },
          headerTintColor:   C.t1,
          headerShadowVisible: false,
          headerBackTitle:   '',
          contentStyle:      { backgroundColor: C.bg },
          animation:         'slide_from_right',
        }}>
        <Stack.Screen
          name="index"
          options={{ headerShown: false }}
        />
        <Stack.Screen
          name="agent/[id]"
          options={{ title: 'Configure agent', headerBackTitle: 'Back' }}
        />
        <Stack.Screen
          name="add"
          options={{ title: 'Add restaurant', presentation: 'modal' }}
        />
      </Stack>
    </>
  );
}
