# Introduction to PMEM-CSI for Kubernetes

**Note: This is Alpha code and not production ready.**

Intel PMEM-CSI is a storage driver for container orchestrators like
Kubernetes. It makes local persistent memory
([PMEM](https://pmem.io/)) available as a filesystem volume to
container applications. It can currently utilize non-volatile memory
devices that can be controlled via the [libndctl utility
library](https://github.com/pmem/ndctl). In this readme, we use
*persistent memory* to refer to a non-volatile dual in-line memory
module (NVDIMM).

The [v0.6.0 release](https://github.com/intel/pmem-csi/releases/tag/v0.6.0)
is the latest feature release and is [regularly updated](./DEVELOPMENT.md#release-management) with newer base images
and bug fixes. Older versions are no longer supported.

The PMEM-CSI driver follows the [CSI
specification](https://github.com/container-storage-interface/spec) by
listening for API requests and provisioning volumes accordingly.

- [PMEM-CSI for Kubernetes](#pmem-csi-for-kubernetes)
    - [Supported Kubernetes versions](#supported-kubernetes-versions)
    - [Design and architecture](design.md)
    - [Instructions for Admins and Users](install.md)
       - [Prerequisites](install.md#prerequisites)
       - [Installation and setup](install.md#installation-and-setup)
       - [Filing issues and contributing](install.md#filing-issues-and-contributing)
    - [Develop and contribute](DEVELOPMENT.md)
    - [Automated testing](autotest.md)
    - [Application examples](examples)

## Supported Kubernetes versions

PMEM-CSI implements the CSI specification version 1.x, which is only
supported by Kubernetes versions >= v1.13. The following table
summarizes the status of support for PMEM-CSI on different Kubernetes
versions:

| Kubernetes version | Required alpha feature gates   | Support status
|--------------------|--------------------------------|----------------
| 1.13               | CSINodeInfo, CSIDriverRegistry,<br>CSIBlockVolume</br>| unsupported <sup>1</sup>
| 1.14               |                                |
| 1.15               | CSIInlineVolume                |
| 1.16               |                                |

<sup>1</sup> Several relevant features are only available in alpha
quality in Kubernetes 1.13 and the combination of skip attach and
block volumes is completely broken, with [the
fix](https://github.com/kubernetes/kubernetes/pull/79920) only being
available in later versions. The external-provisioner v1.0.1 for
Kubernetes 1.13 lacks the `--strict-topology` flag and therefore late
binding is unreliable. It's also a release that is not supported
officially by upstream anymore.
