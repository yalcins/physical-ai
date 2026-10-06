"""Ortak robot arayuzu: ayni kontrol kodu simulasyonda ve gercek robotta calisir.

SimRobot yalnizca istenince yuklenir; boylece Pi 4'te ve ana bilgisayarda pai_gym
kurulu olmadan da UdpRobot / Policy kullanilabilir.
"""
from .base import Robot
from .policy import ACTIONS, Policy
from .udp import UdpRobot

__all__ = ['Robot', 'Policy', 'ACTIONS', 'SimRobot', 'UdpRobot']


def __getattr__(name):
    if name == 'SimRobot':
        from .sim import SimRobot
        return SimRobot
    raise AttributeError(name)
