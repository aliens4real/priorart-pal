# PriorArt Pal — Ontology v1 (draft)

**Domain:** Autonomous passenger vehicles
**Status:** Draft for owner redline · 2026-05-03
**Owner:** @aliens4real (USPTO Primary Examiner, this art)

---

## Why this exists

Every node, edge, content type, and frequency in PriorArt Pal must map to a canonical entry in this ontology. The ontology is what makes structural retrieval possible — without it, "vehicle gateway ECU" and "telematics control unit" never collide, and the tool degrades to vanilla text search.

For each canonical entry, this document specifies:

| Field | Purpose |
|---|---|
| **Code** | Stable machine identifier (e.g., `TELEMATICS_CONTROLLER`). Never changes once published. |
| **Parent type** *(optional)* | If this code is a specialization, the parent canonical code. Used by the matcher for broadest-reasonable-interpretation reasoning — a patent disclosing a specialization (e.g., `PEDESTRIAN`) reads on a query node of the parent (`ROAD_OBSTACLE`) at full credit; a patent disclosing the parent partially reads on a query for the specialization. |
| **Description** | One-paragraph definition; the source of truth when synonyms are ambiguous. |
| **Synonyms (tight)** | Phrases that always map to this code. Used for high-confidence extraction and the default-on synonym filters in the query builder. |
| **Synonyms (loose)** | Phrases that often map to this code but need disambiguation. Surfaced as "tentative" in match results so the examiner can confirm. |
| **Extraction rule** | Guidance Claude follows during ingestion. Includes "must include" structural cues and "do not confuse with" notes. |
| **Disambiguation** | Which other canonical types this is most often confused with, and how to tell them apart. |

### On `parent_type` and the BRI matcher

Patents and claim language operate at multiple levels of generality. A patent that discloses a "pedestrian detector" anticipates a claim's "obstacle detector" element — because *pedestrian is a kind of obstacle*. The matcher needs to know that.

We model this with an explicit `parent_type` field on each canonical code. The matcher's rules:

