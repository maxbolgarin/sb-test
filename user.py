import requests
import config
from collections import namedtuple


class User:
    NOT_LINKED = "NOT_LINKED"
    LINKED_DEVICE = "LINKED_DEVICE"
    LINKED_IP = "LINKED_IP"
    LINKED_FINGER_ASN = "LINKED_TECH_ASN"
    LINKED_TECH_ASN = "LINKED_TECH_ASN"
    Tech = namedtuple("Tech", ["gpu", "screen", "os"])

    def __init__(self, uid):
        self.uid = uid
        self.devices = set()
        self.fingerprints = set()
        self.ips = set()
        self.asns = set()
        self.technical = set()
    
    def parse_event(self, event):
        self.devices.add(event["device_id"].strip())

        if event["device_fingerprint"] != "No data":
            self.fingerprints.add(event["device_fingerprint"].strip())

        self.technical.add(User.Tech(event["gpu_renderers"].strip(),
                                     event["screen"].strip(), event["os"].strip()))

        ips = set(event["ips"].strip().split(","))
        self.ips |= ips

        for ip in ips:
           self.asns.add(requests.get(f"https://ipinfo.io/{ip}/org", 
                                       params={"token": config.ipinfo_token}).text.split()[0])

    def is_linked(self, other):
        # 1. Один device_id
        # 2. Если нет, то один ip
        # 3. Если нет, то один fingerprint и asn
        # 4. Если нет fingerprint, то сравниваются ["gpu", "screen", "os"]

        if isinstance(other, User):
            devices_inter = self.devices & other.devices
            if devices_inter:
                return User.LINKED_DEVICE, devices_inter

            ips_inter = self.ips & other.ips
            if ips_inter:
                return User.LINKED_IP, ips_inter

            finger_inter = self.fingerprints & other.fingerprints
            asns_inter = self.asns & other.asns
            if not finger_inter:
                tech_inter = self.technical & other.technical
                if tech_inter and asns_inter:
                    return User.LINKED_TECH_ASN, (tech_inter, asns_inter)

            elif finger_inter and asns_inter:
                return User.LINKED_FINGER_ASN, (finger_inter, asns_inter)

    
        return User.NOT_LINKED, None

    def check_device(self, device):
        return device in self.devices

    def __repr__(self):
        return f"User {self.uid}\nDevices: {self.devices}\n" + \
                f"Ips: {self.ips}\nFingerprints: {self.fingerprints}\nTech: {self.technical}"

    def __str__(self):
        return self.__repr__()
