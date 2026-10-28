"""设备型号注册表；新增型号只需注册驱动类。"""

from src.devices.drivers.Link_hand import LinkHand
from src.devices.drivers.camera_d435 import CameraD435
from src.devices.drivers.gello_arm import GelloArm
from src.devices.drivers.nrc_arm import NrcArm


MASTER_DRIVERS = {"Gello": GelloArm}
SLAVE_DRIVERS = {"NRC": NrcArm}
HAND_DRIVERS = {"LinkerO6": LinkHand}
CAMERA_DRIVERS = {"D435": CameraD435}


def _create(registry, model, **options):
    try:
        driver = registry[model]
    except KeyError as error:
        raise ValueError(f"未注册的设备型号：{model}") from error
    options.setdefault("name", model)
    return driver(**options)


def create_master_arm(model, **options):
    return _create(MASTER_DRIVERS, model, **options)


def create_slave_arm(model, **options):
    return _create(SLAVE_DRIVERS, model, **options)


def create_hand(model, **options):
    if model == "LinkHand":
        model = "LinkerO6"
    return _create(HAND_DRIVERS, model, **options)


def create_camera(model, **options):
    return _create(CAMERA_DRIVERS, model, **options)
