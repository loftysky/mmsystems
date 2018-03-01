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
import socket

parser = argparse.ArgumentParser()
parser.add_argument('-o', '--output', default='/etc/exports')
parser.add_argument('-v', '--verbose', action='store_true')
parser.add_argument('-n', '--dry-run', action='store_true')

args = parser.parse_args()



if args.output and not args.dry_run:
    if os.path.exists(args.output):
        shutil.copy(args.output, args.output + '.bak')
    out = open(args.output + '.in-progress', 'w')
else:
    out = None


def write(x):
    if args.verbose:
        print x,
    if out is not None:
        out.write(x)

write(header + '\n')


# For NFSv4.
write('/export 10.10.3.0/22(rw,fsid=0,insecure,crossmnt,no_subtree_check,async)\n')


networks = {
    'main': '10.10.0.0/16',
    'untrusted': '10.20.0.0/16',
    'ipsec': '10.90.0.0/24',
    'openvpn': '10.90.1.0/24',
}
all_networks     = tuple(sorted(networks.values()))
networks.update(
    supes='10.10.5.0/24',
    admin_workstations='10.10.3.44', # Mike.
)

authned_networks = ('main', 'ipsec', 'openvpn')
main_networks    = ('main', 'ipsec')


hostname = socket.gethostname()

if hostname == 'nx01.mm':

    volumes = [

        dict(name='scratch', networks=all_networks),
        dict(name='ubuntu-16.04', networks=all_networks),
        
        dict(name='CGartifacts', networks=authned_networks),
        dict(name='CGroot', networks=authned_networks),
        dict(name='EDsource', networks=authned_networks),
        #dict(name='ITroot', networks=authned_networks),

        dict(name='BAroot', networks=main_networks),
        dict(name='digital_media', networks=main_networks),
        dict(name='GMroot', networks=main_networks),
        dict(name='MKroot', networks=main_networks),
        dict(name='svn', networks=main_networks),

    ]

elif hostname == 'nx02.mm':

    volumes = [
        
        dict(name='TerraBlock.bak', networks=['main']),
        dict(name='BBQ-backup', networks=['main']),

        #dict(name='archive', networks=['main']),
        
        dict(name='securitycams', networks=['supes', 'admin_workstations']),

        dict(name='home', networks=authned_networks),
        dict(name='masters', networks=authned_networks),
        
        dict(name='MM02b', networks=authned_networks),
        dict(name='EditOnline', networks=authned_networks),
    ]

else:
    print 'Unknown host:', hostname
    exit(1)

for volume in volumes:
    write('/export/{name}'.format(**volume))
    for network in volume['networks']:
        network = networks.get(network, network)
        write(' \\\n\t{}(rw,nohide,insecure,no_subtree_check,async,no_root_squash)'.format(network))    
    write('\n')


if out is not None:
    out.close()
    shutil.move(args.output + '.in-progress', args.output)

