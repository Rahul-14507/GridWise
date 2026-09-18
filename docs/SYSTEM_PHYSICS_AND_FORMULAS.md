# GridWise: Complete System Inputs, Physics, Formulas & Downstream Usage Map

This document provides a comprehensive mathematical and physical reference for the **GridWise Smart EV Charging Management System**. It specifies every system input, the mathematical formulas and domain physics applied to those inputs, and where each derived metric is consumed throughout the architecture.

---

## 1. System Inputs Catalog

### A. Environmental & Telemetry Inputs (ESP32 Hardware or Sensor Simulator)
| Parameter | Type / Range | Unit | Source | Description |
| :--- | :--- | :--- | :--- | :--- |
| `temperature_c` | Float `[-40.0, 85.0]` | °C | DHT22 / Sensor Simulator | Ambient air temperature. |
| `humidity_percent` | Float `[0.0, 100.0]` | % | DHT22 / Sensor Simulator | Relative ambient air humidity. |
| `solar_voltage_v` | Float `[0.0, 5.0]` | V | LDR / Photodiode sensor | Scaled analog voltage proxy for solar irradiance. |
| `rain_detected` | Boolean | — | Digital rain sensor | Precipitation indicator flag. |
| `rain_intensity` | Float `[0.0, 1.0]` | — | Analog rain sensor | Continuous precipitation severity index (0 = none, 1 = heavy). |
| `timestamp` | ISO-8601 UTC | — | ESP32 RTC / Simulation clock | Current simulation or wall-clock timestamp. |

### B. Electrical Grid & Transformer Configuration
| Parameter | Type / Range | Unit | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `base_grid_capacity_kw` | Float `> 0.0` | kW | `25.0 kW` | Nominal transformer interconnection rating. |
| `thermal_derating_start_c` | Float `> 0.0` | °C | `35.0°C` | Ambient temperature where thermal derating begins. |
| `thermal_critical_temp_c` | Float `> T_start` | °C | `50.0°C` | Ambient temperature where critical derating limit is reached. |
| `thermal_min_capacity_kw` | Float `[0, P_base]` | kW | `15.0 kW` | Minimum transformer safety floor during extreme thermal stress. |

### C. Solar Array & Sensor Calibration Configuration
| Parameter | Type / Range | Unit | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `solar_capacity_kw` | Float `> 0.0` | kW | `12.5 kW` | Rated peak generation capacity of solar PV array. |
| `solar_min_voltage_v` | Float `≥ 0.0` | V | `0.5 V` | Calibrated sensor voltage floor (0% irradiance). |
| `solar_max_voltage_v` | Float `> V_min` | V | `4.2 V` | Calibrated sensor voltage ceiling (100% peak irradiance). |

### D. Stationary Battery Energy Storage System (BESS) Configuration & State
| Parameter | Type / Range | Unit | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `capacity_kwh` | Float `> 0.0` | kWh | `50.0 kWh` | Total virtual BESS storage capacity. |
| `soc_percent` | Float `[0.0, 100.0]` | % | `80.0%` | Current battery state of charge. |
| `max_charge_rate_kw` | Float `> 0.0` | kW | `10.0 kW` | Maximum rate to charge the stationary battery. |
| `max_discharge_rate_kw` | Float `> 0.0` | kW | `10.0 kW` | Maximum rate to discharge from the stationary battery. |
| `minimum_soc_percent` | Float `[0.0, 100.0]` | % | `20.0%` | Emergency reserve floor (discharging stops here). |
| `charging_efficiency` | Float `[0.0, 1.0]` | — | `0.95` (95%) | Coulombic/thermal efficiency during energy integration. |

### E. EV Fleet & Driver Check-in Session Inputs
| Parameter | Type / Range | Unit | Source | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | String | — | Driver / Scanner | Unique vehicle identifier (e.g., `EV-001`). |
| `slot_id` | String / Null | — | Parking Slot Assignment | Assigned physical bay (e.g., `SLOT-01`). |
| `battery_capacity_kwh` | Float `> 0.0` | kWh | Vehicle Spec / Driver | Total battery pack capacity (e.g., `60.0 kWh`). |
| `soc_percent` | Float `[0.0, 100.0]` | % | Vehicle BMS / Driver | Current battery State of Charge. |
| `target_soc_percent` | Float `[0.0, 100.0]` | % | Driver Preference | Desired departure State of Charge. |
| `max_charging_power_kw` | Float `> 0.0` | kW | Onboard Charger Limit | Physical AC/DC hardware limit (e.g., `11.0 kW`). |
| `arrival_time` | DateTime UTC | — | Scanner Timestamp | Exact arrival/connection timestamp. |
| `departure_time` | DateTime UTC | — | Driver Schedule | Target departure deadline (`departure_time > arrival_time`). |

