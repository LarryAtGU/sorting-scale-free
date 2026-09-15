# SCN Visualization and Replay Architecture

## Purpose

The new software will retain the interactive capabilities of the earlier Java
SCN program while keeping visualization completely outside production
statistical runs.

The earlier implementation used a sorting-process monitor to add comparison
links one at a time and a continuously running force layout to improve node
positions. It also distinguished the observed comparison graph from links that
became unnecessary once transitive order information was available.

## Architectural separation

The system has three independent layers:

1. **Experiment core:** executes an algorithm and emits comparison events.
2. **Trace storage/replay:** stores an optional event stream and can replay it at
   any speed without rerunning the sorting algorithm.
3. **Visualizer:** subscribes to live events or a saved replay and renders the
   changing graph.

The experiment core must not import or call visualization code. Production
statistics run in headless mode with rendering disabled. Detailed event traces
are optional so batch experiments do not incur unnecessary storage costs.

## Graph views

The visualizer will offer separate, clearly labelled views of:

- the directed simple SCN containing distinct comparisons actually observed;
- the current transitive reduction, representing a minimal set of displayed
  relations with the same reachability;
- implied or superseded links, optionally shown with reduced opacity;
- the final graph and its in-degree, out-degree, and total-degree encodings.

Removing an edge from the transitive-reduction display never removes it from the
observed comparison trace or changes the algorithm's comparison count.

## Playback features

- add one comparison at a time;
- play, pause, resume, and reset;
- move forward or backward using a comparison-index slider;
- control playback speed;
- show the active comparison and its result;
- distinguish new, repeated, and already-implied comparisons;
- inspect a node's permanent identity, key, degrees, and comparison history;
- display current and final comparison counts.

## Layout features

- initial-input circular layout;
- final-order circular layout;
- deterministic random initial layout;
- continuously improving force-directed layout;
- stable positions between adjacent animation frames;
- node repulsion, edge attraction, boundary forces, damping, and a movement cap;
- node size based on a selectable degree measure;
- optional arrows and highlighting of high-degree nodes.

Layout randomness must use a separate visualization seed. It must never consume
the input-generation stream or affect sorting behaviour.

## Implementation direction

The preferred implementation is a local browser-based viewer fed by exported
JSON trace data. This supports smooth animation and inspection while allowing
the Python experiment engine to remain headless. The first implementation may
use a simple deterministic force layout; more advanced layouts can be added
behind the same interface.

## Verification

- replaying a trace must reconstruct the same directed SCN as the batch engine;
- changing playback speed or layout must not change graph structure;
- seeking backward and forward must be deterministic;
- batch mode must perform no rendering or layout calculations;
- the observed graph and transitive-reduction display must never be conflated.

