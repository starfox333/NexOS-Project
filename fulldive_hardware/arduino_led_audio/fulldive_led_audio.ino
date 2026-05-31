// ============================================================
// FULL-DIVE PROTOTYPE V1 - LED + AUDIO
// Écran LED 30 pixels (5 bandes x 6 LEDs) + Audio binaural
// ============================================================
// Matériel :
//   - Arduino Uno
//   - 30 LEDs WS2812B (5 bandes de 6)
//   - 2 haut-parleurs + ampli
//   - Batterie LiPo + TP4056
// ============================================================

#include <Adafruit_NeoPixel.h>

// === CONFIGURATION ===
#define LED_PIN     6       // Pin data des LEDs
#define NUM_LEDS    30      // 5 bandes x 6 LEDs
#define ROWS        5       // Nombre de bandes
#define COLS        6       // LEDs par bande

#define AUDIO_L     9       // Pin audio gauche (PWM)
#define AUDIO_R     10      // Pin audio droit (PWM)

// === OBJETS ===
Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);

// === VARIABLES ===
uint8_t screenBuffer[ROWS][COLS];  // Buffer écran (luminosité)
uint32_t screenColor = strip.Color(0, 200, 255);  // Cyan AmuSphere
uint8_t currentMode = 0;
unsigned long lastUpdate = 0;

// === MODES D'AFFICHAGE ===
enum DisplayMode {
  MODE_OFF,
  MODE_PULSE_AMUSPHERE,    // Pulsation cyan style SAO
  MODE_ALPHA_STIMULATION,  // 10Hz - relaxation
  MODE_BETA_STIMULATION,   // 20Hz - concentration
  MODE_THETA_STIMULATION,  // 6Hz - méditation profonde
  MODE_PATTERN_SPIRAL,     // Spirale hypnotique
  MODE_PATTERN_WAVE,       // Vague gauche-droite
  MODE_BINAURAL_SYNC,      // Sync avec audio binaural
  MODE_FULL_WHITE,         // Test - tout blanc
  NUM_MODES
};

// === FRÉQUENCES BINAURALES ===
// Fréquence porteuse et battement pour chaque état
struct BinauralPreset {
  uint16_t baseFreq;    // Fréquence de base (Hz)
  uint16_t beatFreq;    // Fréquence de battement (Hz x10 pour décimales)
  uint8_t ledFreq;      // Fréquence LED (Hz)
  const char* name;
};

BinauralPreset presets[] = {
  {200, 100, 10, "Alpha"},    // 200Hz base, 10Hz beat → relaxation
  {200, 200, 20, "Beta"},     // 200Hz base, 20Hz beat → focus
  {200,  60,  6, "Theta"},    // 200Hz base, 6Hz beat → méditation
  {200,  40,  4, "Delta"},    // 200Hz base, 4Hz beat → sommeil
};
uint8_t currentPreset = 0;

// ============================================================
// SETUP
// ============================================================
void setup() {
  Serial.begin(115200);
  Serial.println(F("================================="));
  Serial.println(F("  FULL-DIVE PROTOTYPE V1"));
  Serial.println(F("  LED + Audio Binaural"));
  Serial.println(F("================================="));

  // Init LEDs
  strip.begin();
  strip.setBrightness(50);  // Sécurité yeux (0-255)
  strip.show();

  // Init Audio pins
  pinMode(AUDIO_L, OUTPUT);
  pinMode(AUDIO_R, OUTPUT);

  // Effet de démarrage
  startupAnimation();

  Serial.println(F("Commandes Serial:"));
  Serial.println(F("  0-8 : Changer mode LED"));
  Serial.println(F("  a/b/t/d : Preset binaural"));
  Serial.println(F("  +/- : Luminosité"));
  Serial.println(F("  s : Stop audio"));
}

// ============================================================
// LOOP PRINCIPAL
// ============================================================
void loop() {
  // Lire commandes Serial
  handleSerial();

  // Mise à jour affichage LED
  updateDisplay();

  // Génération audio binaural
  updateBinauralAudio();
}

