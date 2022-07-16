import textual.app
from typing import Any


class App(textual.app.App):
    def __init__(self, *args, servo_ctl, servos, servo_configfile, relay, **kwargs):
        self.servo_ctl = servo_ctl
        self.servos = servos
        self.servo_configfile = servo_configfile
        self.relay = relay
        super().__init__(*args, **kwargs)

    def unbind(self, key: str) -> None:
        """Create unbind method

        Parameters
        ----------
        key : str
            key to unbind
        """
        # Raise exception if key doesn't exist
        self.bindings.get_key(key)
        del self.bindings.keys[key]

    async def dispatch_action(
        self, namespace: object, action_name: str, params: Any
    ) -> None:
        """Override dispach action to raise excption if missing action method"""
        # Raise exception of the method can't be found
        method_name = f"action_{action_name}"
        if getattr(namespace, method_name, None) is None:
            raise textual.app.ActionError(
                "Action method: '{}' not found".format(method_name)
            )
        return await super().dispatch_action(namespace, action_name, params)
