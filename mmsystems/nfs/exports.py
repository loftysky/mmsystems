#!usr/bin/env python

header = '''
# /etc/exports: the access control list for filesystems which may be exported
#       to NFS clients.  See exports(5).
#
# Example for NFSv2 and NFSv3:
# /srv/homes       hostname1(rw,sync,no_subtree_check) hostname2(ro,sync,no_subtree_check)
#
# Example for NFSv4:
# /srv/nfs4        gss/krb5i(rw,sync,fsid=0,crossmnt,no_subtree_check)
# /srv/nfs4/homes  gss/krb5i(rw,sync,no_subtree_check)
'''.lstrip()

import argparse
import os
import shutil
import sys

parser = argparse.ArgumentParser()
parser.add_argument('-o', '--output')
args = parser.parse_args()


if args.output:
    if os.path.exists(args.output):
        shutil.copy(args.output, args.output + '.bak')
    out = open(args.output + '.in-progress', 'w')
else:
    out = sys.stdout


out.write(header + '\n')


# For NFSv4.
out.write('/export 10.10.3.0/22(rw,fsid=0,insecure,crossmnt,no_subtree_check,async)\n')


networks = {
    'main': '10.10.0.0/16',
    'untrusted': '10.20.0.0/16',
    'ipsec': '10.90.0.0/24',
    'openvpn': '10.90.1.0/24',
}
all_networks     = tuple(sorted(networks.values()))
authned_networks = ('main', 'ipsec', 'openvpn')
main_networks    = ('main', 'ipsec')

volumes = [

        dict(name='scratch', networks=all_networks),
        dict(name='ubuntu-16.04', networks=all_networks),
        
        dict(name='CGartifacts', networks=authned_networks),
        dict(name='CGroot', networks=authned_networks),
        dict(name='EDsource', networks=authned_networks),
        #dict(name='ITroot', networks=authned_networks),

        dict(name='AnimationProjects', networks=main_networks),
        dict(name='BAroot', networks=main_networks),
        dict(name='digital_media', networks=main_networks),
        dict(name='GMroot', networks=main_networks),
        dict(name='MKroot', networks=main_networks),
        dict(name='PD01', networks=main_networks),
        #dict(name='VCroot', networks=main_networks),

]


for volume in volumes:
    out.write('/export/{name}'.format(**volume))
    for network in volume['networks']:
        network = networks.get(network, network)
        out.write(' \\\n\t{}(rw,nohide,insecure,no_subtree_check,async,no_root_squash)'.format(network))    
    out.write('\n')


if args.output:
    out.close()
    shutil.move(args.output + '.in-progress', args.output)