// ============================================================
// GESTION DES COMMANDES
// ============================================================
void handleSerial() {
  if (Serial.available()) {
    char cmd = Serial.read();

    switch (cmd) {
      case '0': setMode(MODE_OFF); break;
      case '1': setMode(MODE_PULSE_AMUSPHERE); break;
      case '2': setMode(MODE_ALPHA_STIMULATION); break;
      case '3': setMode(MODE_BETA_STIMULATION); break;
      case '4': setMode(MODE_THETA_STIMULATION); break;
      case '5': setMode(MODE_PATTERN_SPIRAL); break;
      case '6': setMode(MODE_PATTERN_WAVE); break;
      case '7': setMode(MODE_BINAURAL_SYNC); break;
      case '8': setMode(MODE_FULL_WHITE); break;

      case 'a': setPreset(0); break;  // Alpha
      case 'b': setPreset(1); break;  // Beta
      case 't': setPreset(2); break;  // Theta
      case 'd': setPreset(3); break;  // Delta

      case '+': adjustBrightness(10); break;
      case '-': adjustBrightness(-10); break;

      case 's': stopAudio(); break;
    }
  }
}

void setMode(uint8_t mode) {
  currentMode = mode;
  Serial.print(F("Mode: "));
  Serial.println(mode);
}

void setPreset(uint8_t preset) {
  currentPreset = preset;
  Serial.print(F("Binaural: "));
  Serial.println(presets[preset].name);
}

void adjustBrightness(int8_t delta) {
  int16_t newBright = strip.getBrightness() + delta;
  newBright = constrain(newBright, 5, 100);  // Max 100 pour sécurité yeux
  strip.setBrightness(newBright);
  Serial.print(F("Luminosité: "));
  Serial.println(newBright);
}

void stopAudio() {
  noTone(AUDIO_L);
  noTone(AUDIO_R);
  Serial.println(F("Audio OFF"));
}

// ============================================================
// MISE À JOUR AFFICHAGE LED
// ============================================================
void updateDisplay() {
  unsigned long now = millis();

  switch (currentMode) {
    case MODE_OFF:
      clearScreen();
      break;

    case MODE_PULSE_AMUSPHERE:
      pulseAmuSphere(now);
      break;

    case MODE_ALPHA_STIMULATION:
      stimulation(now, 10);  // 10Hz
      break;

    case MODE_BETA_STIMULATION:
      stimulation(now, 20);  // 20Hz
      break;

    case MODE_THETA_STIMULATION:
      stimulation(now, 6);   // 6Hz
      break;

    case MODE_PATTERN_SPIRAL:
      patternSpiral(now);
      break;

    case MODE_PATTERN_WAVE:
      patternWave(now);
      break;

    case MODE_BINAURAL_SYNC:
      binauralSync(now);
      break;

    case MODE_FULL_WHITE:
      fillScreen(strip.Color(255, 255, 255));
      break;
  }

  strip.show();
}

// ============================================================
// EFFETS LED
// ============================================================

void clearScreen() {
  for (int i = 0; i < NUM_LEDS; i++) {
    strip.setPixelColor(i, 0);
  }
}

void fillScreen(uint32_t color) {
  for (int i = 0; i < NUM_LEDS; i++) {
    strip.setPixelColor(i, color);
  }
}

// Pulsation douce cyan - style AmuSphere SAO
void pulseAmuSphere(unsigned long t) {
  // Onde sinusoïdale lente (2 secondes de période)
  float phase = (t % 2000) / 2000.0 * 2 * PI;
  uint8_t brightness = (sin(phase) + 1) * 0.5 * 200 + 20;

  uint32_t color = strip.Color(0, brightness * 0.8, brightness);  // Cyan
  fillScreen(color);
}

// Stimulation à fréquence fixe (yeux fermés)
void stimulation(unsigned long t, uint8_t freqHz) {
  uint16_t period = 1000 / freqHz;  // Période en ms
  bool on = (t % period) < (period / 2);

  if (on) {
    fillScreen(screenColor);
  } else {
    clearScreen();
  }
}

