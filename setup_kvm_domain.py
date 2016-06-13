import libvirt
import yaml
import time
import sys
import os
import argparse
import logging
import re
import multiprocessing
from xml.etree import ElementTree as et


BACKUP_DIR = "./backup/"


logger = logging.getLogger('setup_vm')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
fmt = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%d/%m/%Y %T')
ch.setFormatter(fmt)
logger.addHandler(ch)


def pinning_arg(arg):
    cores = multiprocessing.cpu_count()
    try:
        match = re.match("^([0-9][0-9]?)-([1-9][0-9]?)$", arg).group(0)
        test = re.findall(r'\d+', match)
        if int(test[0]) >= int(test[1]):
            raise
        elif int(test[1]) >= int(cores):
            raise
        else:
            return match
    except:
        raise argparse.ArgumentTypeError("'%s' does not match required format" % arg)


def read_args():
    parser = argparse.ArgumentParser(
            description='Change the "fixed" resources assigned to a VM (cpu, mem, vqueues, cpu pinning) in an non-interactive manner, using transient domains')
    subparsers = parser.add_subparsers(help='Input type: cmd or (config) file.')

    # Read from file
    file_parser = subparsers.add_parser('file', help='Config file')
    file_parser.add_argument('-f', '--file', type=str, help='Config file to read from', required=True)
    file_parser.add_argument('-o', '--option', type=int, choices=range(1,12), help='Option defined in the config file (e.g. Q8)', required=True)
    file_parser.add_argument('-r', '--restart', help='Restart VM to apply changes.', action="store_true")
    file_parser.add_argument('-v', '--verbose', help='Show debug messages', action="store_true")
    file_parser.add_argument('-d', '--dump', help='Dump the new domain XML but do not apply it.', action="store_true")
    file_parser.add_argument('vm', type=str, help='VM name')

    # Read from cmdline
    cmd_parser = subparsers.add_parser('cmd', help='Oneline config')
    cmd_parser.add_argument('-r', '--restart', help='Restart VM to apply changes.', action="store_true")
    cmd_parser.add_argument('-v', '--verbose', help='Show debug messages', action="store_true")
    cmd_parser.add_argument('-d', '--dump', help='Dump the new domain XML but do not apply it.', action="store_true")
    cmd_parser.add_argument('-m', '--memory', type=int,  help='Memory in MB.')
    cmd_parser.add_argument('-c', '--cpu', type=int,  help='vCPU number.')
    cmd_parser.add_argument('-q', '--queues', type=int,  help='virtqueues number.')
    cmd_parser.add_argument('-p', '--pin', type=pinning_arg, help='CPU pinning in [0-9]-[0-9] format (e.g. "1-8").\
                        The second value must be higher than the first one, but lower than the amount of cores in the physical host (check /proc/cpuinfo) ')
    cmd_parser.add_argument('vm', type=str, help='VM name')

    args = parser.parse_args()

    return args


def vm_status(dom):

    logger.debug("- VM %s (id %d) current status" % (dom.name(), dom.ID()))
    infos = dom.info()
    logger.debug('  State = %d' % infos[0])
    logger.debug('  Max Memory = %d' % infos[1])
    logger.debug('  Memory used = %d' % infos[2])
    logger.debug('  Number of virt CPUs = %d' % infos[3])
    logger.debug('  CPU Time (in ns) = %d' % infos[4])

    raw_xml = dom.XMLDesc(0)
    tree = et.fromstring(raw_xml)
    logger.debug("  CPU pinning: %s" % tree.find('.//vcpu').attrib['cpuset'])
    driver = tree.find('.//interface/model').attrib['type']
    if driver == 'virtio':
        try:
            logger.debug("  Vqueues: %s" % tree.find('.//interface/driver').attrib['queues'])
        except:
            logger.debug("  Vqueues: 0")

    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    backup_file = BACKUP_DIR + "/" + dom.name() + '_' + str(time.time()) + '.xml'

    with open(backup_file, 'w') as f:
        f.write(raw_xml)

    logger.info("- Saved %s current XML to %s" % (dom.name(), backup_file))


def vm_edit_xml(dom, args):

    raw_xml = dom.XMLDesc(0)
    tree = et.fromstring(raw_xml)

    if args.cpu is not None:
        logger.debug("- Setting vCPU to %s" % str(args.cpu))
        tree.find('.//vcpu').text = str(args.cpu)
    if args.memory is not None:
        args.memory = int(args.memory) * 1024
        logger.debug("- Setting memory and currentMemory to %s" % str(args.memory))
        tree.find('.//memory').text = str(args.memory)
        tree.find('.//currentMemory').text = str(args.memory)
    if args.queues is not None:
        if tree.find('.//interface/model').attrib['type'] == 'virtio':
            logger.debug("- Setting Vqueues to %s" % str(args.queues))
            iface = tree.find('.//interface/driver')
            iface.set('queues', str(args.queues))
        else:
            logger.error("Cannot change the number of Vqueues because the interface model is not virtio")
            sys.exit(1)

    if args.pin is not None:
        logger.debug("- Setting pinning to %s" % str(args.pin))
        tree.find('.//vcpu').set('cpuset', str(args.pin))

    return et.tostring(tree)


def main():
    args = read_args()

    if args.verbose is True:
        logger.setLevel(logging.DEBUG)

    if args.file is not None:
        logger.debug("- Using config file: %s" % args.file)
        with open(args.file, 'r') as f:
            cfg = yaml.load(f)
            option = str(args.option)
            args.cpu = cfg[option]['cpu']
            args.memory = cfg[option]['memory']
            args.queues = cfg[option]['queues']
            args.pin = cfg[option]['pin']

    lv = libvirt.open('qemu:///system')
    if lv is None:
        logger.error('Failed to open connection to the hypervisor')
        sys.exit(1)

    try:
        dom = lv.lookupByName(args.vm)
    except:
        logger.error('Failed to find the VM')
        sys.exit(1)

    vm_status(dom)
    new_xml = vm_edit_xml(dom, args)
    if args.dump is True:
        print(new_xml)
    else:
        status = dom.info()[0]
        if status not in (libvirt.VIR_DOMAIN_SHUTDOWN, libvirt.VIR_DOMAIN_SHUTOFF):
            logger.info('- Stopping VM')
            dom.destroy()

        # Beware, we're using transient guests.
        # No dom.undefine() needed
        logger.info('- Creating VM')
        lv.createXML(new_xml, 0)

    lv.close()

if __name__ == '__main__':
    main()
