setup-kvm-vm
============

Change assigned resources to KVM virtual machines

Requirements
------------

The only requirement are libvirt's bindings:
```
sudo apt-get install python-libvirt
```
or
```
sudo pip install libvirt-python
```

How to use it
-------------

These are the current parameters:

```
$ python ./setup_kvm_domain.py -h
usage: setup_kvm_domain.py [-h] [-r] [-v] [-d] [-m MEMORY] [-c CPU]
		    [-q QUEUES] [-p PIN]
			   vm

Change the "fixed" resources assigned to a VM (cpu, mem, vqueues, cpu pinning)
in an non-interactive manner, using transient domains

positional arguments:
  vm                    VM name

optional arguments:
  -h, --help            show this help message and exit
  -r, --restart         Restart VM to apply changes.
  -v, --verbose         Show debug messages
  -d, --dump            Dump the new domain XML but do not apply it.
  -m MEMORY, --memory MEMORY
			Memory in MB.
  -c CPU, --cpu CPU     vCPU number.
  -q QUEUES, --queues QUEUES
			virtqueues number.
  -p PIN, --pin PIN     CPU pinning in [0-9]-[0-9] format (e.g. "1-8"). The
			second value must be higher than the first one, but
			lower than the amount of cores in the physical host
			(check /proc/cpuinfo)
```

All parameters can be changed at the same time, so feel free to do so. Some considerations:
- The '-d|--dump' option will output the new domain XML but won't apply it.
- The last thing done by this script is restart the VM.
- Even if setup_kvm_domain.py is run without parameters, the VM will be recreated using the old/original XML.
- You can find a backup of the original domain XML in ./backups/${VM_NAME}_${EPOCH}.xml (The directory is hardcoded in the header)

Example output
--------------
```
$ python ./setup_kvm_domain.py -c 2 -q 4 -m 2048 -p 1-8 -v testVM
27/05/2016 14:08:28 DEBUG: - VM testVM (id 63) current status
27/05/2016 14:08:28 DEBUG:   State = 1
27/05/2016 14:08:28 DEBUG:   Max Memory = 4194304
27/05/2016 14:08:28 DEBUG:   Memory used = 4194304
27/05/2016 14:08:28 DEBUG:   Number of virt CPUs = 1
27/05/2016 14:08:28 DEBUG:   CPU Time (in ns) = 9190000000
27/05/2016 14:08:28 DEBUG:   CPU pinning: 1-8
27/05/2016 14:08:28 DEBUG:   Vqueues: 2
27/05/2016 14:08:28 INFO: - Saved testVM current XML to ./backup//testVM_1464358108.7
27/05/2016 14:08:28 DEBUG: - Setting vCPU to 2
27/05/2016 14:08:28 DEBUG: - Setting memory and currentMemory to 2097152
27/05/2016 14:08:28 DEBUG: - Setting Vqueues to 4
27/05/2016 14:08:28 DEBUG: - Setting pinning to 1-8
27/05/2016 14:08:28 INFO: - Stopping VM
27/05/2016 14:08:28 INFO: - Creating VM
```