### F. Priority & Optimization Weight Inputs
| Parameter | Range | Default | Constraint | Description |
| :--- | :--- | :--- | :--- | :--- |
| `weight_soc_deficit` | `[0.0, 1.0]` | `0.35` | `Sum(weights) = 1.0` | Weight for low battery severity. |
| `weight_departure_urgency` | `[0.0, 1.0]` | `0.40` | `Sum(weights) = 1.0` | Weight for imminent departure deadline. |
| `weight_energy_deficit` | `[0.0, 1.0]` | `0.15` | `Sum(weights) = 1.0` | Weight for absolute energy (kWh) needed. |
| `weight_waiting_time` | `[0.0, 1.0]` | `0.10` | `Sum(weights) = 1.0` | FIFO fairness weight for long-waiting vehicles. |

---

## 2. Formulas & Mathematical Domain Physics

### 1. Solar Availability & Estimated Generation Physics
**Module:** `backend/app/domain/services/solar_service.py`

Given raw analog sensor voltage `V_sensor`:

```
1. Availability Fraction (0.0 to 1.0):
   A_solar = clamp((V_sensor - V_min) / (V_max - V_min), min=0.0, max=1.0)

2. Estimated Solar Power (kW):
   P_solar = A_solar * P_solar_capacity

3. Solar Availability Percentage:
   Availability_% = A_solar * 100.0%
```

**Precipitation Attenuation (Simulation):**
If rain is detected:
```
A_effective = A_solar * (1.0 - 0.70 * rain_intensity)
```

---

### 2. Transformer Thermal Physics & Capacity Derating
**Module:** `backend/app/domain/services/thermal_service.py`

Calculates effective transformer power capacity based on ambient temperature `T`:

```
Thermal Derating Factor (η_thermal):

  Case 1: T <= T_start (e.g. <= 35°C)  [NORMAL]
          η_thermal = 1.0

  Case 2: T_start < T < T_critical (e.g. 35°C to 50°C)  [ELEVATED / DERATED]
          ratio = (T - T_start) / (T_critical - T_start)
          P_effective = P_base - ratio * (P_base - P_min)
          η_thermal = P_effective / P_base

  Case 3: T >= T_critical (e.g. >= 50°C)  [CRITICAL]
          P_effective = P_min
          η_thermal = P_min / P_base

Effective Transformer Capacity:
  P_effective = P_base * η_thermal
```

---

### 3. Diurnal Building Baseload Demand Physics
**Module:** `backend/app/simulation/grid_simulator.py`

Fractional hour of day: `h = hour + (minute / 60) + (second / 3600)`

Between adjacent 24h keypoints `(h1, d1)` and `(h2, d2)`:
```
1. Linear Interpolation:
   fraction = (h - h1) / (h2 - h1)
   P_interpolated = d1 + fraction * (d2 - d1)

2. Noise Perturbation (±5%):
   P_building = max(0.0, P_interpolated * (1.0 + random_noise(-0.05, +0.05)))
```

---

### 4. Facility Net Energy Balance & Available EV Headroom
**Module:** `backend/app/domain/services/energy_service.py`

Net power available for the entire EV fleet without overloading the transformer:

```
P_available_ev = max(0.0, (P_effective - P_building) + P_solar + P_bess_discharge)
```

Where:
- `P_effective`: Derated transformer limit
- `P_building`: Facility baseload demand
- `P_solar`: Live solar PV generation
- `P_bess_discharge`: Power contributed by stationary battery

---

### 5. Individual EV Energy Deficit & Physical Required Power
**Module:** `backend/app/domain/models/ev.py`

For each connected vehicle:

```
1. Energy Deficit (kWh):
   If Current_SoC >= Target_SoC:
       E_required = 0.0 kWh
   Else:
       E_required = Battery_Capacity_kWh * ((Target_SoC - Current_SoC) / 100.0)

2. Remaining Time to Departure (hours):
   t_remaining = max(0.0, (Departure_Time - Current_Time) in seconds / 3600.0)

3. Required Physical Average Power (kW):
   If E_required <= 0.0 or t_remaining <= 0.0:
       P_avg_required = 0.0 kW
   Else:
       P_avg_required = E_required / t_remaining
```

---

### 6. Normalized Urgency Metrics & Multi-Factor Priority Scoring
**Modules:** `backend/app/optimizer/urgency.py`, `backend/app/optimizer/priority.py`

All urgency components are strictly normalized to `[0.0, 1.0]`:

```
1. SoC Urgency:
   U_soc = 1.0 - (Current_SoC / Target_SoC)

2. Energy Deficit Score:
   U_energy = E_required / Battery_Capacity_kWh

3. Departure Urgency (Piecewise continuous curve):
   If t_remaining <= 0.0 h:
       U_dep = 1.0
   Else if 0.0 < t_remaining <= 1.0 h:
       U_dep = 0.8 + 0.2 * (1.0 - t_remaining)
   Else if 1.0 < t_remaining <= 4.0 h:
       U_dep = 0.1 + 0.7 * ((4.0 - t_remaining) / 3.0)
   Else if 4.0 < t_remaining <= 12.0 h:
       U_dep = 0.1 * ((12.0 - t_remaining) / 8.0)
   Else (t_remaining > 12.0 h):
       U_dep = 0.0

4. Waiting Time Fairness:
   waiting_hours = (Current_Time - Arrival_Time) in seconds / 3600.0
   U_wait = min(1.0, waiting_hours / 3.0)

Composite Priority Score (0.0 to 10.0):
   Priority_Score = 10.0 * (
       w_soc * U_soc +
       w_dep * U_dep +
       w_energy * U_energy +
       w_wait * U_wait
   )
```

