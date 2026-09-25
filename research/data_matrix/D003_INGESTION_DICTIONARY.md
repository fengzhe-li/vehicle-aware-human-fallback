# D003 ingestion dictionary (Phase R1)

Maps raw D003 simulator columns to the canonical names used by `src/data/d003_ingest.py`, with the source and semantic status of each. "Official" means stated in the dataset's `1. data_dictionary.csv` or in the owners' paper (arXiv 2507.22252). Everything else is labelled.

Related documents: `research/data_matrix/D003_KNOWN_BLOCKERS.md` (blockers), `docs/OBSERVATION_LAYER.md` (measurement rules).

## File structure

- One CSV per trial: `density_{0|10|20}_nback_{0|1|2}_id_{1..57}_simulator_data.csv` (513 files).
- Three header variants: `FULL_45` (484), `NO_TOR_44` (15, no column 72), `NO_LANE_CHANGE_44` (14, no column 78). Any other header fails.
- The file behaves like two tables joined column-wise:
  - vehicle telemetry on the Unix-epoch `time` clock;
  - export channels 72–85 on a relative clock.

  The relative clock is carried in the second part of the quoted `"laneGap.0,time"` cell and equals `time − time[0]` (max error 9.5e-8 s). **The two-table reading is an inference from the file layout; it is not documented.**
- 42 files end with an export-channel footer row (empty `time`, 2 × k values). It is parsed separately and excluded from telemetry (B3).
- The first data row carries only `time` and the `laneGap` cell `"null,0"`.

## Columns

| Raw column | Canonical name | Unit | Source of meaning | Status |
|---|---|---|---|---|
| `time` | `time_epoch`; derived `t_rel = time − time[0]` | s | Official ("time stamp of measurement"); epoch clock verified | Confirmed |
| `pos.001`, `pos.002` | `pos_x`, `pos_y` | m | Official (global position x/y) | Documented |
| `pos.003`–`pos.006`, `COGPos.*` | `pos_z`, `roll`, `pitch`, `yaw`, `cog_*` | — | Legacy loader names; not in dictionary | Inferred names |
| `speed.001` | `longitudinal_speed` | m/s | Official (`car_speed_x`) | Documented |
| `speed.002` | `lateral_speed` | m/s | Official (`car_speed_y`) | Documented |
| `speed.003` | `vertical_speed` | — | Legacy name; not in dictionary | Inferred name |
| `speed.004`–`.006` | `speed_00N_undocumented` | — | Not in dictionary | Undocumented |
| `accel.001` | `longitudinal_acceleration` | m/s² | Official (`car_accel_x`, "acceleration longitudinal") | Documented; sign convention not stated |
| `accel.002` | `lateral_acceleration` | m/s² | Official (`car_accel_y`) | Documented |
| `accel.003` | `vertical_acceleration` | — | Legacy name | Inferred name |
| `accel.004`–`.006` | `accel_00N_undocumented` | — | Not in dictionary | Undocumented |
| `state`, `lights`, `indicators` | `vehicle_state`, `vehicle_lights`, `indicators` | — | `car_indicator` official (1 = left, −1 = right); others not in dictionary | Partly documented |
| `steeringWheelAngle` | `steering_angle` | rad | Official | Documented; source (driver vs automation) unresolved |
| `steeringWheelSpeed` | `steering_speed` | rad/s | Official | Documented |
| `steeringTorq` | `steering_torque` | — | Not in dictionary | Undocumented |
| `accelerator` | `accelerator` | [0, 1] | Official ("gas position") | Documented |
| `brake` | `brake_force` | N (dictionary) | Dictionary: "brake force"; owners' paper: "braking pedal positions" | **UNRESOLVED** (B6) |
| `roadInfo-roadId.0` … `laneId.0` | `road_id`, `road_abscissa`, `road_gap`, `road_angle`, `lane_id` | — | Dictionary lists the names only | Names documented; meaning of `lane_id` numbering road-dependent (B8) |
| `roadInfo-laneGap.0,time` (component 1) | `lane_gap_component1` | m (inferred) | Dictionary lists the name only | **INFERRED** (B5); not renamed to lane-centre offset |
| `roadInfo-laneGap.0,time` (component 2) | `lane_gap_reltime` | s | Layout inference; equals `t_rel` | Verified numerically |
| `roadInfo-laneGap.0,time` (whole cell) | `lane_gap_raw` | text | — | Kept for audit |
| 72 `Time_Takeover_Request` | `TOR_request` | s (relative) | Official | Documented; multiple values in 26 trials (B1) |
| 73 `Time_Manual_Start` | `manual_start` | s (relative) | Official ("pressed the switch button and switched to manual mode") | Documented; authority meaning **UNRESOLVED** (B7) |
| 74 `Time_Manual_Stop` | `manual_stop` | s (relative) | Official ("switched to automated mode") | Documented; multiple values in 12 trials (B14) |
| 77 `Time_TTC` | `TTC` | s | Official (distance_to_collision / car_speed_x) | Documented; undefined outside the approach domain (B13) |
| 78 `Time_Lane_Change` | `lane_change_time` | s (relative) | Official ("changed to the left lane during takeover") | Documented; validated per trial (B9) |
| 82 `Distance_to_Following_Vehicle` | `distance_to_following` | m | Official | Documented; meaning of 0 **UNRESOLVED** |
| 83 `Distance_to_Leading_Vehicle_Next_Lane` | `distance_to_lead_left` | m | Official ("ahead of the ego car on the left lane") | Documented; meaning of 0 **UNRESOLVED** |
| 84 `Distance_to_Following_Vehicle_Next_Lane` | `distance_to_following_left` | m | Official ("followed the ego car on the left lane") | Documented; meaning of 0 **UNRESOLVED** |
| 85 `Distance_to_Construction` | `distance_to_obstacle` | m | Official ("distance to collosion") | Documented; 1-D longitudinal only |

The canonical names `distance_to_lead_left` and `distance_to_following_left` come from the legacy loader. They follow the dictionary's wording ("left lane") for channels 83–84. Numeric lane IDs are not used to infer left or right.
