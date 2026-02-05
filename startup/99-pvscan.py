import json
from enum import Enum
from typing import Any, Dict, Optional

from ophyd_async.core import Device, Signal


def enum_to_dict(enum_class):
    """Convert enum to dictionary format"""
    members = {}

    for member in enum_class:
        value_type = type(member.value).__name__
        members[member.name] = value_type

    return {
        "enum_name": enum_class.__name__,
        "members": members,
    }


def walk_signals(
    device: Device, path_prefix: Optional[str] = ""
) -> Dict[str, Signal[Any]]:
    """Retrieve all SignalRWs from a device.

    Stores retrieved signals with their dotted attribute paths in a dictionary. Used as
    part of saving and loading a device.

    Parameters
    ----------
    device : Device
        Ophyd device to retrieve read-write signals from.

    path_prefix : str
        For internal use, leave blank when calling the method.

    Returns
    -------
    SignalRWs : dict
        A dictionary matching the string attribute path of a SignalRW with the
        signal itself.

        See Also
    --------
    :func:`ophyd_async.core.get_signal_values`
    :func:`ophyd_async.core.save_to_yaml`

    """

    if not path_prefix:
        path_prefix = ""

    signals: Dict[str, Signal[Any]] = {}
    for attr_name, attr in device.children():
        dot_path = f"{path_prefix}{attr_name}"
        # if type(attr) is Signal:
        if isinstance(attr, Signal):
            signals[dot_path] = attr
        attr_signals = walk_signals(attr, path_prefix=dot_path + ".")
        signals.update(attr_signals)
    return signals


def get_signal_pv_types():
    """
    This is a dictionary that maps the Devices and Signals in the profile to their pvs and types.
    """

    devices = [g for g in globals().values() if isinstance(g, Device)]
    pvs = {
        device.name: {
            signal.name: {
                "pv": signal.source,
                "type": (
                    enum_to_dict(signal._connector.backend.datatype)
                    if issubclass(signal._connector.backend.datatype, Enum)
                    else signal._connector.backend.datatype.__name__
                ),
            }
            for signal in walk_signals(device).values()
            if isinstance(signal, Signal)
        }
        for device in devices
    }
    return pvs


def get_pv_types():
    """
    This is a dictionary that maps all of the PVs in the profile to their types.
    """

    devices = [g for g in globals().values() if isinstance(g, Device)]
    pv_types = {
        signal.source: (
            enum_to_dict(signal._connector.backend.datatype)
            if issubclass(signal._connector.backend.datatype, Enum)
            else signal._connector.backend.datatype.__name__
        )
        for device in devices
        for signal in walk_signals(device).values()
    }
    with open("pv_types.json", "w") as f:
        json.dump(pv_types, f)
    return pv_types