// Spirale hypnotique
void patternSpiral(unsigned long t) {
  float angle = (t % 3000) / 3000.0 * 2 * PI;

  for (int row = 0; row < ROWS; row++) {
    for (int col = 0; col < COLS; col++) {
      int idx = row * COLS + col;

      // Distance et angle depuis le centre
      float dx = col - COLS / 2.0;
      float dy = row - ROWS / 2.0;
      float dist = sqrt(dx * dx + dy * dy);
      float a = atan2(dy, dx);

      // Spirale
      float spiral = sin(dist * 2 - angle + a);
      uint8_t bright = (spiral + 1) * 127;

      strip.setPixelColor(idx, strip.Color(0, bright * 0.8, bright));
    }
  }
}

// Vague gauche-droite
void patternWave(unsigned long t) {
  float phase = (t % 1000) / 1000.0 * 2 * PI;

  for (int row = 0; row < ROWS; row++) {
    for (int col = 0; col < COLS; col++) {
      int idx = row * COLS + col;

      float wave = sin(phase + col * 0.8);
      uint8_t bright = (wave + 1) * 127;

      strip.setPixelColor(idx, strip.Color(0, bright * 0.8, bright));
    }
  }
}

// Synchronisation avec audio binaural
void binauralSync(unsigned long t) {
  uint8_t freq = presets[currentPreset].ledFreq;
  stimulation(t, freq);
}

// Animation de démarrage
void startupAnimation() {
  // Balayage cyan
  for (int i = 0; i < NUM_LEDS; i++) {
    strip.setPixelColor(i, strip.Color(0, 200, 255));
    strip.show();
    delay(30);
  }

  // Flash
  for (int j = 0; j < 3; j++) {
    fillScreen(strip.Color(0, 255, 255));
    strip.show();
    delay(100);
    clearScreen();
    strip.show();
    delay(100);
  }

  // Pulsation fade in
  for (int b = 0; b < 50; b++) {
    fillScreen(strip.Color(0, b * 4, b * 5));
    strip.show();
    delay(20);
  }
}

// ============================================================
// AUDIO BINAURAL
// ============================================================
// Note: Arduino Uno ne peut pas faire de vrai audio binaural
// simultané sur 2 canaux avec tone().
// Pour un vrai binaural, utiliser un module DFPlayer ou DAC.
//
// Ici on alterne rapidement entre les deux fréquences
// pour simuler l'effet (pas idéal mais fonctionne un peu)
// ============================================================

unsigned long lastAudioSwitch = 0;
bool audioChannel = false;

void updateBinauralAudio() {
  if (currentMode == MODE_OFF) {
    return;
  }

  unsigned long now = millis();

  // Alterner entre les canaux toutes les 10ms
  if (now - lastAudioSwitch > 10) {
    lastAudioSwitch = now;
    audioChannel = !audioChannel;

    BinauralPreset& p = presets[currentPreset];
    uint16_t freqL = p.baseFreq;
    uint16_t freqR = p.baseFreq + p.beatFreq / 10;  // beatFreq est x10

    if (audioChannel) {
      tone(AUDIO_L, freqL);
      noTone(AUDIO_R);
    } else {
      noTone(AUDIO_L);
      tone(AUDIO_R, freqR);
    }
  }
}

// ============================================================
// FONCTIONS UTILITAIRES
// ============================================================

// Convertir coordonnées (row, col) en index LED
// Gère le zigzag si les bandes sont câblées en serpentin
int getPixelIndex(int row, int col) {
  // Si câblage en serpentin (bandes alternées)
  if (row % 2 == 1) {
    col = COLS - 1 - col;  // Inverser la colonne
  }
  return row * COLS + col;
}

// Définir un pixel par coordonnées
void setPixel(int row, int col, uint32_t color) {
  if (row >= 0 && row < ROWS && col >= 0 && col < COLS) {
    strip.setPixelColor(getPixelIndex(row, col), color);
  }
}
