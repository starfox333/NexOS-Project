// ============================================================
// FULL-DIVE PROTOTYPE V1 - RGB 12V + AUDIO
// Bande LED RGB analogique 12V + Audio binaural
// ============================================================
// Matériel :
//   - Arduino Uno
//   - Bande LED RGB 12V (30 LEDs / 10 segments)
//   - 3x Transistors (TIP120/2N2222) ou MOSFETs (IRLZ44N)
//   - 3x Résistances 1kΩ (pour base transistors)
//   - Alimentation 12V
//   - 2 haut-parleurs + ampli
// ============================================================
//
// CÂBLAGE :
//
//    +12V ────────────────────────┐
//                                 │
//         ┌───────────────────────┼───┐
//         │    BANDE LED RGB 12V  │   │
//         │   +12V   R    G    B  │   │
//         └─────────┬────┬────┬───┘   │
//                   │    │    │       │
//              ┌────┘    │    └────┐  │
//              │         │         │  │
//           [C/D]     [C/D]     [C/D] │  ← Collecteur/Drain
//         ┌──┴──┐   ┌──┴──┐   ┌──┴──┐│
//         │ T1  │   │ T2  │   │ T3  ││    (Transistors)
//         └──┬──┘   └──┬──┘   └──┬──┘│
//           [B]      [B]      [B]    │  ← Base (via 1kΩ)
//            │        │        │     │
//    Pin 9 ──┴─[1kΩ]  │        │     │
//    Pin 10 ──────────┴─[1kΩ]  │     │
//    Pin 11 ───────────────────┴─[1kΩ]
//                                    │
//    GND ────────────────────────────┘
//
// ============================================================

// === PINS RGB (PWM) ===
#define PIN_RED     9    // Rouge - PWM
#define PIN_GREEN   10   // Vert - PWM
#define PIN_BLUE    11   // Bleu - PWM

// === PINS AUDIO ===
#define PIN_AUDIO_L 3    // Audio gauche (PWM) - changé car 9,10,11 pris
#define PIN_AUDIO_R 5    // Audio droit (PWM)

// === VARIABLES ===
uint8_t currentMode = 1;
uint8_t currentPreset = 0;
uint8_t brightness = 255;  // Luminosité globale (0-255)

unsigned long lastUpdate = 0;
unsigned long lastAudioUpdate = 0;

// === COULEURS PRÉDÉFINIES ===
struct RGB {
  uint8_t r, g, b;
};

RGB COLOR_CYAN     = {0, 200, 255};    // Style AmuSphere
RGB COLOR_RED      = {255, 0, 0};
RGB COLOR_GREEN    = {0, 255, 0};
RGB COLOR_BLUE     = {0, 0, 255};
RGB COLOR_WHITE    = {255, 255, 255};
RGB COLOR_PURPLE   = {150, 0, 255};
RGB COLOR_ORANGE   = {255, 100, 0};
RGB COLOR_OFF      = {0, 0, 0};

// === MODES D'AFFICHAGE ===
enum DisplayMode {
  MODE_OFF,
  MODE_PULSE_AMUSPHERE,    // Pulsation cyan style SAO
  MODE_ALPHA_STIMULATION,  // 10Hz - relaxation
  MODE_BETA_STIMULATION,   // 20Hz - concentration
  MODE_THETA_STIMULATION,  // 6Hz - méditation profonde
  MODE_GAMMA_STIMULATION,  // 40Hz - cognition (recherche Alzheimer)
  MODE_COLOR_CYCLE,        // Cycle de couleurs
  MODE_BREATHING,          // Respiration guidée (4-7-8)
  MODE_BINAURAL_SYNC,      // Sync avec audio binaural
  MODE_FULL_WHITE,         // Test - tout blanc
  MODE_CUSTOM_COLOR,       // Couleur personnalisée
  NUM_MODES
};

// === PRESETS BINAURAUX ===
struct BinauralPreset {
  uint16_t baseFreq;    // Fréquence de base (Hz)
  uint16_t beatFreq;    // Fréquence de battement (Hz x10)
  uint8_t ledFreq;      // Fréquence LED (Hz)
  RGB color;            // Couleur associée
  const char* name;
};

BinauralPreset presets[] = {
  {200, 100, 10, {0, 200, 255},   "Alpha 10Hz"},    // Cyan - relaxation
  {200, 200, 20, {0, 255, 100},   "Beta 20Hz"},     // Vert - focus
  {200,  60,  6, {150, 0, 255},   "Theta 6Hz"},     // Violet - méditation
  {200,  40,  4, {0, 0, 200},     "Delta 4Hz"},     // Bleu - sommeil
  {200, 400, 40, {255, 200, 0},   "Gamma 40Hz"},    // Jaune - cognition
};
const uint8_t NUM_PRESETS = 5;

