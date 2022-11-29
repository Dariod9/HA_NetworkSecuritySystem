# @Author: Dário Matos
# @Date:   2022-08-17 19:36:11
# @Email:  dario.matos@ua.pt
# @Copyright: Insituto de Telecomunicações - Aveiro, Aveiro, Portugal
# @Last Modified by:   Dário Matos
# @Last Modified time: 2022-10-22 18:25:09

import os
import re


class Firewall:
    def __init__(self, name=None, ip=None, username=None, password=None):
        self.name = name
        self.ip = ip
        self.username = username
        self.password = password
        self.interfaces_inside = dict()
        self.interfaces_outside = dict()
        self.interfaces_dmz = dict()
        self.delayed_configs = dict()
        self.started = False
        self.up = False
        self.rules = []

    def check_connection(self):

        response = os.system("ping -c 1 " + self.ip + " >> t.txt")
        if response == 0:
            self.up = True
        else:
            self.up = False

        return self.up

    def config(self, ssh, zones, load_balancers):
        print(f"{self.name} with {self.username} and {self.password}")
        ssh.connect(hostname=self.ip,
                    username=self.username,
                    password=self.password)

        fw_number = self.name.replace("FW", "")

        load_balancers = [lb for lb in load_balancers if lb.up]
        inside_lbs = [lb for lb in load_balancers if lb.zone == "inside"]
        outside_lbs = [lb for lb in load_balancers if lb.zone == "outside"]
        dmz_lbs = [lb for lb in load_balancers if lb.zone == "dmz"]

        if inside_lbs:

            command = f"sudo ip route add {zones['inside']} "

            for lb in inside_lbs:

                lb_number = lb.name.replace("LB", "")

                command += (
                    f"\\nexthop via {lb.interfaces[fw_number]} dev eth" +
                    f"{lb_number} weight 1 ")

            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)

            for line in ssh_stdout:
                print(line.strip('\n'))
            for line in ssh_stderr:
                print('ERR: ' + line.strip('\n'))

        if outside_lbs:

            command = "sudo ip route add default "

            for lb in outside_lbs:

                lb_number = lb.name.replace("LB", "")

                command += (
                    f"\\nexthop via {lb.interfaces[fw_number]} dev eth" +
                    f"{lb_number} weight 1 ")

            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)

            for line in ssh_stdout:
                print(line.strip('\n'))
            for line in ssh_stderr:
                print('ERR: ' + line.strip('\n'))

        if dmz_lbs:

            command = f"sudo ip route add {zones['dmz']} "

            for lb in dmz_lbs:

                lb_number = lb.name.replace("LB", "")

                command += (
                    f"\\nexthop via {lb.interfaces[fw_number]} dev eth" +
                    f"{lb_number} weight 1 ")

            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)

            for line in ssh_stdout:
                print(line.strip('\n'))
            for line in ssh_stderr:
                print('ERR: ' + line.strip('\n'))
        # ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
        #     "cd /etc/iptables/ ; sudo sh ./regras.sh")

        # for line in ssh_stdout:
        #     print(line.strip('\n'))
        # for line in ssh_stderr:
        #     print('ERR: ' + line.strip('\n'))

        ssh.close()

    # TODO Modificar para apagar linha completa ou criar linha nova

    def config_routes(self, lb, add, ssh):
        ssh.connect(hostname=self.ip,
                    username=self.username,
                    password=self.password)
        sftp = ssh.open_sftp()
        conf_file = sftp.open('/etc/iptables/regras.sh')
        config = (conf_file.read()).decode()

        routes = config.split("\n")

        lb_number = lb.name.replace("LB", "")

        new_config = ""

        if len(routes) > 1:

            if not add:
                if lb.zone == "inside":
                    addresses = routes[0].split("nexthop")

                    # Se só tiver um next hop, para tirar, é apagar a linha
                    if len(addresses) == 2:
                        new_addresses = ""
                    else:
                        new_addresses = addresses[0]

                        for address in addresses[1:]:
                            if f"eth{lb_number}" not in address:
                                new_addresses += "nexthop"+address

                        new_addresses += "\n"+routes[1]

                elif lb.zone == "outside":
                    addresses = routes[1].split("nexthop")

                    # Se só tiver um next hop, para tirar, é apagar a linha
                    if len(addresses) == 2:
                        new_addresses = ""
                    else:
                        new_addresses = routes[0]+"\n"+addresses[0]

                        for address in addresses[1:]:
                            if f"eth{lb_number}" not in address:
                                new_addresses += "nexthop"+address

                new_config = new_addresses

            else:
                # Ir buscar o ip do load balance a mudar
                nexthop_to_add = lb.interfaces[self.name.replace("FW", "")]

                if lb.zone == "inside" and f"eth{lb_number}" not in routes[0]:

                    addresses = routes[0].replace(
                        "\n", "") + f" '\'nexthop via {nexthop_to_add}" + \
                        f" dev eth{lb_number} weight 1\n"

                elif lb.zone == "outside" and f"eth{lb_number}" \
                        not in routes[1]:

                    addresses = routes[1].replace(
                        "\n", "") + f" '\'nexthop via {nexthop_to_add}" + \
                        f" dev eth{lb_number} weight 1\n"

                new_config = addresses

            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
                "cd /etc/iptables ;" +
                f"echo '{new_config}' | sudo tee regras.sh>/dev/null ; ")
            for line in ssh_stdout:
                print(line.strip('\n'))
            for line in ssh_stderr:
                print('ERR: ' + line.strip('\n'))

    # def exec_delayed_configs(self, ssh):

    #     ssh.connect(hostname=self.ip,
    #                 username=self.username,
    #                 password=self.password)

    #     for delayed_key in self.delayed_configs.keys():
    #         config = self.delayed_configs.get(delayed_key)
    #         if "nftables" in config[0]:
    #             self.config_nftables(config[1], config[2], ssh)
    #         elif "routes" in config[0]:
    #             self.config_routes(config[1], ssh)

    def reboot(self, ssh):
        ssh.connect(hostname=self.ip,
                    username=self.username,
                    password=self.password)
        self.up = False
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("sudo reboot;")
        for line in ssh_stdout:
            print(line.strip('\n'))
        for line in ssh_stderr:
            print('ERR: ' + line.strip('\n'))

    def flush_routes(self, ssh):
        ssh.connect(hostname=self.ip,
                    username=self.username,
                    password=self.password)
        self.up = False
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
            "sudo ip route flush 0.0.0.0/6; sudo ip route flush default")
        for line in ssh_stdout:
            print(line.strip('\n'))
        for line in ssh_stderr:
            print('ERR: ' + line.strip('\n'))

    def apply_rules(self, ssh):
        ssh.connect(hostname=self.ip,
                    username=self.username,
                    password=self.password)

        for rule in self.rules:

            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(rule)
            for line in ssh_stdout:
                print(line.strip('\n'))
            for line in ssh_stderr:
                print('ERR: ' + line.strip('\n'))

    # def backup_rules(self, ssh):
    #     ssh.connect(hostname=self.ip,
    #                 username=self.username,
    #                 password=self.password)

    #     ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
    #         "cd /etc/ ;" +
    #         "sudo nft list ruleset")
    #     for line in ssh_stdout:
    #         print(line.strip('\n'))
    #         self.rules += line.strip('\n')
    #     for line in ssh_stderr:
    #         print('ERR: ' + line.strip('\n'))

    #     print(self.rules)
        # sftp = ssh.open_sftp()
        # conf_file = sftp.open('/etc/nftables.conf')
        # config = (conf_file.read()).decode()

    def init_nftables(self, ssh):
        ssh.connect(hostname=self.ip,
                    username=self.username,
                    password=self.password)

        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
            "sudo nft flush ruleset; sudo nft -f /etc/nftables2.conf")
        for line in ssh_stdout:
            print(line.strip('\n'))
        for line in ssh_stderr:
            print('ERR: ' + line.strip('\n'))

    def block(self, ssh, ip, zone_ip, port):
        ssh.connect(hostname=self.ip,
                    username=self.username,
                    password=self.password)
        self.up = False

        port_config = "tcp sport " + str(port) if port != 0 else ""

        zone_to_allow = ""

        if zone_ip:
            zone_to_allow = f"ip daddr {zone_ip}"

        command = (f"sudo nft insert rule ip block prerouting ip saddr {ip} " +
                   f"{port_config} {zone_to_allow} counter reject; " +
                   "sudo nft insert rule bridge block prerouting ip saddr " +
                   f"{ip} {port_config} {zone_to_allow} counter reject;")

        self.rules.append(command)

        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)
        for line in ssh_stdout:
            print(line.strip('\n'))
        for line in ssh_stderr:
            print('ERR: ' + line.strip('\n'))

        # self.backup_rules(ssh)

    def allow(self, ssh, ip, zone_ip, port):
        ssh.connect(hostname=self.ip,
                    username=self.username,
                    password=self.password)
        self.up = False

        port_config = "tcp sport " + str(port) if port != 0 else ""

        zone_to_allow = ""

        if zone_ip:
            zone_to_allow = f"ip daddr {zone_ip}"

        command = (f"sudo nft insert rule ip allow prerouting ip saddr {ip} " +
                   f"{port_config} {zone_to_allow} counter accept; " +
                   "sudo nft insert rule bridge allow prerouting ip saddr " +
                   f"{ip} {port_config} {zone_to_allow} counter accept;")

        self.rules.append(command)

        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)
        for line in ssh_stdout:
            print(line.strip('\n'))
        for line in ssh_stderr:
            print('ERR: ' + line.strip('\n'))

        # self.backup_rules(ssh)

    def check_all_connections(self, ssh, load_balancers):
        result = dict()
        result["Managment"] = self.check_connection()
        # result["LB1 Connection"] = True
        # result["LB2 Connection"] = True
        # result["LB3 Connection"] = True
        # result["LB4 Connection"] = True
        for lb in load_balancers:
            result[f"{lb.name} Connection"] = True

        fw_number = self.name.replace("FW", "")

        ssh.connect(hostname=self.ip,
                    username=self.username,
                    password=self.password)

        for lb in load_balancers:

            lb_number = lb.name.replace("LB", "")

            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
                f"ping -c 1 {lb.interfaces[fw_number]}")

            for line in ssh_stderr:
                print('ERR: ' + line.strip('\n') +
                      "\nCan't connect to " + lb.name)

            for line in ssh_stdout:
                if "Unreachable" in line.strip('\n'):
                    print(lb_number)

                    for lb in load_balancers:
                        if lb_number in lb.name:
                            result[f"{lb.name} Connection"] = False

                    #     result["LB1 Connection"] = False
                    # elif lb_number == "2":
                    #     result["LB2 Connection"] = False
                    # elif lb_number == "3":
                    #     result["LB3 Connection"] = False
                    # else:
                    #     result["LB4 Connection"] = False

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

        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
            "free | sed -n 2p | awk '{print $4}'")

        for line in ssh_stderr:
            print('ERR' + line.strip('\n') + "\nCan't connect to " + self.name)
        # return 100-float(ssh_stdout.strip('\n'))
        for line in ssh_stdout:
            retorno = str(line.strip('\n'))

        stats["Available RAM: "] = str(
            int(re.search(r'\d+', retorno).group()) * (10 ** (-6)))+" GB"

        return stats

    def reader(self, input_dict, *kwargs):
        for key in input_dict:
            try:
                setattr(self, key, input_dict[key])
            except:
                print("no such attribute, please consider add it at init")
                continue

    def as_dict(self):
        return f"Firewall {self.name} at {self.ip}"
