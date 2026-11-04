---
title: Off-Grid Solar Power and Battery Systems
category: building
region: all
tags: [solar, off-grid, power, battery, 12v, charge-controller, inverter, lifepo4, lead-acid, wiring, fuse, energy-budget, generator]
risk: medium
critical_warning: "Batteries can deliver huge currents: fuse every positive wire close to the battery. Generators must run outdoors, 20+ feet from windows and doors."
sources: [NREL off-grid PV guidance, National Electrical Code (NEC) Article 690 principles, Battery University]
last_reviewed: 2026-11-03
---

# Off-Grid Solar Power and Battery Systems

## Prioritize loads

Power in priority order: communications (radios, phone charging), lighting (LED), medical devices, water pumping, refrigeration (medicine and food), then tools and comfort. Electric heating and cooking use far more power than small systems can supply — use fire or gas for those.

## Energy budget

List each device: **watts × hours per day = watt-hours (Wh)/day**.

| Device | Watts | Hours | Wh/day |
|---|---|---|---|
| 4 LED bulbs | 4 × 8 | 5 | 160 |
| Phone charging ×3 | 10 | 2 each | 60 |
| Radio (receive) | 5 | 6 | 30 |
| Efficient chest fridge | ~60 avg cycling | 24 | 300–600 |
| Laptop | 50 | 3 | 150 |

## Sizing

- **Panels:** daily Wh ÷ peak sun hours (winter: roughly 2–3 hrs north, 4–5 Southwest) ÷ 0.7 (losses). Example: 700 Wh ÷ 3 ÷ 0.7 ≈ 330 W of panels.
- **Battery bank:** daily Wh × days of autonomy (2–3) ÷ usable depth of discharge. Lead-acid: use only 50%; LiFePO4: 80–90%.
  - Example: 700 Wh × 2 days ÷ 0.8 (LiFePO4) = 1,750 Wh ≈ 150 Ah at 12 V.

## Components

1. **Solar panels** — angle toward true south, tilted about your latitude (steeper in winter). Keep them clean and unshaded; partial shade on one cell can cut output dramatically.
2. **Charge controller** — MPPT (more efficient, best for larger or colder systems) or PWM (cheap, small systems). Must match battery chemistry.
3. **Battery** — LiFePO4 (long life, light, safe chemistry, but don't charge below freezing unless heated), flooded lead-acid (cheap, needs watering and ventilation — produces hydrogen), AGM (sealed lead-acid). Car batteries are designed for starting, not deep cycling — they'll die quickly.
4. **Fuses/breakers** — on every positive conductor near the battery, panel, and loads.
5. **Inverter** (12 V DC → 120 V AC) — pure sine wave for electronics and motors. Inverters waste 10–15% plus idle draw; use DC (12 V/USB) devices where possible.
6. **Wiring** — thicker wire for longer runs and higher current. Keep 12 V runs short; voltage drop is large.

## Wiring order

Connect the **battery to the charge controller first**, then the panels to the controller (prevents controller damage). Disconnect in reverse.

## Battery health

- Lead-acid: recharge fully every day if possible; never leave discharged (sulfation). Resting voltage at full charge ≈ 12.7 V; 50% ≈ 12.2 V.
- LiFePO4: resting ≈ 13.3–13.4 V full; use a BMS (battery management system).
- Insulate batteries from extreme cold — capacity drops sharply below freezing, and a discharged lead-acid battery can freeze and crack. (The "never set a battery on concrete" rule is a myth for modern cases, but a cold floor still chills the battery.)

## Salvage sources after collapse

Solar panels from damaged homes and RVs, deep-cycle batteries from RVs, boats, golf carts, and forklifts, inverters from RVs, LED lights from vehicles, 12 V fridges from trucks and RVs. A vehicle alternator can be driven by a water wheel, bicycle, or small engine to charge batteries.

## Generators

- Run outdoors only, 20+ ft from openings; CO alarms indoors.
- Store fuel with stabilizer; gasoline degrades in 3–6 months untreated (1–2 years stabilized). Propane stores indefinitely.
- Use a generator to bulk-charge batteries for an hour or two, rather than running it for small loads all day.
- Connect to a house only through a transfer switch or interlock — backfeeding can kill line workers.