// === SETUP ===
void setup() {
  Serial.begin(115200);

  // Splash
  Serial.println(F(""));
  Serial.println(F("╔════════════════════════════════════╗"));
  Serial.println(F("║     FULL-DIVE PROTOTYPE V1         ║"));
  Serial.println(F("║     RGB 12V + Audio Binaural       ║"));
  Serial.println(F("╚════════════════════════════════════╝"));
  Serial.println(F(""));

  // Init PWM pins
  pinMode(PIN_RED, OUTPUT);
  pinMode(PIN_GREEN, OUTPUT);
  pinMode(PIN_BLUE, OUTPUT);
  pinMode(PIN_AUDIO_L, OUTPUT);
  pinMode(PIN_AUDIO_R, OUTPUT);

  // Animation de démarrage
  startupAnimation();

  // Aide
  printHelp();
}

// === LOOP ===
void loop() {
  handleSerial();
  updateDisplay();
  updateAudio();
}

// ============================================================
// CONTRÔLE RGB
// ============================================================

void setRGB(uint8_t r, uint8_t g, uint8_t b) {
  // Appliquer la luminosité globale
  r = map(r, 0, 255, 0, brightness);
  g = map(g, 0, 255, 0, brightness);
  b = map(b, 0, 255, 0, brightness);

  analogWrite(PIN_RED, r);
  analogWrite(PIN_GREEN, g);
  analogWrite(PIN_BLUE, b);
}

void setRGB(RGB color) {
  setRGB(color.r, color.g, color.b);
}

void setOff() {
  setRGB(0, 0, 0);
}

// ============================================================
// EFFETS VISUELS
// ============================================================

void updateDisplay() {
  unsigned long now = millis();

  switch (currentMode) {
    case MODE_OFF:
      setOff();
      break;

    case MODE_PULSE_AMUSPHERE:
      effectPulse(now, COLOR_CYAN, 2000);  // 2s période
      break;

    case MODE_ALPHA_STIMULATION:
      effectStrobe(now, presets[0].color, 10);  // 10Hz
      break;

    case MODE_BETA_STIMULATION:
      effectStrobe(now, presets[1].color, 20);  // 20Hz
      break;

    case MODE_THETA_STIMULATION:
      effectStrobe(now, presets[2].color, 6);   // 6Hz
      break;

    case MODE_GAMMA_STIMULATION:
      effectStrobe(now, presets[4].color, 40);  // 40Hz
      break;

    case MODE_COLOR_CYCLE:
      effectColorCycle(now);
      break;

    case MODE_BREATHING:
      effectBreathing478(now);
      break;

    case MODE_BINAURAL_SYNC:
      effectStrobe(now, presets[currentPreset].color,
                   presets[currentPreset].ledFreq);
      break;

    case MODE_FULL_WHITE:
      setRGB(COLOR_WHITE);
      break;
  }
}

// Pulsation douce (sinusoïdale)
void effectPulse(unsigned long t, RGB color, uint16_t periodMs) {
  float phase = (t % periodMs) / (float)periodMs * 2.0 * PI;
  float factor = (sin(phase) + 1.0) / 2.0;  // 0.0 à 1.0

  setRGB(color.r * factor, color.g * factor, color.b * factor);
}

// Clignotement à fréquence fixe (stimulation)
void effectStrobe(unsigned long t, RGB color, uint8_t freqHz) {
  uint16_t periodMs = 1000 / freqHz;
  bool on = (t % periodMs) < (periodMs / 2);

  if (on) {
    setRGB(color);
  } else {
    setOff();
  }
}

// Cycle arc-en-ciel
void effectColorCycle(unsigned long t) {
  uint8_t hue = (t / 20) % 256;  // Cycle complet en ~5s

  // Conversion HSV vers RGB (simplifié)
  uint8_t region = hue / 43;
  uint8_t remainder = (hue - (region * 43)) * 6;

  uint8_t p = 0;
  uint8_t q = 255 - remainder;
  uint8_t tt = remainder;

  switch (region) {
    case 0:  setRGB(255, tt, p); break;
    case 1:  setRGB(q, 255, p); break;
    case 2:  setRGB(p, 255, tt); break;
    case 3:  setRGB(p, q, 255); break;
    case 4:  setRGB(tt, p, 255); break;
    default: setRGB(255, p, q); break;
  }
}

// Respiration guidée 4-7-8
// 4s inspire (bleu monte), 7s retient (violet), 8s expire (cyan descend)
void effectBreathing478(unsigned long t) {
  uint16_t cycleMs = 19000;  // 4+7+8 = 19 secondes
  uint16_t phase = t % cycleMs;

  if (phase < 4000) {
    // Inspire - bleu qui monte
    float factor = phase / 4000.0;
    setRGB(0, 0, 255 * factor);
  }
  else if (phase < 11000) {
    // Retient - violet fixe
    setRGB(150, 0, 255);
  }
  else {
    // Expire - cyan qui descend
    float factor = 1.0 - (phase - 11000) / 8000.0;
    setRGB(0, 200 * factor, 255 * factor);
  }
}

// Animation de démarrage
void startupAnimation() {
  // Fade in cyan
  for (int i = 0; i <= 255; i += 5) {
    setRGB(0, i * 0.8, i);
    delay(10);
  }

  // Flash
  for (int j = 0; j < 3; j++) {
    setRGB(COLOR_WHITE);
    delay(50);
    setOff();
    delay(50);
  }

  // Retour au cyan
  setRGB(COLOR_CYAN);
  delay(500);
  setOff();
}