---

### 7. Feasibility & Deadline Risk Assessment
**Module:** `backend/app/optimizer/urgency.py`

```
Deadline Status:
  - COMPLETE : Current_SoC >= Target_SoC
  - EXPIRED  : t_remaining <= 0 and Current_SoC < Target_SoC
  - AT_RISK  : P_avg_required > Max_Charging_Power_kW (Physically impossible even at full charger speed)
  - FEASIBLE : P_avg_required <= Max_Charging_Power_kW
```

---

### 8. Multi-Pass Power Allocation & Hard Constraints
**Module:** `backend/app/optimizer/optimizer.py`

Distributes `P_available_ev` among EVs sorted by descending Priority Score:

```
Pass 1 — Proportional Allocation:
  weight_ratio_i = Priority_Score_i / Sum(Priority_Scores)
  P_initial_i = min(
      Max_Charging_Power_i,
      P_avg_required_i,
      P_available_ev * weight_ratio_i
  )

Pass 2 — Surplus Redistribution:
  Surplus = P_available_ev - Sum(P_initial_all_evs)
  Allocate surplus sequentially to highest-priority EVs that have remaining headroom:
  Headroom_i = Max_Charging_Power_i - P_initial_i

Pass 3 — Hard Constraint Verification:
  Constraint 1: Sum(P_allocated_i) <= P_available_ev
  Constraint 2: 0.0 <= P_allocated_i <= Max_Charging_Power_i for every vehicle
```

---

### 9. Battery Energy Integration Over Time (Δt)
**Modules:** `backend/app/simulation/ev_simulator.py`, `backend/app/simulation/battery_simulator.py`

When simulation advances by `Δt` seconds:

```
1. Energy Added (kWh):
   ΔE_kwh = P_allocated_kw * (Δt / 3600.0) * Efficiency (e.g. 0.95)

2. State of Charge Update (%):
   New_SoC_% = min(100.0, Old_SoC_% + (ΔE_kwh / Battery_Capacity_kWh) * 100.0)
```

---

## 3. Downstream Consumption & Usage Matrix

| Derived Metric | Producing Module | Consuming Component | Downstream Usage & Operational Effect |
| :--- | :--- | :--- | :--- |
| **`P_effective`** | `ThermalService` | `SystemStateService`, `AppStateService`, `WarningsService` | Clamps grid headroom; triggers `W_TRANSFORMER_DERATED` warning if `T > 35°C` or `C_TRANSFORMER_CRITICAL` if `T > 50°C`. |
| **`P_solar`** | `SolarService` | `EnergyService`, `AdminDashboard` | Adds clean power to `P_available_ev`; visualizes live solar PV generation on dashboard gauge. |
| **`P_building`** | `GridSimulator` | `EnergyService`, `RealtimeCharts` | Deducts facility baseload from grid rating; plotted on real-time facility load charts. |
| **`P_available_ev`** | `EnergyService` | `ChargingOptimizer`, `InfrastructureOverview` | Sets strict aggregate upper limit for total EV power allocations. |
| **`E_required`, `P_avg_req`** | `EV` Model | `UrgencyCalculator`, `EVFleetTable` | Defines charging feasibility; displayed as "Required kW to meet departure" in EV fleet table. |
| **`Priority_Score`** | `PriorityScorer` | `ChargingOptimizer`, `EVFleetTable` | Ranks vehicles and defines proportional power distribution weights across competing charging bays. |
| **`Deadline_Status`** | `UrgencyCalculator` | `ChargingOptimizer`, `WarningsService`, `EVFleetTable` | Categorizes EV (`FEASIBLE`, `AT_RISK`, `EXPIRED`, `COMPLETE`); triggers alerts for at-risk vehicles. |
| **`P_allocated_i`** | `ChargingOptimizer` | `SimulationEngine`, `EVFleetTable` | Controls actual physical charging rate delivered to vehicle; drives battery SoC progression. |
| **`BESS Dispatch Mode`** | `ChargingOptimizer` | `BatterySimulator`, `BatteryStatus` | Commands stationary battery to `DISCHARGE` during grid deficit, `CHARGE` during solar surplus, or `IDLE`. |
| **`Facility Load`** | `AppStateService` | `InfrastructureOverview`, `RealtimeCharts` | `P_load = P_building + Sum(P_allocated) + P_bess_charge`; displays infrastructure capacity utilization bar. |
