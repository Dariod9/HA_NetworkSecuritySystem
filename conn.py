# @Author: Dário Matos
# @Date:   2022-07-21 20:30:32
# @Email:  dario.matos@ua.pt
# @Copyright: Insituto de Telecomunicações - Aveiro, Aveiro, Portugal
# @Last Modified by:   Dário Matos
# @Last Modified time: 2022-10-22 15:55:30

from time import sleep
import paramiko
import json

from firewall import Firewall
from loadbalancer import LoadBalancer

# import firewall
# import loadbalancer


def get():
    return client.get_equipment()


class HASystem:

    def __init__(self):
        self.load_balancers = []
        self.firewalls = []
        self.zones = dict()
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # self.run()

    def run(self):

        # Client init
        self.load_balancers, self.firewalls = self.load_equipment("config.txt")
        self.zones = self.load_zones()
        # self.verify_all(self.load_balancers, self.firewalls)

        # Init Config for all machines
        for lb in self.load_balancers:
            print("Configuring "+lb.name)
            # Check connectivity
            if lb.check_connection():
                lb.config(self.ssh, self.zones, self.firewalls)
                lb.init_nftables(self.ssh, len(self.firewalls))
            else:
                print(f"Cannot startup {lb.name}")

        for fw in self.firewalls:
            # Check connectivity
            if fw.check_connection():
                fw.config(self.ssh, self.zones, self.load_balancers)
                fw.init_nftables(self.ssh)
            else:
                print(f"Cannot startup {fw.name}")

        # Monitoring script
        while True:
            sleep(2)
            self.verify_all(self.load_balancers, self.firewalls)

    def verify_all(self, load_balancers=None, firewalls=None):

        for lb in load_balancers:

            # Se estava up antes
            if lb.up:
                # e depois down, diz que foi abaixo e reconfigura as FW
                if not lb.check_connection():
                    print(f"{lb.name} WENT DOWN")

                    self.change_in_lbs(
                        firewalls, lb, False, load_balancers)

            else:
                # Se continua down, informa
                if not lb.check_connection():
                    print(f"{lb.name} is down")

                # Se volta up, informa e reconfigura as FW
                else:
                    print(f"{lb.name} is now up!")

                    # FW Config
                    self.change_in_lbs(
                        firewalls, lb, True, load_balancers)

                    # Startup config
                    lb.config(self.ssh, self.zones, firewalls)

        for fw in firewalls:

            # Se estava up
            if fw.up:

                # e depois down, diz que foi abaixo e reconfigura as FW
                if not fw.check_connection():
                    print(f"{fw.name} WENT DOWN")
                    self.change_in_firewalls(load_balancers, firewalls)
                # else:
                    # fw.backup_rules(self.ssh)
            # Se estava down
            else:
                # Se continua, informa
                if not fw.check_connection():
                    print(f"{fw.name} is down")

                # Se volta up, informa e reconfigura os LBs
                else:
                    print(f"{fw.name} is now up!")

                    # Configure LBs:
                    self.change_in_firewalls(load_balancers, firewalls)

                    fw.apply_rules(self.ssh)
                    # Startup config
                    fw.config(self.ssh, self.zones, self.load_balancers)

    def change_in_firewalls(self, lbs, firewalls):
        for lb in lbs:
            try:
                print(f"\nRestarting {lb.name} networks, please wait!\n")

                # Delete current routes and reconfigure device
                lb.flush_routes(self.ssh)
                sleep(2)
                lb.config(self.ssh, self.zones, firewalls)

                # Wait for connectivity to configure next device
                while (not lb.check_connection()):
                    sleep(1)

            except Exception as e:
                print(f"Can't configure {lb.name} because "+str(e))
                # lb.delayed_configs[len(
                #     lb.delayed_configs)+1] = ("config_nftables", old_number,
                #                               new_number)
                # print(lb.delayed_configs)

    def change_in_lbs(self, fws, lb, add, load_balancers):
        for fw in fws:
            try:
                print(f"\nRestarting {fw.name} networks, please wait!\n")
                fw.flush_routes(self.ssh)
                sleep(2)
                fw.config(self.ssh, self.zones, load_balancers)
                while (not fw.check_connection()):
                    sleep(1)

            except Exception as e:
                print(f"Can't configure {fw.name} because "+str(e))
                fw.delayed_configs[
                    len(fw.delayed_configs)+1] = ("config_routes", lb)
                print("Has delayed: " + str(fw.delayed_configs))

    def get_equipment(self):

        if self.load_balancers != [] and self.firewalls != []:
            return self.load_balancers+(self.firewalls)
        else:
            return []

    def get_up_equipments(self):
        active_lbs = [lb for lb in self.load_balancers if lb.up]
        active_fws = [fw for fw in self.firewalls if fw.up]

        if active_fws != [] and active_lbs != []:
            return active_lbs+(active_fws)
        else:
            return []

    def check_one_connections(self, device_name):

        device = [dev for dev in self.get_equipment(
        ) if dev.up and dev.name.lower() == device_name.lower()]

        if not device:
            return f"{device_name} is Down"
        else:
            if "LB" in device[0].name:
                return device[0].check_all_connections(
                    self.ssh, self.firewalls)
            else:
                return device[0].check_all_connections(self.ssh,
                                                       self.load_balancers)

    def check_all_connections(self):
        result = dict()

        for device in self.get_up_equipments():
            if "LB" in device.name:
                result[device.name] = device.check_all_connections(
                    self.ssh, self.firewalls)
            else:
                result[device.name] = device.check_all_connections(
                    self.ssh, self.load_balancers)

        return result

    def get_equipment_stats(self, device_name):

        device = [dev for dev in self.get_equipment(
        ) if dev.up and dev.name.lower() == device_name.lower()]

        if not device:
            return f"{device_name} is Down"
        else:
            return device[0].get_cpu_busy(self.ssh)

    def get_all_equipment_stats(self):
        slots = self.get_equipment()
        result = dict()
        for slot in slots:
            if not slot.up:
                result[slot.name] = "Device is Down"
            else:
                result[slot.name] = slot.get_cpu_busy(self.ssh)

        return result

    def configure_device(self, device_name):
        device = [dev for dev in self.get_equipment(
        ) if dev.up and dev.name.lower() == device_name.lower()]

        if not device:
            return f"{device_name} is Down"
        else:
            if "lb" in device_name.lower():
                return device[0].config(self.ssh, self.zones, self.firewalls)
            else:
                return device[0].config(self.ssh, self.zones,
                                        self.load_balancers)

    def block_ip(self, zone, ip, port):

        devices = [fw for fw in self.firewalls if fw.up]

        if not devices:
            return "No active Firewalls"
        else:
            for dev in devices:
                if zone:
                    if zone in self.zones.keys():
                        dev.block(self.ssh, ip, self.zones[zone], port)
                    else:
                        return "Not existing zone"
                else:
                    dev.block(self.ssh, ip, None, port)
                    # dev.backup_rules(self.ssh)

            return "Rule applied"

    def allow_ip(self, zone, ip, port):
        devices = [fw for fw in self.firewalls if fw.up]

        if not devices:
            return "No active Firewalls"
        else:
            for dev in devices:
                if zone:
                    if zone in self.zones.keys():
                        dev.allow(self.ssh, ip, self.zones[zone], port)
                    else:
                        return "Not existing zone"
                else:
                    dev.allow(self.ssh, ip, None, port)
                    # dev.backup_rules(self.ssh)
            return "Rule applied"

    def load_equipment(self, config_file):

        with open(config_file, 'r') as file:
            f = file.readlines()
            load_balancers = []
            firewalls = []

        for jsonObj in f:
            machine = json.loads(jsonObj)
            if machine["type"] == "LB":
                loadbalancer = LoadBalancer()
                loadbalancer.reader(machine)
                load_balancers.append(loadbalancer)
            elif machine["type"] == "FW":
                firewall = Firewall()
                firewall.reader(machine)
                firewalls.append(firewall)

        return load_balancers, firewalls

    def load_zones(self):
        with open('zones.txt') as json_file:
            return json.load(json_file)


if __name__ == "__main__":
    global client
    client = HASystem()
    client.run()