// ============================================================
// AUDIO BINAURAL
// ============================================================

void updateAudio() {
  if (currentMode == MODE_OFF) {
    noTone(PIN_AUDIO_L);
    noTone(PIN_AUDIO_R);
    return;
  }

  // Pour un vrai binaural, il faudrait 2 tons simultanés
  // Arduino ne peut faire qu'un tone() à la fois
  // On alterne rapidement pour simuler

  static bool channel = false;
  static unsigned long lastSwitch = 0;
  unsigned long now = millis();

  if (now - lastSwitch > 5) {  // Alterne toutes les 5ms
    lastSwitch = now;
    channel = !channel;

    BinauralPreset& p = presets[currentPreset];

    if (channel) {
      tone(PIN_AUDIO_L, p.baseFreq);
    } else {
      tone(PIN_AUDIO_R, p.baseFreq + p.beatFreq / 10);
    }
  }
}

void stopAudio() {
  noTone(PIN_AUDIO_L);
  noTone(PIN_AUDIO_R);
  Serial.println(F("Audio OFF"));
}

// ============================================================
// COMMANDES SERIAL
// ============================================================

void handleSerial() {
  if (!Serial.available()) return;

  char cmd = Serial.read();

  switch (cmd) {
    // Modes
    case '0': setMode(MODE_OFF); break;
    case '1': setMode(MODE_PULSE_AMUSPHERE); break;
    case '2': setMode(MODE_ALPHA_STIMULATION); break;
    case '3': setMode(MODE_BETA_STIMULATION); break;
    case '4': setMode(MODE_THETA_STIMULATION); break;
    case '5': setMode(MODE_GAMMA_STIMULATION); break;
    case '6': setMode(MODE_COLOR_CYCLE); break;
    case '7': setMode(MODE_BREATHING); break;
    case '8': setMode(MODE_BINAURAL_SYNC); break;
    case '9': setMode(MODE_FULL_WHITE); break;

    // Presets binauraux
    case 'a': setPreset(0); break;  // Alpha
    case 'b': setPreset(1); break;  // Beta
    case 't': setPreset(2); break;  // Theta
    case 'd': setPreset(3); break;  // Delta
    case 'g': setPreset(4); break;  // Gamma

    // Contrôles
    case '+': adjustBrightness(20); break;
    case '-': adjustBrightness(-20); break;
    case 's': stopAudio(); break;
    case 'h': printHelp(); break;

    // Couleurs directes
    case 'r': setRGB(COLOR_RED); break;
    case 'v': setRGB(COLOR_GREEN); break;  // v pour vert
    case 'l': setRGB(COLOR_BLUE); break;   // l pour bleu
    case 'c': setRGB(COLOR_CYAN); break;
    case 'p': setRGB(COLOR_PURPLE); break;
    case 'w': setRGB(COLOR_WHITE); break;
  }
}

void setMode(uint8_t mode) {
  currentMode = mode;
  Serial.print(F("Mode: "));
  Serial.println(mode);
}

void setPreset(uint8_t preset) {
  if (preset < NUM_PRESETS) {
    currentPreset = preset;
    Serial.print(F("Preset: "));
    Serial.println(presets[preset].name);
  }
}

void adjustBrightness(int8_t delta) {
  int16_t newBright = brightness + delta;
  brightness = constrain(newBright, 10, 255);
  Serial.print(F("Luminosité: "));
  Serial.println(brightness);
}

void printHelp() {
  Serial.println(F(""));
  Serial.println(F("=== COMMANDES ==="));
  Serial.println(F("MODES:"));
  Serial.println(F("  0 = OFF"));
  Serial.println(F("  1 = Pulse AmuSphere (cyan)"));
  Serial.println(F("  2 = Alpha 10Hz (relaxation)"));
  Serial.println(F("  3 = Beta 20Hz (focus)"));
  Serial.println(F("  4 = Theta 6Hz (méditation)"));
  Serial.println(F("  5 = Gamma 40Hz (cognition)"));
  Serial.println(F("  6 = Cycle couleurs"));
  Serial.println(F("  7 = Respiration 4-7-8"));
  Serial.println(F("  8 = Sync binaural"));
  Serial.println(F("  9 = Blanc test"));
  Serial.println(F(""));
  Serial.println(F("PRESETS AUDIO:"));
  Serial.println(F("  a=Alpha b=Beta t=Theta d=Delta g=Gamma"));
  Serial.println(F(""));
  Serial.println(F("CONTRÔLES:"));
  Serial.println(F("  +/- = luminosité"));
  Serial.println(F("  s = stop audio"));
  Serial.println(F("  h = aide"));
  Serial.println(F(""));
  Serial.println(F("COULEURS:"));
  Serial.println(F("  r=rouge v=vert l=bleu c=cyan p=violet w=blanc"));
  Serial.println(F(""));
}