- **Patent more specific than query** — patent has `PEDESTRIAN`, query has `ROAD_OBSTACLE` → **full match** (the specific reads on the generic).
- **Patent less specific than query** — patent has `ROAD_OBSTACLE`, query has `PEDESTRIAN` → **partial match, flagged** (the generic doesn't fully disclose the specific; examiner confirms).
- **Same type** — full match.
- **Sibling types under same parent** — no match (e.g., `PEDESTRIAN` and `ANIMAL` are both `ROAD_OBSTACLE` but distinct).

Hierarchies in v1: `ACTUATOR` parent, `MOBILE_DEVICE` parent, `NEARBY_VEHICLE` parent, `ROAD_OBSTACLE` parent, `ENERGY_STORAGE_DEVICE` parent. More may emerge as the corpus grows.

### On agency abstraction (the "vehicle transmits" problem)

Patents routinely attribute functions to a higher-level structural element when the action is physically performed by an embedded sub-component:

| What the claim says | What's really happening | Sub-component that does the work |
|---|---|---|
| "the vehicle transmits a message to a server" | comms via cellular / Wi-Fi | `TELEMATICS_CONTROLLER` |
| "the vehicle communicates with a roadside unit" | DSRC / C-V2X PC5 sidelink | `V2X_TRANSCEIVER` |
| "the vehicle detects an obstacle" | sensor + perception pipeline | `RANGING_SENSOR` + `PERCEPTION_MODULE` |
| "the system determines a route" | planning compute | `PLANNING_MODULE` |
| "the controller receives image data" | physical bus + buffer + driver | `IN_VEHICLE_NETWORK` + driver |
| "the apparatus authenticates the user" | crypto + biometric pipeline | `ALGORITHM` (subtype) + `DRIVER_STATE_SENSOR` |

The doctrine matters for examination: a claim element can be met by any component that performs the function, even if the claim attributes it to a different element ("the vehicle transmits" is anticipated by prior art with a transceiver doing the transmitting, because the transceiver is part of the vehicle).

We model this with a **matcher rule rather than a separate edge type** — extraction stays faithful to claim language, the matcher does the substitution work:

- **Container substitution** — if a patent has `VEHICLE --SENDS_TO--> X` and a query has `TELEMATICS_CONTROLLER --SENDS_TO--> X'`, the matcher considers them a partial match (flagged as `agency_substituted`) provided that:
  - `TELEMATICS_CONTROLLER` is in the *typical-subsystems* list for `VEHICLE` (see attribute below)
  - The edge type and target match (or are themselves substitutable)
- **Reverse direction** — if a patent has `TELEMATICS_CONTROLLER --SENDS_TO--> X` and a query has `VEHICLE --SENDS_TO--> X'`, full match (the specific reads on the generic agent — same logic as `parent_type` BRI).
- **Result UI** — every agency-substituted match is displayed with both the patent's surface attribution AND the actual sub-component, so the examiner can confirm the substitution is reasonable.

To support this, the relevant high-level nodes carry a `typical_subsystems` attribute listing the canonical types they commonly stand in for. For `VEHICLE`:

```
typical_subsystems = [
  TELEMATICS_CONTROLLER, V2X_TRANSCEIVER, IN_VEHICLE_NETWORK,
  AV_COMPUTE_PLATFORM, DOMAIN_CONTROLLER, CHASSIS_CONTROLLER,
  PERCEPTION_MODULE, SENSOR_FUSION_MODULE, PREDICTION_MODULE,
  PLANNING_MODULE, CONTROL_MODULE, SAFETY_MONITOR,
  RANGING_SENSOR, CAMERA, INERTIAL_SENSOR, POSITIONING_SENSOR,
  DRIVER_STATE_SENSOR, STEERING_ACTUATOR, THROTTLE_ACTUATOR,
  BRAKE_ACTUATOR, WHEEL, POWERTRAIN, ENERGY_STORAGE_DEVICE,
  DRIVER_INTERFACE, DATA_LOGGER, DATABASE
]
```

Other nodes with non-empty `typical_subsystems`: `NEARBY_VEHICLE` (mirrors `VEHICLE`), `GROUND_MOBILE_ROBOT`, `AERIAL_VEHICLE`, `AV_COMPUTE_PLATFORM` (typical-subsystems: `ALGORITHM` family), `DRIVER_INTERFACE` (`DRIVER_STATE_SENSOR` for monitoring functions).

This is mechanical lookup, not LLM reasoning — keeps matcher behavior predictable and explainable to the examiner.

Everything here is **v1 draft** — designed to be redlined. The expectation is iteration: ingest the seed corpus, see what doesn't fit, refine.

---

## Top-level structure

The ontology has five sections, each capturing a different dimension of what a patent describes:

1. **[Node types](#1-node-types)** — components, modules, devices (the "things" in the system)
2. **[Edge / relation types](#2-edge--relation-types)** — how nodes connect (the "verbs")
3. **[Content types](#3-content-types)** — what flows over an edge (the "payload")
4. **[Frequency vocabulary](#4-frequency-vocabulary)** — how often / when an edge fires
5. **[Threshold / condition vocabulary](#5-threshold--condition-vocabulary)** — numeric or categorical guards on edges and node behaviors

A patent's extracted graph references entries from all five.

---

## 1. Node types

Fifty-five canonical node types across ten categories. Several types form parent-child hierarchies (see "On `parent_type`" above). Pick the granularity carefully — too few and we collapse meaningful distinctions; too many and every patent looks unique.

### 1.1 Sensors

#### `RANGING_SENSOR`
> Active sensor that measures distance to objects via emitted energy (light, RF, sound).

- **Tight synonyms:** lidar, LIDAR, laser scanner, laser range finder, radar, RADAR, millimeter-wave radar, MMW radar, ultrasonic sensor, ultrasonic transducer, sonar, time-of-flight sensor, ToF sensor
- **Loose synonyms:** active sensor, ranging device, depth sensor, proximity sensor, distance sensor
- **Extraction rule:** Map any sensor that emits energy and measures return time/phase to derive distance. Capture the modality (`lidar` / `radar` / `ultrasonic`) as a node attribute. If the patent specifies sweep pattern (rotating, solid-state, mechanical), capture as `scan_pattern`.
- **Disambiguation:** vs. `CAMERA` — cameras are passive; if the patent describes structured-light or active-illumination cameras, prefer `CAMERA` with `illumination=active` attribute. vs. `POSITIONING_SENSOR` — GNSS doesn't measure object range, it measures self-position.
- **Attributes to capture:** `modality`, `range_max_m`, `field_of_view_deg`, `scan_pattern`, `wavelength_nm`

#### `CAMERA`
> Passive imaging sensor producing 2D pixel arrays. Includes mono, stereo, surround, and IR variants.

- **Tight synonyms:** camera, imaging sensor, image sensor, CMOS sensor, CCD sensor, monocular camera, stereo camera, surround-view camera, fisheye camera, IR camera, near-IR camera, thermal camera, RGB camera
- **Loose synonyms:** vision sensor, optical sensor, imaging device, vision module
- **Extraction rule:** Map anything producing 2D image frames (raw or compressed). For stereo, capture as one `CAMERA` node with `configuration=stereo` rather than two separate cameras. For 360° / surround, capture as one node with `configuration=surround` and `camera_count` attribute.
- **Disambiguation:** vs. `RANGING_SENSOR` (active depth) — passive stereo is still `CAMERA` because depth is computed downstream. vs. `PERCEPTION_MODULE` — a "vision system" that does object detection is the perception module, not the camera.
- **Attributes:** `configuration` (mono / stereo / surround / multi-pinhole), `mount_position` (front / rear / side / interior), `spectrum` (visible / near-IR / thermal), `resolution`, `frame_rate_hz`

#### `INERTIAL_SENSOR`
> Measures linear acceleration, angular velocity, or magnetic field for ego motion estimation.

- **Tight synonyms:** IMU, inertial measurement unit, accelerometer, gyroscope, magnetometer, MEMS gyro, MEMS accelerometer, AHRS, attitude and heading reference system
- **Loose synonyms:** motion sensor, orientation sensor, dynamics sensor
- **Extraction rule:** If it measures ego motion (own-vehicle dynamics) without external reference, this is the type. A 6-DOF or 9-DOF IMU is a single `INERTIAL_SENSOR` node, not three.
- **Disambiguation:** vs. `POSITIONING_SENSOR` — IMU alone gives relative motion only; absolute position needs GNSS or HD-map matching. Many patents combine the two in a single "navigation module" — extract them separately if the disclosure distinguishes them.
- **Attributes:** `dof` (3 / 6 / 9), `update_rate_hz`

#### `POSITIONING_SENSOR`
> Provides absolute or globally-referenced ego position.

- **Tight synonyms:** GNSS receiver, GPS receiver, GPS module, GLONASS receiver, Galileo receiver, BeiDou receiver, RTK GPS, DGPS, differential GPS, multi-constellation GNSS
- **Loose synonyms:** positioning module, satellite receiver, navigation receiver, location sensor
- **Extraction rule:** Map any sensor providing latitude/longitude or absolute pose. Includes RTK/PPP-corrected GNSS. Visual-inertial odometry that produces absolute pose via map matching is **not** this — that's `PERCEPTION_MODULE` with a localization role.
- **Disambiguation:** vs. `INERTIAL_SENSOR` — IMU is relative, GNSS is absolute. vs. dead-reckoning modules — those are `PERCEPTION_MODULE` (compute), not sensors.
- **Attributes:** `constellations`, `correction_source` (none / SBAS / RTK / PPP), `update_rate_hz`

#### `DRIVER_STATE_SENSOR`
> Sensor specifically aimed at the driver / occupants for state monitoring — gaze, attention, drowsiness, biometric vital signs, posture, hands-on-wheel.

- **Tight synonyms:** driver monitoring system, DMS, driver-facing camera, gaze-tracking camera, gaze sensor, drowsiness detection sensor, eye tracker, attention sensor, vital signal detection unit, biometric sensor, EEG sensor, ECG sensor, EOG sensor, PPG sensor, electroencephalogram sensor, electrocardiogram sensor, photoplethysmogram sensor, hands-on-wheel sensor, capacitive steering sensor
- **Loose synonyms:** in-cabin camera, internal camera, occupant sensor, in-cabin sensor
- **Extraction rule:** Distinct from generic `CAMERA` because it is *specifically* sensing the driver / occupant for state classification. If a patent describes a single camera that does both road perception and driver monitoring, extract two nodes (one `CAMERA`, one `DRIVER_STATE_SENSOR`) linked via `PART_OF` to the same `CAMERA_MODULE` if disclosed.
- **Disambiguation:** vs. `CAMERA` — interior cameras only become this when the disclosure ties them to driver/occupant state. vs. `DRIVER_INTERFACE` — that's the HMI surface for input/output; this is the sensing channel.
- **Attributes:** `signal_type` (visible / IR / EEG / ECG / EOG / PPG / capacitive / other), `target` (driver / passengers / both), `update_rate_hz`

### 1.2 Functional compute modules

#### `PERCEPTION_MODULE`
> Transforms raw sensor data into a structured world model: detected objects, classified entities, lane geometry, semantic scene labels, free space, etc.

- **Tight synonyms:** perception module, perception system, object detector, object detection neural network, scene understanding module, semantic segmentation module, lane detector, lane recognition module, sign recognition, traffic light detector, free-space estimator, occupancy grid module
- **Loose synonyms:** vision system, AI vision stack, recognition module, scene parser
- **Extraction rule:** Any compute element that takes sensor data in and emits structured detections / classifications / geometry. If the patent describes multiple specialized perception modules (e.g., separate object detector + lane detector), extract each as a separate `PERCEPTION_MODULE` node and link them with `PART_OF` to the parent perception system if disclosed.
- **Disambiguation:** vs. `SENSOR_FUSION_MODULE` — fusion combines outputs of multiple sensors / perception stages; perception transforms one sensor's data. A "fused perception system" gets extracted as both a `PERCEPTION_MODULE` and a `SENSOR_FUSION_MODULE` linked together. vs. `PREDICTION_MODULE` — perception sees what's there now; prediction projects what they'll do next.
- **Attributes:** `output_type` (objects / segmentation / lanes / signs / free_space / multi), `architecture` (NN / classical CV / hybrid), `runs_on` (link to `AV_COMPUTE_PLATFORM`)

#### `SENSOR_FUSION_MODULE`
> Combines outputs from two or more sensors (or two or more perception modules) into a unified representation.

- **Tight synonyms:** sensor fusion module, multi-sensor fusion, late fusion, early fusion, feature fusion, Kalman filter, extended Kalman filter, EKF, unscented Kalman filter, particle filter, fusion processor
- **Loose synonyms:** data fusion, fusion stack, integrator, multi-modal fusion
- **Extraction rule:** Must take ≥2 distinct sensor or perception inputs and produce a single combined output. The fusion stage is what an examiner often cares about most for AV anticipation — capture it explicitly even when the patent buries it inside a larger "perception system."
- **Disambiguation:** vs. `PERCEPTION_MODULE` — single-sensor perception is just `PERCEPTION_MODULE`. vs. `PREDICTION_MODULE` — fusion is about combining current observations; prediction is about future.
- **Attributes:** `fusion_stage` (early / mid / late), `input_modalities` (list of sensor types), `algorithm_family` (Kalman / NN / particle / heuristic)

#### `PREDICTION_MODULE`
> Projects future trajectories or behaviors of detected agents (other vehicles, pedestrians, cyclists).

- **Tight synonyms:** prediction module, behavior prediction, trajectory prediction, intent prediction, agent forecasting, motion prediction, pedestrian intent module
- **Loose synonyms:** forecasting module, anticipation module, world-model predictor
- **Extraction rule:** Specifically about *other* agents' future motion, not ego planning. If the module predicts only ego trajectory, that's `PLANNING_MODULE`.
- **Disambiguation:** vs. `PLANNING_MODULE` — planning decides ego action; prediction estimates other agents. vs. `PERCEPTION_MODULE` — perception observes; prediction projects.
- **Attributes:** `prediction_horizon_s`, `output_form` (single trajectory / distribution / multi-modal trajectories)

#### `PLANNING_MODULE`
> Decides the ego vehicle's intended path, behavior, or maneuver.

- **Tight synonyms:** path planner, trajectory planner, behavior planner, motion planner, maneuver planner, decision module, decision-making module, route planner, mission planner, lane-change planner, RRT planner, A* planner, MPC planner
- **Loose synonyms:** planner, decision engine, navigation planner, autonomy planner, top-level controller
- **Extraction rule:** Anything producing a desired ego path/trajectory/behavior. Many patents disclose a hierarchical stack (mission → behavior → trajectory) — extract each layer as a separate `PLANNING_MODULE` node with `level` attribute.
- **Disambiguation:** vs. `CONTROL_MODULE` — planning produces a desired trajectory; control turns it into actuator commands. The line is fuzzy in some patents that combine both — if the disclosure has a separate control stage, extract both; otherwise pick the dominant role.
- **Attributes:** `level` (mission / behavior / trajectory / lane / maneuver), `algorithm_family` (sampling / optimization / NN / rule-based)

#### `CONTROL_MODULE`
> Converts a planned trajectory into actuator-level commands (steering angle, accel, brake force).

- **Tight synonyms:** controller, motion controller, vehicle controller, lateral controller, longitudinal controller, steering controller, speed controller, PID controller, MPC controller, model-predictive controller, low-level controller
- **Loose synonyms:** drive controller, command generator, actuation layer
- **Extraction rule:** Closes the loop between planner and actuators. If the patent says "controller" without further qualification but the function is clearly actuator-command generation, this is the type.
- **Disambiguation:** vs. `PLANNING_MODULE` — planner says where to go; controller says how to actuate. vs. actuator nodes — the controller computes commands; the actuator executes them.
- **Attributes:** `axis` (lateral / longitudinal / both), `algorithm_family` (PID / MPC / NN / hybrid)

#### `SAFETY_MONITOR`
> Independent supervisory module that can detect unsafe states and override or constrain the primary autonomy stack. Often runs on a separate compute platform with its own sensing for ASIL-D / fail-operational architectures.

- **Tight synonyms:** safety monitor, safety supervisor, safety controller, fail-operational supervisor, fallback supervisor, safety domain controller, redundant safety processor, watchdog, safety watchdog, runtime safety monitor, runtime assurance monitor, safety arbiter
- **Loose synonyms:** monitor (loose — could mean log/metrics monitor), supervisor (loose — could mean a planner level)
- **Extraction rule:** Use when the disclosure describes a structurally separate safety chain that runs in parallel with the primary perception/planning/control stack and can intervene. Common pattern: takes redundant sensor input, runs simplified checks, can issue an `OVERRIDES` edge to `PLANNING_MODULE` or `CONTROL_MODULE`.
- **Disambiguation:** vs. `CONTROL_MODULE` — primary controller is part of the active control loop; safety monitor sits *outside* and intervenes only when needed. vs. `AV_COMPUTE_PLATFORM` — safety monitor often runs on its own platform but is itself a software role.
- **Attributes:** `compute_separation` (same_box / separate_compute / lockstep_pair), `intervention_modes` (limit_acceleration / lateral_lock / minimum_risk_maneuver / emergency_brake / handoff_to_driver), `ASIL_level` (A / B / C / D / unspecified)

#### `CHASSIS_CONTROLLER`
> ECU running vehicle-dynamics control loops — anti-lock braking (ABS), electronic stability control (ESC), traction control (TCS), yaw-moment control. Distinct from `CONTROL_MODULE` because it operates at chassis-dynamics timescale (often >100 Hz) and its claim language is heavily yaw / slip / friction-coefficient terminology.

- **Tight synonyms:** chassis controller, vehicle dynamics controller, VDC, electronic stability controller, ESC, ESP, electronic stability program, ABS controller, traction control system, TCS, yaw controller, yaw moment controller, integrated chassis control, ICC
- **Loose synonyms:** stability controller, dynamics controller, brake controller (loose — overlaps with `BRAKE_ACTUATOR` interface)
- **Extraction rule:** Use when the disclosure references stability / yaw / slip / lockup control as the function. Often interacts with `BRAKE_ACTUATOR` and `STEERING_ACTUATOR` to apply differential braking or steering corrections.
- **Disambiguation:** vs. `CONTROL_MODULE` — that's AV-stack motion control (trajectory tracking); chassis controller is the lower-level dynamics stabilization. vs. `BRAKE_ACTUATOR` — actuator executes; chassis controller commands.
- **Attributes:** `functions` (subset of: ABS / ESC / TCS / yaw_control / rollover_mitigation / brake_assist), `update_rate_hz`

### 1.3 Compute platforms

#### `AV_COMPUTE_PLATFORM`
> The physical compute hardware running perception / planning / control software.

- **Tight synonyms:** AV computer, autonomous driving computer, central compute platform, AI compute platform, in-vehicle compute, FSD computer, NVIDIA DRIVE platform, Tesla FSD chip, Mobileye EyeQ
- **Loose synonyms:** compute unit, processing platform, on-board computer, ECU, electronic control unit
- **Extraction rule:** Hardware, not software. Capture only when the patent specifically describes the compute platform as a structural element (chip, board, redundant pair). Generic mentions of "a processor" do not warrant a node — only when the disclosure cares about the hardware as such (redundancy, AI accelerators, automotive-grade certification, etc.).
- **Disambiguation:** vs. functional compute modules — those are software roles; this is the box they run on. vs. `DOMAIN_CONTROLLER` — domain controllers are domain-specific (chassis / ADAS / body / infotainment); the AV compute platform is the central autonomy brain. vs. `TELEMATICS_CONTROLLER` — telematics is a comms gateway, not the AV brain.
- **Attributes:** `redundancy` (single / dual / triple), `accelerator_type` (CPU / GPU / NPU / FPGA / ASIC), `certification` (ASIL-D / ASIL-B / etc.)

#### `DOMAIN_CONTROLLER`
> A consolidated ECU serving an entire functional domain — ADAS, chassis, body, infotainment, powertrain. Modern E/E architectures replace dozens of small ECUs with a few domain controllers, optionally further consolidated into zonal controllers (one per physical region of the vehicle).

- **Tight synonyms:** domain controller, ADAS domain controller, chassis domain controller, body domain controller, infotainment domain controller, powertrain domain controller, vehicle integration ECU, vehicle integration unit, VIU, zonal controller, zonal gateway, zone ECU, central gateway, central computer
- **Loose synonyms:** ECU (loose — covers any electronic control unit), gateway (loose — overlaps with telematics/network gateway)
- **Extraction rule:** Use when the disclosure references domain consolidation explicitly (one ECU serving multiple functions in a domain) or zonal architecture. Capture which domain via attribute.
- **Disambiguation:** vs. `AV_COMPUTE_PLATFORM` — the AV brain runs the autonomy stack itself. The ADAS domain controller may *be* the AV compute platform in some architectures, may be a separate front-end in others. vs. `TELEMATICS_CONTROLLER` — telematics is comms-specific; gateway/zonal controllers may host the telematics function as one role among several.
- **Attributes:** `domain` (ADAS / chassis / body / infotainment / powertrain / cockpit / safety / multi), `architecture_pattern` (centralized / domain / zonal / hybrid), `redundancy`

### 1.4 Actuators

#### `ACTUATOR`
> Generic parent for any electromechanical mechanism that converts a control signal into vehicle motion or motion-affecting force. Use when the patent says "actuator" without specifying steering / throttle / brake, or when the disclosure speaks at the level of "an actuator coupled to the controller."

- **Tight synonyms:** actuator, electromechanical actuator, drive-by-wire actuator, motion actuator, wheel actuator (loose; could be steering or brake)
- **Loose synonyms:** mechanism, drive mechanism, control mechanism
- **Extraction rule:** Use as the catch-all when the disclosure is intentionally generic. When the patent specifies the function, prefer `STEERING_ACTUATOR`, `THROTTLE_ACTUATOR`, or `BRAKE_ACTUATOR`.
- **Attributes:** `function_inferred` (unspecified / lateral / longitudinal / both)

#### `STEERING_ACTUATOR`
- **Parent type:** `ACTUATOR`
> Mechanism that physically turns the wheels in response to a steering command.

- **Tight synonyms:** steering actuator, electric power steering, EPS, steer-by-wire, steering motor, rack-mounted EPS, column-mounted EPS, steering rack actuator
- **Loose synonyms:** steering system, steering subsystem
- **Extraction rule:** The physical actuator only — the steering controller is `CONTROL_MODULE`.
- **Attributes:** `architecture` (column EPS / rack EPS / steer-by-wire), `redundancy`

#### `THROTTLE_ACTUATOR`
- **Parent type:** `ACTUATOR`
> Commands engine torque or drive-motor torque for forward propulsion.

- **Tight synonyms:** throttle actuator, throttle-by-wire, accelerator actuator, electronic throttle, drive-by-wire throttle, motor torque controller (when EV), powertrain command interface, vehicle speed adjusting actuator
- **Loose synonyms:** acceleration actuator, propulsion actuator
- **Extraction rule:** Commands forward motion. For EVs, this often is the inverter/motor torque request, which gets extracted as `THROTTLE_ACTUATOR` for ontology consistency even though there's no literal throttle.
- **Attributes:** `powertrain_type` (ICE / hybrid / EV / fuel-cell)

#### `BRAKE_ACTUATOR`
- **Parent type:** `ACTUATOR`
> Applies braking force, including regenerative braking.

- **Tight synonyms:** brake actuator, brake-by-wire, electronic brake, EBC, electric parking brake, regenerative braking system, brake hydraulic actuator, brake booster
- **Loose synonyms:** braking system, deceleration actuator
- **Attributes:** `architecture` (hydraulic / electric / regenerative / blended)

#### `WHEEL`
> The road wheel + tire as a structural element of the vehicle. Patents reference it constantly in chassis-dynamics, traction-control, lane-departure-yaw-moment, and tire-pressure-monitoring claims. We collapse wheel and tire into one canonical type because patent claim language conflates them ("turning inside wheel", "tire pressure", "wheel slip"); the matcher uses the synonyms to recognize either form.

- **Tight synonyms:** wheel, tire, tyre, road wheel, drive wheel, driven wheel, front wheel, rear wheel, left wheel, right wheel, turning inside wheel, turning outside wheel, vehicle wheel, wheel hub assembly
- **Loose synonyms:** rolling element, contact patch (loose — strictly the tire-road interface)
- **Extraction rule:** Use whenever the disclosure references wheels or tires as physical elements being controlled, monitored, or dimensioned. If the patent specifies which wheel (front-left, turning-inside, etc.), capture as attribute. Multi-wheel claims usually warrant one `WHEEL` node with `count=4` rather than four separate nodes — unless the disclosure treats individual wheels as distinct (independent torque vectoring, in-wheel motors).
- **Disambiguation:** vs. `STEERING_ACTUATOR` — actuator is what turns the wheel; the wheel itself is a separate structural element. vs. `BRAKE_ACTUATOR` — same idea: actuator applies force, wheel rotates.
- **Attributes:** `position` (front_left / front_right / rear_left / rear_right / front_axle / rear_axle / all / unspecified), `count`, `has_in_wheel_motor` (true / false / unspecified), `has_pressure_sensor` (true / false / unspecified)

### 1.5 Communications

#### `IN_VEHICLE_NETWORK`
> The bus / network that connects ECUs and components inside the vehicle — CAN, CAN-FD, FlexRay, LIN, MOST, automotive Ethernet, time-sensitive networking. Captured as a node when the patent's claim involves the network topology, redundancy, or specific bus protocol as part of the inventive concept.

- **Tight synonyms:** in-vehicle network, vehicle network, CAN bus, CAN-FD, FlexRay, LIN bus, MOST bus, automotive Ethernet, TSN, time-sensitive networking, in-vehicle Ethernet, IVN, vehicle backbone, automotive backbone, ring network (when in-vehicle), star topology, redundant bus, gateway bus
- **Loose synonyms:** bus (loose), network (loose), wired link (loose — could be intra- or inter-component)
- **Extraction rule:** Extract when the disclosure references the network as an inventive structural element (specific protocol, topology, redundancy scheme, gateway pattern, mixed-criticality scheduling). Generic mentions of "wired connection" or "communication path" without protocol detail don't warrant a node — those are implicit in `SENDS_TO` edges.
- **Disambiguation:** vs. `TELEMATICS_CONTROLLER` — telematics is the off-board-comms gateway; in-vehicle network is the on-vehicle bus it bridges to. vs. `V2X_TRANSCEIVER` — V2X is short-range RF; in-vehicle network is wired/optical inside the vehicle.
- **Attributes:** `protocol` (CAN / CAN-FD / FlexRay / LIN / MOST / automotive_Ethernet / TSN / proprietary / multi), `topology` (bus / star / ring / hybrid), `redundancy` (single / dual / triple), `safety_critical` (true / false / unspecified)

#### `TELEMATICS_CONTROLLER`
> On-vehicle gateway bridging in-cabin / chassis networks to off-board cellular / cloud services.

- **Tight synonyms:** telematics control unit, TCU, T-Box, telematics ECU, vehicle gateway, vehicle gateway ECU, connectivity controller, head-unit gateway, in-vehicle communications module, cellular gateway, eCall module
- **Loose synonyms:** comms module, connectivity ECU, data router, in-vehicle modem
- **Extraction rule:** Bidirectional bridge between **in-vehicle networks** (CAN, automotive Ethernet) and **off-board networks** (cellular, Wi-Fi). Distinct from infotainment unless the disclosure specifically calls out the cellular/V2X stack.
- **Disambiguation:** vs. `V2X_TRANSCEIVER` — V2X is short-range vehicle-to-X (DSRC, C-V2X PC5); telematics is long-range cellular/cloud. vs. infotainment — only call this telematics if cellular/V2X is the primary role.
- **Attributes:** `bearer` (4G / 5G / Wi-Fi / multi), `supports_ota`, `supports_ecall`

#### `V2X_TRANSCEIVER`
> Short-range radio for vehicle-to-vehicle / vehicle-to-infrastructure / vehicle-to-pedestrian comms.

- **Tight synonyms:** V2X module, V2X transceiver, V2V module, V2I module, DSRC radio, dedicated short-range communications, C-V2X module, cellular V2X, PC5 sidelink, OBU, on-board unit
- **Loose synonyms:** roadside-comms module, vehicle-comms module, ITS module
- **Extraction rule:** Specifically peer-to-peer or vehicle-to-infrastructure short-range. If the disclosure ambiguously says "wireless module," lean on context — DSRC bands (5.9 GHz) or BSM messaging confirms V2X.
- **Disambiguation:** vs. `TELEMATICS_CONTROLLER` — telematics is cellular long-range; V2X is short-range peer/infra. They often coexist in the same patent.
- **Attributes:** `radio_technology` (DSRC / C-V2X / hybrid), `message_set_supported` (BSM / SPaT / MAP / PSM)

### 1.6 Servers / off-board services

#### `SERVER`
> Compute resource not tied to the ego vehicle's autonomy stack — fleet ops, HD-map service, OTA backend, ML training infrastructure, cloud teleassist, roadside edge compute, third-party data provider.

- **Tight synonyms:** server, backend server, cloud server, fleet management server, HD map server, teleoperations server, remote operator center, OTA server, cloud platform, edge server (when roadside, not in-vehicle), data center, microservice
- **Loose synonyms:** remote compute, backend, off-board system, ground station, cloud, web service, hosting infrastructure
- **Extraction rule:** Anything that is **not the ego vehicle's own compute** but provides a service the vehicle consumes or that ingests vehicle data. Capture the **role(s)** (`map_server` / `fleet_ops` / `ota` / `teleassist` / `analytics` / `key_management` / `data_broker`) as an attribute since one server can play several. Capture **location** (`cloud` / `roadside_edge` / `private_data_center` / `peer_vehicle_compute`).
- **Disambiguation:** vs. `AV_COMPUTE_PLATFORM` — that's in-vehicle; this is anywhere else. vs. `MOBILE_DEVICE` — a smartphone running an app is a `MOBILE_DEVICE`, not a server, even if it exposes a network endpoint. The literal word "edge" is ambiguous — verify by checking whether the disclosure means in-vehicle compute (→ `AV_COMPUTE_PLATFORM`) or roadside/cloud (→ `SERVER`).
- **Attributes:** `roles` (list), `location` (cloud / roadside_edge / private_data_center / peer_vehicle_compute), `connection_to_vehicle` (cellular / V2X / wifi / wired)

### 1.7 HMI

#### `DRIVER_INTERFACE`
> Hardware/software exposed to the human driver — display, input controls, driver monitoring camera.

- **Tight synonyms:** HMI, human-machine interface, driver display, instrument cluster, head-up display, HUD, infotainment display, touch panel, steering wheel button cluster, driver monitoring system, DMS, driver-facing camera, gaze-tracking camera, takeover request indicator
- **Loose synonyms:** display, dashboard, user interface, driver UI
- **Extraction rule:** Anything where the human and the AV stack interact bidirectionally. Includes both information presentation (HUD, cluster) and intent capture (button, voice, gaze).
- **Attributes:** `function` (display / input / monitoring / multi)

### 1.8 Data sources / persistence

#### `DATA_LOGGER`
> Onboard storage of vehicle / sensor / event data for post-incident reconstruction, regulatory compliance, ML training, and operational telemetry. The "EDR" (event data recorder) and "drive recorder" pattern, with growing scope for AV-specific DSSAD (data storage system for automated driving) requirements.

- **Tight synonyms:** data logger, event data recorder, EDR, drive recorder, AV black box, autonomous vehicle data recorder, DSSAD, data storage system for automated driving, telemetry logger, sensor data logger, blackbox
- **Loose synonyms:** logger (loose — could mean software logger), recorder (loose), storage device (loose)
- **Extraction rule:** Use when the disclosure references onboard logging of vehicle dynamics, sensor data, or events for post-event analysis — distinct from operational `DATABASE` use. EDR-specific patents (regulatory or self-imposed) almost always warrant this node.
- **Disambiguation:** vs. `DATABASE` — database is structured live data; data logger is append-only event/telemetry capture, often with strict retention and tamper-resistance requirements. vs. `MEMORY` (not a canonical type) — refers to a structural recording subsystem, not generic memory.
- **Attributes:** `data_classes` (vehicle_dynamics / sensor_raw / sensor_processed / control_commands / event_snapshots / video / audio / multi), `retention_policy` (rolling_buffer / event_triggered / continuous / regulatory_minimum), `tamper_resistance` (true / false / unspecified), `regulatory_mode` (DSSAD / EDR / fleet_telemetry / unspecified)

#### `DATABASE`
> A structured data store — on-vehicle (e.g., HD-map cache, telemetry log, audit trail) or off-board (fleet operations DB, ride-history DB, ML feature store). Distinct from `SERVER` (which *hosts* databases) and from `HD_MAP_DATA` (which is one specific kind of stored content).

- **Tight synonyms:** database, DB, data store, datastore, repository, data repository, knowledge base, KB, table store, key-value store, document store, time-series database, telemetry database, log database, feature store, vector database, vector store
- **Loose synonyms:** storage, archive, registry, ledger, cache, memory store
- **Extraction rule:** Extract a `DATABASE` node whenever the disclosure references a structured store accessed by the system — local or remote. Capture **what's stored** as a `content_kind` attribute, **where it lives** as a `location` attribute, and **how it's accessed** via incoming `READS_FROM` / `WRITES_TO` edges. If the patent references a server that *contains* a database, extract both: the `SERVER` and the `DATABASE`, linked via `PART_OF` (the database is part of the server).
- **Disambiguation:** vs. `HD_MAP_DATA` — that's a specific *kind of stored content* with its own behavior; `DATABASE` is the generic structured store. If both apply (e.g., "the HD map is stored in a vector database"), extract both, linked via `PART_OF`. vs. `SERVER` — server is the compute host; database is the data layer it serves.
- **Attributes:**
  - `location` (on_vehicle / cloud / roadside_edge / mobile_device)
  - `content_kind` (hd_map / telemetry / event_log / audit / customer / training_data / vector_embeddings / configuration / other)
  - `paradigm` (relational / document / key_value / time_series / vector / graph / object / unspecified)
  - `update_method` (static / batch / streaming / OTA)

#### `HD_MAP_DATA`
> High-definition map data used for localization, planning, and prediction. Modeled as a node because it is a discrete data input the rest of the system depends on.

- **Tight synonyms:** HD map, high-definition map, lane-level map, semantic map, map tile, map data store, prior map, vector map, base map, lanelet map
- **Loose synonyms:** map, navigation map (loose because nav maps are typically lower fidelity)
- **Extraction rule:** Map data is a node when the disclosure treats it as a structural input (stored on-vehicle, fetched from `OFF_BOARD_SERVER`, indexed by location). Generic statements like "the vehicle has GPS navigation" do not warrant a node.
- **Disambiguation:** vs. `SERVER` with `roles=[map_server]` — the *server* is one node, the *data* delivered is another. They link via `READS_FROM`.
- **Attributes:** `format` (lanelet / OpenDRIVE / proprietary), `update_method` (static / OTA / streaming)

### 1.9 Environmental entities

> Things in the world the ego vehicle perceives, predicts, communicates with, or navigates around. These are *not* components of the ego vehicle — they are the surrounding context. They show up as referents in claims constantly ("a sensor that detects a preceding vehicle", "the system communicates with a roadside traffic light").
>
> Organized into three sub-categories:
> - **Vehicles & peer platforms** — ego, nearby, preceding, ground robot, aerial
> - **Road obstacles** (`ROAD_OBSTACLE` parent + 7 child types: pedestrian, cyclist, animal, debris, accident scene, hazard, work zone)
> - **Roadway features** — road, intersection, lane marking, traffic light, traffic sign, parking space
> - **Human-related** — operator, mobile device variants
>
> The `ROAD_OBSTACLE` hierarchy mirrors examiner BRI: a patent disclosing a "pedestrian detector" reads on a claim's "obstacle detector" because *pedestrian is a kind of obstacle*. The matcher uses the `parent_type` field to apply this reasoning automatically.

#### `VEHICLE`
> The ego vehicle itself, treated as a structural element when the disclosure cares about its physical form (sedan / SUV / truck / motorcycle / bus), powertrain (ICE / hybrid / EV / fuel-cell), or the fact that components are mounted on / integrated with it.

- **Tight synonyms:** vehicle, ego vehicle, host vehicle, subject vehicle, the vehicle, automobile, car, passenger car, autonomous vehicle, self-driving vehicle, AV, automated vehicle, host car
- **Loose synonyms:** unit, platform, machine, transport
- **Extraction rule:** Almost every patent has this implicitly. Extract a `VEHICLE` node when the disclosure makes a claim about *what kind* of vehicle, *what's mounted on it*, or *its physical configuration*. If the patent only describes computational/software elements with no physical claim about the vehicle itself, the `VEHICLE` node may be omitted to keep graphs sparse.
- **Disambiguation:** vs. `NEARBY_VEHICLE` — `VEHICLE` is *the ego vehicle*; `NEARBY_VEHICLE` is anyone else.
- **Attributes:** `body_type` (sedan / SUV / truck / motorcycle / bus / shuttle / robotaxi), `powertrain` (ICE / hybrid / EV / fuel_cell), `automation_level` (SAE 0–5)

#### `NEARBY_VEHICLE`
> Another vehicle sharing the road — perceived by the ego vehicle's sensors, predicted by the prediction module, and/or communicated with via V2X.

- **Tight synonyms:** nearby vehicle, surrounding vehicle, other vehicle, remote vehicle, target vehicle, neighboring vehicle, adjacent vehicle, oncoming vehicle, cross-traffic vehicle, following vehicle, traffic participant (when it's a vehicle), road agent (when it's a vehicle)
- **Loose synonyms:** traffic, agent, road user, dynamic obstacle (loose because pedestrians/cyclists also fit)
- **Extraction rule:** Any disclosed vehicle that is *not* the ego vehicle. Capture the relative position via attribute when the patent specifies it. If the patent specifically calls out the *preceding* vehicle, prefer `PRECEDING_VEHICLE` for the additional matching specificity.
- **Disambiguation:** vs. `PRECEDING_VEHICLE` — preceding is a strict specialization. vs. `VEHICLE` — that's ego only.
- **Attributes:** `relative_position` (preceding / following / adjacent_left / adjacent_right / oncoming / cross_traffic / unspecified), `count` (single / multiple / fleet)

#### `PRECEDING_VEHICLE`
- **Parent type:** `NEARBY_VEHICLE`
> The vehicle directly ahead of the ego vehicle in the same lane. Distinct canonical type because it is *the* central referent in adaptive cruise control, lane following, automated platooning, and rear-end collision avoidance claims.

- **Tight synonyms:** preceding vehicle, lead vehicle, leading vehicle, vehicle ahead, vehicle in front, front vehicle, forward vehicle, target vehicle (in ACC/CACC context)
- **Loose synonyms:** the other vehicle (loose — context-dependent), platoon leader (loose — only fits when platoon disclosed)
- **Extraction rule:** Use when the disclosure specifically references the vehicle directly ahead, especially in claims about following distance, time-headway, ACC, CACC, or collision warning. If the patent mentions *both* preceding and other surrounding vehicles, extract both `PRECEDING_VEHICLE` and one or more `NEARBY_VEHICLE` nodes.
- **Disambiguation:** vs. `NEARBY_VEHICLE` — preceding is the strict specialization (directly ahead, same lane). When in doubt, use `NEARBY_VEHICLE` with `relative_position=preceding`.
- **Attributes:** `same_lane` (true / false / unspecified), `following_distance_m`, `time_headway_s`

#### `TRAFFIC_LIGHT`
> Roadside signal device controlling vehicle right-of-way at intersections or other regulated points. Both perceived (by camera + perception) and potentially communicated with (via V2I / SPaT).

- **Tight synonyms:** traffic light, traffic signal, signal, signal light, stoplight, traffic control device, signal head
- **Loose synonyms:** light (loose — could mean headlight, brake light), signal (loose — could mean turn signal)
- **Extraction rule:** Disclosed roadside signal whose state controls vehicle motion. If the patent describes V2I exchange of signal phase / timing (SPaT messages), additionally link the `TRAFFIC_LIGHT` to a `SERVER` (with `roles=[v2i_provider]`) or to a roadside `V2X_TRANSCEIVER`.
- **Disambiguation:** vs. `TRAFFIC_SIGN` (separate type if added) — signs are static; signals change state.
- **Attributes:** `phases` (red/yellow/green / pedestrian / left-turn arrow / etc.), `controllable_by_v2i` (true / false / unspecified)

#### `INTERSECTION`
> A topological road feature where two or more roads cross or merge — explicitly referenced when the claim is about intersection-management, unprotected-turn, traffic-light interaction, four-way-stop reasoning, or roundabout navigation.

- **Tight synonyms:** intersection, junction, crossroads, four-way stop, T-intersection, roundabout, traffic circle, signalized intersection, unsignalized intersection, merge point, on-ramp merge, off-ramp diverge
- **Loose synonyms:** road junction, crossing
- **Extraction rule:** Extract when the disclosure treats the intersection as a *thing the vehicle reasons about* — not just where the vehicle happens to be. Often appears in conjunction with `TRAFFIC_LIGHT`, `MAP_TILE`, and `PLANNING_MODULE`.
- **Disambiguation:** vs. `MAP_TILE` — map data describes the intersection; the intersection itself is a separate node when the disclosure reasons about it directly.
- **Attributes:** `geometry_type` (4-way / T / roundabout / merge / diverge / unspecified), `signalized` (true / false / unspecified), `lane_count_in/out`

#### `MOBILE_DEVICE`
> A user-carried smartphone, tablet, or wearable that interacts with the AV stack. Generic catch-all for cases where the disclosure doesn't specify whose device it is (e.g., "a fleet operator's mobile device", "a remote user's phone", "a third-party device").

- **Tight synonyms:** mobile device, smartphone, phone, smart phone, mobile phone, tablet, smartwatch, wearable, user device, fleet operator device, remote user device, third-party mobile device
- **Loose synonyms:** device (loose — could mean any onboard device), terminal
- **Extraction rule:** Use when the disclosure references a user-carried device but doesn't specify *whose*. When the role is identified (driver vs passenger), prefer the specific subtypes below. The *app* on the device is captured as an attribute, not a separate node.
- **Disambiguation:** vs. `DRIVER_MOBILE_DEVICE` / `PASSENGER_MOBILE_DEVICE` — use those when the disclosure specifies the carrier. vs. `SERVER` — phones aren't servers even when they expose APIs. vs. `DRIVER_INTERFACE` — that's the in-cabin UI; mobile devices are user-carried.
- **Attributes:** `role` (fleet_app / digital_key / remote_summon / third_party / unspecified), `connection_to_vehicle` (cellular / BLE / NFC / wifi)

#### `DRIVER_MOBILE_DEVICE`
- **Parent type:** `MOBILE_DEVICE`
> A smartphone / tablet / wearable carried by the *driver* (or designated operator) — distinct because the trust model, pairing pattern, and use cases (digital key, remote summon, vehicle diagnostics, infotainment pairing) differ from devices carried by passengers.

- **Tight synonyms:** driver's phone, driver phone, driver's smartphone, driver mobile device, owner's phone, key fob phone, digital key phone, remote summon device, driver's wearable, driver smartwatch
- **Loose synonyms:** authorized device, paired device, registered phone
- **Extraction rule:** Use when the disclosure makes clear the device belongs to the *driver / operator / owner* — typically associated with paired authentication, digital-key features, remote summon, or pre-drive vehicle interactions. If the patent is about ride-hailing (driver vs rider), this is the human at the wheel (or the operator triggering autonomous summon).
- **Disambiguation:** vs. `PASSENGER_MOBILE_DEVICE` — passenger devices belong to non-driver occupants; their permissions and interactions differ. vs. `MOBILE_DEVICE` — generic when role is unspecified. vs. `DRIVER_INTERFACE` — that's the in-cabin UI; this is a separate device the driver carries.
- **Attributes:**
  - `role` (digital_key / remote_summon / diagnostics / infotainment_pair / driver_authentication / driver_monitoring_companion)
  - `paired` (true / false / unspecified)
  - `connection_to_vehicle` (cellular / BLE / NFC / wifi / UWB)

#### `GROUND_MOBILE_ROBOT`
> Non-passenger autonomous ground platform — warehouse robots, sidewalk delivery bots, industrial AGVs, mobile drive units, agricultural rovers, inspection robots. Important for coordinated-mobility claims and **analogous-art rejections** — many warehouse / delivery / agricultural autonomy patents anticipate passenger-AV claims at the perception, planning, or fleet-coordination level.

- **Tight synonyms:** robot, mobile robot, autonomous mobile robot, AMR, autonomous ground vehicle, AGV, automated guided vehicle, mobile drive unit, MDU, warehouse robot, delivery robot, sidewalk robot, last-mile delivery robot, ground drone, inspection robot, agricultural robot
- **Loose synonyms:** unmanned vehicle (loose — could mean aerial or marine), self-driving robot, drone (loose — usually aerial)
- **Extraction rule:** Extract when the disclosure references an autonomous or remotely-supervised ground platform that is *not* a passenger vehicle. If the patent's whole subject is a delivery robot or warehouse AGV, that platform is treated as the disclosure's "vehicle" — extract `GROUND_MOBILE_ROBOT` as the central node where a passenger-AV patent would have `VEHICLE`. If the disclosure is about a passenger AV that *interacts* with such robots (coordinated curb-side delivery, mixed pedestrian-and-robot perception), extract them as a separate node alongside the ego `VEHICLE`.
- **Disambiguation:** vs. `VEHICLE` / `NEARBY_VEHICLE` — those are passenger vehicles. vs. `AERIAL_VEHICLE` — this rolls; that flies.
- **Attributes:**
  - `form_factor` (warehouse_AGV / sidewalk_delivery / industrial_floor / inspection / agricultural / cleaning / quadruped / humanoid / other)
  - `payload_class` (light / heavy / hazardous / passenger_capable / unspecified)
  - `navigation_mode` (rail_guided / SLAM / fiducial / GPS / hybrid / unspecified)
  - `is_disclosure_subject` (true if the patent is *about* this robot vs. just referring to one)

#### `AERIAL_VEHICLE`
> Autonomous or remotely-piloted aerial platform — UAV, multicopter, fixed-wing drone, VTOL/eVTOL. Relevant for V2X-with-drones claims, drone-as-roadside-unit, drone-assisted perception (overhead view feeding ground vehicles), package-delivery coordination, and the eVTOL-passenger-mobility category that increasingly cross-cites with road-AV art.

- **Tight synonyms:** UAV, unmanned aerial vehicle, drone, aerial drone, aerial vehicle, autonomous aerial vehicle, multicopter, quadcopter, hexacopter, octocopter, fixed-wing UAV, VTOL, eVTOL, electric vertical takeoff and landing, delivery drone, surveillance drone, mapping drone
- **Loose synonyms:** aircraft (loose — could be manned), flying robot, UAS, unmanned aircraft system
- **Extraction rule:** Extract when the disclosure references an aerial autonomous platform. As with `GROUND_MOBILE_ROBOT`, if the patent's subject *is* the aerial vehicle, treat it as the central platform node; if the patent is about a passenger AV that interacts with one (drone-fed overhead perception, V2I from a drone, package-handoff coordination), extract as a separate adjacent node.
- **Disambiguation:** vs. `GROUND_MOBILE_ROBOT` — flies vs. rolls. vs. `VEHICLE` — passenger eVTOL is genuinely ambiguous; if the disclosure treats it as a passenger-mobility platform with seats and a driver/operator, extract it as `VEHICLE` with `body_type=eVTOL` instead. Use `AERIAL_VEHICLE` for unmanned or cargo-only flying platforms.
- **Attributes:**
  - `form_factor` (quadcopter / hexacopter / octocopter / fixed_wing / VTOL / eVTOL / hybrid_VTOL / lighter_than_air / other)
  - `purpose` (delivery / surveillance / inspection / mapping / passenger_eVTOL / data_relay / agricultural / other)
  - `max_payload_kg`
  - `max_endurance_min`
  - `is_disclosure_subject` (true if the patent is *about* the aerial vehicle vs. just referring to one)

#### `PASSENGER_MOBILE_DEVICE`
- **Parent type:** `MOBILE_DEVICE`
> A smartphone / tablet / wearable carried by a non-driver occupant — used for ride-hailing rider experience, in-cabin entertainment pairing, ride sharing identity, and cabin-environment personalization.

- **Tight synonyms:** passenger's phone, passenger phone, passenger's smartphone, passenger mobile device, rider's phone, rider phone, rider device, occupant device, rider app device, robotaxi rider device
- **Loose synonyms:** guest device, in-cabin device
- **Extraction rule:** Use when the disclosure references a device carried by a non-driver occupant — most commonly in robotaxi / ride-sharing patents (rider summons / unlocks / personalizes the cabin). Also covers patents about in-cabin infotainment streaming to a passenger's device.
- **Disambiguation:** vs. `DRIVER_MOBILE_DEVICE` — driver vs non-driver carrier. vs. `MOBILE_DEVICE` — generic when carrier role is unspecified.
- **Attributes:**
  - `role` (rider_app / cabin_personalization / infotainment_streaming / fare_payment / rider_authentication / accessibility_assist)
  - `paired` (true / false / unspecified)
  - `connection_to_vehicle` (cellular / BLE / NFC / wifi)

#### `ROAD_OBSTACLE`
> Generic catch-all for things in or near the roadway that the ego vehicle should perceive, classify, and avoid or respond to. Use as the canonical type when the patent's disclosure is generic ("an obstacle", "an object in the roadway"); use a more specific child type when the disclosure names what the obstacle is.

- **Tight synonyms:** obstacle, road obstacle, object in the roadway, road object, hazard (loose; see HAZARD child), barrier, blockage, target object (in collision-avoidance context), foreign object, stationary object, dynamic object
- **Loose synonyms:** object (very loose — could mean any node), thing, item, target (loose — could mean target vehicle / target lane)
- **Extraction rule:** Map generic obstacle / object disclosures here. When the patent specifies the kind of obstacle (pedestrian, cyclist, animal, debris, etc.), prefer the child type — but if the disclosure switches between generic and specific in the same claim, extract both nodes (a generic `ROAD_OBSTACLE` and the specific child) so the matcher can reason at either level.
- **Disambiguation:** vs. `NEARBY_VEHICLE` family — vehicles are agents, not obstacles, even though they can collide; keep the vehicle taxonomy separate. vs. `LANE_MARKING` / `TRAFFIC_SIGN` — those are road infrastructure, not obstacles.
- **Attributes:** `agency` (dynamic_agent / static_object / environmental_condition), `classified_by` (perception / V2X / map / unspecified)

#### `PEDESTRIAN`
- **Parent type:** `ROAD_OBSTACLE`
> A human on foot in or near the roadway.

- **Tight synonyms:** pedestrian, person, walker, foot traffic, jaywalker, person crossing, vulnerable road user (loose — also covers cyclists), VRU
- **Loose synonyms:** human, individual
- **Extraction rule:** Use when the disclosure specifically references a person on foot. If the patent uses "pedestrian and cyclist" together as a category, extract both as separate nodes.
- **Attributes:** `posture` (standing / walking / running / fallen / unspecified), `crossing_intent` (estimated / declared / unknown)

#### `CYCLIST`
- **Parent type:** `ROAD_OBSTACLE`
> A human riding a bicycle, e-bike, scooter, or similar small wheeled personal mobility device in or near the roadway.

- **Tight synonyms:** cyclist, bicyclist, bike rider, e-bike rider, scooter rider, micromobility rider, vulnerable road user (loose — also covers pedestrians)
- **Loose synonyms:** rider (loose — could mean motorcyclist or passenger), bicycle (loose — refers to vehicle, not person)
- **Extraction rule:** Includes any small personal-mobility human-powered or low-power device with a single rider (bicycle, e-bike, e-scooter, mobility scooter). Distinguish from motorcyclist if the disclosure makes the distinction; otherwise prefer `CYCLIST` for non-motorcycle two-wheel.
- **Attributes:** `device_type` (bicycle / e-bike / e-scooter / mobility-scooter / unspecified)

#### `ANIMAL`
- **Parent type:** `ROAD_OBSTACLE`
> A non-human living creature in or near the roadway — wildlife, livestock, pets.

- **Tight synonyms:** animal, deer, wildlife, livestock, dog, cat, pet, large animal, small animal
- **Loose synonyms:** creature, fauna
- **Extraction rule:** Use whenever the disclosure references animals as a perceived entity. If the patent specifies category (large vs. small, wildlife vs. domestic), capture as attribute.
- **Attributes:** `size_class` (small / medium / large / unspecified), `category` (wildlife / livestock / domestic / unspecified)

#### `DEBRIS`
- **Parent type:** `ROAD_OBSTACLE`
> Physical objects in the roadway that don't move under their own power — fallen trees, tire shred, dropped cargo, broken parts, lost loads.

- **Tight synonyms:** debris, road debris, fallen object, dropped cargo, lost load, tire shred, fallen tree, fallen branch, broken part, road hazard (loose; see HAZARD), foreign object debris, FOD
- **Loose synonyms:** object on road, item in lane
- **Extraction rule:** Static physical objects, distinct from environmental conditions (`HAZARD`) and from active incident scenes (`ACCIDENT_SCENE`).
- **Attributes:** `size_class` (small / medium / large / unspecified), `material` (organic / metal / cargo / unspecified)

#### `ACCIDENT_SCENE`
- **Parent type:** `ROAD_OBSTACLE`
> An active incident — wrecked or disabled vehicles, deployed airbags, scattered parts, emergency responders, flares, cones placed in response to a collision.

- **Tight synonyms:** accident scene, crash scene, collision scene, disabled vehicle, wrecked vehicle, emergency response scene, incident scene, broken-down vehicle
- **Loose synonyms:** stopped vehicle (loose — could be just stopped, not an accident), emergency situation
- **Extraction rule:** Use when the disclosure references the *scene* itself, especially involving emergency responders, deployed safety equipment, or collision aftermath. Distinguish from `WORK_ZONE` (planned construction) and from `DEBRIS` (physical objects without ongoing incident context).
- **Attributes:** `responders_present` (true / false / unspecified), `vehicles_involved_count`

#### `HAZARD`
- **Parent type:** `ROAD_OBSTACLE`
> Environmental danger condition — water, ice, oil spill, sinkhole, fog patch, smoke, flooding. Not a discrete object, but a region of the roadway with degraded driveability.

- **Tight synonyms:** hazard, road hazard, ice patch, water on road, hydroplaning condition, oil spill, sinkhole, pothole, fog patch, smoke, flooding, washout, surface contamination
- **Loose synonyms:** danger, risk, unsafe area, slippery condition
- **Extraction rule:** Use for *condition*-type obstacles, not discrete objects. If the patent describes degraded surface conditions or visibility, this is the type. Distinguish from `DEBRIS` (discrete physical objects) and `WEATHER_DATA` content type (which is the data describing weather).
- **Attributes:** `condition_type` (ice / water / oil / sinkhole / pothole / fog / smoke / flooding / other), `severity` (low / medium / high / unspecified)

#### `WORK_ZONE`
- **Parent type:** `ROAD_OBSTACLE`
> A planned construction or maintenance zone — cones, barriers, workers, equipment, signage indicating a temporary lane shift or closure.

- **Tight synonyms:** work zone, construction zone, road work, road construction, maintenance zone, lane closure, temporary work zone, traffic cone arrangement
- **Loose synonyms:** roadwork, construction (loose — could mean any building activity)
- **Extraction rule:** Distinguish from `ACCIDENT_SCENE` (unplanned incident) and `HAZARD` (environmental condition). Work zones are intentional and typically signaled.
- **Attributes:** `signaled_by` (cones / barriers / signs / arrow_board / multi), `worker_present` (true / false / unspecified)

#### `ROAD`
> The roadway itself — the topological substrate the ego vehicle drives on. Used when the disclosure references "the road" / "roadway" as a structural element distinct from intersections, lanes, or the vehicles on it.

- **Tight synonyms:** road, roadway, highway, street, freeway, expressway, surface road, lane (loose — `LANE_MARKING` is more specific), thoroughfare, path
- **Loose synonyms:** route (loose — route is a planned path through roads, see `EGO_TRAJECTORY`), driving surface
- **Extraction rule:** Extract when the disclosure treats the road as a referent ("vehicles travelling on a road", "shape of the road", "approaching the road"). When the patent specifically discusses lane markings or intersections, prefer `LANE_MARKING` / `INTERSECTION` for those features.
- **Disambiguation:** vs. `INTERSECTION` — intersections are points where roads meet; the road is the linear substrate. vs. `LANE_MARKING` — markings are painted features *on* the road.
- **Attributes:** `class` (highway / urban / rural / private / parking_lot / unspecified), `lane_count`, `surface` (asphalt / concrete / gravel / dirt / unspecified)

#### `LANE_MARKING`
> Painted or otherwise demarcated lane boundary on the road surface — solid lines, dashed lines, lane-departure boundaries, stop bars, crosswalks (loose).

- **Tight synonyms:** lane marking, lane line, road marking, painted line, lane boundary, lane stripe, dashed line, solid line, double yellow, white line, stop bar, lane departure boundary
- **Loose synonyms:** marking, line, road paint, crosswalk (loose — sometimes its own thing), road sign (loose — different)
- **Extraction rule:** Map painted / physical lane delineators. Distinguish from `TRAFFIC_SIGN` (vertical signage) and from `ROAD` (the substrate).
- **Attributes:** `style` (solid / dashed / double / dotted / unspecified), `color` (white / yellow / red / blue / unspecified)

#### `TRAFFIC_SIGN`
> Roadside or overhead signage conveying static or quasi-static information — stop signs, yield signs, speed limit signs, route markers, regulatory and warning signs.

- **Tight synonyms:** traffic sign, road sign, regulatory sign, warning sign, stop sign, yield sign, speed limit sign, route marker, guide sign, no-entry sign, do-not-enter sign, signage
- **Loose synonyms:** sign (loose — could be any sign), road information
- **Extraction rule:** Use for signs whose state is static (or changes only via maintenance). Distinguish from `TRAFFIC_LIGHT` (signal that cycles) and `LANE_MARKING` (painted lane delineators).
- **Attributes:** `category` (regulatory / warning / guide / route / construction / other), `mounting` (post / overhead / portable_sign_board)

#### `PARKING_SPACE`
> A discrete parking position — single-vehicle or structural (multi-space lot or garage). Important for AV-summon, parking-management, and ride-hailing pickup/dropoff claims.

- **Tight synonyms:** parking space, parking spot, parking stall, parking position, parking slot, parking bay, dropoff zone, pickup zone, loading zone, parking structure (loose — sometimes refers to whole facility), parking lot (loose — facility)
- **Loose synonyms:** space, slot, position
- **Extraction rule:** Use for individual parking positions and the immediate context (single bay, ADA bay). For the larger facility (whole lot, whole garage), capture as attribute or extract as a separate `PARKING_FACILITY` if v2 needs it. For now, fold facility into this type with `scope=facility` attribute.
- **Attributes:** `scope` (individual_space / facility), `accessibility` (standard / ADA / EV_charging / motorcycle / other), `occupancy_state` (occupied / vacant / reserved / unknown)

#### `HUMAN_OPERATOR`
> A human in a non-driver role who interacts with the AV stack — fleet operations console operator, parking-lot operator, teleassist remote driver, ride-hailing dispatcher, safety supervisor.

- **Tight synonyms:** operator, human operator, fleet operator, teleassist operator, remote operator, dispatcher, safety driver (when in supervisory role), monitor, supervisor, parking lot operator, fleet dispatcher, command center operator
- **Loose synonyms:** user (loose — could mean rider or driver), agent (loose — could mean software agent or human)
- **Extraction rule:** Use for humans whose role is non-driver and non-passenger. Distinguish from a literal driver in the vehicle (extracted as a relationship to `DRIVER_INTERFACE` rather than as a separate node) and from passengers / riders. Often appears as the recipient of an alert or the issuer of a remote command.
- **Disambiguation:** vs. `DRIVER_INTERFACE` — that's the surface; this is the human. vs. ride-hailing rider — riders are extracted via `PASSENGER_MOBILE_DEVICE` or as occupants.
- **Attributes:** `role` (fleet_dispatcher / teleassist / safety_supervisor / parking_operator / dispatcher / other), `location` (in_facility / remote / in_vehicle)

### 1.10 Software methods

#### `ALGORITHM`
> A specific computational method the patent claims as inventive on its own — distinct from the module that runs it. Use when the disclosure makes the *algorithm itself* a structural element of the claim, not merely a generic implementation detail.

- **Tight synonyms:** algorithm, method, technique, procedure, process, computational method, machine learning model, neural network, deep learning model, classifier, regressor, policy, optimizer
- **Loose synonyms:** approach, scheme, mechanism, logic, function (loose — could mean a software function or a mathematical function)
- **Extraction rule:** Extract an `ALGORITHM` node when the patent specifically claims an algorithmic technique (e.g., "a Kalman filter algorithm for fusing", "a neural network trained to detect"). Link it to the compute module that runs it via `PART_OF`. If the disclosure only mentions algorithms generically as implementation detail of a module, capture the algorithm family as an attribute on the module instead and skip the `ALGORITHM` node.
- **Disambiguation:** vs. functional compute modules — modules are roles; algorithms are the methods inside them. A `PERCEPTION_MODULE` *uses* one or more `ALGORITHM`s. vs. `AV_COMPUTE_PLATFORM` — that's hardware; algorithm is software-only.
- **Attributes:**
  - `family` (one of the canonical sub-types below, or `OTHER`)
  - `purpose` (perception / fusion / prediction / planning / control / localization / classification / other)
  - `training_data_required` (true / false / unspecified)
- **Canonical algorithm sub-types** (the value of `family`):

  | Sub-type | Tight synonyms |
  |---|---|
  | `KALMAN_FILTER` | Kalman filter, KF, EKF, UKF, extended Kalman filter, unscented Kalman filter, linear Kalman filter |
  | `PARTICLE_FILTER` | particle filter, sequential Monte Carlo, SMC, bootstrap filter |
  | `NN_INFERENCE` | neural network, deep learning model, CNN, convolutional neural network, RNN, LSTM, transformer, attention model, deep neural network |
  | `GRAPH_SEARCH` | A*, Dijkstra, graph search, shortest path, breadth-first, depth-first |
  | `SAMPLING_PLANNER` | RRT, RRT*, PRM, sampling-based planner, rapidly-exploring random tree |
  | `MPC` | model predictive control, MPC, receding-horizon control, optimal control |
  | `PID_CONTROL` | PID, proportional-integral-derivative, PI controller, P controller |
  | `HMM` | hidden Markov model, HMM, Markov chain |
  | `BAYESIAN_INFERENCE` | Bayesian inference, Bayesian filter, posterior estimation, MAP estimation |
  | `RL_POLICY` | reinforcement learning policy, RL agent, learned policy, Q-learning, actor-critic, PPO, SAC |
  | `BEHAVIOR_CLONING` | behavior cloning, imitation learning, learning from demonstration |
  | `HEURISTIC_RULESET` | rule-based, finite state machine, FSM, decision tree, expert system |
  | `OPTIMIZATION` | quadratic program, QP, mixed-integer, MILP, gradient descent, convex optimization |
  | `OTHER` | (anything not above — preserved with surface form for ontology evolution) |

### 1.11 Energy & propulsion

> Storage and conversion of energy for vehicle motion. Important for the EV / hybrid / fuel-cell intersection with AV — patents on AV-aware energy management, V2V/V2G charging, range-aware planning, and fault-tolerant power distribution all sit here.

#### `ENERGY_STORAGE_DEVICE`
> Generic parent for any device that stores energy for vehicle propulsion or onboard systems. Use when the patent says "energy storage" / "power source" generically; use a child type when the disclosure names the specific technology.

- **Tight synonyms:** energy storage device, energy storage system, ESS, power source, energy source, electrical storage, power supply (loose; can be 12V auxiliary), onboard energy storage
- **Loose synonyms:** storage, source
- **Extraction rule:** Catch-all parent. Prefer a child type (`BATTERY`, `ULTRACAPACITOR`, `FUEL_CELL`) when the disclosure specifies.
- **Attributes:** `nominal_voltage_v`, `usable_energy_kwh`, `cooling` (passive / liquid / refrigerant)

#### `BATTERY`
- **Parent type:** `ENERGY_STORAGE_DEVICE`
> Electrochemical cell or pack storing electrical energy — the workhorse for EVs, hybrids, and 12V auxiliary systems.

- **Tight synonyms:** battery, battery pack, traction battery, high-voltage battery, HV battery, lithium-ion battery, Li-ion pack, NCA pack, NMC pack, LFP battery, removable battery, swappable battery, 12V auxiliary battery, low-voltage battery
- **Loose synonyms:** cell, pack, module (loose — overlaps with software module)
- **Extraction rule:** Default to `BATTERY` for unspecified electrochemical storage. Capture chemistry, swappability, and voltage tier as attributes.
- **Attributes:** `chemistry` (Li-ion / LFP / NMC / NCA / NiMH / lead_acid / solid_state / other), `voltage_tier` (HV / LV / 48V / unspecified), `swappable` (true / false / unspecified), `capacity_kwh`

#### `ULTRACAPACITOR`
- **Parent type:** `ENERGY_STORAGE_DEVICE`
> Electrostatic / electrochemical capacitor for high-power, low-energy storage — typically paired with a battery for regen-braking burst absorption.

- **Tight synonyms:** ultracapacitor, supercapacitor, EDLC, electric double-layer capacitor, capacitor (loose; usually means electronic component, not vehicle storage)
- **Loose synonyms:** cap (loose), high-power storage
- **Extraction rule:** Specifically for high-cycle, high-power storage paired with primary battery. Distinguish from generic electronic capacitor components.
- **Attributes:** `capacitance_f`, `voltage_v`

#### `FUEL_CELL`
- **Parent type:** `ENERGY_STORAGE_DEVICE`
> Hydrogen / methanol / other fuel-cell stack converting fuel to electricity onboard — primary propulsion energy source for FCEVs, sometimes range-extender for BEVs.

- **Tight synonyms:** fuel cell, fuel cell stack, FC, hydrogen fuel cell, PEM fuel cell, PEMFC, SOFC, methanol fuel cell, range-extender fuel cell
- **Loose synonyms:** stack (loose — could mean software stack)
- **Extraction rule:** Map fuel-cell architectures here. Hydrogen tank may be a separate node if disclosed structurally; for v1 fold tank info into `fuel_storage` attribute.
- **Attributes:** `fuel_type` (hydrogen / methanol / other), `output_kw`, `fuel_storage` (compressed_350bar / compressed_700bar / liquid / metal_hydride)

#### `POWERTRAIN`
> The propulsion system as a unified node — engine, electric machine(s), transmission, inverter, drivetrain components viewed together. Use when the patent treats propulsion structurally or makes claims about hybrid power-split, EV inverter control, or torque-distribution between machines.

- **Tight synonyms:** powertrain, drivetrain, propulsion system, drive system, traction system, electric drive, hybrid powertrain, multi-mode powertrain, EV powertrain, ICE powertrain, fuel-cell powertrain, eAxle, e-axle
- **Loose synonyms:** drive (loose — could be storage drive), motor (loose — see `THROTTLE_ACTUATOR`), engine (loose — only the ICE part)
- **Extraction rule:** Use for the propulsion system as a structural element. Sub-components (engine, electric machine, inverter, transmission) become attributes or are referenced via `PART_OF` if the disclosure breaks them out.
- **Disambiguation:** vs. `THROTTLE_ACTUATOR` — that's the *command interface*; powertrain is the *physical system*. vs. `ENERGY_STORAGE_DEVICE` — battery / fuel cell stores energy; powertrain converts and delivers it.
- **Attributes:** `architecture` (ICE / hybrid_series / hybrid_parallel / hybrid_power_split / EV_single_motor / EV_dual_motor / EV_in-wheel / fuel_cell / unspecified), `electric_machine_count`, `transmission_type` (CVT / DCT / planetary / direct / unspecified)

#### `CHARGING_STATION`
> A discrete charging point for EVs — wired (level-1 / level-2 / DC fast) or wireless (inductive). Important for EV-AV intersection: fleet routing to chargers, AV self-summon for charging, V2G grid integration, robot recharging.

- **Tight synonyms:** charging station, EV charger, EVSE, electric vehicle supply equipment, DC fast charger, level 2 charger, level 3 charger, supercharger, inductive charger, wireless charger, charge point, charging pile, charging interface, V2G charger
- **Loose synonyms:** charger (loose — could mean phone charger), station (loose)
- **Extraction rule:** Use for fixed (or robot-deployed) charging infrastructure that an EV connects to. Capture charge level and connector type when disclosed.
- **Disambiguation:** vs. `BATTERY` — battery is what's being charged; station provides the energy. vs. `OFF_BOARD_SERVER` — sometimes a charger has a backend; extract both linked via `PART_OF`.
- **Attributes:** `charge_level` (L1_AC / L2_AC / DC_fast / wireless / V2G), `connector` (J1772 / CCS / CHAdeMO / NACS / Type2 / wireless_pad / unspecified), `power_kw`

---

## 2. Edge / relation types

Fourteen canonical relation types. Most carry a `content` (see §3) and a `frequency` (see §4); a few are structural and don't.

| Code | Description | Carries content? | Carries frequency? |
|---|---|---|---|
| `SENDS_TO` | Generic data flow from one node to another | yes | yes |
| `BROADCASTS_TO` | Multi-target push of the same payload | yes | yes |
| `FUSES_FROM` | Multi-source convergence into a fusion target | yes | yes |
| `CONTROLS` | Issues actuator-level commands | yes | yes |
| `MEASURES` | Sensor observes the physical environment | yes (modality) | yes |
| `DETECTS` | Sensor / perception module identifies a specific entity in the environment | yes (entity type) | yes |
| `CLASSIFIES` | Assigns a class label / category to a detected entity or scenario | yes (classification scheme) | yes |
| `ALERTS_TO` | Notifies a human (driver / occupant / operator) of a condition | yes (alert type) | yes |
| `OVERRIDES` | Supervisory module preempts the primary control or planning loop | yes (override scope) | yes |
| `READS_FROM` / `WRITES_TO` | Persistent or buffered storage I/O | yes | yes |
| `PUBLISHES` / `SUBSCRIBES_TO` | Pub/sub pattern (named topic) | yes | yes |
| `AUTHENTICATES_WITH` | Security relationship for off-board comms | no | no |
| `PART_OF` | Software composition (module is a sub-component) | no | no |
| `MOUNTED_ON` | Physical composition (sensor on vehicle / platform) | no | no |

For each, brief synonyms and rules:

### `SENDS_TO`
- **Tight synonyms:** sends, transmits, provides, supplies, communicates, forwards, outputs, delivers, passes, hands off
- **Loose synonyms:** connects to, talks to, interfaces with
- **Rule:** The default for any unidirectional flow that doesn't fit a more specific relation. If the patent shows a one-to-many fan-out, prefer `BROADCASTS_TO`.

### `BROADCASTS_TO`
- **Tight synonyms:** broadcasts to, multicasts to, fans out to, publishes to all subscribers, distributes to
- **Rule:** Use when one source pushes the same payload to ≥2 targets. Visually grouped in the canvas.

### `FUSES_FROM`
- **Tight synonyms:** fuses, combines, integrates, merges, aggregates, synthesizes, late fuses, early fuses, weighted-combines
- **Rule:** Use when ≥2 sources converge at one target and the disclosure characterizes the operation as combination/integration. The target node is typically a `SENSOR_FUSION_MODULE`.

### `CONTROLS`
- **Tight synonyms:** controls, commands, drives, actuates, instructs, sends command to, regulates, modulates
- **Rule:** Specifically for module → actuator command paths. Not for one module configuring another (that's `SENDS_TO` with content type `CONFIGURATION`).

### `MEASURES`
- **Tight synonyms:** measures, observes, senses, captures, scans, perceives, monitors
- **Rule:** Sensor → environment relationship at the *raw signal* level. Always emanates from a sensor node. Use for the act of taking a reading; use `DETECTS` for the act of recognizing a specific entity from those readings.

### `DETECTS`
- **Tight synonyms:** detects, identifies, recognizes, classifies, locates, finds, perceives (loose), tracks (when output is a tracked entity)
- **Loose synonyms:** sees, observes (loose — overlaps with MEASURES)
- **Rule:** Source is a `RANGING_SENSOR`, `CAMERA`, `PERCEPTION_MODULE`, or `SENSOR_FUSION_MODULE`. Target is the *entity type* being detected (typically a `ROAD_OBSTACLE` family member, `NEARBY_VEHICLE`, `LANE_MARKING`, `TRAFFIC_LIGHT`, etc.). Distinct from `MEASURES` because the act is *recognition* of a specific class, not just signal acquisition. The content payload is typically `OBJECT_DETECTION_LIST` or `OBJECT_CLASSIFICATION`.

### `CLASSIFIES`
- **Tight synonyms:** classifies, categorizes, labels, assigns class, identifies as, recognizes as, types as, marks as
- **Loose synonyms:** identifies (loose — overlaps with DETECTS), recognizes (loose)
- **Rule:** Source is typically a `PERCEPTION_MODULE`, `SENSOR_FUSION_MODULE`, or `ALGORITHM` node (NN classifier). Target is the *entity being classified* (often a `ROAD_OBSTACLE` or sub-type, `NEARBY_VEHICLE`, scenario, image region). Frequently appears alongside `DETECTS` — detection finds it, classification labels it. Use the more specific edge when the disclosure separates the two stages.

### `ALERTS_TO`
- **Tight synonyms:** alerts, warns, notifies, signals, informs, warns (the driver), provides notification, issues warning, provides alert, presents alert
- **Loose synonyms:** outputs (loose — could be any output), displays (loose), tells (loose)
- **Rule:** Source is typically a `PERCEPTION_MODULE`, `PLANNING_MODULE`, or `CONTROL_MODULE`. Target is a `DRIVER_INTERFACE`, `HUMAN_OPERATOR`, `DRIVER_MOBILE_DEVICE`, or `PASSENGER_MOBILE_DEVICE`. Distinct from generic `SENDS_TO` because the recipient is human, the payload is `ALERT_MESSAGE` or similar, and the implication is human action expected.

### `OVERRIDES`
- **Tight synonyms:** overrides, preempts, supersedes, intervenes, takes over, vetoes, interrupts, inhibits, prohibits, prevents, disables, suppresses, takes priority over
- **Loose synonyms:** controls (loose — overlaps with `CONTROLS`)
- **Rule:** Almost always sourced from `SAFETY_MONITOR`, `CHASSIS_CONTROLLER`, or another supervisory layer; targets the primary `PLANNING_MODULE` or `CONTROL_MODULE`. Captures the structural pattern of an independent safety chain that can preempt the autonomy stack — distinct from `CONTROLS` because the target is itself a controller, not an actuator. Content payload often `OVERRIDE_COMMAND` (a constraint or replacement command).

### `READS_FROM` / `WRITES_TO`
- **Tight synonyms (read):** reads, retrieves, fetches, queries, loads, accesses
- **Tight synonyms (write):** writes, stores, saves, persists, logs, records
- **Rule:** Use for buffered/queued/persistent I/O — distinct from a streaming `SENDS_TO`. Examples: planner reads HD map tiles; perception writes detections to a buffer the planner consumes.

### `PUBLISHES` / `SUBSCRIBES_TO`
- **Tight synonyms (pub):** publishes, posts, advertises
- **Tight synonyms (sub):** subscribes to, listens to, consumes from
- **Rule:** Use when the patent explicitly describes a topic-based pub/sub pattern (ROS, DDS, MQTT). Otherwise prefer `SENDS_TO`. Capture the topic name as the edge `topic` attribute.

### `AUTHENTICATES_WITH`
- **Tight synonyms:** authenticates with, mutually authenticates, performs handshake with, exchanges credentials with, validates identity of
- **Rule:** Used for off-board comms. Often paired with a `SENDS_TO` covering the post-handshake data flow.

### `PART_OF`
- **Tight synonyms:** is a component of, is part of, comprises, includes, contains, is integrated into
- **Rule:** Software / functional composition. Not directional in the data-flow sense — the child `is part of` the parent.

### `MOUNTED_ON`
- **Tight synonyms:** mounted on, attached to, installed on, fixed to, located on, integrated with (when physical)
- **Rule:** Physical composition. Most commonly sensors → vehicle / sensors → bracket / sensors → roof rack.

---

## 3. Content types

What flows over an edge. Twenty canonical content types covering the core AV data classes.

| Code | Description | Typical sources | Typical targets |
|---|---|---|---|
| `POINT_CLOUD` | 3D points from a ranging sensor | `RANGING_SENSOR` (lidar / radar) | `PERCEPTION_MODULE`, `SENSOR_FUSION_MODULE` |
| `CAMERA_FRAME` | Raw or compressed image | `CAMERA` | `PERCEPTION_MODULE` |
| `OBJECT_DETECTION_LIST` | Per-frame detections (boxes + class) | `PERCEPTION_MODULE` | `OBJECT_TRACKER`-role module, `SENSOR_FUSION_MODULE` |
| `OBJECT_TRACK_LIST` | Tracked entities with velocity/history | `PERCEPTION_MODULE`, `SENSOR_FUSION_MODULE` | `PREDICTION_MODULE`, `PLANNING_MODULE` |
| `PREDICTED_TRAJECTORY` | Future motion of other agents | `PREDICTION_MODULE` | `PLANNING_MODULE` |
| `EGO_TRAJECTORY` | Planned ego path | `PLANNING_MODULE` | `CONTROL_MODULE` |
| `CONTROL_COMMAND` | Steering angle, accel, brake setpoints | `CONTROL_MODULE` | actuator nodes |
| `POSITION_FIX` | Lat/lon, heading, velocity | `POSITIONING_SENSOR`, `PERCEPTION_MODULE` (loc role) | `PLANNING_MODULE`, `SERVER` |
| `MAP_TILE` | HD map data segment | `SERVER` (map role), `HD_MAP_DATA` | `PERCEPTION_MODULE`, `PLANNING_MODULE` |
| `V2X_MESSAGE` | BSM, SPaT, MAP, PSM | `V2X_TRANSCEIVER` | `PERCEPTION_MODULE`, `PLANNING_MODULE` |
| `VEHICLE_STATE` | Speed, gear, occupancy, dynamics | chassis sensors, `INERTIAL_SENSOR` | most compute nodes |
| `CALIBRATION_DATA` | Sensor extrinsics / intrinsics | `SERVER`, on-vehicle storage | `PERCEPTION_MODULE`, `SENSOR_FUSION_MODULE` |
| `OBJECT_CLASSIFICATION` | Class label + confidence for a detected entity (pedestrian / vehicle / sign / etc.) | `PERCEPTION_MODULE` | `PLANNING_MODULE`, `PREDICTION_MODULE` |
| `CONFIDENCE_SCORE` | Probability / confidence / quality value attached to any other content | most modules | most modules |
| `ROAD_GEOMETRY` | Road shape, lane shape, curvature, slope | `PERCEPTION_MODULE`, `HD_MAP_DATA` | `PLANNING_MODULE`, `CONTROL_MODULE` |
| `WEATHER_DATA` | Precipitation, visibility, surface condition, temperature | `SERVER`, on-vehicle sensors | `PLANNING_MODULE`, `PERCEPTION_MODULE` |
| `DRIVER_STATE_DATA` | Gaze direction, drowsiness level, biometric signals, attention score | `DRIVER_STATE_SENSOR` | `PLANNING_MODULE`, `DRIVER_INTERFACE` |
| `SERVICE_REQUEST` | Ride request, charging request, dispatch request, summon command | `MOBILE_DEVICE` family, `SERVER` | `SERVER`, `PLANNING_MODULE` |
| `ALERT_MESSAGE` | Driver / operator notification payload (text, audio, haptic, visual cue) | `PERCEPTION_MODULE`, `PLANNING_MODULE`, `CONTROL_MODULE` | `DRIVER_INTERFACE`, `HUMAN_OPERATOR`, mobile device family |

Each content type has its own synonym set. Examples for two:

#### `OBJECT_TRACK_LIST`
- **Tight synonyms:** tracked objects, tracked entities, object tracks, track list, perceived agents, fused tracks, world model
- **Loose synonyms:** detected objects (loose because raw detections are usually `OBJECT_DETECTION_LIST`), agents, dynamic obstacles
- **Attributes:** `per_object_fields` (e.g., `[position, velocity, class, track_id, covariance]`), `coordinate_frame` (ego / world / map)

#### `EGO_TRAJECTORY`
- **Tight synonyms:** trajectory, path, planned path, planned trajectory, reference trajectory, motion plan, drive plan, intended path
- **Loose synonyms:** route (loose — route is mission-level), course
- **Attributes:** `horizon_s`, `discretization` (waypoints / spline / polynomial), `degrees_of_freedom`

The full content-type synonym tables live in [`docs/ontology-content-synonyms.md`](ontology-content-synonyms.md) once we draft the remainder. For now, the table above is the canonical type list; per-type synonym detail lands as we ingest the seed patents and see what wording they actually use.

---

## 4. Frequency vocabulary

Five categorical buckets. Each can additionally carry a numeric `value_hz` or `value_ms` when the patent specifies one.

| Code | Description | Tight synonyms |
|---|---|---|
| `REAL_TIME` | Implies bounded latency, often coupled with `PERIODIC` | real-time, hard real-time, deterministic latency, low-latency, sub-millisecond, deterministic |
| `PERIODIC` | Fixed cycle | periodic, cyclic, every N ms, at N Hz, regular interval, scheduled |
| `EVENT_DRIVEN` | Fires on a triggering condition | event-driven, on event, triggered by, when condition, on threshold, asynchronous-trigger |
| `ON_DEMAND` | Request/reply | on demand, on request, polled, query-response, fetch when needed |
| `ASYNCHRONOUS` | Fire-and-forget, no scheduling guarantee | asynchronous, best-effort, no guarantees, eventual, opportunistic |

**Attributes:** `value_hz` (numeric), `value_ms_period` (numeric, alternative form), `latency_bound_ms` (when `REAL_TIME`).

**Range queries:** the query builder lets you specify `≥ N Hz`, `≤ N ms`, or a range. Stored as `min_hz` / `max_hz` on the query edge.

---

## 5. Threshold / condition vocabulary

Conditions and thresholds appear on both nodes (behavioral guards: "engages autonomy if speed > 30 mph") and edges (gating: "sends alert when distance < 5 m"). Five forms cover the common cases.

| Code | Description | Example |
|---|---|---|
| `NUMERIC_THRESHOLD` | Single value comparison | `speed > 30 mph` |
| `RANGE_THRESHOLD` | Within / outside a range | `5 m < distance < 50 m` |
| `TIME_THRESHOLD` | Duration-based | `condition persists > 5 s` |
| `ENUM_CONDITION` | Categorical state | `mode == AUTONOMOUS` |
| `COMPOSITE` | Boolean combination | `(speed > 30) AND (mode == HIGHWAY)` |

**Stored as:** an `expression` field with a tiny structured AST so the UI can render it readably and the matcher can compare semantically (not just string-match).

**Synonym filters apply to the variable names too** — "speed" matches "velocity," "vehicle_speed," "ego_velocity," etc.

---

## JSON schema (per-patent extracted graph)

The end product of ingestion for one patent looks like:

```json
{
  "patent_id": "US9254846B2",
  "ontology_version": "v1",
  "extracted_at": "2026-05-04T12:34:56Z",
  "extracted_by": "claude-sonnet-4-6",
  "nodes": [
    {
      "id": "n1",
      "canonical_type": "PERCEPTION_MODULE",
      "surface_form": "object detection neural network",
      "attributes": {
        "output_type": "objects",
        "architecture": "NN"
      },
      "cite": {"paragraph": 12, "char_start": 410, "char_end": 478}
    }
  ],
  "edges": [
    {
      "id": "e1",
      "from": "n1",
      "to": "n2",
      "canonical_relation": "SENDS_TO",
      "content": {
        "canonical_type": "OBJECT_TRACK_LIST",
        "surface_form": "tracked agents with velocities",
        "attributes": {
          "per_object_fields": ["position", "velocity", "class"]
        }
      },
      "frequency": {
        "category": "PERIODIC",
        "value_hz": 10
      },
      "condition": {
        "form": "NUMERIC_THRESHOLD",
        "expression": "obj_range < 50",
        "units": "m"
      },
      "cite": {"paragraph": 38, "char_start": 502, "char_end": 615}
    }
  ],
  "unmapped": [
    {
      "surface_form": "GMLAN coordinator",
      "guessed_type": "TELEMATICS_CONTROLLER",
      "confidence": "low",
      "cite": {"paragraph": 41, "char_start": 1023, "char_end": 1048}
    }
  ]
}
```

The `unmapped` array captures things Claude couldn't confidently bucket — fed into the triage queue for ontology evolution.

---

## What I want you to redline

Tell me, section by section:

1. **Node types** — anything I'm missing in passenger AV? Anything I've split that should be one type? Anything I've merged that you want separate? My main concern: did I get the perception/fusion/prediction split right, or do you actually treat them as one stack?
2. **Edge types** — does `MEASURES` (sensor→environment) earn its keep, or is it noise? Did I miss any examiner-relevant relation?
3. **Content types** — twelve feels right but I'm guessing. Anything from your daily citations that doesn't fit?
4. **Synonyms** — pick any one canonical type you know cold and tell me which synonyms I missed or mis-classified (tight vs loose).
5. **Disambiguation** — call out the disambiguation notes that don't match how you actually distinguish in practice.

Once we agree on the shape, I write the machine-readable version (Python module the extractor consumes) and we run it against the first seed patent.
