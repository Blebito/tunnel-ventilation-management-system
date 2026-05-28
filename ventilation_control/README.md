# Ventilation Control – KiCad Electrical Schematic

This folder contains the KiCad 7 project files for the electrical schematic of the
tunnel ventilation control prototype (Figure 13 in the thesis).

## Files

| File | Description |
|------|-------------|
| `ventilation_control.kicad_pro` | KiCad project configuration |
| `ventilation_control.kicad_sch` | Schematic source file |
| `bom.csv` | Bill of Materials |

## Circuit Overview

The schematic shows all connections between the **Raspberry Pi** and the two exhaust
fans, controlled through **IRLZ44N MOSFET** transistors.

```
VCC ──┬─────────────────────┬── VCC
      │                     │
     [M2]                  [M1]      ← Fans MF50200V1-1000U-A99
      │                     │
     [D2] ← freewheeling   [D1] ← freewheeling diodes 1N4007
      │                     │
    Drain(Q2)            Drain(Q1)
      │                     │
   Gate(Q2)←[R1]←GPIO18  Gate(Q1)←[R2]←GPIO23   ← Raspberry Pi GPIO
      │                     │
   Source(Q2)           Source(Q1)
      │                     │
     GND ─────────────────GND
```

### Component List

| Ref | Value | Function |
|-----|-------|----------|
| J1  | Raspberry_Pi | 40-pin GPIO header (Raspberry Pi 5) |
| U1  | MQ-135 | Air quality sensor |
| Q1  | IRLZ44N | N-ch MOSFET – Fan 1 switch |
| Q2  | IRLZ44N | N-ch MOSFET – Fan 2 switch |
| R1  | 1 kΩ | Gate resistor Q2 (GPIO18) |
| R2  | 1 kΩ | Gate resistor Q1 (GPIO23) |
| D1  | 1N4007 | Freewheeling diode Fan 1 |
| D2  | 1N4007 | Freewheeling diode Fan 2 |
| M1  | Fan_MF50200V1 | Exhaust fan 1 – 5 V DC |
| M2  | Fan_MF50200V1 | Exhaust fan 2 – 5 V DC |

### GPIO Pin Assignments

| GPIO | Function |
|------|----------|
| GPIO17 | MQ-135 digital output (DO) |
| GPIO18 / PWM0 | Fan 2 control – Q2 gate |
| GPIO23 | Fan 1 control – Q1 gate |

### Power

- Fans and MOSFETs are powered from a **5 V switched-mode power supply**.
- Logic ground (Raspberry Pi GND) and power ground are **common**.
- Power supply and Raspberry Pi power rail are **separate** (see schematic notes).

## Notes

- The Raspberry Pi symbol used is a **generic 40-pin connector** (`J1 – Raspberry_Pi`).
  At the time the schematic was drawn, a dedicated Raspberry Pi 5 KiCad symbol was
  not available. Pin labels in the schematic match the actual Raspberry Pi 5 GPIO
  header exactly.
- The schematic is **identical** to Figure 13 in the thesis; only the document
  language has been changed to English for the repository.

## How to Open

1. Install [KiCad 7](https://www.kicad.org/download/) or newer.
2. Open `ventilation_control.kicad_pro`.
3. The schematic editor will open `ventilation_control.kicad_sch` automatically.
