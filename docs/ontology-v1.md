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
| **Description** | One-paragraph definition; the source of truth when synonyms are ambiguous. |
| **Synonyms (tight)** | Phrases that always map to this code. Used for high-confidence extraction and the default-on synonym filters in the query builder. |
| **Synonyms (loose)** | Phrases that often map to this code but need disambiguation. Surfaced as "tentative" in match results so the examiner can confirm. |
| **Extraction rule** | Guidance Claude follows during ingestion. Includes "must include" structural cues and "do not confuse with" notes. |
| **Disambiguation** | Which other canonical types this is most often confused with, and how to tell them apart. |

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

Twenty-six canonical node types, grouped into eight categories. Pick the granularity carefully — too few and we collapse meaningful distinctions; too many and every patent looks unique.

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

### 1.3 Compute hardware

#### `AV_COMPUTE_PLATFORM`
> The physical compute hardware running perception / planning / control software.

- **Tight synonyms:** AV computer, autonomous driving computer, central compute platform, domain controller, ADAS ECU, AI compute platform, in-vehicle compute, FSD computer, NVIDIA DRIVE platform, Tesla FSD chip, Mobileye EyeQ
- **Loose synonyms:** compute unit, processing platform, on-board computer, ECU, electronic control unit
- **Extraction rule:** Hardware, not software. Capture only when the patent specifically describes the compute platform as a structural element (chip, board, redundant pair). Generic mentions of "a processor" do not warrant a node — only when the disclosure cares about the hardware as such (redundancy, AI accelerators, automotive-grade certification, etc.).
- **Disambiguation:** vs. functional compute modules — those are software roles; this is the box they run on. vs. `TELEMATICS_CONTROLLER` — telematics is a comms gateway, not the AV brain.
- **Attributes:** `redundancy` (single / dual / triple), `accelerator_type` (CPU / GPU / NPU / FPGA / ASIC), `certification` (ASIL-D / ASIL-B / etc.)

### 1.4 Actuators

#### `STEERING_ACTUATOR`
> Mechanism that physically turns the wheels in response to a steering command.

- **Tight synonyms:** steering actuator, electric power steering, EPS, steer-by-wire, steering motor, rack-mounted EPS, column-mounted EPS, steering rack actuator
- **Loose synonyms:** steering system, steering subsystem
- **Extraction rule:** The physical actuator only — the steering controller is `CONTROL_MODULE`.
- **Attributes:** `architecture` (column EPS / rack EPS / steer-by-wire), `redundancy`

#### `THROTTLE_ACTUATOR`
> Commands engine torque or drive-motor torque for forward propulsion.

- **Tight synonyms:** throttle actuator, throttle-by-wire, accelerator actuator, electronic throttle, drive-by-wire throttle, motor torque controller (when EV), powertrain command interface
- **Loose synonyms:** acceleration actuator, propulsion actuator
- **Extraction rule:** Commands forward motion. For EVs, this often is the inverter/motor torque request, which gets extracted as `THROTTLE_ACTUATOR` for ontology consistency even though there's no literal throttle.
- **Attributes:** `powertrain_type` (ICE / hybrid / EV / fuel-cell)

#### `BRAKE_ACTUATOR`
> Applies braking force, including regenerative braking.

- **Tight synonyms:** brake actuator, brake-by-wire, electronic brake, EBC, electric parking brake, regenerative braking system, brake hydraulic actuator, brake booster
- **Loose synonyms:** braking system, deceleration actuator
- **Attributes:** `architecture` (hydraulic / electric / regenerative / blended)

### 1.5 Off-board comms

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

### 1.8 Data sources

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
> Six canonical types defined here. **Likely additions** I expect you'll want — flag yes/no on each: `PEDESTRIAN`, `CYCLIST`, `TRAFFIC_SIGN`, `ROAD_OBSTACLE`, `LANE_MARKING`. Adding any of those follows the same pattern as the six below.

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
> A user-carried smartphone, tablet, or wearable that interacts with the AV stack — for ride-hailing dispatch, remote summon, key-as-a-phone, infotainment pairing, ride-sharing UX, or driver/rider authentication.

- **Tight synonyms:** mobile device, smartphone, phone, smart phone, mobile phone, tablet, smartwatch, wearable, user device, rider device, passenger device, fleet rider app device
- **Loose synonyms:** device (loose — could mean any onboard device), terminal
- **Extraction rule:** Extract when the disclosure specifically references a user-carried device interacting with the AV stack (typically over cellular or BLE). The *app* on the device is captured as an attribute, not a separate node.
- **Disambiguation:** vs. `SERVER` — phones aren't servers even when they expose APIs. vs. `DRIVER_INTERFACE` — that's the in-cabin UI; mobile devices are user-carried.
- **Attributes:** `role` (rider_app / fleet_app / digital_key / remote_summon / passenger_infotainment), `connection_to_vehicle` (cellular / BLE / NFC / wifi)

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

---

## 2. Edge / relation types

Ten canonical relation types. Most carry a `content` (see §3) and a `frequency` (see §4); a few are structural and don't.

| Code | Description | Carries content? | Carries frequency? |
|---|---|---|---|
| `SENDS_TO` | Generic data flow from one node to another | yes | yes |
| `BROADCASTS_TO` | Multi-target push of the same payload | yes | yes |
| `FUSES_FROM` | Multi-source convergence into a fusion target | yes | yes |
| `CONTROLS` | Issues actuator-level commands | yes | yes |
| `MEASURES` | Sensor observes the physical environment | yes (modality) | yes |
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
- **Tight synonyms:** measures, observes, senses, captures, detects, scans, perceives
- **Rule:** Sensor → environment relationship. Always emanates from a sensor node. Many patents leave this implicit ("the lidar scans the surroundings"); we still extract it because it lets the query graph express "I want a vehicle that measures with X modality."

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

What flows over an edge. Twelve canonical content types covering the core AV data classes.

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
| `CALIBRATION_DATA` | Sensor extrinsics / intrinsics | `OFF_BOARD_SERVER`, on-vehicle storage | `PERCEPTION_MODULE`, `SENSOR_FUSION_MODULE` |

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
