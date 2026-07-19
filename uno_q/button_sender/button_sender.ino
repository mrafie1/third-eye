#include <Arduino_Modulino.h>

ModulinoButtons buttons;
bool wasPressed[3] = {false, false, false};

void setup() {
  Serial1.begin(115200);
  Modulino.begin();
  buttons.begin();
}

void loop() {
  if (!buttons.update()) {
    return;
  }

  for (int i = 0; i < 3; i++) {
    const bool pressed = buttons.isPressed(i);
    if (pressed && !wasPressed[i]) {
      Serial1.println(i);
    }
    wasPressed[i] = pressed;
  }
}
