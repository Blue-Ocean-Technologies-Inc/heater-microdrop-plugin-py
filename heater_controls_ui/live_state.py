"""Live (non-persisted) heater UI state shared inside the plugin.

Carries the worker-thread -> GUI-thread hand-offs the firmware-upload dialog
needs: the backend's upload signals, the connected board's whoami id, and its
serial port. The message handler writes these on the dramatiq worker thread;
the dialog controller observes them with dispatch="ui".
"""
from traits.api import Event, HasTraits, Str


class HeaterLiveState(HasTraits):
    """Heater UI state that is intentionally not persisted anywhere."""

    #: (topic, message) tuples of the backend's firmware-upload signals
    #: (started / log line / finished), ferried from the worker-thread
    #: listener to the GUI thread: the firmware-upload dialog controller
    #: observes this with dispatch="ui". An Event fires on every write — a
    #: plain trait's equality check would swallow identical log lines.
    firmware_upload_message = Event()

    #: The connected board's whoami device_id (BOARD_ID signal). The
    #: firmware-upload dialog shows it read-only and flashes exactly that
    #: board; empty until a board identifies (cleared on disconnect).
    board_device_id = Str()

    #: The connected board's serial port (CONNECTED signal). The
    #: firmware-upload dialog keeps its port combo in sync with this
    #: auto-detected port; empty while disconnected.
    board_port = Str()


#: Module-level singleton shared inside the heater plugin.
heater_live_state = HeaterLiveState()
