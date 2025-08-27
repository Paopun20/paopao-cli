import code

class Terminal(code.InteractiveConsole):
    def __init__(self, locals=None):
        super().__init__(locals=locals or {})
        self.prompt = ">>> "
        self._events = {
            "on_input": [],
            "on_eval": [],
            "on_exit": [],
            "on_interrupt": [],
        }

    # Event registration
    def on(self, event_name, callback):
        """Register a callback for an event."""
        if event_name not in self._events:
            raise ValueError(f"Unknown event: {event_name}")
        if not callable(callback):
            raise ValueError("Callback must be callable")
        self._events[event_name].append(callback)

    # Trigger event
    def _trigger(self, event_name, *args, **kwargs):
        for callback in self._events.get(event_name, []):
            callback(*args, **kwargs)

    # Terminal main loop
    def run(self):
        try:
            while True:
                try:
                    line = input(self.prompt)
                    self._trigger("on_input", line)
                except EOFError:
                    print("\nExiting terminal.")
                    break

                more = self.push(line)
                self._trigger("on_eval", line, more)

                self.prompt = "... " if more else ">>> "

        except KeyboardInterrupt:
            self._trigger("on_interrupt")
            print("\nKeyboardInterrupt — exiting terminal.")
            self._trigger("on_exit")

    # Helper methods
    def set(self, name, value):
        self.locals[name] = value

    def get(self, name):
        return self.locals.get(name)
