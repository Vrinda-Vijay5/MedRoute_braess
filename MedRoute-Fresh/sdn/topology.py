"""Six-host MedRoute diamond with TCLink shaping support.

Run with ``sudo mn --custom sdn/topology.py --topo medroute --controller remote``.
Hosts attach to S1 and S4. Switch DPIDs and the h1/h2 route ports are stable
because ``sdn/routes.json`` and the controller depend on them. The S2-S3 link is
the optional shortcut.
"""
from mininet.link import TCLink
from mininet.topo import Topo


class MedRouteTopo(Topo):
    PROFILES = {
        "balanced_diamond": {"primary_bw": 100, "alternate_bw": 100,
                              "primary_delay": "1ms", "alternate_delay": "1ms"},
        "asymmetric_diamond": {"primary_bw": 100, "alternate_bw": 40,
                                "primary_delay": "2ms", "alternate_delay": "5ms"},
        "low_capacity_diamond": {"primary_bw": 25, "alternate_bw": 25,
                                  "primary_delay": "3ms", "alternate_delay": "3ms"},
    }

    def build(self, shortcut=True, profile="balanced_diamond"):
        if profile not in self.PROFILES:
            raise ValueError("unknown topology profile: {}".format(profile))
        conditions = self.PROFILES[profile]
        for index in range(1, 7):
            ip = "10.0.0.{}/24".format(index)
            host = self.addHost("h{}".format(index), ip=ip)

        opts = {"protocols": "OpenFlow13", "failMode": "secure"}
        s1 = self.addSwitch("s1", dpid="0000000000000001", **opts)
        s2 = self.addSwitch("s2", dpid="0000000000000002", **opts)
        s3 = self.addSwitch("s3", dpid="0000000000000003", **opts)
        s4 = self.addSwitch("s4", dpid="0000000000000004", **opts)

        # Keep h1 and h2 on their existing route ports for routes.json.
        # The four additional hosts attach at S1 and S4 without changing those ports.
        self.addLink("h1", s1, port2=1, cls=TCLink,
                     bw=100, delay="1ms", max_queue_size=1000)
        self.addLink("h2", s4, port2=3, cls=TCLink,
                     bw=100, delay="1ms", max_queue_size=1000)
        self.addLink("h3", s1, port2=6, cls=TCLink,
                     bw=100, delay="1ms", max_queue_size=1000)
        self.addLink("h4", s1, port2=7, cls=TCLink,
                     bw=100, delay="1ms", max_queue_size=1000)
        self.addLink("h5", s4, port2=4, cls=TCLink,
                     bw=100, delay="1ms", max_queue_size=1000)
        self.addLink("h6", s4, port2=5, cls=TCLink,
                     bw=100, delay="1ms", max_queue_size=1000)

        self.addLink(s1, s2, port1=2, port2=1, cls=TCLink,
                     bw=conditions["primary_bw"], delay=conditions["primary_delay"], max_queue_size=1000)
        self.addLink(s1, s3, port1=3, port2=1, cls=TCLink,
                     bw=conditions["alternate_bw"], delay=conditions["alternate_delay"], max_queue_size=1000)
        self.addLink(s2, s4, port1=2, port2=1, cls=TCLink,
                     bw=conditions["primary_bw"], delay=conditions["primary_delay"], max_queue_size=1000)
        self.addLink(s3, s4, port1=2, port2=2, cls=TCLink,
                     bw=conditions["alternate_bw"], delay=conditions["alternate_delay"], max_queue_size=1000)
        if shortcut:
            self.addLink(s2, s3, port1=3, port2=3, cls=TCLink,
                         bw=min(conditions["primary_bw"], conditions["alternate_bw"]),
                         delay="1ms", max_queue_size=1000)


topos = {"medroute": lambda: MedRouteTopo()}
