# @Author: Dário Matos
# @Date:   2022-07-22 12:38:26
# @Email:  dario.matos@ua.pt
# @Copyright: Insituto de Telecomunicações - Aveiro, Aveiro, Portugal
# @Last Modified by:   Dário Matos
# @Last Modified time: 2022-10-22 18:34:15

import os
import re


class LoadBalancer:

    def __init__(self, name=None, ip=None, username=None, password=None):
        self.name = name
        self.ip = ip
        self.username = username
        self.password = password
        self.interfaces = dict()
        self.internal_networks = []
        self.zone = None
        self.delayed_configs = dict()
        self.started = False
        self.up = False

    def check_connection(self):

        # Test ping to admin
        response = os.system("ping -c 1 " + self.ip + " >> t.txt")

        if response == 0:
            self.up = True
        else:
            self.up = False

        return self.up

    def config(self, ssh, zones, firewalls):
        print(f"{self.name} with {self.username} and {self.password}")
        ssh.connect(hostname=self.ip,
                    username=self.username,
                    password=self.password)

        lb_number = self.name.replace("LB", "")

        # INITIATE PRIVATE STATIC ROUTES
        if self.zone == "inside":
            priv_routes = ("sudo ip route add default via " +
                           f"{self.interfaces['gateway']} dev eth0 table " +
                           f"privs; sudo ip rule add to {zones[self.zone]} " +
                           "lookup privs;")

        elif self.zone == "outside":
            priv_routes = ("sudo ip route add default via " +
                           f"{self.interfaces['gateway']} dev eth0 table " +
                           f"int; sudo ip rule add to {zones[self.zone]} " +
                           "lookup int")

        else:
            priv_routes = ("sudo ip route add default via " +
                           f"{self.interfaces['gateway']} dev eth0 table " +
                           f"privs; sudo ip rule add to {zones[self.zone]} " +
                           "lookup privs")

        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(priv_routes)

        for line in ssh_stdout:
            print(line.strip('\n'))
        for line in ssh_stderr:
            print('ERR: ' + line.strip('\n'))

        # INITIAL NFTABLES CONFIG
        # self.init_nftables(ssh, len(firewalls))

        # firewalls = [fw for fw in firewalls if fw.up]  # --- THIS WORKS!!
        # INITIAL MARKING AND ROUTES TO ACTIVE FW
        for fw in firewalls:
            command = ""

            sftp = ssh.open_sftp()
            conf_file = sftp.open('/etc/iproute2/rt_tables')
            config = (conf_file.read()).decode()

            mark_number = fw.name.replace("FW", "")

            if not fw.up:
                fw = self.get_next_up_fw(fw, firewalls)

            number = fw.name.replace("FW", "")

            # check fw to mark
            if "20"+number not in config:
                config += f"/n20{number} fw{number}"
                ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
                    f"cd /etc/iproute2; echo '{config}' | sudo " +
                    "tee nftables.conf;")
                for line in ssh_stdout:
                    print(line.strip('\n'))
                for line in ssh_stderr:
                    print('ERR: ' + line.strip('\n'))

            if self.zone == "inside":

                command += (f"sudo ip rule add fwmark 0x{mark_number} lookup" +
                            f" fw{number};" + "sudo ip route add default via" +
                            f" {fw.interfaces_inside[lb_number]} " +
                            f"dev eth{number} table fw{number}")

            elif self.zone == "outside":
                command += (f"sudo ip rule add fwmark 0x{mark_number} lookup" +
                            f" fw{number};" + "sudo ip route add default via" +
                            f" {fw.interfaces_outside[lb_number]} " +
                            f"dev eth{number} table fw{number}")

            else:
                command += (f"sudo ip rule add fwmark 0x{mark_number} lookup" +
                            f" fw{number};" + "sudo ip route add default via" +
                            f" {fw.interfaces_dmz[lb_number]} " +
                            f"dev eth{number} table fw{number}")

            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)
            # "cd /etc/iptables/ ; sudo sh ./regras.sh")

            for line in ssh_stdout:
                print(line.strip('\n'))
            for line in ssh_stderr:
                print('ERR: ' + line.strip('\n'))

    def init_nftables(self, ssh, firewall_nr):
        if self.zone == "inside":
            x = open("nftables_inside.conf")
            s = x.read().replace("XXX", str(firewall_nr))

            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
                "cd /etc/ ;" +
                f"echo '{s}' | sudo tee nftables.conf ; " +
                "sudo nft flush ruleset ; sudo nft -f nftables.conf")

            for line in ssh_stdout:
                print(line.strip('\n'))
            for line in ssh_stderr:
                print('ERR: ' + line.strip('\n'))

        else:
            x = open("nftables_outside.conf")
            s = x.read().replace("XXX", str(firewall_nr))

            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
                "cd /etc/ ;" +
                f"echo '{s}' | sudo tee nftables.conf ; " +
                "sudo nft flush ruleset ; sudo nft -f nftables.conf")

            for line in ssh_stdout:
                print(line.strip('\n'))
            for line in ssh_stderr:
                print('ERR: ' + line.strip('\n'))

    # TODO Fix, it's deleting the files

    # def config_nftables(self, old_number, new_number, ssh):
    #     ssh.connect(hostname=self.ip,
    #                 username=self.username,
    #                 password=self.password)
    #     sftp = ssh.open_sftp()
    #     conf_file = sftp.open('/etc/nftables.conf')
    #     config = (conf_file.read()).decode()
    #     print(old_number)
    #     print(new_number)

    #     if new_number != 0:
    #         new_config = config.replace(
    #             f'mod {old_number}', f'mod {new_number}')
    #         ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
    #             "cd /etc/ ;" +
    #             f"echo '{new_config}' | sudo tee nftables.conf ; " +
    #             "sudo nft flush ruleset ; sudo nft -f nftables.conf")
    #         for line in ssh_stdout:
    #             print(line.strip('\n'))
    #         for line in ssh_stderr:
    #             print('ERR: ' + line.strip('\n'))
    #     else:
    #         print("!NENHUMA FIREWALL ATIVA!")

    def get_next_up_fw(self, fw, firewalls):

        arranjed_firewalls = firewalls[firewalls.index(
            fw):]+firewalls[:firewalls.index(fw)]

        for fws in arranjed_firewalls:
            if fws.check_connection():
                return fws

    def exec_delayed_configs(self, ssh, firewalls):

        ssh.connect(hostname=self.ip,
                    username=self.username,
                    password=self.password)

        self.config(ssh, firewalls)

        for delayed_key in self.delayed_configs.keys():
            config = self.delayed_configs.get(delayed_key)
            if "nftables" in config[0]:
                self.config_nftables(config[1], config[2], ssh)

    def flush_routes(self, ssh):
        ssh.connect(hostname=self.ip,
                    username=self.username,
                    password=self.password)
        self.up = False
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
            "sudo ip rule flush fwmark 0x1; sudo ip rule flush fwmark 0x2; " +
            "sudo ip rule " +
            "flush to 1.1.1.0/24; sudo ip rule flush to 2.2.2.0/24")
        for line in ssh_stdout:
            print(line.strip('\n'))
        for line in ssh_stderr:
            print('ERR: ' + line.strip('\n'))

    def reader(self, input_dict, *kwargs):
        for key in input_dict:
            try:
                setattr(self, key, input_dict[key])
            except:
                print("no such attribute,please consider add it at init")
                continue

    def check_all_connections(self, ssh, firewalls):
        result = dict()
        result["Managment"] = self.check_connection()
        for fw in firewalls:
            result[f"{fw.name} Connection"] = True

        lb_number = self.name.replace("LB", "")

        ssh.connect(hostname=self.ip,
                    username=self.username,
                    password=self.password)

        for fw in firewalls:

            fw_number = fw.name.replace("FW", "")

            if self.zone == "inside":
                ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
                    f"ping -c 1 {fw.interfaces_inside[lb_number]}")
            elif self.zone == "outside":
                ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
                    f"ping -c 1 {fw.interfaces_outside[lb_number]}")
            else:
                ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
                    f"ping -c 1 {fw.interfaces_dmz[lb_number]}")

            for line in ssh_stderr:
                print('ERR: ' + line.strip('\n') +
                      "\nCan't connect to " + fw_number)

            for line in ssh_stdout:
                if "Unreachable" in line.strip('\n'):
                    if fw_number in fw.name:
                        result[f"{fw.name} Connection"] = False
                    # if fw_number == "1":
                    #     result["FW1 Connection"] = False
                    # else:
                    #     result["FW2 Connection"] = False

        return result

    def get_cpu_busy(self, ssh):
        stats = dict()

        ssh.connect(hostname=self.ip,
                    username=self.username,
                    password=self.password)

        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
            "iostat -c | sed -n 4p | awk '{print $6}'")

        for line in ssh_stderr:
            print('ERR' + line.strip('\n') + "\nCan't connect to " + self.name)
        # return 100-float(ssh_stdout.strip('\n'))
        for line in ssh_stdout:
            retorno = str(line.strip('\n'))

        stats["CPU Utilization: "] = str(round(100-float(retorno), 2))+"%"
        cpu = round(100-float(retorno), 2)
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
            "free | sed -n 2p | awk '{print $4}'")

        for line in ssh_stderr:
            print('ERR' + line.strip('\n') + "\nCan't connect to " + self.name)
        # return 100-float(ssh_stdout.strip('\n'))
        for line in ssh_stdout:
            retorno = str(line.strip('\n'))

        stats["Available RAM: "] = str(
            int(re.search(r'\d+', retorno).group()) * (10 ** (-6)))+" GB"
        ram = (re.search(r'\d+', retorno).group()) * (10 ** (-6))

        if cpu > 85:
            return "CPU overload"

        if ram < 0.5:
            return "Not enough RAM"

        return stats

    def as_dict(self):
        return f"Load Balancer {self.name} at {self.ip}"
